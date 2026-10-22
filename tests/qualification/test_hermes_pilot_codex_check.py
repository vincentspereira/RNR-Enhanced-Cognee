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


def test_fixture_receipt_is_private_and_never_overwritten(check, tmp_path, monkeypatch):
    monkeypatch.setattr(check, "STATE", tmp_path / "receipt.json")
    fixture = "a" * 32
    state = {"fixture": fixture, "capture_session": "cognee_capture_" + fixture}
    check.save_state(state)
    import os
    assert check.read_state(os.geteuid()) == state
    assert check.STATE.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError): check.save_state({"fixture": "b" * 32})
    assert check.read_state(os.geteuid()) == state


def test_followup_receipt_is_separate_private_and_never_replaces_original(check, tmp_path, monkeypatch):
    import os
    monkeypatch.setattr(check, "HOME", tmp_path)
    monkeypatch.setattr(check, "STATE", tmp_path / "original.json")
    old = {"fixture": "a" * 32, "capture_session": "cognee_capture_" + "a" * 32}
    new = {"fixture": "b" * 32, "capture_session": "cognee_capture_" + "b" * 32}
    check.save_state(old)
    original = check.STATE.read_bytes()
    check.save_state(new, followup=True)
    assert check.read_state(os.geteuid(), followup=True) == new
    assert check.state_path(True).stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError): check.save_state(old, followup=True)
    assert check.STATE.read_bytes() == original and check.read_state(os.geteuid()) == old
    with pytest.raises(check.CheckError): check.state_path("PRIVATE_PATH")


@pytest.mark.parametrize("interval,valid", [("thirteen", False), ("nineteen", True)])
def test_followup_record_verification_requires_the_distinct_new_interval(check, interval, valid):
    fixture = "b" * 32
    row = {"id": "synthetic-followup", "version": 1,
           "content": fixture + " " + interval + "-day review PRIVATE_CONTENT"}
    def request(method, path, body=None):
        if method == "POST":
            assert body["query"] == "Cedar qualification " + fixture and body["include_shared"] is False
            return {"results": [row]}
        return row
    client = NS(request=request)
    if valid:
        assert check.verify_saved(NS(_client=client), fixture, followup=True) == row
    else:
        with pytest.raises(check.CheckError, match="saved_fixture_content"):
            check.verify_saved(NS(_client=client), fixture, followup=True)


