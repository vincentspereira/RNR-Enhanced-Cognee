"""One authorized synthetic GLM check, without changing any model defaults.

The human operator reads only the main route and selected Z.ai credential.
An ordinary key crosses stdin to hermes-runtime, never arguments or files.
Only that restricted child makes one fixed Coding Plan request; no auto-detect,
general API fallback, Hermes startup, memory writes or trace files are used.
"""
from __future__ import annotations

import contextlib
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
import subprocess
import sys


OWNER_HOME = Path("/home/vincentspereira")
RUNTIME_HOME = Path("/var/lib/hermes-runtime")
PROFILE = RUNTIME_HOME / ".hermes/profiles/enhanced-cognee-pilot"
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
BASE_URL = "https://api.z.ai/api/coding/paas/v4"
REQUEST_URL = BASE_URL + "/chat/completions"
MODEL = "glm-5.3-flash"
ACK = "COGNEE_PILOT_OK"
PROMPT = "This is a synthetic connectivity check for a memory integration. Reply only with COGNEE_PILOT_OK."
LIMIT = 1048576


class CheckError(RuntimeError):
    """Fixed public diagnostics; no values from private configuration."""


class MissingKey(CheckError):
    """Only a missing environment key permits checking the selected pool."""


class ResponseCheckError(CheckError):
    """A response arrived but did not satisfy the fixed acknowledgement contract."""

    def __init__(self, category, details):
        super().__init__("The bounded synthetic response was not validated.")
        self.category = category
        self.details = details


class ReportedFailure(CheckError):
    """Only reconstructed, allowlisted failure fields may reach the operator."""

    def __init__(self, report):
        super().__init__("The restricted Z.ai check did not pass.")
        self.report = report


FAILURE_CATEGORIES = frozenset({
    "unclassified", "dependency_missing", "sdk_argument_error", "tls_certificate_error",
    "tls_error", "dns_error", "connection_error", "timeout", "http_error",
    "response_parse_error", "no_choices", "completion_limit_reached", "missing_content",
    "unexpected_content", "unexpected_tool_calls", "returned_model_mismatch",
})
FINISH_REASONS = frozenset({"stop", "length", "tool_calls", "content_filter", "function_call"})


def token_counts(result):
    usage = getattr(result, "usage", None)
    return {field: value if type(value := getattr(usage, field, None)) is int
            and 0 <= value <= 16777216 else None
            for field in ("prompt_tokens", "completion_tokens", "total_tokens")}


def response_details(result):
    choices = getattr(result, "choices", None)
    choice = choices[0] if choices else None
    message = getattr(choice, "message", None)
    reason = getattr(choice, "finish_reason", None)
    return {"completion_received": True, "finish_reason": reason if reason in FINISH_REASONS else None,
            "content_present": isinstance(getattr(message, "content", None), str)
                and bool(message.content.strip()),
            "reasoning_present": bool(getattr(message, "reasoning_content", None)),
            "tokens": token_counts(result)}


def failure_details(error):
    if isinstance(error, ResponseCheckError):
        return {"category": error.category, **error.details}
    category = "unclassified"
    current = error
    seen = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        name = type(current).__name__
        package = type(current).__module__.split(".")[0]
        if isinstance(current, ssl.SSLCertVerificationError):
            category = "tls_certificate_error"
            break
        if isinstance(current, ssl.SSLError):
            category = "tls_error"
        elif isinstance(current, socket.gaierror):
            category = "dns_error"
            break
        elif isinstance(current, (TimeoutError,)) or (
                package in {"openai", "httpx", "httpcore"} and name in {
                    "APITimeoutError", "ConnectTimeout", "ReadTimeout", "WriteTimeout", "PoolTimeout"}):
            category = "timeout"
        elif isinstance(current, ModuleNotFoundError):
            category = "dependency_missing"
        elif isinstance(current, TypeError):
            category = "sdk_argument_error"
        elif package in {"openai", "httpx", "httpcore"} and name in {
                "APIConnectionError", "ConnectError", "ReadError", "WriteError", "NetworkError"}:
            category = "connection_error"
        elif package == "openai" and name == "APIResponseValidationError":
            category = "response_parse_error"
        elif type(getattr(current, "status_code", None)) is int:
            category = "http_error"
        current = current.__cause__ or current.__context__
    return {"category": category, "completion_received": False, "finish_reason": None,
            "content_present": None, "reasoning_present": None,
            "tokens": {field: None for field in ("prompt_tokens", "completion_tokens", "total_tokens")}}


