"""Credential selection and one-request isolation without native cloud calls."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest


@pytest.fixture
def check():
    path = Path("integrations/hermes/deployment/check_zai_pilot_connectivity.py").resolve()
    spec = importlib.util.spec_from_file_location("zai_connectivity", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KEY = "synthetic-zai-model-key-no-real-account"


def test_model_reference_wins_without_copying_other_provider_keys(check):
    key, source = check.choose_key({"key_env": "MODEL_REFERENCE"}, {
        "MODEL_REFERENCE": KEY, "GLM_API_KEY": "synthetic-other-model-key",
        "UNRELATED_PRIVATE_KEY": "DO_NOT_COPY"})
    assert key == KEY and source == "main_model_environment_reference"


@pytest.mark.parametrize("alias", ["GLM_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY"])
def test_known_native_zai_aliases_are_supported(check, alias):
    assert check.choose_key({}, {alias: KEY}) == (KEY, "zai_environment_alias")


def test_alias_order_matches_native_resolver(check):
    assert check.choose_key({}, {"GLM_API_KEY": KEY, "ZAI_API_KEY": "synthetic-second-key"})[0] == KEY


def test_empty_model_reference_does_not_shadow_native_alias(check):
    assert check.choose_key({"key_env": "  "}, {"GLM_API_KEY": KEY})[0] == KEY


def test_pool_fallback_is_zai_only_and_requires_unique_usable_credential(check):
    auth = {"credential_pool": {"unrelated": [{"access_token": "DO_NOT_COPY_PRIVATE"}],
        "zai": [{"access_token": KEY}, {"access_token": KEY},
                {"access_token": "ignored-disabled-key", "disabled": True}]}}
    assert check.choose_key({}, {}, auth) == (KEY, "single_zai_credential_pool_entry")
    auth["credential_pool"]["zai"].append({"runtime_api_key": "synthetic-second-eligible-key"})
    with pytest.raises(check.CheckError, match="Multiple") as error:
        check.choose_key({}, {}, auth)
    assert KEY not in str(error.value) and "DO_NOT_COPY_PRIVATE" not in str(error.value)


@pytest.mark.parametrize("value", [None, "", "short", "your_placeholder_value", "YOUR_PLACEHOLDER_VALUE",
                                  "${SOME_REFERENCE_VALUE}", "synthetic-key\nNEW=value", "key with private whitespace"])
def test_unusable_credentials_are_not_sent(check, value):
    with pytest.raises(check.CheckError):
        check.choose_key({}, {"GLM_API_KEY": value})


@pytest.mark.parametrize("reference", ["BAD-REFERENCE", "PRIVATE\nVALUE", {}, ""])
def test_invalid_model_reference_is_never_interpreted_as_code_or_path(check, reference):
    with pytest.raises(check.CheckError):
        check.choose_key({"key_env": reference, "api_key_env": reference}, {})


def test_guard_accepts_only_the_fixed_coding_plan_request(check):
    check.guard_request(httpx.Request("POST", check.REQUEST_URL))


@pytest.mark.parametrize("method,url", [
    ("POST", "https://api.z.ai/api/paas/v4/chat/completions"),
    ("POST", "http://api.z.ai/api/coding/paas/v4/chat/completions"),
    ("POST", "https://other.example/api/coding/paas/v4/chat/completions"),
    ("POST", "https://api.z.ai/api/coding/paas/v4/chat/completions?key=PRIVATE"),
    ("GET", "https://api.z.ai/api/coding/paas/v4/chat/completions")])
def test_wrong_host_general_api_redirect_target_or_method_is_refused(check, method, url):
    with pytest.raises(check.CheckError) as error:
        check.guard_request(httpx.Request(method, url))
    assert "PRIVATE" not in str(error.value)


def model_response(check, *, content=None, model=None):
    message = SimpleNamespace(content=check.ACK if content is None else content, tool_calls=None)
    return SimpleNamespace(model=check.MODEL if model is None else model,
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(prompt_tokens=30, completion_tokens=20, total_tokens=50))


def sdk_stub(check, response, calls):
    class SDK:
        def __init__(self, **kwargs):
            assert kwargs["api_key"] == KEY and kwargs["base_url"] == check.BASE_URL
            assert kwargs["max_retries"] == 0 and kwargs["timeout"] == 60
            transport = kwargs["http_client"]
            assert transport.follow_redirects is False
            assert transport._trust_env is False
            assert transport.event_hooks["request"] == [check.guard_request]
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def create(self, **kwargs):
            calls.append(kwargs)
            assert kwargs == {"model": "glm-5.3-flash", "messages": [{"role": "user", "content": check.PROMPT}],
                              "stream": False, "max_tokens": 512, "reasoning_effort": "low",
                              "extra_body": {"thinking": {"type": "enabled"}}}
            assert KEY not in json.dumps(kwargs)
            return response
    return SDK


def test_exactly_one_small_synthetic_request_and_only_numeric_usage_leaves_check(check):
    calls = []
    result = check.invoke_model(KEY, sdk_factory=sdk_stub(check, model_response(check), calls))
    assert len(calls) == 1
    assert result == {"model_reply_validated": True, "returned_model_matches_requested": True,
                      "tokens": {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50}}
    assert KEY not in json.dumps(result) and check.ACK not in json.dumps(result)


def test_harmless_reply_whitespace_does_not_fail_connectivity(check):
    response = model_response(check, content="\n " + check.ACK + "\n")
    assert check.invoke_model(KEY, sdk_factory=sdk_stub(check, response, []))["model_reply_validated"] is True


@pytest.mark.parametrize("mutation", ["private-content", "other-model", "wrong-variant", "tool-call", "empty"])
def test_unexpected_model_reply_never_gets_printed_or_accepted(check, mutation):
    response = model_response(check)
    if mutation == "private-content": response.choices[0].message.content = "PRIVATE_RESPONSE_SENTINEL"
    elif mutation == "other-model": response.model = "other-model"
    elif mutation == "wrong-variant": response.model = "glm-5.3-flashx"
    elif mutation == "tool-call": response.choices[0].message.tool_calls = [{"private": "PRIVATE_RESPONSE_SENTINEL"}]
    else: response.choices = []
    with pytest.raises(check.CheckError) as error:
        check.invoke_model(KEY, sdk_factory=sdk_stub(check, response, []))
    assert "PRIVATE_RESPONSE_SENTINEL" not in str(error.value)


def receipt(check):
    return {"complete": True, "effective_user": "hermes-runtime", "model": check.MODEL, "base_url": check.BASE_URL,
        "model_reply_validated": True, "returned_model_matches_requested": True, "maximum_requests": 1,
        "model_called": True, "model_defaults_changed": False, "credential_written_to_files": False,
        "memory_records_written": False, "hermes_capture_qualified": False, "runtime_qualified": False,
        "tokens": {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50}}


def test_key_crosses_only_stdin_and_application_executes_as_restricted_user(check, monkeypatch):
    source = Path(check.__file__).read_bytes()
    def run(command, **options):
        assert command[:6] == ["/usr/bin/sudo", "-n", "-u", "hermes-runtime", "--", "/usr/bin/setpriv"]
        assert "--no-new-privs" in command and "-i" in command and "-I" in command and "-B" in command
        assert str(check.RELEASE / "venv/bin/python") in command
        assert options["input"] == json.dumps({"api_key": KEY}).encode()
        assert all(KEY not in arg for arg in command)
        assert KEY not in json.dumps(options["env"])
        compile(command[-1], "restricted-zai-child", "exec")
        assert len(command[-1].encode()) < 131072
        return SimpleNamespace(returncode=0, stdout=json.dumps(receipt(check)).encode(), stderr=b"")
    monkeypatch.setattr(check.subprocess, "run", run)
    assert check.run_restricted(source, KEY)["model_reply_validated"] is True


@pytest.mark.parametrize("mutation", ["extra", "role", "flag", "negative-tokens", "failure-private", "failure-http"])
def test_parent_never_echoes_untrusted_child_or_provider_details(check, monkeypatch, mutation):
    report = receipt(check)
    status = 0
    if mutation == "extra": report["private"] = "PRIVATE_RESPONSE_SENTINEL"
    elif mutation == "role": report["effective_user"] = "root"
    elif mutation == "flag": report["model_defaults_changed"] = True
    elif mutation == "negative-tokens": report["tokens"]["total_tokens"] = -1
    else:
        status = 1
        report = {"complete": False, "failure_stage": "coding_plan_request" if mutation == "failure-http" else "PRIVATE_RESPONSE_SENTINEL", "http_status": 429}
    monkeypatch.setattr(check.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=status, stdout=json.dumps(report).encode(), stderr=b"PRIVATE_RESPONSE_SENTINEL"))
    with pytest.raises(check.CheckError) as error:
        check.run_restricted(b"# source", KEY)
    assert "PRIVATE_RESPONSE_SENTINEL" not in str(error.value)
    if mutation == "failure-http":
        assert isinstance(error.value, check.ReportedFailure)
        assert error.value.report["http_status"] == 429


def test_explicit_test_selection_required_before_any_private_file_read(check, monkeypatch):
    monkeypatch.setattr(check.pwd, "getpwuid", lambda uid: SimpleNamespace(pw_name="vincentspereira", pw_uid=1000))
    monkeypatch.setattr(check, "read_owner_file", lambda *args, **kwargs: pytest.fail("No private file read permitted"))
    with pytest.raises(SystemExit, match="explicit test selection"):
        check.main(b"# source", approved_model_test=False)


def test_child_enters_private_home_after_uid_switch_before_qualification(check, monkeypatch, capsys):
    directories = []
    monkeypatch.setattr(check.os, "chdir", directories.append)
    monkeypatch.setattr(check.pwd, "getpwuid", lambda uid: SimpleNamespace(pw_name="wrong-user"))
    with pytest.raises(SystemExit):
        check.restricted_check({"api_key": KEY})
    assert directories == [check.RUNTIME_HOME]
    assert json.loads(capsys.readouterr().out)["failure_stage"] == "restricted_identity"


def test_private_yaml_parse_errors_never_reach_operator_output(check, monkeypatch, capsys):
    import sys
    monkeypatch.setattr(check.pwd, "getpwuid", lambda uid: SimpleNamespace(
        pw_name="vincentspereira", pw_uid=1000, pw_dir=str(check.OWNER_HOME)))
    monkeypatch.setattr(check, "RELEASE", Path(sys.executable).resolve().parent)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-Hermes")
    monkeypatch.setattr(check.os, "chdir", lambda path: None)
    monkeypatch.setattr(check, "read_owner_file", lambda *args, **kwargs: b"model: [\n PRIVATE_CONFIG_SENTINEL")
    with pytest.raises(SystemExit) as error:
        check.main(b"# source", approved_model_test=True)
    assert "PRIVATE_CONFIG_SENTINEL" not in str(error.value)
    assert not capsys.readouterr().out


def test_reasoning_only_token_exhaustion_is_identifiable_without_reply_text(check):
    response = model_response(check)
    response.choices[0].message.content = None
    response.choices[0].message.reasoning_content = "PRIVATE_REASONING_SENTINEL"
    response.choices[0].finish_reason = "length"
    response.usage.completion_tokens = 512
    with pytest.raises(check.ResponseCheckError) as error:
        check.invoke_model(KEY, sdk_factory=sdk_stub(check, response, []))
    public = check.failure_details(error.value)
    assert public["category"] == "completion_limit_reached"
    assert public["completion_received"] is True
    assert public["content_present"] is False and public["reasoning_present"] is True
    assert public["finish_reason"] == "length" and public["tokens"]["completion_tokens"] == 512
    assert "PRIVATE_REASONING_SENTINEL" not in json.dumps(public)


@pytest.mark.parametrize("kind,category", [
    ("certificate", "tls_certificate_error"), ("dns", "dns_error"),
    ("timeout", "timeout"), ("dependency", "dependency_missing"),
    ("argument", "sdk_argument_error"), ("connection", "connection_error"),
    ("http", "http_error"), ("unknown", "unclassified")])
def test_failure_classification_never_copies_exception_messages(check, kind, category):
    errors = {
        "certificate": check.ssl.SSLCertVerificationError("PRIVATE_EXCEPTION_SENTINEL"),
        "dns": check.socket.gaierror("PRIVATE_EXCEPTION_SENTINEL"),
        "timeout": httpx.ReadTimeout("PRIVATE_EXCEPTION_SENTINEL"),
        "dependency": ModuleNotFoundError("PRIVATE_EXCEPTION_SENTINEL"),
        "argument": TypeError("PRIVATE_EXCEPTION_SENTINEL"),
        "connection": httpx.ConnectError("PRIVATE_EXCEPTION_SENTINEL"),
        "http": RuntimeError("PRIVATE_EXCEPTION_SENTINEL"),
        "unknown": RuntimeError("PRIVATE_EXCEPTION_SENTINEL"),
    }
    if kind == "http": errors[kind].status_code = 403
    public = check.failure_details(errors[kind])
    assert public["category"] == category
    assert "PRIVATE_EXCEPTION_SENTINEL" not in json.dumps(public)


def test_wrapped_certificate_error_preserves_only_fixed_cause_category(check):
    outer = httpx.ConnectError("PRIVATE_CONNECTION_SENTINEL")
    outer.__cause__ = check.ssl.SSLCertVerificationError("PRIVATE_CERT_SENTINEL")
    assert check.failure_details(outer)["category"] == "tls_certificate_error"


@pytest.mark.parametrize("field,value", [
    ("category", "PRIVATE_SENTINEL"), ("finish_reason", "PRIVATE_SENTINEL"),
    ("content_present", "PRIVATE_SENTINEL"), ("reasoning_present", 1),
    ("completion_received", {}), ("tokens", "PRIVATE_SENTINEL")])
def test_untrusted_failure_fields_are_refused_without_echoing_values(check, field, value):
    report = {"failure_stage": "coding_plan_request", field: value}
    with pytest.raises(check.CheckError) as error:
        check.sanitized_failure(report)
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_failure_reconstruction_discards_extra_provider_fields(check):
    report = check.sanitized_failure({"failure_stage": "coding_plan_request", "category": "http_error",
        "http_status": 429, "private_body": "PRIVATE_SENTINEL", "private_key": KEY,
        "tokens": {"completion_tokens": "PRIVATE_SENTINEL", "extra": KEY}})
    assert report["http_status"] == 429
    assert report["tokens"]["completion_tokens"] is None
    assert "PRIVATE_SENTINEL" not in json.dumps(report) and KEY not in json.dumps(report)


def test_parent_displays_only_reconstructed_failure_receipt(check, monkeypatch, capsys):
    import sys
    monkeypatch.setattr(check.pwd, "getpwuid", lambda uid: SimpleNamespace(
        pw_name="vincentspereira", pw_uid=1000, pw_dir=str(check.OWNER_HOME)))
    monkeypatch.setattr(check, "RELEASE", Path(sys.executable).resolve().parent)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-Hermes")
    monkeypatch.setattr(check.os, "chdir", lambda path: None)
    monkeypatch.setattr(check, "read_owner_file", lambda *a, **kw: b"PRIVATE_CONFIG_SENTINEL")
    import yaml
    monkeypatch.setattr(yaml, "safe_load", lambda data: {"model": {"provider": "zai"}})
    parser = SimpleNamespace(__file__=str(check.RELEASE / "repo/agent/secret_scope.py"),
        _decode_env_bytes=lambda data: "", _parse_env_text=lambda data: {"GLM_API_KEY": KEY})
    monkeypatch.setitem(sys.modules, "agent", SimpleNamespace(secret_scope=parser))
    monkeypatch.setitem(sys.modules, "agent.secret_scope", parser)
    def fail(*args):
        raise check.ReportedFailure(check.sanitized_failure({
            "failure_stage": "coding_plan_request", "category": "completion_limit_reached"}))
    monkeypatch.setattr(check, "run_restricted", fail)
    with pytest.raises(SystemExit) as error:
        check.main(b"# approved source", approved_model_test=True)
    assert error.value.code == 1
    output = capsys.readouterr().out
    assert json.loads(output)["category"] == "completion_limit_reached"
    assert "PRIVATE_CONFIG_SENTINEL" not in output and KEY not in output