@pytest.mark.parametrize("mutation", ["path", "session", "extra", "public", "link"])
def test_unsafe_or_changed_fixture_receipts_are_refused(check, tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(check, "STATE", tmp_path / "receipt.json")
    state = {"fixture": "a" * 32, "capture_session": "cognee_capture_" + "a" * 32}
    if mutation == "path": state["fixture"] = "../PRIVATE_SENTINEL"
    elif mutation == "session": state["capture_session"] = "PRIVATE_SENTINEL"
    elif mutation == "extra": state["private"] = "PRIVATE_SENTINEL"
    check.save_state(state)
    if mutation == "public": check.STATE.chmod(0o644)
    elif mutation == "link":
        target = tmp_path / "original"
        check.STATE.rename(target)
        check.STATE.symlink_to(target)
    import os
    with pytest.raises((check.CheckError, OSError)) as error: check.read_state(os.geteuid())
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_scope_readiness_is_required_before_model_memory_calls(check):
    provider = NS(handle_tool_call=lambda *a: json.dumps({"ready": True, "tenant_id": "other",
        "project_id": "hermes_pilot", "subject": "hermes_pilot_runtime", "capture": "selected", "active_records": 0}))
    with pytest.raises(check.CheckError, match="pilot_memory_scope_or_credential"):
        check.memory_status(provider)


@pytest.mark.parametrize("mutation", ["empty", "duplicate", "version", "canonical-version", "unsafe-id", "content"])
def test_saved_evidence_requires_one_current_matching_record(check, mutation):
    fixture = "a" * 32
    row = {"id": "synthetic-id", "version": 1, "content": "Larch " + fixture + " thirteen-day review"}
    rows = [dict(row)]
    if mutation == "empty": rows = []
    elif mutation == "duplicate": rows.append(dict(row))
    elif mutation == "version": rows[0]["version"] = 2
    elif mutation == "canonical-version": row["version"] = 2
    elif mutation == "unsafe-id": rows[0]["id"] = "../PRIVATE_SENTINEL"
    else: row["content"] = fixture + " unrelated PRIVATE_SENTINEL"
    client = NS(request=lambda method, path, body=None: {"results": rows} if method == "POST" else row)
    with pytest.raises(check.CheckError) as error: check.verify_saved(NS(_client=client), fixture)
    assert "PRIVATE_SENTINEL" not in str(error.value)


def agent_fixture(check):
    names = ["enhanced_recall", "enhanced_remember", "enhanced_get", "enhanced_status", "terminal"]
    def factory(*args, **kwargs):
        transport = NS(follow_redirects=True, event_hooks={"request": []})
        return NS(_client=transport, max_retries=2)
    return NS(tools=[{"function": {"name": name}} for name in names], _memory_manager=object(),
              _fallback_chain=[], _fallback_activated=False, client=factory(), _create_openai_client=factory)


def test_request_scoped_and_rebuilt_clients_share_guards_without_mutating_factory_inputs(check):
    agent = agent_fixture(check)
    cached = agent._create_openai_client({}, reason="cached", shared=False)
    agent._request_client_cache = {"client": cached}
    options = {"api_key": TOKEN, "base_url": check.BASE_URL, "default_headers": {"private": "PRIVATE_HEADER"}}
    original = json.loads(json.dumps(options))
    seen = []
    factory = agent._create_openai_client
    def native_factory(kwargs, **metadata):
        seen.append(metadata)
        return factory(kwargs, **metadata)
    agent._create_openai_client = native_factory
    requests = check.restrict_agent(agent, {"enhanced_recall"})
    clients = [agent.client, cached]
    clients.extend(agent._create_openai_client(options, reason="request", shared=False) for _ in range(3))
    clients.append(agent._create_openai_client(options, reason="recovery", shared=True))
    for client in clients:
        assert client.max_retries == 0 and not client._client.follow_redirects
        body = {"model": check.MODEL, "store": False, "tools": [{"name": "enhanced_recall"}]}
        client._client.event_hooks["request"][-1](httpx.Request("POST", check.BASE_URL + "/responses", json=body))
        client._client.event_hooks["response"][-1](NS(status_code=200))
    assert requests["count"] == 6 and requests["http_statuses"] == [200] * 6
    replacement = agent._create_openai_client(options, reason="another_request", shared=False)
    with pytest.raises(check.CheckError, match="unexpected_memory_test_request"):
        replacement._client.event_hooks["request"][-1](httpx.Request("POST", check.BASE_URL + "/responses", json=body))
    assert options == original and seen[-1] == {"reason": "another_request", "shared": False}


def test_real_httpx_request_client_guard_runs_before_transport_and_has_one_global_limit(check):
    sent = []
    def respond(request):
        sent.append(request)
        return httpx.Response(200, json={"id": "synthetic-response", "object": "response", "status": "completed"})
    clients = []
    def factory(*args, **kwargs):
        client = NS(max_retries=2, _client=httpx.Client(transport=httpx.MockTransport(respond)))
        clients.append(client)
        return client
    agent = agent_fixture(check)
    agent.client = factory()
    agent._create_openai_client = factory
    counts = check.restrict_agent(agent, {"enhanced_recall"})
    payload = {"model": check.MODEL, "store": False,
               "input": "Synthetic request", "tools": [{"type": "function", "name": "enhanced_recall",
               "parameters": {"type": "object", "properties": {}}}]}
    try:
        for _ in range(6):
            request_client = agent._create_openai_client({}, reason="request", shared=False)
            request_client._client.post(check.BASE_URL + "/responses", json=payload)
        assert len(sent) == counts["count"] == 6 and counts["http_statuses"] == [200] * 6
        with pytest.raises(check.CheckError, match="unexpected_memory_test_request"):
            agent._create_openai_client({}, reason="request", shared=False)._client.post(
                check.BASE_URL + "/responses", json=payload)
        assert len(sent) == 6 and counts["guard_failure"] == "unexpected_memory_test_request"
    finally:
        for client in clients: client._client.close()


def test_concurrent_request_clients_cannot_exceed_the_shared_physical_limit(check):
    from concurrent.futures import ThreadPoolExecutor
    agent = agent_fixture(check)
    requests = check.restrict_agent(agent, {"enhanced_recall"})
    def attempt(_):
        client = agent._create_openai_client({}, reason="request", shared=False)
        body = {"model": check.MODEL, "store": False, "tools": [{"name": "enhanced_recall"}]}
        try:
            client._client.event_hooks["request"][-1](httpx.Request("POST", check.BASE_URL + "/responses", json=body))
            return True
        except check.CheckError:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(20))) == 6
    assert requests["count"] == 6


