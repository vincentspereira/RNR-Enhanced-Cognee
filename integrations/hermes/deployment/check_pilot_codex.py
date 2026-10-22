"""One synthetic Responses completion using the pilot's own OAuth credential.

Native Hermes request conversion, headers, stream assembly and completion
normalization are exercised; this is not a full Hermes chat/capture test.
No auth resolver, refresh/import, fallback, memory call or settings write.
"""
from __future__ import annotations

import contextlib
import io
import json
import logging
import os
from pathlib import Path
import pwd
import socket
import ssl
import stat
import sys
import time


HOME = Path("/var/lib/hermes-runtime")
PROFILE = HOME / ".hermes/profiles/enhanced-cognee-pilot"
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
BASE_URL = "https://chatgpt.com/backend-api/codex"
MODEL = "gpt-6.1-sol"
ACK = "COGNEE_PILOT_OK"
PROMPT = "This is an invented-data memory-integration connectivity check. Reply exactly COGNEE_PILOT_OK."


class CheckError(RuntimeError):
    """Fixed category; no exception messages or response text in reports."""


def read_private(name, uid):
    if name not in {"config.yaml", "enhanced_cognee.json", "auth.json"}:
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


def preflight(approved_test):
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
    snapshots = {name: read_private(name, account.pw_uid)
                 for name in ("config.yaml", "enhanced_cognee.json", "auth.json")}
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
    return {"category": category, "http_status": status, "provider_code": provider_code}


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


if __name__ == "__main__":
    raise SystemExit("Use the reviewed hash-verified restricted operator command.")