def sanitized_failure(report):
    category = report.get("category", "unclassified")
    reason = report.get("finish_reason")
    if category not in FAILURE_CATEGORIES or (reason is not None and reason not in FINISH_REASONS):
        raise CheckError("The restricted check returned an unexpected failure receipt.")
    clean = {"complete": False, "failure_stage": report["failure_stage"], "category": category}
    status = report.get("http_status")
    clean["http_status"] = status if type(status) is int and 100 <= status <= 599 else None
    for field in ("completion_received", "content_present", "reasoning_present"):
        value = report.get(field)
        if value is not None and type(value) is not bool:
            raise CheckError("The restricted check returned an unexpected failure receipt.")
        clean[field] = value
    clean["finish_reason"] = reason
    raw_tokens = report.get("tokens")
    if raw_tokens is not None and not isinstance(raw_tokens, dict):
        raise CheckError("The restricted check returned an unexpected failure receipt.")
    clean["tokens"] = {}
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = (raw_tokens or {}).get(field)
        clean["tokens"][field] = value if type(value) is int and 0 <= value <= 16777216 else None
    clean.update(model_defaults_changed=False, credential_written_to_files=False,
                 memory_records_written=False, hermes_capture_qualified=False, runtime_qualified=False)
    return clean


def read_owner_file(name, uid, *, secret):
    if name not in {"config.yaml", ".env", "auth.json"}:
        raise CheckError("Unapproved source file.")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in (OWNER_HOME / ".hermes").parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            if info.st_uid not in {0, uid} or info.st_mode & 0o022:
                raise CheckError("An owner configuration directory needs protection review.")
        source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(source, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_mode & 0o022
                    or info.st_nlink != 1 or info.st_size > LIMIT
                    or (secret and stat.S_IMODE(info.st_mode) != 0o600)):
                raise CheckError("An owner credential/configuration file needs protection review.")
            raw = handle.read(LIMIT + 1)
            after = os.fstat(handle.fileno())
            if (len(raw) != info.st_size or (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                    != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
                raise CheckError("A source file changed during inspection.")
        return raw
    finally:
        os.close(fd)


def usable_key(value):
    return (isinstance(value, str) and 16 <= len(value) <= 4096 and value.isascii()
            and all(33 <= ord(char) <= 126 for char in value)
            and not value.startswith(("${", "your_", "YOUR_")))


def choose_key(model, env_values, auth=None):
    reference = model.get("key_env") or model.get("api_key_env")
    if isinstance(reference, str):
        reference = reference.strip()
    if reference not in (None, ""):
        if not isinstance(reference, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", reference):
            raise CheckError("The main provider credential reference needs review.")
        if usable_key(env_values.get(reference)):
            return env_values[reference], "main_model_environment_reference"
    for variable in ("GLM_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY"):
        if usable_key(env_values.get(variable)):
            return env_values[variable], "zai_environment_alias"
    if auth is not None:
        pool = auth.get("credential_pool", {}) if isinstance(auth, dict) else {}
        rows = pool.get("zai", []) if isinstance(pool, dict) else []
        keys = []
        for row in rows[:32] if isinstance(rows, list) else []:
            if not isinstance(row, dict) or row.get("disabled") is True:
                continue
            value = row.get("access_token") or row.get("runtime_api_key")
            if usable_key(value) and value not in keys:
                keys.append(value)
        if len(keys) == 1:
            return keys[0], "single_zai_credential_pool_entry"
        if len(keys) > 1:
            raise CheckError("Multiple eligible Z.ai pool credentials need explicit selection; none was used.")
    raise MissingKey("No usable existing Z.ai credential was found in the selected sources.")


def guard_request(request):
    if request.method != "POST" or str(request.url) != REQUEST_URL:
        raise CheckError("The test refused a request outside the fixed Coding Plan endpoint.")


def invoke_model(key, sdk_factory=None):
    import httpx
    if sdk_factory is None:
        from openai import OpenAI
        sdk_factory = OpenAI
    # No proxy discovery, redirects, auto-retries or endpoint/model detection.
    with httpx.Client(trust_env=False, follow_redirects=False, verify=True,
                      timeout=httpx.Timeout(60, connect=10), event_hooks={"request": [guard_request]}) as transport:
        with sdk_factory(api_key=key, base_url=BASE_URL, max_retries=0,
                         timeout=60, http_client=transport) as client:
            result = client.chat.completions.create(
                model=MODEL, messages=[{"role": "user", "content": PROMPT}], stream=False,
                max_tokens=512, reasoning_effort="low", extra_body={"thinking": {"type": "enabled"}})
    details = response_details(result)
    if not result.choices:
        raise ResponseCheckError("no_choices", details)
    message = result.choices[0].message
    returned = getattr(result, "model", None)
    matched = (isinstance(returned, str) and
               (returned.casefold() == MODEL or returned.casefold().startswith(MODEL + "-")))
    if not matched:
        raise ResponseCheckError("returned_model_mismatch", details)
    if getattr(message, "tool_calls", None):
        raise ResponseCheckError("unexpected_tool_calls", details)
    if not isinstance(message.content, str) or message.content.strip() != ACK:
        category = "completion_limit_reached" if details["finish_reason"] == "length" else (
            "missing_content" if not details["content_present"] else "unexpected_content")
        raise ResponseCheckError(category, details)
    if details["finish_reason"] == "length":
        raise ResponseCheckError("completion_limit_reached", details)
    return {"model_reply_validated": True, "returned_model_matches_requested": True, "tokens": details["tokens"]}


def restricted_check(payload):
    phase = "restricted_identity"
    try:
        os.chdir(RUNTIME_HOME)
        account = pwd.getpwuid(os.geteuid())
        fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
        if (account.pw_name != "hermes-runtime" or account.pw_uid == 0 or Path(account.pw_dir) != RUNTIME_HOME
                or Path.cwd() != RUNTIME_HOME or os.environ.get("HERMES_HOME") != str(PROFILE)
                or set(os.getgroups()) | {os.getegid()} != {account.pw_gid}
                or fields.get("NoNewPrivs", "").strip() != "1"
                or any(fields.get(key, "").strip() != "0000000000000000" for key in ("CapEff", "CapAmb"))
                or not Path(sys.executable).resolve(strict=True).is_relative_to(RELEASE)):
            raise CheckError("The restricted test launch needs review.")
        if not isinstance(payload, dict) or set(payload) != {"api_key"} or not usable_key(payload["api_key"]):
            raise CheckError("Use only the selected ordinary Z.ai credential.")
        phase = "coding_plan_request"
        logging.disable(logging.CRITICAL)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = invoke_model(payload["api_key"])
        print(json.dumps({"complete": True, "effective_user": "hermes-runtime", "model": MODEL,
                          "base_url": BASE_URL, **result, "maximum_requests": 1,
                          "model_called": True, "model_defaults_changed": False,
                          "credential_written_to_files": False, "memory_records_written": False,
                          "hermes_capture_qualified": False, "runtime_qualified": False}))
    except Exception as error:
        status = getattr(error, "status_code", None)
        print(json.dumps({"complete": False, "failure_stage": phase,
                          "http_status": status if type(status) is int and 100 <= status <= 599 else None,
                          **failure_details(error),
                          "model_defaults_changed": False, "credential_written_to_files": False}))
        raise SystemExit(1) from None


def run_restricted(source, key):
    code = ("import json,sys\nnamespace={'__name__':'reviewed_zai_check_child'}\n"
            "exec(compile(" + repr(source) + ",'reviewed-zai-check','exec'),namespace)\n"
            "namespace['restricted_check'](json.load(sys.stdin))\n")
    result = subprocess.run(
        ["/usr/bin/sudo", "-n", "-u", "hermes-runtime", "--", "/usr/bin/setpriv", "--no-new-privs", "--",
         "/usr/bin/env", "-i", "HOME=" + str(RUNTIME_HOME), "USER=hermes-runtime", "LOGNAME=hermes-runtime",
         "HERMES_HOME=" + str(PROFILE), "PATH=/usr/bin:/bin", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1",
         str(RELEASE / "venv/bin/python"), "-I", "-B", "-c", code],
        input=json.dumps({"api_key": key}).encode(), cwd="/tmp", env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=85)
    if len(result.stdout) > 65536:
        raise CheckError("The restricted check returned an unexpected receipt.")
    report = json.loads(result.stdout)
    if result.returncode:
        if (isinstance(report, dict) and report.get("complete") is False
                and report.get("failure_stage") in {"restricted_identity", "coding_plan_request"}):
            raise ReportedFailure(sanitized_failure(report))
        raise CheckError("Restricted Z.ai check did not complete; verify the operator sudo session.")
    expected = {"complete": True, "effective_user": "hermes-runtime", "model": MODEL, "base_url": BASE_URL,
                "model_reply_validated": True, "returned_model_matches_requested": True, "maximum_requests": 1,
                "model_called": True, "model_defaults_changed": False, "credential_written_to_files": False,
                "memory_records_written": False, "hermes_capture_qualified": False, "runtime_qualified": False}
    if (not isinstance(report, dict) or set(report) != set(expected) | {"tokens"}
            or any(type(report.get(field)) is not type(value) or report.get(field) != value for field, value in expected.items())
            or not isinstance(report.get("tokens"), dict)
            or set(report["tokens"]) != {"prompt_tokens", "completion_tokens", "total_tokens"}
            or any(value is not None and (type(value) is not int or not 0 <= value <= 16777216) for value in report["tokens"].values())):
        raise CheckError("The restricted check returned an unexpected receipt.")
    return report


def main(source, *, approved_model_test=False):
    try:
        account = pwd.getpwuid(os.geteuid())
        if (approved_model_test is not True or account.pw_name != "vincentspereira" or account.pw_uid == 0
                or Path(account.pw_dir) != OWNER_HOME or os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes"
                or not Path(sys.executable).resolve(strict=True).is_relative_to(RELEASE)
                or not isinstance(source, bytes) or len(source) > 65536):
            raise CheckError("Use the approved human operator, protected Python and explicit test selection.")
        os.chdir(OWNER_HOME)
        snapshots = {}
        def read(name, secret=True):
            raw = read_owner_file(name, account.pw_uid, secret=secret)
            snapshots[name] = (raw, secret)
            return raw
        import yaml
        config = yaml.safe_load(read("config.yaml", secret=False))
        model = config.get("model") if isinstance(config, dict) else None
        if not isinstance(model, dict) or str(model.get("provider", "")).casefold() not in {"zai", "glm", "z-ai", "z.ai", "zhipu"}:
            raise CheckError("The main configured Z.ai provider changed; no credential selected.")
        sys.path.insert(0, str(RELEASE / "repo"))
        import agent.secret_scope as parser
        if not Path(parser.__file__).resolve().is_relative_to(RELEASE / "repo"):
            raise CheckError("The native profile parser source differs.")
        try:
            raw_env = read(".env")
        except FileNotFoundError:
            raw_env = b""
        env_values = parser._parse_env_text(parser._decode_env_bytes(raw_env))
        try:
            key, key_source = choose_key(model, env_values)
        except MissingKey:
            auth = json.loads(read("auth.json"))
            key, key_source = choose_key(model, env_values, auth)
        report = run_restricted(source, key)
        unchanged = all(read_owner_file(name, account.pw_uid, secret=private) == raw
                        for name, (raw, private) in snapshots.items())
        report.update(key_source=key_source, owner_source_files_unchanged=unchanged)
    except ReportedFailure as error:
        print(json.dumps(error.report, indent=2))
        raise SystemExit(1) from None
    except CheckError as error:
        raise SystemExit("STOP: " + str(error)) from None
    except Exception:
        raise SystemExit("STOP: Z.ai check incomplete; no private details printed or model settings written.") from None
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    raise SystemExit("Use the hash-verified approved one-request operator command.")