def test_reused_client_transport_does_not_get_duplicate_counting_hooks(check):
    agent = agent_fixture(check)
    client = agent.client
    agent._create_openai_client = lambda *args, **kwargs: client
    counts = check.restrict_agent(agent, {"enhanced_recall"})
    for _ in range(3):
        assert agent._create_openai_client({}, reason="reuse", shared=False) is client
    assert len(client._client.event_hooks["request"]) == len(client._client.event_hooks["response"]) == 1
    body = {"model": check.MODEL, "store": False, "tools": [{"name": "enhanced_recall"}]}
    client._client.event_hooks["request"][-1](httpx.Request("POST", check.BASE_URL + "/responses", json=body))
    assert counts["count"] == 1


def test_agent_surface_is_narrowed_without_replacing_native_handlers(check):
    agent = agent_fixture(check)
    allowed = {"enhanced_recall", "enhanced_remember"}
    requests = check.restrict_agent(agent, allowed)
    assert {t["function"]["name"] for t in agent.tools} == allowed
    assert agent.valid_tool_names == allowed and agent.client.max_retries == 0
    assert not agent.client._client.follow_redirects
    guard = agent.client._client.event_hooks["request"][-1]
    body = {"model": check.MODEL, "store": False, "tools": [{"name": name} for name in allowed]}
    for _ in range(6): guard(httpx.Request("POST", check.BASE_URL + "/responses", json=body))
    assert requests["count"] == 6
    with pytest.raises(check.CheckError): guard(httpx.Request("POST", check.BASE_URL + "/responses", json=body))
    assert requests["guard_failure"] == "unexpected_memory_test_request"
    observer = agent.client._client.event_hooks["response"][-1]
    for status in [200, 401, 429, 500, 200, 503, 403]: observer(NS(status_code=status))
    assert requests["http_statuses"] == [200, 401, 429, 500, 200, 503]


@pytest.mark.parametrize("mutation", ["other-model", "store", "tool", "tier", "url"])
def test_agent_request_guard_refuses_model_fallback_and_nonmemory_tools(check, mutation):
    agent = agent_fixture(check)
    check.restrict_agent(agent, {"enhanced_recall"})
    body = {"model": check.MODEL, "store": False, "tools": [{"name": "enhanced_recall"}]}
    if mutation == "other-model": body["model"] = "other-model"
    elif mutation == "store": body["store"] = True
    elif mutation == "tool": body["tools"] = [{"name": "terminal"}]
    elif mutation == "tier": body["service_tier"] = "ultrafast"
    url = "https://api.openai.com/v1/responses" if mutation == "url" else check.BASE_URL + "/responses"
    with pytest.raises(check.CheckError):
        agent.client._client.event_hooks["request"][-1](httpx.Request("POST", url, json=body))


