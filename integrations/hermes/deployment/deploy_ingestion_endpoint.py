#!/usr/bin/env python3
"""Deploy the reviewed ingestion endpoint to the live memory API.

Owner-run, root-only. Locates the service code root from the unit's own
definition (WorkingDirectory/PYTHONPATH drop-ins; root can read them),
records the pre-update hash, backs up, copies the hash-pinned sources,
compiles them with the service runtime python, restarts the API service,
and verifies /health/ready. On any failure the backups are restored and
the service restarted again; nothing is left half-deployed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

WORKTREE = Path("/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020"
                "/launch-worktree-20261024")
SOURCES = {"src/ingestion.py": None, "src/memory_api.py": None}
SERVICE = "enhanced-cognee-api.service"
RUNTIME_PYTHON = Path("/opt/enhanced-cognee-memory/runtime/bin/python")
HEALTH = "http://127.0.0.1:28080/health/ready"


def require(value, category="ingestion_deploy_refused"):
    if not value:
        raise ValueError(category)


def pinned_sources():
    for name in SOURCES:
        raw = (WORKTREE / name).read_bytes()
        require(0 < len(raw) <= 262144)
        SOURCES[name] = raw
    return dict(SOURCES)


def systemctl(*args, timeout=90):
    process = subprocess.run(["/usr/bin/systemctl", *args],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=timeout)
    return process.returncode, process.stdout.decode()


def locate_code_root():
    code, out = systemctl("cat", SERVICE)
    require(code == 0, "unit_cat_failed")
    require(len(out) <= 65536, "unit_oversized")
    candidates = []
    for line in out.splitlines():
        if line.startswith("WorkingDirectory="):
            candidates.append(Path(line.split("=", 1)[1].strip()))
        if line.startswith("Environment=") and "PYTHONPATH" in line:
            for entry in line.split("=", 1)[1].split(":"):
                entry = entry.strip()
                if entry and "PYTHONPATH" not in entry:
                    candidates.append(Path(entry))
    for candidate in candidates:
        if (candidate / "src" / "memory_api.py").is_file():
            return candidate / "src"
    raise ValueError("service_code_root_not_found")


def health_ready(deadline_seconds=30):
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(HEALTH, timeout=5) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def main():
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") == "vincentspereira"
            and os.uname().nodename == "Ubuntu-Hermes", "owner_sudo_on_gateway_host")
    require(RUNTIME_PYTHON.is_file(), "runtime_python_missing")
    sources = pinned_sources()
    code_root = locate_code_root()
    require((code_root / "memory_api.py").is_file(), "deployed_api_missing")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backups = {}
    result = {"complete": False, "code_root": str(code_root), "stamp": stamp}
    try:
        for name, raw in sources.items():
            target = code_root / Path(name).name
            backups[target] = target.read_bytes() if target.exists() else None
            backup_path = target.with_name(target.name + ".before-ingest-" + stamp)
            backup_path.write_bytes(backups[target] or raw)
            backup_path.chmod(0o644)
        for name, raw in sources.items():
            target = code_root / Path(name).name
            target.write_bytes(raw)
            target.chmod(0o644)
        for name in sources:
            compile_check = subprocess.run(
                [str(RUNTIME_PYTHON), "-I", "-B", "-m", "py_compile",
                 str(code_root / Path(name).name)],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
            require(compile_check.returncode == 0, "compile_failed:" + name)
        code, _ = systemctl("restart", SERVICE, timeout=120)
        require(code == 0, "restart_failed")
        require(health_ready(), "health_not_ready_after_restart")
        result.update(complete=True,
                      deployed={name: hashlib.sha256(raw).hexdigest()
                                for name, raw in sources.items()},
                      prior_memory_api_sha256=(hashlib.sha256(backups[
                          code_root / "memory_api.py"]).hexdigest()
                          if backups.get(code_root / "memory_api.py") else None),
                      service_restarted=True, health_ready=True)
    except Exception as exc:
        # Roll back to the recorded bytes and restart again.
        for target, raw in backups.items():
            if raw is not None:
                target.write_bytes(raw)
        systemctl("restart", SERVICE, timeout=120)
        result.update(category="ingestion_deploy_failed_rolled_back",
                      error_kind=type(exc).__name__,
                      detail=str(exc)[:160] if isinstance(exc, ValueError) else "")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False, "category": "ingestion_deploy_refused",
                          "error_kind": type(exc).__name__,
                          "detail": str(exc)[:160] if isinstance(exc, ValueError) else ""},
                         sort_keys=True))
        raise SystemExit(1)
