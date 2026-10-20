"""Launch API/worker with role-specific systemd credentials, never agent keys."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys


_COMMON = frozenset({"ENCRYPTION_MASTER_KEY", "ENHANCED_MEMORY_KEYRING_JSON", "ENHANCED_EMBEDDING_MODEL",
    "ENHANCED_MODEL_CACHE", "ENHANCED_INDEX_CONFIG", "ENHANCED_INDEX_KEY", "INDEX_ARCADEDB_USER",
    "INDEX_ARCADEDB_PASSWORD", "INDEX_QDRANT_API_KEY"})
_API = _COMMON | {"ENHANCED_MEMORY_DATABASE_URL", "ENHANCED_JWT_SECRET", "ENHANCED_OIDC_ISSUER",
    "ENHANCED_OIDC_JWKS_URI", "ENHANCED_OIDC_AUDIENCE", "ENHANCED_DASHBOARD_ORIGINS",
    "ENHANCED_RATE_LIMIT_PER_MINUTE", "ENHANCED_MAX_CONCURRENT_REQUESTS", "ENHANCED_MAX_PAYLOAD_BYTES"}
_WORKER = _COMMON | {"ENHANCED_INDEX_DATABASE_URL", "INDEX_VALKEY_URL"}


def credential_environment(role: str, directory: str) -> dict[str, str]:
    if role not in {"api", "worker"}:
        raise ValueError("Choose a supported service role")
    parent = Path(directory)
    if not parent.is_absolute() or parent != parent.resolve(strict=True):
        raise ValueError("Use the service manager's private credential directory")
    fd = os.open(parent / (role + ".json"), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise ValueError("Service credential must be a private regular file owned by this service")
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
    allowed = _API if role == "api" else _WORKER
    if (not isinstance(value, dict) or set(value) - allowed
            or any(not isinstance(item, str) or "\0" in item for item in value.values())):
        raise ValueError("Unexpected service credential fields")
    required = {"ENHANCED_MEMORY_DATABASE_URL"} if role == "api" else {"ENHANCED_INDEX_DATABASE_URL", "ENHANCED_INDEX_CONFIG", "ENHANCED_INDEX_KEY"}
    if not all(value.get(key) for key in required) or not (value.get("ENCRYPTION_MASTER_KEY") or value.get("ENHANCED_MEMORY_KEYRING_JSON")):
        raise ValueError("Missing role-specific service configuration")
    environment = {key: value for key, value in os.environ.items() if key in {"LANG", "LC_ALL", "TZ"}}
    environment.update(value)
    environment.update(PATH="/usr/local/bin:/usr/bin:/bin", ENHANCED_ENV="production",
        ENHANCED_REQUIRE_TENANT="1", ENHANCED_LOAD_DOTENV="0", COGNEE_LOG_FILE="false",
        COGNEE_TELEMETRY_ENABLED="0", HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1",
        PYTHONUNBUFFERED="1", ENHANCED_CAPABILITIES="")
    return environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("api", "worker"))
    args = parser.parse_args()
    try:
        env = credential_environment(args.role, os.environ["CREDENTIALS_DIRECTORY"])
        command = [sys.executable, "-m", "src.index_runtime", "run"] if args.role == "worker" else [
            sys.executable, "-m", "uvicorn", "src.memory_api:app", "--host", "127.0.0.1", "--port", "28080", "--no-access-log"]
        os.execve(sys.executable, command, env)
    except Exception:
        parser.exit(1, "Service launch refused; check private role configuration. No secret values were printed.\n")


if __name__ == "__main__":
    main()