def test_agent_missing_memory_or_configured_fallback_is_refused(check):
    agent = agent_fixture(check)
    agent._fallback_chain = [{"provider": "other"}]
    with pytest.raises(check.CheckError, match="unexpected_model_fallback"):
        check.restrict_agent(agent, {"enhanced_recall"})


@pytest.mark.parametrize("payload", [b"PRIVATE_BODY", b"[]", b"null", b'{"tools":[null]}'])
def test_invalid_request_payloads_have_only_fixed_guard_diagnostics(check, payload):
    agent = agent_fixture(check)
    requests = check.restrict_agent(agent, {"enhanced_recall"})
    with pytest.raises(check.CheckError) as caught:
        agent.client._client.event_hooks["request"][-1](
            httpx.Request("POST", check.BASE_URL + "/responses", content=payload))
    assert requests["count"] == 0
    assert requests["guard_failure"] in {"invalid_memory_test_payload", "unexpected_memory_test_wire_contract"}
    assert "PRIVATE_" not in str(caught.value)


@pytest.mark.parametrize("reason,exit_reason,expected_reason,expected_exit", [
    ("format_error", "all_retries_exhausted_no_response", "format_error", "all_retries_exhausted_no_response"),
    ("session_persistence_failed:PRIVATE_CAUSE", "session_persistence_failed", "session_persistence_failed", "session_persistence_failed"),
    ("timeout", "max_iterations_reached(5)", "timeout", "max_iterations_reached"),
    ("PRIVATE_REASON", "PRIVATE_EXIT", None, None),
    (["PRIVATE_REASON"], {"PRIVATE_EXIT": TOKEN}, None, None),
])
def test_native_result_diagnostics_allow_only_fixed_codes_and_bounded_metadata(
        check, reason, exit_reason, expected_reason, expected_exit):
    result = {"completed": False, "failed": True, "error": "PRIVATE_ERROR " + TOKEN,
              "final_response": "PRIVATE_RESPONSE", "messages": ["PRIVATE_HISTORY"],
              "failure_reason": reason, "turn_exit_reason": exit_reason,
              "session_id": "PRIVATE_SESSION", "model": "PRIVATE_MODEL"}
    report = check.failure(check.NativeTurnError(result,
        {"count": 6, "http_statuses": [200, 400, True, "PRIVATE_STATUS", 429, 401, 503]},
        ["enhanced_recall", "PRIVATE_TOOL", "enhanced_recall"]))
    detail = report["native_diagnostics"]
    assert detail["native_failure_reason"] == expected_reason and detail["native_exit_reason"] == expected_exit
    assert detail["http_statuses"] == [200, 400, 429, 401] and report["http_status"] == 401
    assert detail["tool_calls"] == ["enhanced_recall"] and detail["native_response_present"]
    assert "PRIVATE_" not in json.dumps(report) and TOKEN not in json.dumps(report)


