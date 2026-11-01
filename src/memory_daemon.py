"""Launch memory services with role-specific private systemd credentials."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import struct
import sys


_COMMON = frozenset({"ENCRYPTION_MASTER_KEY", "ENHANCED_MEMORY_KEYRING_JSON", "ENHANCED_EMBEDDING_MODEL",
    "ENHANCED_MODEL_CACHE", "ENHANCED_INDEX_CONFIG", "ENHANCED_INDEX_KEY", "INDEX_ARCADEDB_USER",
    "INDEX_ARCADEDB_PASSWORD", "INDEX_QDRANT_API_KEY"})
_API = _COMMON | {"ENHANCED_MEMORY_DATABASE_URL", "ENHANCED_JWT_SECRET", "ENHANCED_OIDC_ISSUER",
    "ENHANCED_OIDC_JWKS_URI", "ENHANCED_OIDC_AUDIENCE", "ENHANCED_DASHBOARD_ORIGINS",
    "ENHANCED_RATE_LIMIT_PER_MINUTE", "ENHANCED_MAX_CONCURRENT_REQUESTS", "ENHANCED_MAX_PAYLOAD_BYTES"}
_WORKER = _COMMON | {"ENHANCED_INDEX_DATABASE_URL", "INDEX_VALKEY_URL"}
_BACKUP = frozenset({"ENHANCED_MEMORY_DATABASE_URL", "ENHANCED_BACKUP_SIGNING_KEY",
    "ENHANCED_BACKUP_SIGNING_KEY_ID", "ENHANCED_BACKUP_RECIPIENT"})
# Owner-selected local destination inside Ubuntu-Hermes. The scheduled service
# cannot inherit a cloud-sync or agent-supplied output directory.
BACKUP_DIRECTORY = "/var/backups/enhanced-cognee"


def _systemd_private_acl(fd: int, info, parent: Path) -> bool:
    """Admit systemd's root-owned, read-only, service-UID ACL credential mount."""
    try:
        directory = parent.stat()
        root = parent.parent.stat()
        if (parent.parent != Path("/run/credentials")
                or not parent.name.endswith(".service")
                or info.st_uid != 0 or info.st_gid != 0
                or stat.S_IMODE(info.st_mode) != 0o440
                or directory.st_uid != 0 or directory.st_gid != 0
                or stat.S_IMODE(directory.st_mode) != 0o550
                or root.st_uid != 0 or root.st_mode & 0o022
                or not os.statvfs(parent).f_flag & os.ST_RDONLY):
            return False

        def acl(permission):
            entries = ((1, permission, 0xFFFFFFFF), (2, permission, os.geteuid()),
                       (4, 0, 0xFFFFFFFF), (16, permission, 0xFFFFFFFF),
                       (32, 0, 0xFFFFFFFF))
            return struct.pack("<I", 2) + b"".join(struct.pack("<HHI", *entry) for entry in entries)

        # The mode's group read bit is the ACL mask, not a grant to the root
        # group. Refuse extra users/groups or any write/other access.
        return (os.getxattr(fd, "system.posix_acl_access") == acl(4)
                and os.getxattr(parent, "system.posix_acl_access") == acl(5))
    except (OSError, AttributeError, struct.error):
        return False


