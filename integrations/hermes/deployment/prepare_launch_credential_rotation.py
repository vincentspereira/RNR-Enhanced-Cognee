"""Generate protected replacement login candidates; never apply a rotation.

Fixed Enhanced Cognee scope. No agent profile traversal, secret output, network,
password guessing, account grants, service restart or encryption-key replacement.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import stat
import tempfile

BASE = Path("/var/lib/enhanced-cognee-rotation")
CONFIG = Path("/etc/enhanced-cognee")
FILES = ("api.json", "worker.json", "operator.json", "backup.json", "index.json",
         "api-database.json", "worker-database.json", "qdrant.yaml", "valkey-users.acl",
         "valkey.conf", "pg_hba.conf")
GRAPH_FILES = ("server-users.jsonl", "server-users.json", "server-groups.json")


def protected_directory(path):
    for parent in [*reversed(path.parents), path]:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("root_owned_nonwritable_directory_required")


def read_config(path):
    protected_directory(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_size > 1048576:
            raise ValueError("protected_configuration_required")
        raw = stream.read(1048577)
        after = os.fstat(stream.fileno())
        if len(raw) > 1048576 or (info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("configuration_changed_during_snapshot")
        return raw


def write_private(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def replacements():
    suffix = secrets.token_hex(6)
    result = {}
    for store in ("postgresql", "arcadedb", "valkey"):
        result[store] = {role: {"username": "ec_" + role + "_" + suffix,
                               "password": secrets.token_urlsafe(32)}
                         for role in ("api", "worker", "operator")}
    # Qdrant uses API keys, not username/password accounts. Current native
    # configuration supports a read key and an administrative/write key.
    result["qdrant"] = {role: {"api_key": secrets.token_urlsafe(32)} for role in ("readonly", "admin_write")}
    result["application"] = {"issuer": {"jwt_signing_key": secrets.token_urlsafe(32)}}
    return result


def graph_metadata():
    """Inspect only fixed store-config paths; never expose password hashes."""
    directory = Path("/var/lib/enhanced-cognee/arcade/config")
    result = []
    # The graph service owns its data. These are evidence inputs, not trusted
    # executable code or credential sources. Refuse symlink ancestors.
    for parent in [*reversed(directory.parents), directory]:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("graph_config_directory_refused")
    for name in GRAPH_FILES:
        path = directory / name
        row = {"name": name, "present": os.path.lexists(path)}
        if row["present"]:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                row.update(regular=stat.S_ISREG(info.st_mode), uid=info.st_uid,
                           mode=format(stat.S_IMODE(info.st_mode), "04o"))
                if row["regular"] and info.st_size <= 262144:
                    raw = stream.read(262145)
                    try:
                        objects = [json.loads(line) for line in raw.splitlines() if line.strip()] if name.endswith("jsonl") else [json.loads(raw)]
                        row["parsed"] = True
                        row["entry_count"] = len(objects)
                        # Report fixed known schema predicates, never arbitrary
                        # keys that might actually be usernames or secrets.
                        row["name_password_databases_schema"] = all(isinstance(x, dict)
                            and {"name", "password", "databases"} <= x.keys() for x in objects)
                        algorithms = {x["password"].split("$", 1)[0] for x in objects
                                      if isinstance(x, dict) and isinstance(x.get("password"), str)}
                        row["pbkdf2_sha256_present"] = "PBKDF2WithHmacSHA256" in algorithms
                    except (ValueError, UnicodeError):
                        row["parsed"] = False
        result.append(row)
    return result


def main():
    if os.geteuid() != 0:
        raise ValueError("local_root_operator_required")
    os.umask(0o077)
    protected_directory(BASE.parent)
    if not os.path.lexists(BASE):
        BASE.mkdir(mode=0o700)
    protected_directory(BASE)
    if stat.S_IMODE(BASE.stat().st_mode) != 0o700:
        raise ValueError("private_rotation_directory_required")
    stage = Path(tempfile.mkdtemp(prefix="candidate-", dir=BASE))
    result = {"complete": False, "stage": str(stage), "credentials_activated": False,
              "service_changed": False, "profiles_changed": False, "encryption_keys_changed": False,
              "recovery_keys_changed": False, "fleet_launch_approved": False}
    try:
        snapshots = stage / "configuration-before"
        snapshots.mkdir(mode=0o700)
        count = 0
        for name in FILES:
            path = CONFIG / name
            if os.path.lexists(path):
                write_private(snapshots / name, read_config(path))
                count += 1
        write_private(stage / "replacement-logins.private.json", json.dumps(replacements(), ensure_ascii=True).encode())
        result.update(configuration_snapshots=count, replacement_identity_count=12,
                      credentials_generated=True, rollback_is_service_qualified=False)
        try:
            result["graph_authentication_metadata"] = graph_metadata()
        except (OSError, ValueError):
            result["graph_metadata_unavailable"] = True
        result["complete"] = True
    except (OSError, ValueError):
        result["category"] = "credential_preparation_incomplete_preserve_stage"
    write_private(stage / "summary.json", json.dumps(result, ensure_ascii=True).encode())
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError):
        print('{"complete":false,"category":"protected_operator_preparation_refused"}')
        raise SystemExit(1)