@pytest.mark.parametrize("outcome", ["complete", "incomplete", "exception", "guard-rejected", "no-recall", "no-save", "wrong-order"])
def test_native_agent_runtime_overrides_and_fresh_history(check, monkeypatch, tmp_path, outcome):
    import sys
    release = tmp_path / "release"
    (release / "repo").mkdir(parents=True)
    source = release / "repo/run_agent.py"
    source.touch()
    monkeypatch.setattr(check, "RELEASE", release)
    options = {}
    class Manager:
        def add_provider(self, provider): pass
        def initialize_all(self, session, **kwargs):
            assert session == "synthetic-session" and kwargs["hermes_home"] == str(check.PROFILE)
    class Agent:
        def __init__(self, **kwargs):
            options.update(kwargs)
        def run_conversation(self, prompt, conversation_history):
            assert conversation_history == [] and prompt == "synthetic user decision"
            # Pinned Hermes tool_executor passes preview and display args positionally.
            sequence = ["enhanced_recall", "enhanced_remember"]
            if outcome == "no-recall": sequence = ["enhanced_remember"]
            if outcome == "no-save": sequence = ["enhanced_recall"]
            if outcome == "wrong-order": sequence.reverse()
            for name in sequence:
                options["tool_progress_callback"]("tool.started", name, "PRIVATE_PREVIEW", {"content": "PRIVATE_ARGUMENTS"})
            requests["count"] = 3
            if outcome == "exception": raise TimeoutError("PRIVATE_EXCEPTION_SENTINEL")
            if outcome in {"incomplete", "guard-rejected"}:
                if outcome == "guard-rejected": requests["guard_failure"] = "unexpected_memory_test_wire_contract"
                return {"completed": False, "failed": True, "error": "PRIVATE_ERROR_SENTINEL",
                        "failure_reason": "format_error", "turn_exit_reason": "PRIVATE_EXIT_SENTINEL"}
            return {"completed": True, "final_response": "PRIVATE_SYNTHETIC_REPLY"}
        def close(self): options["closed"] = True
    monkeypatch.setitem(sys.modules, "run_agent", NS(__file__=str(source), AIAgent=Agent))
    monkeypatch.setitem(sys.modules, "agent.memory_manager", NS(MemoryManager=Manager))
    requests = {"count": 0, "http_statuses": [400] if outcome == "incomplete" else []}
    monkeypatch.setattr(check, "restrict_agent", lambda agent, allowed: requests)
    if outcome in {"no-recall", "no-save", "wrong-order"}:
        with pytest.raises(check.CheckError, match="model_did_not_recall_then_select_capture"):
            check.native_memory_turn("capture", TOKEN, object(), "synthetic-session", "synthetic user decision")
        assert options["closed"]
        return
    if outcome != "complete":
        with pytest.raises(check.NativeTurnError) as caught:
            check.native_memory_turn("capture", TOKEN, object(), "synthetic-session", "synthetic user decision")
        report = check.failure(caught.value)
        assert options["closed"] and report["category"] == "native_agent_turn_incomplete"
        assert report["http_status"] == (400 if outcome == "incomplete" else None)
        assert report["native_diagnostics"]["model_requests"] == 3
        assert report["native_diagnostics"]["native_exception_category"] == ("timeout" if outcome == "exception" else None)
        assert "PRIVATE_" not in json.dumps(report) and TOKEN not in json.dumps(report)
        return
    answer, calls, count = check.native_memory_turn("capture", TOKEN, object(), "synthetic-session", "synthetic user decision")
    assert calls == ["enhanced_recall", "enhanced_remember"] and count == 3 and options["closed"]
    assert options["fallback_model"] == {} and options["credential_pool"] is None
    assert options["model"] == check.MODEL and options["provider"] == "openai-codex"
    assert options["skip_background_review"] and options["save_trajectories"] is False
    assert options["reasoning_config"] == {"enabled": True, "effort": "low"}


@pytest.mark.parametrize("stage", ["capture", "recall", "capture_followup"])
@pytest.mark.parametrize("fails", [False, True])
def test_memory_stage_orchestration_preserves_credentials_and_separates_sessions(check, monkeypatch, tmp_path, capsys, stage, fails):
    exercise_memory_stage(check, monkeypatch, tmp_path, capsys, stage, fails)


@pytest.mark.parametrize("mutation", ["existing-receipt", "scope", "old-record", "old-receipt",
                                     "provenance", "origin", "post-count", "fixture-collision", "same-id"])
def test_followup_capture_refuses_replay_or_changed_evidence(check, monkeypatch, tmp_path, capsys, mutation):
    exercise_memory_stage(check, monkeypatch, tmp_path, capsys, "capture_followup", False, mutation)