def credential_environment(role: str, directory: str) -> dict[str, str]:
    if role not in {"api", "worker", "backup"}:
        raise ValueError("Choose a supported service role")
    parent = Path(directory)
    if not parent.is_absolute() or parent != parent.resolve(strict=True):
        raise ValueError("Use the service manager's private credential directory")
    fd = os.open(parent / (role + ".json"), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        owned_private = info.st_uid == os.geteuid() and not info.st_mode & 0o077
        if not stat.S_ISREG(info.st_mode) or not (owned_private or _systemd_private_acl(handle.fileno(), info, parent)):
            raise ValueError("Service credential must be a private regular file with verified service access")
        raw = handle.read(65537)
    if len(raw) > 65536:
        raise ValueError("Service credential exceeded its size limit")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate service configuration field")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=unique)
    allowed = {"api": _API, "worker": _WORKER, "backup": _BACKUP}[role]
    if (not isinstance(value, dict) or set(value) - allowed
            or any(not isinstance(item, str) or "\0" in item for item in value.values())):
        raise ValueError("Unexpected service credential fields")
    required = {"api": {"ENHANCED_MEMORY_DATABASE_URL"},
        "worker": {"ENHANCED_INDEX_DATABASE_URL", "ENHANCED_INDEX_CONFIG", "ENHANCED_INDEX_KEY"},
        "backup": {"ENHANCED_MEMORY_DATABASE_URL", "ENHANCED_BACKUP_SIGNING_KEY", "ENHANCED_BACKUP_RECIPIENT"}}[role]
    if (not all(value.get(key) for key in required)
            or (role != "backup" and not (value.get("ENCRYPTION_MASTER_KEY") or value.get("ENHANCED_MEMORY_KEYRING_JSON")))):
        raise ValueError("Missing role-specific service configuration")
    if role == "backup" and len(value["ENHANCED_BACKUP_SIGNING_KEY"].encode()) < 32:
        raise ValueError("A persistent backup signing key of at least 32 bytes is required")
    environment = {key: value for key, value in os.environ.items() if key in {"LANG", "LC_ALL", "TZ"}}
    environment.update(value)
    # Optional LLM route (families 3/4): loaded with the same private-file
    # verification and exposed as env; an absent file leaves the route off.
    if role == "api":
        llm_path = parent / "llm.json"
        if llm_path.exists():
            llm_fd = os.open(llm_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
            with os.fdopen(llm_fd, "rb") as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or not (
                        info.st_uid == os.geteuid() and not info.st_mode & 0o077
                        or _systemd_private_acl(handle.fileno(), info, parent)):
                    raise ValueError("The LLM route credential must be a private regular file")
                llm_raw = handle.read(65537)
            if len(llm_raw) > 65536:
                raise ValueError("LLM route credential exceeded its size limit")
            llm_value = json.loads(llm_raw, object_pairs_hook=unique)
            llm_allowed = {"base_url", "api_key", "model", "daily_token_cap"}
            if (not isinstance(llm_value, dict) or set(llm_value) - llm_allowed
                    or not all(isinstance(llm_value.get(key), str) and llm_value[key]
                               for key in ("base_url", "api_key", "model"))
                    or not llm_value["base_url"].startswith("https://")):
                raise ValueError("Unexpected LLM route credential fields")
            environment["ENHANCED_LLM_BASE_URL"] = llm_value["base_url"]
            environment["ENHANCED_LLM_API_KEY"] = llm_value["api_key"]
            environment["ENHANCED_LLM_MODEL"] = llm_value["model"]
            environment["ENHANCED_LLM_TOKEN_CAP"] = str(llm_value.get("daily_token_cap", 50000))
    environment.update(PATH="/usr/local/bin:/usr/bin:/bin", ENHANCED_ENV="production",
        ENHANCED_REQUIRE_TENANT="1", ENHANCED_LOAD_DOTENV="0", COGNEE_LOG_FILE="false",
        COGNEE_TELEMETRY_ENABLED="0", HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1",
        PYTHONUNBUFFERED="1", ENHANCED_CAPABILITIES="")
    return environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("api", "worker", "backup"))
    args = parser.parse_args()
    try:
        env = credential_environment(args.role, os.environ["CREDENTIALS_DIRECTORY"])
        command = [sys.executable, "-m", "src.index_runtime", "run"] if args.role == "worker" else [
            sys.executable, "-m", "uvicorn", "src.memory_api:app", "--host", "127.0.0.1", "--port", "28080", "--no-access-log", "--ws", "none"]
        if args.role == "backup":
            command = [sys.executable, "-m", "src.memory_backup", "create", "--directory", BACKUP_DIRECTORY,
                       "--recipient", env["ENHANCED_BACKUP_RECIPIENT"]]
        os.execve(sys.executable, command, env)
    except Exception:
        parser.exit(1, "Service launch refused; check private role configuration. No secret values were printed.\n")


if __name__ == "__main__":
    main()
