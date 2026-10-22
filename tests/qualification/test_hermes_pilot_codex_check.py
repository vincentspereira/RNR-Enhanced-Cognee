"""No live OAuth or model calls: verify bounded native completion orchestration."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS

import httpx
import pytest


@pytest.fixture
def check():
    spec = importlib.util.spec_from_file_location("pilot_codex_check",
        Path("integrations/hermes/deployment/check_pilot_codex.py").resolve())
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOKEN = "synthetic-pilot-access-token-never-a-real-account"


def credential(check):
    return {"credential_pool": {"openai-codex": [{"auth_type": "oauth", "label": "cognee-pilot-codex",
        "source": "manual:device_code", "base_url": check.BASE_URL, "access_token": TOKEN}]}}


def test_only_the_pilot_oauth_entry_is_selected(check):
    raw = credential(check)
    raw["unrelated"] = "PRIVATE_OTHER_SENTINEL"
    assert check.select_credential(json.dumps(raw).encode()) == TOKEN


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "provider", "label", "type", "source",
    "disabled", "url", "token-space", "token-short"])
def test_ambiguous_unsafe_or_general_api_credentials_are_refused(check, mutation):
    auth = credential(check)
    row = auth["credential_pool"]["openai-codex"][0]
    if mutation == "duplicate": auth["credential_pool"]["openai-codex"].append(dict(row))
    elif mutation == "missing": auth = {}
    elif mutation == "provider": auth["credential_pool"] = {"openai": [row]}
    elif mutation == "label": row["label"] = "PRIVATE_OTHER_SENTINEL"
    elif mutation == "type": row["auth_type"] = "api_key"
    elif mutation == "source": row["source"] = "device_code"
    elif mutation == "disabled": row["disabled"] = True
    elif mutation == "url": row["base_url"] = "https://api.openai.com/v1"
    elif mutation == "token-space": row["access_token"] = TOKEN + "\nPRIVATE_SENTINEL"
    else: row["access_token"] = "short"
    with pytest.raises(check.CheckError) as error:
        check.select_credential(json.dumps(auth).encode())
    assert "PRIVATE_" not in str(error.value) and TOKEN not in str(error.value)


def fixture_components(check, *, model="gpt-6.1-sol", terminal=True, text=None, finish="stop", tool_calls=None):
    def headers(kwargs, **options):
        assert options == {"access_token": TOKEN, "base_url": check.BASE_URL}
        kwargs["default_headers"] = {"originator": "hermes-agent"}
    def convert(messages, **options):
        assert messages == [{"role": "user", "content": check.PROMPT}]
        assert options == {"current_issuer_kind": "codex_backend", "current_issuer_model": check.MODEL}
        return [{"role": "user", "content": [{"type": "input_text", "text": check.PROMPT}]}]
    def preflight(payload, **options):
        assert options == {"allow_stream": True}
        assert payload["model"] == check.MODEL and payload["store"] is False and payload["stream"] is True
        assert payload["reasoning"] == {"effort": "low"}
        assert "tools" not in payload and "max_output_tokens" not in payload
        return payload
    def consume(stream, **options):
        for event in stream: options["on_event"](event)
        return NS(status="completed")
    def normalize(final, **options):
        assert options == {"issuer_kind": "codex_backend", "issuer_model": check.MODEL}
        return [text if text is not None else check.ACK], tool_calls, NS(
            prompt_tokens=25, completion_tokens=20, total_tokens=45), finish
    return (NS(apply_required_codex_headers=headers), NS(_chat_messages_to_responses_input=convert,
        _preflight_codex_api_kwargs=preflight), NS(_consume_codex_event_stream=consume),
        NS(_parse_codex_final_response=normalize))


def sdk_fixture(check, calls, *, model="gpt-6.1-sol", terminal=True, wrong_url=False, retry=False,
                body_mutation=None):
    class Stream:
        def __iter__(self):
            yield NS(type="response.created", response=NS(model=model))
            if terminal: yield NS(type="response.completed", response=NS(model=model))
        def close(self): calls.append("closed")
    class SDK:
        def __init__(self, **options):
            assert options["api_key"] == TOKEN and options["base_url"] == check.BASE_URL
            assert options["max_retries"] == 0 and options["timeout"] == 60
            assert options["default_headers"] == {"originator": "hermes-agent"}
            self.transport = options["http_client"]
            assert not self.transport._trust_env and not self.transport.follow_redirects
            self.responses = NS(create=self.create)
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def create(self, **payload):
            calls.append("request")
            if body_mutation: payload.update(body_mutation)
            url = "https://api.openai.com/v1/responses" if wrong_url else check.BASE_URL + "/responses"
            request = httpx.Request("POST", url, json=payload)
            for hook in self.transport.event_hooks["request"]: hook(request)
            if retry:
                for hook in self.transport.event_hooks["request"]: hook(request)
            return Stream()
    return SDK


def test_one_native_stream_completion_and_no_private_output(check):
    calls = []
    result = check.invoke(TOKEN, fixture_components(check), sdk_factory=sdk_fixture(check, calls))
    assert calls == ["request", "closed"]
    assert result["model_reply_validated"] and result["server_model_matches_requested"]
    assert result["tokens"]["total_tokens"] == 45
    assert TOKEN not in json.dumps(result) and check.ACK not in json.dumps(result)


@pytest.mark.parametrize("model", [None, "other-model", "gpt-6.1-solx"])
def test_requested_model_echo_cannot_substitute_for_server_model_evidence(check, model):
    with pytest.raises(check.CheckError, match="server_model_unverified"):
        check.invoke(TOKEN, fixture_components(check), sdk_factory=sdk_fixture(check, [], model=model))


@pytest.mark.parametrize("mutation", ["no-terminal", "text", "tools", "incomplete"])
def test_incomplete_or_unexpected_responses_never_qualify(check, mutation):
    components = fixture_components(check, text="PRIVATE_REPLY_SENTINEL" if mutation == "text" else None,
        tool_calls=[{"private": "PRIVATE_TOOL_SENTINEL"}] if mutation == "tools" else None,
        finish="length" if mutation == "incomplete" else "stop")
    with pytest.raises(check.CheckError) as error:
        check.invoke(TOKEN, components, sdk_factory=sdk_fixture(check, [], terminal=mutation != "no-terminal"))
    assert "PRIVATE_" not in str(error.value)


@pytest.mark.parametrize("mutation", ["wrong-url", "retry", "model", "store", "tools", "tier", "reasoning"])
def test_guard_refuses_retry_wrong_route_and_unauthorized_request_fields(check, mutation):
    bodies = {"model": {"model": "other-model"}, "store": {"store": True},
              "tools": {"tools": [{"private": "PRIVATE_SENTINEL"}]},
              "tier": {"service_tier": "ultrafast"}, "reasoning": {"reasoning": {"effort": "high"}}}
    with pytest.raises(check.CheckError) as error:
        check.invoke(TOKEN, fixture_components(check), sdk_factory=sdk_fixture(check, [],
            wrong_url=mutation == "wrong-url", retry=mutation == "retry", body_mutation=bodies.get(mutation)))
    assert "PRIVATE_" not in str(error.value)


def test_preflight_requires_explicit_selection_before_reading_auth(check, monkeypatch):
    monkeypatch.setattr(check.pwd, "getpwuid", lambda uid: NS(pw_name="hermes-runtime"))
    monkeypatch.setattr(check, "read_private", lambda *a: pytest.fail("No auth read without selection"))
    with pytest.raises(check.CheckError): check.preflight(False)


@pytest.mark.parametrize("kind,category", [("dns", "dns_error"), ("tls", "tls_certificate_error"),
    ("timeout", "timeout"), ("dependency", "dependency_missing"), ("http", "http_error"),
    ("unknown", "unclassified"), ("sdk-timeout", "timeout"), ("connection", "connection_error")])
def test_safe_error_categories_do_not_copy_exception_bodies(check, kind, category):
    errors = {"dns": check.socket.gaierror("PRIVATE_SENTINEL"),
        "tls": check.ssl.SSLCertVerificationError("PRIVATE_SENTINEL"),
        "timeout": TimeoutError("PRIVATE_SENTINEL"), "dependency": ModuleNotFoundError("PRIVATE_SENTINEL"),
        "http": RuntimeError("PRIVATE_SENTINEL"), "unknown": RuntimeError("PRIVATE_SENTINEL"),
        "sdk-timeout": httpx.ReadTimeout("PRIVATE_SENTINEL"), "connection": httpx.ConnectError("PRIVATE_SENTINEL")}
    error = errors[kind]
    if kind == "http": error.status_code = 401
    public = check.failure(error)
    assert public["category"] == category and "PRIVATE_" not in json.dumps(public)


@pytest.mark.parametrize("code,expected", [("usage_limit_reached", "usage_limit_reached"), ("PRIVATE_PROVIDER_SENTINEL", None)])
def test_only_allowlisted_provider_codes_leave_failure_report(check, code, expected):
    error = RuntimeError("PRIVATE_ERROR_SENTINEL")
    error.code = code
    report = check.failure(error)
    assert report["provider_code"] == expected and "PRIVATE_" not in json.dumps(report)


def setup_main(check, monkeypatch):
    snapshots = {"auth.json": json.dumps(credential(check)).encode(), "config.yaml": b"memory-only"}
    monkeypatch.setattr(check, "preflight", lambda approved: (1000, snapshots))
    monkeypatch.setattr(check.os, "chdir", lambda path: None)
    monkeypatch.setattr(check.logging, "disable", lambda value: None)
    monkeypatch.setattr(check, "native_components", lambda: ())
    monkeypatch.setattr(check, "read_private", lambda name, uid: snapshots[name])
    return snapshots


def test_main_reports_transport_only_not_capture_or_full_turn_qualification(check, monkeypatch, capsys):
    setup_main(check, monkeypatch)
    monkeypatch.setattr(check, "invoke", lambda *a: {"model_reply_validated": True})
    check.main(approved_test=True)
    report = json.loads(capsys.readouterr().out)
    assert report["complete"] and report["model_called"] and report["profile_settings_and_auth_unchanged"]
    assert not any(report[field] for field in ("model_defaults_changed", "human_credentials_copied",
        "memory_records_written", "full_hermes_turn_tested", "hermes_capture_qualified", "runtime_qualified"))


def test_native_failure_is_sanitized_and_original_auth_not_replaced(check, monkeypatch, capsys):
    snapshots = setup_main(check, monkeypatch)
    original = dict(snapshots)
    def fail(*a): raise RuntimeError("PRIVATE_EXCEPTION_SENTINEL")
    monkeypatch.setattr(check, "invoke", fail)
    with pytest.raises(SystemExit): check.main(approved_test=True)
    output = capsys.readouterr().out
    report = json.loads(output)
    assert not report["complete"] and report["profile_settings_and_auth_unchanged"]
    assert "PRIVATE_" not in output and TOKEN not in output and snapshots == original
