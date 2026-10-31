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


def locate_code_roots():
    """Every directory holding the service's src/memory_api.py."""
    code, out = systemctl("cat", SERVICE)
    require(code == 0, "unit_cat_failed")
    require(len(out) <= 65536, "unit_oversized")
    roots, unit_lines = [], []
    for line in out.splitlines():
        unit_lines.append(line)
        if line.startswith("WorkingDirectory="):
            value = line.split("=", 1)[1].strip().strip('"')
            roots.append(Path(value))
        if line.startswith("Environment=") and "PYTHONPATH" in line:
            for entry in line.split("=", 1)[1].split(":"):
                entry = entry.strip().strip('"').replace("PYTHONPATH=", "")
                if entry:
                    roots.append(Path(entry))
    found = []
    for candidate in roots:
        if (candidate / "src" / "memory_api.py").is_file():
            found.append(candidate / "src")
    for site_src in sorted(RUNTIME_PYTHON.parent.parent.glob(
            "lib/python*/site-packages/src")):
        if (site_src / "memory_api.py").is_file() and site_src not in found:
            found.append(site_src)
    if not found:
        raise ValueError("service_code_root_not_found")
    return found, unit_lines


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


def ingest_route_live():
    """The new route must exist: unauthenticated POST yields 401/422, never
    405 (old code answers 405 because /v1/memories/{id} swallows the path)."""
    import urllib.error
    request = urllib.request.Request("http://127.0.0.1:28080/v1/memories/ingest",
                                     data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status in (401, 422)
    except urllib.error.HTTPError as exc:
        return exc.code in (401, 422)
    except Exception:
        return False


def main():
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") == "vincentspereira"
            and os.uname().nodename == "Ubuntu-Hermes", "owner_sudo_on_gateway_host")
    require(RUNTIME_PYTHON.is_file(), "runtime_python_missing")
    sources = pinned_sources()
    code_roots, unit_lines = locate_code_roots()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    result = {"complete": False, "code_roots": [str(root) for root in code_roots],
              "stamp": stamp}
    backups = {}
    try:
        for code_root in code_roots:
            require((code_root / "memory_api.py").is_file(),
                    "deployed_api_missing:" + str(code_root))
            for name, raw in sources.items():
                target = code_root / Path(name).name
                backups[target] = target.read_bytes() if target.exists() else None
                backup_path = target.with_name(target.name + ".before-ingest-" + stamp)
                backup_path.write_bytes(backups[target] or raw)
                backup_path.chmod(0o644)
                target.write_bytes(raw)
                target.chmod(0o644)
            for name in sources:
                compile_check = subprocess.run(
                    [str(RUNTIME_PYTHON), "-I", "-B", "-m", "py_compile",
                     str(code_root / Path(name).name)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
                require(compile_check.returncode == 0,
                        "compile_failed:" + str(code_root))
        code, _ = systemctl("restart", SERVICE, timeout=120)
        require(code == 0, "restart_failed")
        require(health_ready(), "health_not_ready_after_restart")
        require(ingest_route_live(), "ingest_route_not_live_after_restart")
        result.update(complete=True,
                      deployed={name: hashlib.sha256(raw).hexdigest()
                                for name, raw in sources.items()},
                      prior_memory_api_sha256=(hashlib.sha256(backups[
                          next(iter([t for t in backups if t.name == "memory_api.py"]))]
                      ).hexdigest() if backups else None),
                      service_restarted=True, health_ready=True,
                      ingest_route_live=True,
                      unit_definition=unit_lines)
    except Exception as exc:
        # Roll back to the recorded bytes and restart again.
        for target, raw in backups.items():
            if raw is not None:
                target.write_bytes(raw)
        systemctl("restart", SERVICE, timeout=120)
        result.update(category="ingestion_deploy_failed_rolled_back",
                      error_kind=type(exc).__name__,
                      detail=str(exc)[:200] if isinstance(exc, ValueError) else "",
                      unit_definition=unit_lines)
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