def exercise_memory_stage(check, monkeypatch, tmp_path, capsys, stage, fails, mutation=None):
    import sys
    fixture = "a" * 32
    state = {"fixture": fixture, "capture_session": "cognee_capture_" + fixture}
    snapshots = {"auth.json": json.dumps(credential(check)).encode(),
        "config.yaml": b"memory:\n  provider: enhanced_cognee\n",
        "enhanced_cognee.json": json.dumps({"base_url": "http://127.0.0.1:28080", "timeout": 10,
            "include_shared": True, "capture_policy": "selected"}).encode()}
    monkeypatch.setattr(check, "preflight", lambda approved: (1000, snapshots))
    monkeypatch.setattr(check.os, "chdir", lambda path: None)
    monkeypatch.setattr(check.os, "umask", lambda mask: None)
    monkeypatch.setattr(check.logging, "disable", lambda value: None)
    monkeypatch.setattr(check, "read_private", lambda name, uid: b"PRIVATE_MEMORY_TOKEN" if name == ".env" else snapshots[name])
    monkeypatch.setattr(check, "verify_provider", lambda: None)
    monkeypatch.setattr(check, "HOME", tmp_path)
    monkeypatch.setattr(check, "STATE", tmp_path / "fixture.json")
    followup = stage == "capture_followup"
    receipt_path = check.state_path(followup)
    release = tmp_path / "release"
    (release / "repo").mkdir(parents=True)
    monkeypatch.setattr(check, "RELEASE", release)
    source = release / "repo/mock.py"
    source.touch()
    provider = NS(initialize=lambda *a, **kw: None, shutdown=lambda: None)
    resets = []
    secrets = NS(__file__=str(source), load_env_file=lambda path: {"ENHANCED_COGNEE_ACCESS_TOKEN": "PRIVATE_MEMORY_TOKEN"},
        set_secret_scope=lambda values, **kw: "PRIVATE_BINDING", reset_secret_scope=resets.append)
    loader = NS(__file__=str(source), find_provider_dir=lambda name: check.ARTIFACT,
        load_memory_provider=lambda name: provider)
    monkeypatch.setitem(sys.modules, "agent", NS(secret_scope=secrets))
    monkeypatch.setitem(sys.modules, "agent.secret_scope", secrets)
    monkeypatch.setitem(sys.modules, "plugins", NS(memory=loader))
    def status(p):
        count = (1 + int(receipt_path.exists())) if followup else int(check.STATE.exists())
        if mutation == "scope": count = 2
        if mutation == "post-count" and receipt_path.exists(): count = 3
        return {"active_records": count}
    monkeypatch.setattr(check, "memory_status", status)
    row = {"id": "synthetic-record-id", "content": fixture + " thirteen days", "version": 1}
    old_reads = []
    def saved(p, f, **kwargs):
        if not kwargs.get("followup"):
            old_reads.append(f)
            return dict(row, version=2) if mutation == "old-record" and len(old_reads) > 1 else dict(row)
        return {"id": "synthetic-record-id" if mutation == "same-id" else "synthetic-followup-id",
                "content": f + " nineteen days", "version": 1,
                "provenance": {"session_id": "PRIVATE_SESSION" if mutation == "provenance" else "cognee_capture_" + f},
                "metadata": {"write_origin": "PRIVATE_ORIGIN" if mutation == "origin" else "hermes_selected_tool"}}
    monkeypatch.setattr(check, "verify_saved", saved)
    prompts = []
    receipts = []
    def turn(stage, token, actual_provider, session, prompt):
        if mutation in {"existing-receipt", "scope", "fixture-collision"}:
            pytest.fail("Refused followup must not call a model")
        prompts.append(prompt)
        receipts.append(receipt_path.read_bytes())
        if stage == "recall":
            assert "thirteen" not in prompt and "13" not in prompt
            assert session != state["capture_session"]
        else:
            assert "remember" not in prompt.casefold()
            assert ("nineteen-day" if followup else "thirteen-day") in prompt
            if followup: assert fixture not in prompt
        if fails:
            raise check.NativeTurnError({"completed": False, "error": "PRIVATE_ERROR"}, {"count": 1}, [])
        if mutation == "old-receipt":
            check.STATE.write_bytes(check.STATE.read_bytes())
        return "thirteen days, synthetic-record-id", ["enhanced_remember"] if stage == "capture" else ["enhanced_recall"], 3
    monkeypatch.setattr(check, "native_memory_turn", turn)
    if stage in {"recall", "capture_followup"}: check.save_state(state)
    baseline_receipt = check.STATE.read_bytes() if followup else None
    if mutation == "existing-receipt":
        check.save_state(state, followup=True)
    if mutation == "fixture-collision":
        monkeypatch.setattr(check.uuid, "uuid4", lambda: NS(hex=fixture))
    if fails or mutation:
        with pytest.raises(SystemExit): check.main_memory(stage=stage, approved_test=True)
    else:
        check.main_memory(stage=stage, approved_test=True)
    output = capsys.readouterr().out
    report = json.loads(output)
    if fails or mutation:
        expected_phase = "native_agent_turn" if fails else (
            "fixture_preparation" if mutation in {"existing-receipt", "scope", "fixture-collision"} else "saved_memory_verification")
        assert not report["complete"] and report["failure_stage"] == expected_phase
        assert report["memory_writes_may_have_occurred"] == (stage != "recall" and expected_phase != "fixture_preparation")
        assert report["profile_settings_and_credentials_unchanged"] is True
        if fails: assert report["native_diagnostics"]["native_error_present"]
        if receipts: assert receipt_path.read_bytes() == receipts[0]
    else:
        assert report["complete"] and report["native_agent_turn_passed"]
        assert report["memory_records_written"] == (stage != "recall")
        assert report["fresh_session_recall_passed"] == (stage == "recall")
        if followup:
            assert report["original_fixture_and_receipt_preserved"] and report["synthetic_active_records"] == 2
    if followup: assert check.STATE.read_bytes() == baseline_receipt
    assert not report["runtime_qualified"] and "PRIVATE_" not in output and TOKEN not in output
    assert resets == ["PRIVATE_BINDING"]


