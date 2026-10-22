"""One synthetic Responses completion using the pilot's own OAuth credential.

Native Hermes request conversion, headers, stream assembly and completion
normalization are exercised; this is not a full Hermes chat/capture test.
No auth resolver, refresh/import, fallback, memory call or settings write.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import pwd
import re
import socket
import ssl
import stat
import sys
import time
import uuid


HOME = Path("/var/lib/hermes-runtime")
PROFILE = HOME / ".hermes/profiles/enhanced-cognee-pilot"
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
BASE_URL = "https://chatgpt.com/backend-api/codex"
MODEL = "gpt-6.1-sol"
ACK = "COGNEE_PILOT_OK"
PROMPT = "This is an invented-data memory-integration connectivity check. Reply exactly COGNEE_PILOT_OK."


class CheckError(RuntimeError):
    """Fixed category; no exception messages or response text in reports."""


class NativeTurnError(CheckError):
    """An incomplete native turn with a bounded, content-free diagnostic."""

    def __init__(self, result, requests, calls, cause=None):
        super().__init__("native_agent_turn_incomplete")
        row = result if isinstance(result, dict) else {}
        reasons = {"context_overflow", "truncated", "invalid_response", "empty_response", "loop_error",
                   "interpreter_shutdown", "session_busy", "gateway_connection", "host_error",
                   "rate_limit", "upstream_rate_limit", "overloaded", "server_error", "timeout",
                   "model_not_found", "format_error", "auth", "billing", "billing_unverified",
                   "permission_denied", "content_policy_blocked", "connection_error"}
        exits = {"unknown", "empty_response_exhausted", "all_retries_exhausted_no_response",
                 "pending_tool_result", "interpreter_shutdown", "local_processing_error",
                 "repeated_outer_errors", "error_near_max_iterations", "context_compression_timeout",
                 "context_compression_exhausted", "session_persistence_failed", "run_budget_exhausted"}
        reason = row.get("failure_reason")
        exit_reason = row.get("turn_exit_reason")
        if isinstance(reason, str) and reason.startswith("session_persistence_failed:"):
            reason = "session_persistence_failed"
        if isinstance(exit_reason, str) and re.fullmatch(r"max_iterations_reached\([0-9]{1,3}\)", exit_reason):
            exit_reason = "max_iterations_reached"
        statuses = requests.get("http_statuses", [])
        self.diagnostics = {
            "native_result_is_mapping": isinstance(result, dict),
            "native_completed": row.get("completed") is True,
            "native_failed": row.get("failed") is True,
            "native_error_present": bool(row.get("error")),
            "native_interrupted": row.get("interrupted") is True,
            "native_partial": row.get("partial") is True,
            "native_response_present": isinstance(row.get("final_response"), str) and bool(row["final_response"].strip()),
            "native_failure_reason": reason if isinstance(reason, str) and reason in reasons | {"session_persistence_failed"} else None,
            "native_exit_reason": exit_reason if isinstance(exit_reason, str) and exit_reason in exits | {"max_iterations_reached"} else None,
            "model_requests": requests["count"] if type(requests.get("count")) is int and 0 <= requests["count"] <= 6 else None,
            "http_statuses": [s for s in statuses[:6] if type(s) is int and 100 <= s <= 599] if isinstance(statuses, list) else [],
            "tool_calls": sorted(set(c for c in calls if c in {"enhanced_recall", "enhanced_get", "enhanced_status", "enhanced_remember"})),
            "request_guard_failure": requests.get("guard_failure") if requests.get("guard_failure") in {
                "unexpected_memory_test_request", "unexpected_memory_test_wire_contract", "invalid_memory_test_payload"} else None,
        }
        safe_categories = {"dns_error", "tls_certificate_error", "timeout", "dependency_missing",
                           "sdk_or_native_argument_error", "http_error", "connection_error", "provider_stream_error"}
        detail = failure(cause) if cause is not None else {}
        self.diagnostics["native_exception_category"] = detail.get("category") if detail.get("category") in safe_categories else None
        self.http_status = detail.get("http_status")
        if self.http_status is None:
            self.http_status = next((s for s in reversed(self.diagnostics["http_statuses"]) if s >= 400), None)


def read_private(name, uid):
    if name not in {"config.yaml", "enhanced_cognee.json", "auth.json", ".env"}:
        raise CheckError("unapproved_file")
    fd = os.open(PROFILE / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != uid
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1 or before.st_size > 1048576):
            raise CheckError("unsafe_profile_file")
        raw = handle.read(1048577)
        after = os.fstat(handle.fileno())
        if (len(raw) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise CheckError("concurrent_file_change")
        return raw


def preflight(approved_test, *, include_auth=True):
    account = pwd.getpwuid(os.geteuid())
    if (approved_test is not True or account.pw_name != "hermes-runtime" or account.pw_uid == 0
            or Path(account.pw_dir) != HOME or os.environ.get("HOME") != str(HOME)
            or os.environ.get("HERMES_HOME") != str(PROFILE)
            or set(os.getgroups()) | {os.getegid()} != {account.pw_gid}
            or not Path(sys.executable).resolve(strict=True).is_relative_to(RELEASE)):
        raise CheckError("restricted_identity")
    fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    if (fields.get("NoNewPrivs", "").strip() != "1"
            or any(fields.get(key, "").strip() != "0000000000000000" for key in ("CapEff", "CapAmb"))):
        raise CheckError("restricted_process_protection")
    for path in reversed((PROFILE, *PROFILE.parents)):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, account.pw_uid} or info.st_mode & 0o022:
            raise CheckError("unsafe_profile_ancestor")
    info = PROFILE.stat()
    if info.st_uid != account.pw_uid or stat.S_IMODE(info.st_mode) != 0o700:
        raise CheckError("unsafe_profile_directory")
    names = ("config.yaml", "enhanced_cognee.json") + (("auth.json",) if include_auth else ())
    snapshots = {name: read_private(name, account.pw_uid) for name in names}
    return account.pw_uid, snapshots


def select_credential(raw):
    auth = json.loads(raw)
    pool = auth.get("credential_pool", {}) if isinstance(auth, dict) else {}
    rows = pool.get("openai-codex", []) if isinstance(pool, dict) else []
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise CheckError("pilot_oauth_selection")
    row = rows[0]
    token = row.get("access_token")
    if (row.get("auth_type") != "oauth" or row.get("label") != "cognee-pilot-codex"
            or row.get("source") != "manual:device_code" or row.get("disabled") is True
            or row.get("base_url", "").rstrip("/") != BASE_URL
            or not isinstance(token, str) or not 32 <= len(token) <= 32768
            or not token.isascii() or any(ord(char) < 33 or ord(char) > 126 for char in token)):
        raise CheckError("pilot_oauth_selection")
    return token


def native_components():
    sys.path.insert(0, str(RELEASE / "repo"))
    from agent import codex_headers, codex_responses_adapter, codex_runtime, auxiliary_codex_response
    modules = (codex_headers, codex_responses_adapter, codex_runtime, auxiliary_codex_response)
    if any(not Path(module.__file__).resolve(strict=True).is_relative_to(RELEASE / "repo") for module in modules):
        raise CheckError("native_module_source")
    return modules


def invoke(token, components, sdk_factory=None):
    import httpx
    if sdk_factory is None:
        from openai import OpenAI
        sdk_factory = OpenAI
    headers, adapter, runtime, normalizer = components
    inputs = adapter._chat_messages_to_responses_input(
        [{"role": "user", "content": PROMPT}], current_issuer_kind="codex_backend", current_issuer_model=MODEL)
    payload = adapter._preflight_codex_api_kwargs({"model": MODEL,
        "instructions": "Return only the requested acknowledgement.", "input": inputs,
        "store": False, "stream": True, "reasoning": {"effort": "low"}}, allow_stream=True)
    kwargs = {}
    headers.apply_required_codex_headers(kwargs, access_token=token, base_url=BASE_URL)
    dispatched = 0
    def guard(request):
        nonlocal dispatched
        if request.method != "POST" or str(request.url) != BASE_URL + "/responses" or dispatched:
            raise CheckError("unexpected_request_or_retry")
        body = json.loads(request.content)
        if (body.get("model") != MODEL or body.get("store") is not False or body.get("stream") is not True
                or body.get("tools") or body.get("service_tier")
                or body.get("reasoning") != {"effort": "low"}):
            raise CheckError("unexpected_request_contract")
        dispatched += 1
    observed = {"terminal": False, "model_seen": False, "model_mismatch": False}
    deadline = time.monotonic() + 75
    events = 0
    def observe(event):
        nonlocal events
        events += 1
        if time.monotonic() > deadline or events > 4096:
            raise TimeoutError("Bounded synthetic stream exceeded its limit.")
        response = getattr(event, "response", None)
        model = getattr(response, "model", None)
        if isinstance(model, str) and model:
            observed["model_seen"] = True
            observed["model_mismatch"] |= not (model.casefold() == MODEL or model.casefold().startswith(MODEL + "-"))
        observed["terminal"] |= getattr(event, "type", None) == "response.completed"
    with httpx.Client(trust_env=False, follow_redirects=False, verify=True,
                      timeout=httpx.Timeout(60, connect=10), event_hooks={"request": [guard]}) as transport:
        with sdk_factory(api_key=token, base_url=BASE_URL, max_retries=0, timeout=60,
                         http_client=transport, **kwargs) as client:
            stream = client.responses.create(**payload)
            try:
                final = runtime._consume_codex_event_stream(stream, model=MODEL, on_event=observe)
            finally:
                stream.close()
    text_parts, tool_calls, usage, finish = normalizer._parse_codex_final_response(
        final, issuer_kind="codex_backend", issuer_model=MODEL)
    if dispatched != 1 or not observed["terminal"]:
        raise CheckError("missing_completed_response")
    if not observed["model_seen"] or observed["model_mismatch"]:
        raise CheckError("server_model_unverified")
    if finish != "stop" or tool_calls or "".join(text_parts).strip() != ACK:
        raise CheckError("unexpected_or_incomplete_reply")
    counts = {}
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = getattr(usage, field, None)
        counts[field] = value if type(value) is int and 0 <= value <= 16777216 else None
    return {"native_responses_contract_passed": True, "model_reply_validated": True,
            "server_model_matches_requested": True, "tokens": counts}


def failure(error):
    category = "unclassified"
    status = None
    provider_code = None
    current = error
    seen = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        code = getattr(current, "status_code", None)
        if type(code) is int and 100 <= code <= 599: status = code
        reason = getattr(current, "code", None)
        if isinstance(reason, str) and reason in {
                "rate_limit_exceeded", "usage_limit_reached", "model_not_found", "unsupported_model",
                "token_expired", "insufficient_quota", "authentication_error", "permission_denied"}:
            provider_code = reason
        if isinstance(current, CheckError): category = str(current); break
        if isinstance(current, ssl.SSLCertVerificationError): category = "tls_certificate_error"; break
        if isinstance(current, socket.gaierror): category = "dns_error"; break
        if isinstance(current, TimeoutError): category = "timeout"
        elif isinstance(current, ModuleNotFoundError): category = "dependency_missing"
        elif isinstance(current, TypeError): category = "sdk_or_native_argument_error"
        elif status is not None: category = "http_error"
        elif type(current).__module__.split(".")[0] in {"openai", "httpx", "httpcore"}:
            if type(current).__name__ in {"APITimeoutError", "ReadTimeout", "ConnectTimeout", "WriteTimeout", "PoolTimeout"}:
                category = "timeout"
            elif type(current).__name__ in {"APIConnectionError", "ConnectError", "ReadError", "WriteError"}:
                category = "connection_error"
        current = current.__cause__ or current.__context__
    if category == "unclassified" and provider_code is not None:
        category = "provider_stream_error"
    result = {"category": category, "http_status": status, "provider_code": provider_code}
    if isinstance(error, NativeTurnError):
        result.update(http_status=error.http_status, native_diagnostics=error.diagnostics)
    return result


def main(*, approved_test=False):
    snapshots = {}
    uid = None
    phase = "restricted_preflight"
    try:
        uid, snapshots = preflight(approved_test)
        os.chdir(HOME)
        logging.disable(logging.CRITICAL)
        phase = "pilot_credential"
        token = select_credential(snapshots["auth.json"])
        phase = "native_imports"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            components = native_components()
            phase = "codex_responses_request"
            result = invoke(token, components)
        phase = "preservation_check"
        if any(read_private(name, uid) != raw for name, raw in snapshots.items()):
            raise CheckError("profile_state_changed_preserve_and_review")
        print(json.dumps({"complete": True, "effective_user": "hermes-runtime",
            "profile": "enhanced-cognee-pilot", "model": MODEL, "base_url": BASE_URL,
            **result, "maximum_requests": 1, "model_called": True,
            "profile_settings_and_auth_unchanged": True, "model_defaults_changed": False,
            "human_credentials_copied": False, "memory_records_written": False,
            "full_hermes_turn_tested": False, "hermes_capture_qualified": False,
            "runtime_qualified": False}, indent=2))
    except Exception as error:
        unchanged = None
        if snapshots:
            try: unchanged = all(read_private(name, uid) == raw for name, raw in snapshots.items())
            except Exception: pass
        print(json.dumps({"complete": False, "failure_stage": phase, **failure(error),
            "profile_settings_and_auth_unchanged": unchanged,
            "memory_records_written": False, "runtime_qualified": False}, indent=2))
        raise SystemExit(1) from None


STATE = HOME / "cognee-pilot-model-test.json"
ARTIFACT = Path("/opt/hermes-runtime/providers/enhanced-cognee-0.1.0-29cb9fa3400a")
PROVIDER_HASHES = {
    "__init__.py": "b221c38baab2c2915f42683e0b8e764be0a42bc3d160f9ab786fd8ea64da6a0a",
    "client.py": "8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64",
    "plugin.yaml": "c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48",
}


def verify_provider():
    for path in (ARTIFACT, *ARTIFACT.parents):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise CheckError("provider_directory_protection")
    if set(os.listdir(ARTIFACT)) != set(PROVIDER_HASHES):
        raise CheckError("provider_payload")
    for name, expected in PROVIDER_HASHES.items():
        fd = os.open(ARTIFACT / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o6022
                    or info.st_nlink != 1 or info.st_size > 65536
                    or hashlib.sha256(handle.read(65537)).hexdigest() != expected):
                raise CheckError("provider_payload")
    link = PROFILE / "plugins/enhanced_cognee"
    info = link.lstat()
    if not stat.S_ISLNK(info.st_mode) or info.st_uid != os.geteuid() or link.resolve(strict=True) != ARTIFACT:
        raise CheckError("provider_link")


def read_state(uid):
    fd = os.open(STATE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1 or info.st_size > 4096):
            raise CheckError("unsafe_test_receipt")
        state = json.loads(handle.read(4097))
    if (not isinstance(state, dict) or set(state) != {"fixture", "capture_session"}
            or not isinstance(state["fixture"], str) or len(state["fixture"]) != 32
            or any(c not in "0123456789abcdef" for c in state["fixture"])
            or state["capture_session"] != "cognee_capture_" + state["fixture"]):
        raise CheckError("test_receipt_shape")
    return state


def save_state(state):
    fd = os.open(STATE, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(state, handle)
        handle.flush()
        os.fsync(handle.fileno())


def memory_status(provider):
    status = json.loads(provider.handle_tool_call("enhanced_status", {}))
    if (status.get("ready") is not True or status.get("tenant_id") != "qualification"
            or status.get("project_id") != "hermes_pilot" or status.get("subject") != "hermes_pilot_runtime"
            or status.get("capture") != "selected" or status.get("schema_version") != 3
            or status.get("encryption") != "AES-256-GCM" or type(status.get("active_records")) is not int):
        raise CheckError("pilot_memory_scope_or_credential")
    return status


def verify_saved(provider, fixture):
    result = provider._client.request("POST", "/v1/memories/recall", {
        "query": "Larch qualification " + fixture, "limit": 10, "include_shared": False})
    rows = [row for row in result.get("results", []) if fixture in str(row.get("content", ""))]
    if len(rows) != 1 or rows[0].get("version") != 1:
        raise CheckError("saved_fixture_not_unique_or_version_one")
    row = provider._client.request("GET", "/v1/memories/" + rows[0]["id"])
    content = row.get("content", "").casefold()
    if fixture not in content or not re.search(r"\b(?:thirteen|13)[ -]+day", content):
        raise CheckError("saved_fixture_content")
    return row


def restrict_agent(agent, allowed):
    names = {tool.get("function", {}).get("name") for tool in agent.tools}
    if not allowed.issubset(names) or agent._memory_manager is None:
        raise CheckError("native_memory_tools_missing")
    # Narrow only this qualification instance; native handlers remain untouched.
    agent.tools = [tool for tool in agent.tools if tool.get("function", {}).get("name") in allowed]
    agent.valid_tool_names = set(allowed)
    if agent._fallback_chain or agent._fallback_activated:
        raise CheckError("unexpected_model_fallback")
    client = agent.client
    client.max_retries = 0
    transport = client._client
    transport.follow_redirects = False
    requests = {"count": 0, "http_statuses": [], "guard_failure": None}
    def guard(request):
        if request.method != "POST" or str(request.url) != BASE_URL + "/responses" or requests["count"] >= 6:
            requests["guard_failure"] = "unexpected_memory_test_request"
            raise CheckError("unexpected_memory_test_request")
        try:
            raw = request.content
            if request.headers.get("content-encoding") == "zstd":
                from compression import zstd
                raw = zstd.decompress(raw)
            body = json.loads(raw)
            if not isinstance(body, dict): raise ValueError()
        except Exception:
            requests["guard_failure"] = "invalid_memory_test_payload"
            raise CheckError("invalid_memory_test_payload") from None
        if (body.get("model") != MODEL or body.get("store") is not False
                or body.get("service_tier") or not isinstance(body.get("tools"), list)
                or any(not isinstance(tool, dict) or tool.get("name") not in allowed for tool in body["tools"])):
            requests["guard_failure"] = "unexpected_memory_test_wire_contract"
            raise CheckError("unexpected_memory_test_wire_contract")
        requests["count"] += 1
    def observe_response(response):
        status = response.status_code
        if type(status) is int and 100 <= status <= 599 and len(requests["http_statuses"]) < 6:
            requests["http_statuses"].append(status)
    transport.event_hooks["request"].append(guard)
    transport.event_hooks.setdefault("response", []).append(observe_response)
    return requests


def native_memory_turn(stage, token, provider, session, prompt):
    import run_agent
    from agent.memory_manager import MemoryManager
    if not Path(run_agent.__file__).resolve(strict=True).is_relative_to(RELEASE / "repo"):
        raise CheckError("native_agent_source")
    manager = MemoryManager()
    manager.add_provider(provider)
    manager.initialize_all(session, hermes_home=str(PROFILE), agent_context="primary", platform="cli")
    calls = []
    def progress(event_type, tool_name=None, **kwargs):
        if event_type == "tool.started" and tool_name in {
                "enhanced_remember", "enhanced_recall", "enhanced_get", "enhanced_status"}:
            calls.append(tool_name)
    agent = run_agent.AIAgent(model=MODEL, provider="openai-codex", api_mode="codex_responses",
        api_key=token, base_url=BASE_URL, enabled_toolsets=["memory"], max_iterations=5,
        run_budget_seconds=100, fallback_model={}, credential_pool=None,
        reasoning_config={"enabled": True, "effort": "low"}, save_trajectories=False,
        quiet_mode=True, skip_background_review=True, session_id=session,
        memory_manager=manager, tool_progress_callback=progress, cwd=str(HOME))
    try:
        allowed = {"enhanced_recall", "enhanced_get", "enhanced_status"}
        if stage == "capture": allowed.add("enhanced_remember")
        requests = restrict_agent(agent, allowed)
        try:
            result = agent.run_conversation(prompt, conversation_history=[])
        except Exception as cause:
            raise NativeTurnError(None, requests, calls, cause) from None
        if (not isinstance(result, dict) or result.get("completed") is not True
                or result.get("failed") or result.get("error") or not 0 < requests["count"] <= 6):
            raise NativeTurnError(result, requests, calls)
        if stage == "capture" and ("enhanced_recall" not in calls or "enhanced_remember" not in calls
                or calls.index("enhanced_recall") > calls.index("enhanced_remember")):
            raise CheckError("model_did_not_recall_then_select_capture")
        return result.get("final_response", ""), sorted(set(calls)), requests["count"]
    finally:
        agent.close()


def main_memory(*, stage, approved_test=False):
    if stage == "inspect":
        return main_inspect(approved_test=approved_test)
    snapshots = {}
    provider = None
    binding = None
    secrets = None
    uid = None
    phase = "restricted_preflight"
    try:
        if stage not in {"capture", "recall"}: raise CheckError("unapproved_stage")
        uid, snapshots = preflight(approved_test)
        snapshots[".env"] = read_private(".env", uid)
        import yaml
        config = yaml.safe_load(snapshots["config.yaml"])
        settings = json.loads(snapshots["enhanced_cognee.json"])
        if (not isinstance(config, dict) or config.get("memory", {}).get("provider") != "enhanced_cognee"
                or settings != {"base_url": "http://127.0.0.1:28080", "timeout": 10,
                               "include_shared": True, "capture_policy": "selected"}):
            raise CheckError("pilot_memory_settings_changed_preserve_and_review")
        os.chdir(HOME)
        os.umask(0o077)
        logging.disable(logging.CRITICAL)
        token = select_credential(snapshots["auth.json"])
        verify_provider()
        sys.path.insert(0, str(RELEASE / "repo"))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            import agent.secret_scope as secrets
            from plugins import memory as loader
            if any(not Path(module.__file__).resolve(strict=True).is_relative_to(RELEASE / "repo")
                   for module in (secrets, loader)):
                raise CheckError("native_memory_source")
            values = secrets.load_env_file(PROFILE / ".env")
            memory_token = values.get("ENHANCED_COGNEE_ACCESS_TOKEN")
            if not isinstance(memory_token, str) or not memory_token:
                raise CheckError("missing_pilot_memory_token")
            binding = secrets.set_secret_scope({"ENHANCED_COGNEE_ACCESS_TOKEN": memory_token}, profile_home=str(PROFILE))
            phase = "memory_provider_preflight"
            if loader.find_provider_dir("enhanced_cognee").resolve() != ARTIFACT:
                raise CheckError("native_memory_discovery")
            provider = loader.load_memory_provider("enhanced_cognee")
            provider.initialize("pilot_preflight", hermes_home=str(PROFILE), agent_context="primary")
            before = memory_status(provider)
            phase = "fixture_preparation"
            if stage == "capture":
                if os.path.lexists(STATE) or before["active_records"] != 0:
                    raise CheckError("existing_test_evidence_preserved_review_before_retry")
                fixture = uuid.uuid4().hex
                state = {"fixture": fixture, "capture_session": "cognee_capture_" + fixture}
                prompt = ("For the entirely fictional Larch qualification project " + fixture
                    + ", our standing planning decision is a thirteen-day review cycle. Explain this decision in one sentence.")
                session = state["capture_session"]
                previous = None
            else:
                state = read_state(uid)
                fixture = state["fixture"]
                previous = verify_saved(provider, fixture)
                session = "cognee_recall_" + uuid.uuid4().hex
                prompt = ("For the entirely fictional Larch qualification project " + fixture
                    + ", what standing review interval did we decide on? Use saved evidence and cite its record ID.")
            phase = "native_agent_turn"
            if stage == "capture": save_state(state)
            answer, calls, requests = native_memory_turn(stage, token, provider, session, prompt)
            phase = "saved_memory_verification"
            # agent.close shuts the provider down; reinitialize for authoritative reads.
            provider.initialize("pilot_verification", hermes_home=str(PROFILE), agent_context="primary")
            row = verify_saved(provider, fixture)
            after = memory_status(provider)
            if after["active_records"] != 1:
                raise CheckError("unexpected_memory_record_count")
            if stage == "recall" and (row != previous or row["id"] not in answer
                    or not re.search(r"\b(?:thirteen|13)[ -]+day", answer.casefold())):
                raise CheckError("fresh_session_recall_not_verified")
            if any(read_private(name, uid) != raw for name, raw in snapshots.items()):
                raise CheckError("profile_state_changed_preserve_and_review")
        print(json.dumps({"complete": True, "stage": stage, "effective_user": "hermes-runtime",
            "profile": "enhanced-cognee-pilot", "model": MODEL, "native_agent_turn_passed": True,
            "selected_capture_passed": stage == "capture", "fresh_session_recall_passed": stage == "recall",
            "profile_settings_and_credentials_unchanged": True, "model_defaults_changed": False,
            "tool_calls": calls, "model_requests": requests, "synthetic_active_records": 1,
            "current_version": row["version"], "memory_records_written": stage == "capture",
            "runtime_qualified": False}, indent=2))
    except Exception as error:
        preserved = None
        if uid is not None and snapshots:
            try:
                preserved = all(read_private(name, uid) == raw for name, raw in snapshots.items())
            except Exception:
                preserved = False
        print(json.dumps({"complete": False, "failure_stage": phase, **failure(error),
            "test_evidence_present_preserve_for_review": os.path.lexists(STATE),
            "memory_writes_may_have_occurred": stage == "capture" and phase in {"native_agent_turn", "saved_memory_verification"},
            "profile_settings_and_credentials_unchanged": preserved,
            "runtime_qualified": False}, indent=2))
        raise SystemExit(1) from None
    finally:
        if provider is not None:
            with contextlib.suppress(Exception), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                provider.shutdown()
        if binding is not None:
            secrets.reset_secret_scope(binding)


def inspect_fixture(provider, state):
    fixture = state["fixture"]
    result = provider._client.request("POST", "/v1/memories/recall", {
        "query": "Larch qualification " + fixture, "limit": 20, "include_shared": False})
    rows = result.get("results")
    if not isinstance(rows, list) or len(rows) > 20 or any(not isinstance(row, dict) for row in rows):
        raise CheckError("inspection_recall_shape")
    matching = [row for row in rows if fixture in str(row.get("content", ""))]
    report = {"matching_fixture_records": len(matching), "current_version": None,
              "fixture_content_validated": False, "capture_session_provenance_matches": False,
              "selected_tool_origin_matches": False}
    if len(matching) == 1:
        ident = matching[0].get("id")
        if not isinstance(ident, str) or len(ident) > 64 or not re.fullmatch(r"[A-Za-z0-9_-]+", ident):
            raise CheckError("inspection_record_id_shape")
        row = provider._client.request("GET", "/v1/memories/" + ident)
        version = row.get("version")
        content = row.get("content")
        if not isinstance(content, str) or len(content) > 262144:
            raise CheckError("inspection_record_shape")
        report["current_version"] = version if type(version) is int and 0 < version < 1000000 else None
        report["fixture_content_validated"] = fixture in content and bool(
            re.search(r"\b(?:thirteen|13)[ -]+day", content.casefold()))
        metadata, provenance = row.get("metadata", {}), row.get("provenance", {})
        report["capture_session_provenance_matches"] = (
            isinstance(provenance, dict) and provenance.get("session_id") == state["capture_session"])
        report["selected_tool_origin_matches"] = (
            isinstance(metadata, dict) and metadata.get("write_origin") == "hermes_selected_tool")
    # Receipt/provenance and canonical data do not prove a completed agent turn.
    report["capture_agent_turn_qualified"] = False
    return report


def state_stamp():
    info = STATE.lstat()
    return info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def main_inspect(*, approved_test=False):
    phase = "restricted_preflight"
    provider = None
    secrets = None
    binding = None
    try:
        uid, snapshots = preflight(approved_test, include_auth=False)
        snapshots[".env"] = read_private(".env", uid)
        settings = json.loads(snapshots["enhanced_cognee.json"])
        if settings != {"base_url": "http://127.0.0.1:28080", "timeout": 10,
                        "include_shared": True, "capture_policy": "selected"}:
            raise CheckError("pilot_memory_settings_changed_preserve_and_review")
        os.chdir(HOME)
        logging.disable(logging.CRITICAL)
        verify_provider()
        phase = "receipt_inspection"
        receipt_stamp = state_stamp()
        state = read_state(uid)
        sys.path.insert(0, str(RELEASE / "repo"))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            import agent.secret_scope as secrets
            from plugins import memory as loader
            if any(not Path(module.__file__).resolve(strict=True).is_relative_to(RELEASE / "repo")
                   for module in (secrets, loader)):
                raise CheckError("native_memory_source")
            memory_token = secrets.load_env_file(PROFILE / ".env").get("ENHANCED_COGNEE_ACCESS_TOKEN")
            if not isinstance(memory_token, str) or not memory_token:
                raise CheckError("missing_pilot_memory_token")
            binding = secrets.set_secret_scope({"ENHANCED_COGNEE_ACCESS_TOKEN": memory_token}, profile_home=str(PROFILE))
            if loader.find_provider_dir("enhanced_cognee").resolve() != ARTIFACT:
                raise CheckError("native_memory_discovery")
            provider = loader.load_memory_provider("enhanced_cognee")
            provider.initialize("pilot_receipt_inspection", hermes_home=str(PROFILE), agent_context="primary")
            phase = "authenticated_memory_inspection"
            status = memory_status(provider)
            result = inspect_fixture(provider, state)
            if (any(read_private(name, uid) != raw for name, raw in snapshots.items())
                    or read_state(uid) != state or state_stamp() != receipt_stamp):
                raise CheckError("profile_or_receipt_changed_preserve_and_review")
        print(json.dumps({"complete": True, "stage": "inspect", "effective_user": "hermes-runtime",
            "profile": "enhanced-cognee-pilot", "scope_active_records": status["active_records"],
            **result, "checked_profile_files_and_receipt_unchanged": True, "oauth_store_read": False,
            "model_called": False, "memory_records_written": False, "runtime_qualified": False}, indent=2))
    except Exception as error:
        print(json.dumps({"complete": False, "failure_stage": phase, **failure(error),
            "test_evidence_preserved": True, "model_called": False,
            "memory_records_written": False, "runtime_qualified": False}, indent=2))
        raise SystemExit(1) from None
    finally:
        if provider is not None:
            with contextlib.suppress(Exception), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                provider.shutdown()
        if binding is not None:
            secrets.reset_secret_scope(binding)


if __name__ == "__main__":
    raise SystemExit("Use the reviewed hash-verified restricted operator command.")
