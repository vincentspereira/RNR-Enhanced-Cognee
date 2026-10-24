"""Install staged, recovery-prefix-only cache identity; preserve existing ACLs.

Fixed protected inputs, bounded cache restart, no worker privilege expansion.
No encryption-key changes, agent profile traversal or secret output.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import signal
import socket
import time
from urllib.parse import quote, unquote, urlsplit

STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
ACL = Path("/etc/enhanced-cognee/valkey-users.acl")
AUTHORITY = Path("/etc/enhanced-cognee/launch-cache-authority.json")
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"


def acl_addition(original, username, password):
    if not re.fullmatch(r"ec_operator_[0-9a-f]{12}", username) or not isinstance(password, str) or len(password) < 40:
        raise ValueError("generated_operator_identity_required")
    for line in original.decode("ascii").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        tokens = shlex.split(line, comments=False)
        if tokens[:2] == ["user", username]:
            raise ValueError("existing_cache_operator_preserved")
    rule = ("user "+username+" reset on #"+hashlib.sha256(password.encode()).hexdigest()
            +" ~ec:lr_*:* -@all +ping +get +set +del\n").encode("ascii")
    return original + (b"\n" if original and not original.endswith(b"\n") else b"") + rule


def read_reply(stream):
    line = stream.readline(4097)
    if len(line) > 4096 or not line.endswith(b"\r\n"):
        raise ValueError("bounded_cache_response_required")
    if line[:1] == b"-":
        return "refused", None
    if line[:1] == b"+":
        return "simple", line[1:-2]
    if line[:1] == b":":
        return "integer", int(line[1:-2])
    if line[:1] == b"$":
        size = int(line[1:-2])
        if size == -1:
            return "bulk", None
        if not 0 <= size <= 4096:
            raise ValueError("bounded_cache_response_required")
        raw = stream.read(size+2)
        if len(raw) != size+2 or raw[-2:] != b"\r\n":
            raise ValueError("bounded_cache_response_required")
        return "bulk", raw[:-2]
    raise ValueError("bounded_cache_response_required")


def command(sock, stream, *parts):
    encoded = [x if isinstance(x, bytes) else str(x).encode() for x in parts]
    sock.sendall(b"*"+str(len(encoded)).encode()+b"\r\n"+b"".join(
        b"$"+str(len(x)).encode()+b"\r\n"+x+b"\r\n" for x in encoded))
    return read_reply(stream)


def cache_call(username, password, *parts):
    with socket.create_connection(("127.0.0.1", 28537), timeout=3) as sock:
        with sock.makefile("rb") as stream:
            if command(sock, stream, "AUTH", username, password) != ("simple", b"OK"):
                return "refused", None
            return command(sock, stream, *parts)


def ping(username, password):
    deadline = time.monotonic()+30
    while time.monotonic() < deadline:
        try:
            return cache_call(username, password, "PING") == ("simple", b"PONG")
        except OSError:
            time.sleep(1)
    return False


def main():
    if os.geteuid() != 0:
        raise ValueError("local_root_operator_required")
    os.umask(0o077)
    source = Path(__file__).with_name("recover_launch_graph_operator.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != SHARED_SHA256:
        raise ValueError("reviewed_shared_source_required")
    shared = {"__name__":"verified_cache_file_primitives"}
    exec(compile(source, "<verified-cache-file-primitives>", "exec"), shared)
    shared["UNIT"] = "enhanced-cognee-cache.service"
    read, write, replace, control = (shared[k] for k in ("read_file", "private_write", "replace_file", "control"))
    candidate = json.loads(read(STAGE / "replacement-logins.private.json", 0))["valkey"]["operator"]
    username, password = candidate["username"], candidate["password"]
    original = read(ACL, 0)
    replacement = acl_addition(original, username, password)
    worker = json.loads(read(Path("/etc/enhanced-cognee/worker.json"), 0))
    uri = urlsplit(worker["INDEX_VALKEY_URL"])
    if uri.scheme != "redis" or uri.hostname not in {"127.0.0.1", "localhost"} or uri.port != 28537 or uri.path not in {"", "/0"}:
        raise ValueError("fixed_cache_binding_required")
    old_user, old_password = unquote(uri.username or "default"), unquote(uri.password or "")
    if not ping(old_user, old_password):
        raise ValueError("existing_worker_cache_authentication_required")
    if os.path.lexists(AUTHORITY):
        raise ValueError("existing_operator_authority_preserved")
    attempt = STAGE / "cache-operator-installation"
    attempt.mkdir(mode=0o700)
    write(attempt / "users.before.acl", original)
    result = {"complete":False, "evidence":str(attempt), "cache_service_restarted":False,
        "existing_worker_rules_changed":False, "profiles_changed":False, "encryption_keys_changed":False,
        "all_credentials_rotated":False, "fleet_launch_approved":False}
    touched = False
    def interrupted(signum, frame):
        raise InterruptedError("operator_interrupted")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        write(attempt / "before-stop.json", b'{"installation_started":true}')
        touched = True
        control("stop")
        if read(ACL, 0) != original:
            raise ValueError("cache_acl_changed_before_stop")
        replace(ACL, replacement, 0)
        control("start")
        result["cache_service_restarted"] = True
        if not ping(username, password) or not ping(old_user, old_password):
            raise ValueError("new_or_existing_cache_authentication_failed")
        key = "ec:lr_"+secrets.token_hex(8)+":"+"a"*64
        if (cache_call(username,password,"SET",key,"invented-recovery-probe","EX",60) != ("simple", b"OK")
                or cache_call(username,password,"GET",key) != ("bulk",b"invented-recovery-probe")
                or cache_call(username,password,"DEL",key) != ("integer",1)
                or cache_call(username,password,"GET","ec:outside-recovery:"+secrets.token_hex(8))[0] != "refused"):
            raise ValueError("cache_recovery_prefix_acceptance_failed")
        url = "redis://"+quote(username,safe="")+":"+quote(password,safe="")+"@127.0.0.1:28537/0"
        write(AUTHORITY, json.dumps({"INDEX_VALKEY_URL":url}).encode())
        result.update(complete=True, new_operator_authenticated=True, existing_worker_authenticated=True,
            new_namespace_set_get_delete_verified=True, other_namespace_denied=True,
            protected_operator_authority_installed=True)
    except BaseException:
        result["category"] = "cache_operator_installation_failed_preserve_evidence"
        if touched:
            try:
                control("stop")
                write(attempt / "users.failed.acl", read(ACL, 0))
                replace(ACL, original, 0)
                control("start")
                result["rollback_worker_authenticated"] = ping(old_user, old_password)
                if os.path.lexists(AUTHORITY):
                    os.rename(AUTHORITY, AUTHORITY.with_name(AUTHORITY.name+".failed-"+secrets.token_hex(8)))
            except BaseException:
                result["rollback_worker_authenticated"] = False
    write(attempt / "summary.json", json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError):
        print('{"complete":false,"category":"cache_operator_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