def test_invalid_memory_stage_cannot_read_credentials(check, monkeypatch, capsys):
    monkeypatch.setattr(check, "preflight", lambda *a: pytest.fail("Invalid stage must not read auth"))
    with pytest.raises(SystemExit): check.main_memory(stage="delete", approved_test=True)
    report = json.loads(capsys.readouterr().out)
    assert not report["complete"] and report["category"] == "unapproved_stage"


@pytest.mark.parametrize("mode", ["empty", "one", "duplicates", "wrong-content", "wrong-session", "wrong-origin", "corrected"])
def test_read_only_fixture_inspection_reports_evidence_without_qualifying_capture(check, mode):
    fixture = "a" * 32
    state = {"fixture": fixture, "capture_session": "cognee_capture_" + fixture}
    row = {"id": "synthetic-record-id", "version": 1,
        "content": fixture + " thirteen-day review PRIVATE_CONTENT_SENTINEL",
        "provenance": {"session_id": state["capture_session"], "private": "PRIVATE_PROVENANCE_SENTINEL"},
        "metadata": {"write_origin": "hermes_selected_tool", "private": "PRIVATE_METADATA_SENTINEL"}}
    rows = [dict(row)]
    if mode == "empty": rows = []
    elif mode == "duplicates": rows.append(dict(row))
    elif mode == "wrong-content": row["content"] = fixture + " different decision PRIVATE_CONTENT_SENTINEL"
    elif mode == "wrong-session": row["provenance"]["session_id"] = "PRIVATE_OTHER_SESSION_SENTINEL"
    elif mode == "wrong-origin": row["metadata"]["write_origin"] = "other"
    elif mode == "corrected": row["version"] = 2
    calls = []
    def request(method, path, body=None):
        calls.append((method, path, body))
        assert method == "GET" or (method == "POST" and path == "/v1/memories/recall")
        if method == "POST":
            assert body["include_shared"] is False and body["limit"] == 20
            return {"results": rows}
        return row
    result = check.inspect_fixture(NS(_client=NS(request=request)), state)
    assert result["matching_fixture_records"] == len(rows)
    assert not result["capture_agent_turn_qualified"]
    if len(rows) == 1:
        assert result["fixture_content_validated"] == (mode != "wrong-content")
        assert result["capture_session_provenance_matches"] == (mode != "wrong-session")
        assert result["selected_tool_origin_matches"] == (mode != "wrong-origin")
    else:
        assert len(calls) == 1 and result["current_version"] is None
    assert "PRIVATE_" not in json.dumps(result) and fixture not in json.dumps(result)


