"""Recover the built-in graph operator using the exact protected staged secret.

Bounded graph stop/start; preserve all user-file bytes before replacement and
restore on failed verification. No graph database, profile, encryption key or
other store is changed. Built-in root is required for server-level commands.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import pwd
import secrets
import signal
import stat
import subprocess
import time

STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
USERS = Path("/var/lib/enhanced-cognee/arcade/config/server-users.jsonl")
AUTHORITY = Path("/etc/enhanced-cognee/launch-index-authority.json")
UNIT = "enhanced-cognee-graph.service"


def read_file(path, owner, limit=262144):
    for parent in reversed(path.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, owner} or info.st_mode & 0o022:
            raise ValueError("protected_ancestor_required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != owner or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > limit:
            raise ValueError("protected_file_required")
        raw = stream.read(limit+1)
        if len(raw) > limit:
            raise ValueError("input_budget")
        return raw


def private_write(path, raw, owner=0):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        os.fchown(stream.fileno(), owner, pwd.getpwuid(owner).pw_gid)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def replace_file(path, raw, owner):
    candidate = path.with_name(path.name + ".candidate-" + secrets.token_hex(8))
    private_write(candidate, raw, owner)
    os.replace(candidate, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def password_hash(password, salt=None):
    # ArcadeDB PBKDF2 uses the Base64 text as salt, not the decoded bytes.
    salt = salt or base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 65536, dklen=32)
    return "PBKDF2WithHmacSHA256$65536$" + salt + "$" + base64.b64encode(derived).decode("ascii")


def matches(password, encoded):
    parts = encoded.split("$")
    if len(parts) != 4 or parts[0] != "PBKDF2WithHmacSHA256" or parts[1] != "65536":
        return False
    return hmac.compare_digest(password_hash(password, parts[2]), encoded)


def replace_root(raw, password):
    lines = raw.splitlines(keepends=True)
    rows = [json.loads(line) for line in lines if line.strip()]
    if (not rows or any(not isinstance(r, dict) or not {"name", "password", "databases"} <= r.keys() for r in rows)
            or len({r["name"] for r in rows}) != len(rows)
            or sum(r["name"] == "root" for r in rows) != 1):
        raise ValueError("unique_builtin_root_schema_required")
    output = []
    for line in lines:
        if line.strip():
            row = json.loads(line)
            if row["name"] == "root":
                row["password"] = password_hash(password)
                line = json.dumps(row, ensure_ascii=True).encode() + b"\n"
        output.append(line)
    return b"".join(output), rows


def graph_status(username, password):
    client = HTTPConnection("127.0.0.1", 28536, timeout=3)
    try:
        header = base64.b64encode((username+":"+password).encode()).decode("ascii")
        client.request("GET", "/api/v1/server?mode=basic", headers={"Authorization": "Basic "+header})
        response = client.getresponse()
        response.read(8193)
        return response.status
    finally:
        client.close()


def control(action):
    process = subprocess.run(["/usr/bin/systemctl", action, UNIT], capture_output=True,
        timeout=45, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
    if process.returncode:
        raise ValueError("graph_service_control_failed")


def await_status(username, password):
    deadline = time.monotonic()+45
    while time.monotonic() < deadline:
        try:
            code = graph_status(username, password)
            if code == 200:
                return True
            if code in {401, 403}:
                return False
        except OSError:
            pass
        time.sleep(1)
    return False


def main():
    if os.geteuid() != 0:
        raise ValueError("local_root_operator_required")
    os.umask(0o077)
    candidates = json.loads(read_file(STAGE / "replacement-logins.private.json", 0))
    password = candidates["arcadedb"]["operator"]["password"]
    if not isinstance(password, str) or len(password) < 40 or not password.isascii():
        raise ValueError("generated_stage_secret_required")
    worker = json.loads(read_file(Path("/etc/enhanced-cognee/worker.json"), 0))
    api = json.loads(read_file(Path("/etc/enhanced-cognee/api.json"), 0))
    if any(x.get("INDEX_ARCADEDB_USER") == "root" for x in (api, worker)):
        raise ValueError("root_service_clients_require_coordinated_rotation")
    owner = pwd.getpwnam("ecmem_graph").pw_uid
    original = read_file(USERS, owner)
    replacement, rows = replace_root(original, password)
    worker_name, worker_password = worker["INDEX_ARCADEDB_USER"], worker["INDEX_ARCADEDB_PASSWORD"]
    if not any(r["name"] == worker_name and matches(worker_password, r["password"]) for r in rows):
        raise ValueError("installed_hash_format_not_verified")
    if graph_status(worker_name, worker_password) != 200:
        raise ValueError("existing_worker_authentication_required")
    if graph_status(worker_name, "invented-invalid-control-"+secrets.token_hex(8)) not in {401, 403}:
        raise ValueError("graph_authentication_refusal_required")
    previous_authority = None
    if os.path.lexists(AUTHORITY):
        previous_authority = read_file(AUTHORITY, 0)
        if json.loads(previous_authority).get("INDEX_ARCADEDB_USER") != "ARCADEDB_PASSWORD":
            raise ValueError("existing_operator_authority_requires_review")
    attempt = STAGE / "graph-operator-recovery"
    attempt.mkdir(mode=0o700)  # Existing/incomplete attempt refuses replay.
    private_write(attempt / "server-users.before.jsonl", original)
    private_write(attempt / "server-groups.before.json", read_file(USERS.with_name("server-groups.json"), owner))
    if previous_authority is not None:
        private_write(attempt / "operator-authority.before.json", previous_authority)
    result = {"complete": False, "evidence": str(attempt), "graph_service_restarted": False,
        "other_stores_changed": False, "profiles_changed": False, "memory_data_changed": False,
        "all_credentials_rotated": False, "fleet_launch_approved": False}
    stopped = False
    modified = False
    def interrupted(signum, frame):
        raise InterruptedError("operator_interrupted")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        private_write(attempt / "before-stop.json", b'{"rotation_started":true}')
        stopped = True
        control("stop")
        if read_file(USERS, owner) != original:
            raise ValueError("graph_user_file_changed_before_stop")
        modified = True
        replace_file(USERS, replacement, owner)
        private_write(attempt / "user-file-replaced.json", b'{"graph_root_password_replaced":true}')
        control("start")
        result["graph_service_restarted"] = True
        if not await_status("root", password) or graph_status(worker_name, worker_password) != 200:
            raise ValueError("new_operator_or_existing_worker_refused")
        authority = json.dumps({"INDEX_ARCADEDB_USER": "root", "INDEX_ARCADEDB_PASSWORD": password}).encode()
        replace_file(AUTHORITY, authority, 0)
        result.update(complete=True, installed_hash_format_verified=True,
            graph_root_password_replaced=True, existing_user_entries_preserved=True,
            existing_worker_authenticated=True, new_operator_authenticated=True,
            protected_operator_authority_installed=True, previous_root_hash_retained=True)
    except BaseException:
        result["category"] = "graph_operator_recovery_failed_preserve_evidence"
        if stopped:
            try:
                control("stop")
                if modified:
                    private_write(attempt / "server-users.failed.jsonl", read_file(USERS, owner))
                    replace_file(USERS, original, owner)
                control("start")
                result["rollback_worker_authenticated"] = await_status(worker_name, worker_password)
                # A failed fsync may follow a successful atomic authority
                # replacement. Restore its prior state as well as the user file.
                if os.path.lexists(AUTHORITY):
                    current = read_file(AUTHORITY, 0)
                    if json.loads(current).get("INDEX_ARCADEDB_PASSWORD") == password:
                        private_write(attempt / "operator-authority.failed.json", current)
                        if previous_authority is not None:
                            replace_file(AUTHORITY, previous_authority, 0)
                        else:
                            os.rename(AUTHORITY, AUTHORITY.with_name(AUTHORITY.name+".failed-"+secrets.token_hex(8)))
            except (OSError, ValueError, subprocess.SubprocessError):
                result["rollback_worker_authenticated"] = False
    private_write(attempt / "summary.json", json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        allowed = {"local_root_operator_required", "generated_stage_secret_required",
                   "root_service_clients_require_coordinated_rotation", "installed_hash_format_not_verified",
                   "existing_worker_authentication_required", "graph_authentication_refusal_required",
                   "existing_operator_authority_requires_review", "unique_builtin_root_schema_required",
                   "protected_ancestor_required", "protected_file_required", "input_budget"}
        reason = str(error) if type(error) is ValueError and str(error) in allowed else "protected_input_or_service_error"
        print(json.dumps({"complete": False, "category": "graph_recovery_preflight_refused_no_secret_output",
                          "reason": reason}))
        raise SystemExit(1)
