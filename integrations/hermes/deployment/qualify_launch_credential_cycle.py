"""Finite real API expiry/native secret reload in a NEW synthetic fixture.

No model call, memory write, existing profile edit, timer or service switch.
Root signs only fixed ordinary claims; keys never enter child argv/env/stdin.
This tests components, not the installed issuer or a running gateway process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import pwd
import resource
import stat
import subprocess
import sys
import tempfile
import time
import uuid

REVISION = "21abf4857ca8dce8e0a3aafc725266c8d3754529"
BASE = Path("/opt/enhanced-cognee-memory/candidates") / REVISION
RELEASE = Path("/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1")
# Public random fixture identifiers only. The reviewed directory walker opens
# every ancestor O_RDONLY; each private child remains owner-only mode 0700.
# Preserve earlier fixtures under hermes-credential-qualification unchanged.
FIXTURES = Path("/var/lib/hermes-renewal-qualification")
CHILD_PHASE = "identity"
CHILD_DIAGNOSTICS = {}
PROCESS_STARTED = time.monotonic()
FILES = {
    "deployment/provision_pilot_access.py": "f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6",
    "deployment/renew_pilot_access.py": "8fb4b4dfe3941a15755bf367c982d0aadfad7fcaac94932df9b46202d8583567",
    "deployment/fleet_credential_lifecycle.py": "f9e16e1629710d839b45cdb21eadd81787cce66c160b5d25814fe039feef5a62",
    "enhanced_cognee/__init__.py": "fcc7be3d7659671f14006f685c8e5419554075a1e35ca4dde687d7ae46400061",
    "enhanced_cognee/client.py": "8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64",
    "enhanced_cognee/plugin.yaml": "c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48",
}


def require(value, category):
    if not value:
        raise ValueError(category)


def definitions(path, name):
    namespace = {"__name__": name}
    exec(compile(path.read_bytes(), "<verified-" + name + ">", "exec"), namespace)
    return namespace


def claims_for(run_id):
    require(isinstance(run_id, str) and len(run_id) == 16
            and all(c in "0123456789abcdef" for c in run_id), "fixture_identifier")
    return {"sub": "renew_" + run_id, "agent_id": "renewal_qualification", "tenant": "qualification",
            "project_id": "renew_" + run_id, "roles": ["api_client"], "capture_policy": "selected"}


def protected(path):
    for item in [*reversed(path.parents), path]:
        info = item.lstat()
        require(info.st_uid == 0 and not info.st_mode & 0o022 and not stat.S_ISLNK(info.st_mode),
                "public_artifact_protection")


def status_diagnostic(identity, code, body, expires):
    data = body if isinstance(body, dict) else {}
    return {"http_status": code if type(code) is int and 100 <= code <= 599 else 0,
            "body_is_object": isinstance(body, dict), "ready": data.get("ready") is True,
            "schema_matches": data.get("schema_version") == 3,
            "encryption_matches": data.get("encryption") == "AES-256-GCM",
            "tenant_matches": data.get("tenant_id") == identity["tenant"],
            "project_matches": data.get("project_id") == identity["project_id"],
            "subject_matches": data.get("subject") == identity["sub"],
            "active_count_valid": type(data.get("active_records")) is int and data["active_records"] >= 0,
            "pending_count_valid": type(data.get("pending_change_events")) is int and data["pending_change_events"] >= 0,
            "seconds_remaining": max(-86400, min(86400, int(expires-time.time()))),
            "initialization_elapsed_ms": max(0, min(110000, int((time.monotonic()-PROCESS_STARTED)*1000)))}


def valid_diagnostic(value):
    flags = {"body_is_object", "ready", "schema_matches", "encryption_matches", "tenant_matches",
             "project_matches", "subject_matches", "active_count_valid", "pending_count_valid"}
    return (isinstance(value, dict) and set(value) == flags | {"http_status", "seconds_remaining", "initialization_elapsed_ms"}
            and all(type(value[k]) is bool for k in flags)
            and type(value["http_status"]) is int and (value["http_status"] == 0 or 100 <= value["http_status"] <= 599)
            and type(value["seconds_remaining"]) is int and -86400 <= value["seconds_remaining"] <= 86400
            and type(value["initialization_elapsed_ms"]) is int and 0 <= value["initialization_elapsed_ms"] <= 110000)


def exception_metadata(error):
    """Fixed categories and line numbers only; never exception messages/locals."""
    known = {"ValueError", "TypeError", "AttributeError", "KeyError", "NameError",
             "RuntimeError", "MemoryTransportError", "PermissionError", "FileNotFoundError",
             "OSError", "URLError", "HTTPError", "TimeoutError"}
    chain = []
    seen = set()
    while error is not None and id(error) not in seen and len(chain) < 4:
        seen.add(id(error))
        kind = type(error).__name__
        row = {"kind": kind if kind in known else "other"}
        number = getattr(error, "errno", None)
        if type(number) is int and 0 < number < 4096:
            row["errno"] = number
        frames = []
        trace = error.__traceback__
        while trace is not None:
            if trace.tb_frame.f_code.co_filename == __file__:
                frames.append(trace.tb_lineno)
            trace = trace.tb_next
        row["helper_lines"] = frames[-4:]
        chain.append(row)
        error = error.__cause__ or error.__context__
    return chain


def child(artifact, data):
    global CHILD_PHASE, CHILD_DIAGNOSTICS
    account = pwd.getpwuid(os.geteuid())
    fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    require(account.pw_name == "hermes-runtime" and account.pw_uid != 0 and not os.getgroups()
            and fields.get("NoNewPrivs", "").strip() == "1"
            and all(fields.get(k, "").strip() == "0000000000000000" for k in ("CapEff", "CapAmb")),
            "restricted_child_identity")
    run_id = data["run_id"]
    identity = claims_for(run_id)
    require(artifact.parent == BASE and artifact.name == "credential-cycle-" + run_id, "fixture_artifact")
    protected(artifact)
    CHILD_PHASE = "source_load"
    core = definitions(artifact / "deployment/provision_pilot_access.py", "cycle_issuer")
    renewal = definitions(artifact / "deployment/renew_pilot_access.py", "cycle_journal")
    lifecycle = definitions(artifact / "deployment/fleet_credential_lifecycle.py", "cycle_transaction")
    core["IDENTITY"] = identity
    request_status = core["api_status"]
    def observed_status(token):
        global CHILD_DIAGNOSTICS
        try:
            code, body = request_status(token)
        except Exception:
            if CHILD_PHASE == "initial_status":
                CHILD_DIAGNOSTICS = status_diagnostic(identity, 0, {}, data["expires_at"])
            raise
        if CHILD_PHASE == "initial_status":
            CHILD_DIAGNOSTICS = status_diagnostic(identity, code, body, data["expires_at"])
        return code, body
    core["api_status"] = observed_status
    profile = FIXTURES / run_id
    info = profile.lstat()
    require(info.st_uid == account.pw_uid and stat.S_IMODE(info.st_mode) == 0o700
            and stat.S_ISDIR(info.st_mode), "fixture_profile_protection")
    require(os.environ.get("HOME") == str(profile) and os.environ.get("HERMES_HOME") == str(profile),
            "isolated_fixture_home")
    os.environ["HERMES_HOME"] = str(profile)
    CHILD_PHASE = "fixture_files"
    os.umask(0o077)
    files = {".env": ("SYNTHETIC_UNRELATED_VALUE=preserved\nENHANCED_COGNEE_ACCESS_TOKEN=" + data["old"] + "\n").encode(),
             "config.yaml": b"memory:\n  provider: enhanced_cognee\n",
             "auth.json": b'{"synthetic_marker":"preserve"}',
             "enhanced_cognee.json": json.dumps({"base_url": "http://127.0.0.1:28080", "timeout": 10,
                 "capture_policy": "selected", "include_shared": True}).encode()}
    for name, raw in files.items():
        fd = os.open(profile / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    (profile / "plugins").mkdir(mode=0o700)
    (profile / "plugins/enhanced_cognee").symlink_to(artifact / "enhanced_cognee")
    sys.path.insert(0, str(RELEASE / "repo"))
    CHILD_PHASE = "native_imports"
    from agent import secret_scope as secrets
    from plugins import memory as loader
    from gateway.run_agent_cache import GatewayAgentCacheMixin
    require(all(Path(m.__file__).resolve().is_relative_to(RELEASE / "repo") for m in (secrets, loader)),
            "pinned_native_code")
    require(loader.find_provider_dir("enhanced_cognee").resolve() == artifact / "enhanced_cognee",
            "pinned_provider_binding")
    binding = secrets.set_secret_scope(secrets.load_env_file(profile / ".env"), profile_home=str(profile))
    try:
        provider = loader.load_memory_provider("enhanced_cognee")
        require(provider is not None, "provider_discovery")
        provider.initialize("real-cycle-" + run_id, hermes_home=str(profile), agent_context="primary")
        require(provider._client.base_url == "http://127.0.0.1:28080", "fixed_api_origin")
        require(provider._client.token == data["old"], "initial_native_credential")
        CHILD_PHASE = "initial_status"
        lifecycle["accepted_status"](core, data["old"])
        CHILD_PHASE = "initial_native_status"
        initial = provider._client.request("GET", "/v1/memories/status")
        require(initial.get("project_id") == identity["project_id"], "initial_native_scope")
        class CacheProbe(GatewayAgentCacheMixin):
            _MEMORY_IDENTITY_PROVIDER_MEMO = {}
        before = CacheProbe._memory_provider_identity_signature("enhanced_cognee")
        CHILD_PHASE = "fixture_transaction_open"
        directory = core["open_directory"](profile, {0, account.pw_uid})
        try:
            import fcntl
            lock = os.open(".cognee-renewal.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            try:
                core["read_private_fd"](lock, account.pw_uid)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                class Interrupted(Exception):
                    pass
                for phase, expected in (("prepared", files[".env"]), ("published", None)):
                    CHILD_PHASE = "interruption_" + phase
                    def stop(current):
                        if current == phase:
                            raise Interrupted()
                    try:
                        lifecycle["publish"](core, renewal, directory, data["bundle"], account.pw_uid, checkpoint=stop)
                    except Interrupted:
                        pass
                    else:
                        raise ValueError("interruption_not_exercised")
                    current = core["read_private_at"](directory, ".env", account.pw_uid)[0]
                    if expected is not None:
                        require(current == expected, "prepared_attempt_changed_environment")
                    else:
                        require(renewal["environment"](core, current) == data["bundle"]["token"], "published_attempt_missing")
                    require(renewal["reconcile"](core, directory, account.pw_uid, current) == 1,
                            "interrupted_journal_reconciliation")
            finally:
                os.close(lock)
        finally:
            os.close(directory)
        require(renewal["token_claims"](core, data["old"])["exp"] == data["expires_at"], "expiry_binding")
        remaining = data["expires_at"] + 2 - time.time()
        require(0 < remaining <= 65, "expiry_window")
        CHILD_PHASE = "await_expiry"
        time.sleep(remaining)
        # The retained client must actually be refused after real wall-clock
        # expiry, before scope refresh/reinitialization accepts the new token.
        CHILD_PHASE = "expired_refusal"
        try:
            provider._client.request("GET", "/v1/memories/status")
        except Exception as error:
            require(getattr(error, "status_code", None) == 401, "expired_client_not_denied")
        else:
            raise ValueError("expired_client_not_denied")
        CHILD_PHASE = "native_refresh"
        require(secrets.refresh_installed_secret_scope(profile), "native_secret_refresh")
        after = CacheProbe._memory_provider_identity_signature("enhanced_cognee")
        require(before.get("credential_revision") != after.get("credential_revision"), "native_cache_identity_unchanged")
        refreshed = loader.load_memory_provider("enhanced_cognee")
        refreshed.initialize("real-cycle-" + run_id, hermes_home=str(profile), agent_context="primary")
        require(refreshed._client.base_url == "http://127.0.0.1:28080", "fixed_api_origin")
        require(refreshed._client.token == data["bundle"]["token"], "refreshed_native_credential")
        CHILD_PHASE = "new_status"
        response = refreshed._client.request("GET", "/v1/memories/status")
        require(response.get("project_id") == identity["project_id"] and response.get("active_records") == 0,
                "refreshed_scope_refused")
        CHILD_PHASE = "preservation"
        require(all((profile / name).read_bytes() == raw for name, raw in files.items() if name != ".env"),
                "fixture_settings_changed")
        return {"complete": True, "real_api_expiry_denied": True, "new_credential_accepted": True,
                "native_secret_refresh_passed": True, "native_cache_identity_changed": True,
                "prepared_and_published_journals_reconciled": True, "settings_and_synthetic_auth_preserved": True,
                "memory_records_written": False, "model_called": False}
    finally:
        secrets.reset_secret_scope(binding)


def output_limit():
    resource.setrlimit(resource.RLIMIT_FSIZE, (16384, 16384))


def cycle_receipt(received):
    expected = {"complete": True, "real_api_expiry_denied": True, "new_credential_accepted": True,
        "native_secret_refresh_passed": True, "native_cache_identity_changed": True,
        "prepared_and_published_journals_reconciled": True, "settings_and_synthetic_auth_preserved": True,
        "memory_records_written": False, "model_called": False}
    require(type(received) is dict and set(received) == set(expected)
            and all(type(received[k]) is bool and received[k] is v for k, v in expected.items()), "child_receipt")
    return received


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", type=Path)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    if args.child is not None:
        try:
            result = child(args.child, json.load(sys.stdin))
        except BaseException as error:
            result = {"complete": False, "category": "cycle_child_refused_preserve_fixture", "phase": CHILD_PHASE}
            result["exception_metadata"] = exception_metadata(error)
            status = getattr(error, "status_code", None)
            if type(status) is int and 400 <= status <= 599:
                result["native_http_status"] = status
            if valid_diagnostic(CHILD_DIAGNOSTICS):
                result["initial_status_diagnostic"] = CHILD_DIAGNOSTICS
        print(json.dumps(result))
        return 0 if result["complete"] else 1
    require(os.geteuid() == 0 and Path(sys.prefix) == BASE / "runtime", "protected_operator_python_required")
    os.umask(0o077)
    evidence = Path(tempfile.mkdtemp(prefix="ec-credential-cycle-", dir="/var/tmp"))
    result = {"complete": False, "stage": "real_credential_cycle_components", "evidence": str(evidence),
              "source_revision": REVISION, "installed_issuer_qualified": False,
              "running_gateway_reload_qualified": False, "scheduled_firing_qualified": False,
              "existing_profiles_changed": False, "fleet_launch_approved": False}
    try:
        result["checkpoint"] = "source_preflight"
        run_id = uuid.uuid4().hex[:16]
        account = pwd.getpwnam("hermes-runtime")
        root = Path(__file__).absolute().parents[1]
        source = {}
        for name, expected in FILES.items():
            path = root / name
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                require(stat.S_ISREG(info.st_mode) and info.st_size <= 65536, "source_size")
                raw = stream.read(65537)
            require(hashlib.sha256(raw).hexdigest() == expected, "source_hash")
            source[name] = raw
        protected(BASE)
        artifact = BASE / ("credential-cycle-" + run_id)
        artifact.mkdir(mode=0o755)
        artifact.chmod(0o755)
        for name, raw in source.items():
            target = artifact / name
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            target.parent.chmod(0o755)
            with target.open("xb") as stream:
                stream.write(raw)
            target.chmod(0o644)
        script = artifact / "cycle.py"
        script.write_bytes(Path(__file__).read_bytes())
        script.chmod(0o644)
        result["operator_helper_sha256"] = hashlib.sha256(script.read_bytes()).hexdigest()
        protected(FIXTURES.parent)
        if not FIXTURES.exists():
            FIXTURES.mkdir(mode=0o755)
            FIXTURES.chmod(0o755)
        protected(FIXTURES)
        require(stat.S_IMODE(FIXTURES.stat().st_mode) == 0o755, "fixture_parent_directory_read_access")
        profile = FIXTURES / run_id
        profile.mkdir(mode=0o700)
        os.chown(profile, account.pw_uid, account.pw_gid)
        core = definitions(artifact / "deployment/provision_pilot_access.py", "cycle_root_issuer")
        result["checkpoint"] = "ordinary_claims"
        core["IDENTITY"] = claims_for(run_id)
        now = int(time.time())
        key = core["load_signing_key"]()
        bundle = core["make_bundle"](key, now)
        expires = now + 60
        old = core["sign_claims"](dict(core["IDENTITY"], iat=expires-86400, exp=expires), key)
        del key
        data = json.dumps({"run_id": run_id, "old": old, "bundle": bundle, "expires_at": expires}).encode()
        require(len(data) < 8192, "ordinary_bundle_budget")
        executable = RELEASE / "venv/bin/python"
        protected(executable.resolve(strict=True))
        result["checkpoint"] = "restricted_child"
        with ((evidence / "bounded-child-receipt.json").open("xb") as output,
              (evidence / "bounded-child-stderr.log").open("xb") as errors):
            process = subprocess.run(["/usr/bin/setpriv", "--no-new-privs", "--", str(executable), "-I", "-B",
                    str(script), "--child", str(artifact)], input=data, stdout=output, stderr=errors,
                user=account.pw_uid, group=account.pw_gid, extra_groups=(), cwd="/", timeout=110,
                preexec_fn=output_limit, env={"PATH": "/usr/bin:/bin", "HOME": str(profile), "HERMES_HOME": str(profile),
                    "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1",
                    "LITELLM_LOCAL_MODEL_COST_MAP": "True"})
        received = json.loads((evidence / "bounded-child-receipt.json").read_bytes())
        result["child_stderr_bytes"] = (evidence / "bounded-child-stderr.log").stat().st_size
        result["checkpoint"] = "child_receipt"
        phases = {"identity", "source_load", "fixture_files", "native_imports", "initial_status", "initial_native_status", "fixture_transaction_open",
                  "interruption_prepared", "interruption_published", "await_expiry", "expired_refusal",
                  "native_refresh", "new_status", "preservation"}
        if isinstance(received, dict) and received.get("complete") is False and received.get("phase") in phases:
            result["child_failure_phase"] = received["phase"]
            # Child ran the hash-recorded helper in a root-owned artifact. Still
            # project only exact bounded metadata rather than arbitrary JSON.
            metadata = received.get("exception_metadata")
            if isinstance(metadata, list) and len(metadata) <= 4:
                allowed = {"ValueError", "TypeError", "AttributeError", "KeyError", "NameError", "RuntimeError",
                           "MemoryTransportError", "PermissionError", "FileNotFoundError", "OSError",
                           "URLError", "HTTPError", "TimeoutError", "other"}
                if all(isinstance(row, dict) and set(row) <= {"kind", "errno", "helper_lines"}
                       and row.get("kind") in allowed and isinstance(row.get("helper_lines"), list)
                       and len(row["helper_lines"]) <= 4
                       and all(type(n) is int and 0 < n < 10000 for n in row["helper_lines"])
                       and ("errno" not in row or type(row["errno"]) is int and 0 < row["errno"] < 4096)
                       for row in metadata):
                    result["exception_metadata"] = metadata
            if valid_diagnostic(received.get("initial_status_diagnostic")):
                result["initial_status_diagnostic"] = received["initial_status_diagnostic"]
            status = received.get("native_http_status")
            if type(status) is int and 400 <= status <= 599:
                result["native_http_status"] = status
        require(process.returncode == 0, "child_exit")
        result.update(cycle_receipt(received))
        result["synthetic_fixture"] = str(profile)
    except BaseException:
        result["category"] = "credential_cycle_incomplete_preserve_evidence"
    (evidence / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