@pytest.mark.parametrize("rows", [None, {}, ["PRIVATE_SENTINEL"], [{}] * 21,
    [{"content": "a" * 32, "id": "../PRIVATE_SENTINEL"}]])
def test_malformed_inspection_results_do_not_expand_reads_or_echo_content(check, rows):
    provider = NS(_client=NS(request=lambda *a, **kw: {"results": rows}))
    with pytest.raises(check.CheckError) as error:
        check.inspect_fixture(provider, {"fixture": "a" * 32, "capture_session": "capture"})
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_inspect_stage_never_reads_oauth_or_constructs_a_model_agent(check, monkeypatch, tmp_path, capsys):
    import sys
    snapshots = {"config.yaml": b"memory-only", "enhanced_cognee.json": json.dumps({
        "base_url": "http://127.0.0.1:28080", "timeout": 10, "include_shared": True, "capture_policy": "selected"}).encode()}
    def preflight(approved, *, include_auth=True):
        assert approved and include_auth is False
        return 1000, snapshots
    monkeypatch.setattr(check, "preflight", preflight)
    monkeypatch.setattr(check, "read_private", lambda name, uid:
        b"PRIVATE_MEMORY_TOKEN" if name == ".env" else snapshots[name])
    monkeypatch.setattr(check.os, "chdir", lambda path: None)
    monkeypatch.setattr(check.logging, "disable", lambda value: None)
    monkeypatch.setattr(check, "verify_provider", lambda: None)
    monkeypatch.setattr(check, "read_state", lambda uid: {"fixture": "a" * 32, "capture_session": "capture"})
    monkeypatch.setattr(check, "state_stamp", lambda: (1, 10, 100, 100))
    monkeypatch.setattr(check, "select_credential", lambda *a: pytest.fail("No OAuth selection during inspection"))
    monkeypatch.setattr(check, "native_memory_turn", lambda *a: pytest.fail("No model call during inspection"))
    monkeypatch.setattr(check, "save_state", lambda *a: pytest.fail("No receipt write during inspection"))
    release = tmp_path / "release"
    (release / "repo").mkdir(parents=True)
    source = release / "repo/mock.py"
    source.touch()
    monkeypatch.setattr(check, "RELEASE", release)
    provider = NS(initialize=lambda *a, **kw: None, shutdown=lambda: None)
    resets = []
    secrets = NS(__file__=str(source), load_env_file=lambda path: {"ENHANCED_COGNEE_ACCESS_TOKEN": "PRIVATE_MEMORY_TOKEN"},
        set_secret_scope=lambda *a, **kw: "PRIVATE_BINDING", reset_secret_scope=resets.append)
    loader = NS(__file__=str(source), find_provider_dir=lambda name: check.ARTIFACT, load_memory_provider=lambda name: provider)
    monkeypatch.setitem(sys.modules, "agent", NS(secret_scope=secrets))
    monkeypatch.setitem(sys.modules, "agent.secret_scope", secrets)
    monkeypatch.setitem(sys.modules, "plugins", NS(memory=loader))
    monkeypatch.setattr(check, "memory_status", lambda provider: {"active_records": 0})
    monkeypatch.setattr(check, "inspect_fixture", lambda *a: {"matching_fixture_records": 0, "capture_agent_turn_qualified": False})
    check.main_memory(stage="inspect", approved_test=True)
    output = capsys.readouterr().out
    report = json.loads(output)
    assert report["complete"] and report["stage"] == "inspect"
    assert report["checked_profile_files_and_receipt_unchanged"] and not report["oauth_store_read"]
    assert not report["model_called"] and not report["memory_records_written"]
    assert "PRIVATE_" not in output and resets == ["PRIVATE_BINDING"]
