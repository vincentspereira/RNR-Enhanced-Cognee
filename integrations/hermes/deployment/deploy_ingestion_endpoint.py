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
SOURCES = {"src/ingestion.py": None, "src/llm_summarize.py": None,
           "src/memory_api.py": None}
SERVICE = "enhanced-cognee-api.service"
RUNTIME_PYTHON = Path("/opt/enhanced-cognee-memory/runtime/bin/python")
HEALTH = "http://127.0.0.1:28080/health/ready"
LLM_CREDENTIAL = Path("/etc/enhanced-cognee/llm.json")
LLM_DROPIN = Path("/etc/systemd/system/enhanced-cognee-api.service.d/30-llm.conf")
DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"
DEFAULT_MODEL = "GLM-5.3-Flash"


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
    """Every directory holding the service's src/memory_api.py: paths named
    by the unit AND the site-packages of every interpreter the unit names."""
    code, out = systemctl("cat", SERVICE)
    require(code == 0, "unit_cat_failed")
    require(len(out) <= 65536, "unit_oversized")
    roots, interpreters, unit_lines = [], [RUNTIME_PYTHON], []
    for line in out.splitlines():
        unit_lines.append(line)
        if line.startswith("WorkingDirectory="):
            roots.append(Path(line.split("=", 1)[1].strip().strip('"')))
        if line.startswith("Environment=") and "PYTHONPATH" in line:
            for entry in line.split("=", 1)[1].split(":"):
                entry = entry.strip().strip('"').replace("PYTHONPATH=", "")
                if entry:
                    roots.append(Path(entry))
        if line.startswith("ExecStart="):
            parts = line.split("=", 1)[1].strip().split()
            if parts:
                interpreters.append(Path(parts[0]))
    found = []
    for candidate in roots:
        if (candidate / "src" / "memory_api.py").is_file():
            found.append(candidate / "src")
    for interpreter in interpreters:
        for site_src in sorted(Path(interpreter).parent.parent.glob(
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
    """AUTHENTICATED probe: the boundary's 401 fires before routing, so an
    unauthenticated check proves nothing. With a real role token an empty
    body must reach validation (422); old code answers 405 because
    /v1/memories/{record_id} swallows the path."""
    import urllib.error
    env = Path("/home/vincentspereira/.hermes/profiles/web-researcher/.env")
    token = ""
    for line in env.read_text().splitlines():
        if line.startswith("ENHANCED_COGNEE_ACCESS_TOKEN="):
            token = line.split("=", 1)[1].strip()
    if not token:
        raise ValueError("probe_token_missing")
    request = urllib.request.Request("http://127.0.0.1:28080/v1/memories/ingest",
                                     data=b"{}", method="POST",
                                     headers={"Authorization": "Bearer " + token,
                                              "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status in (200, 422)
    except urllib.error.HTTPError as exc:
        return exc.code in (200, 422)
    except Exception:
        return False


def install_llm_route():
    """Interactive one-time credential setup: prompts on the owner terminal,
    writes root-only llm.json plus the LoadCredential drop-in. Skips
    silently when already installed or when no prompt is possible."""
    import getpass
    if LLM_CREDENTIAL.exists() or LLM_DROPIN.exists():
        return "already-installed"
    if not sys.stdin.isatty():
        return "skipped-no-tty-configure-separately"
    print("Configure the memory model route (approved LLM route A).")
    print("The key is written only to %s (root, 0600) and never echoed." % LLM_CREDENTIAL)
    base_url = input("Base URL [%s]: " % DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    model = input("Model [%s]: " % DEFAULT_MODEL).strip() or DEFAULT_MODEL
    api_key = getpass.getpass("API key (hidden): ").strip()
    if not api_key:
        return "skipped-no-key"
    cap = input("Daily token cap per project [50000]: ").strip() or "50000"
    LLM_CREDENTIAL.write_text(json.dumps({
        "base_url": base_url, "api_key": api_key, "model": model,
        "daily_token_cap": int(cap)}, indent=1) + "\n")
    LLM_CREDENTIAL.chmod(0o600)
    LLM_DROPIN.write_text(
        "[Service]\nLoadCredential=llm.json:%s\n" % LLM_CREDENTIAL)
    LLM_DROPIN.chmod(0o644)
    return "installed"


def probe_role_token():
    env = Path("/home/vincentspereira/.hermes/profiles/web-researcher/.env")
    for line in env.read_text().splitlines():
        if line.startswith("ENHANCED_COGNEE_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise ValueError("probe_token_missing")


def authenticated_status(path):
    """Returns (code, body, diagnostic) - the diagnostic carries the raw
    first bytes so a refusal is never debugged blind."""
    import urllib.error
    request = urllib.request.Request("http://127.0.0.1:28080" + path,
                                     headers={"Authorization": "Bearer "
                                              + probe_role_token()})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read(2048)
            try:
                body = json.loads(raw) if raw else {}
            except ValueError:
                body = {}
            return response.status, body, raw[:200].decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, {}, exc.read(200).decode("utf-8", "replace")
    except Exception as exc:
        return 0, {}, type(exc).__name__


def main():
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") == "vincentspereira"
            and os.uname().nodename == "Ubuntu-Hermes", "owner_sudo_on_gateway_host")
    require(RUNTIME_PYTHON.is_file(), "runtime_python_missing")
    sources = pinned_sources()
    code_roots, unit_lines = locate_code_roots()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    result = {"complete": False, "code_roots": [str(root) for root in code_roots],
              "stamp": stamp}
    llm_setup = install_llm_route()
    result["llm_route_setup"] = llm_setup
    if llm_setup == "installed":
        code, _ = systemctl("daemon-reload")
        require(code == 0, "daemon_reload_failed")
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
        status_code, summarization, diag = authenticated_status(
            "/v1/memories/summarization/status")
        language_code, _, language_diag = authenticated_status(
            "/v1/memories/detect-language")
        result["probe_diagnostics"] = {
            "ingest": "ok", "summarization_status": [status_code, diag],
            "detect_language": [language_code, language_diag]}
        require(status_code == 200,
                "summarization_status_route_not_live:code=%d:diag=%s"
                % (status_code, diag[:120]))
        require(language_code in (405, 422),
                "detect_language_route_not_live:code=%d" % language_code)
        result.update(complete=True,
                      deployed={name: hashlib.sha256(raw).hexdigest()
                                for name, raw in sources.items()},
                      prior_memory_api_sha256=(hashlib.sha256(backups[
                          next(iter([t for t in backups if t.name == "memory_api.py"]))]
                      ).hexdigest() if backups else None),
                      service_restarted=True, health_ready=True,
                      ingest_route_live=True,
                      llm_route=summarization,
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
