#!/usr/bin/env python3
"""Install the approved automated fleet token renewal (timer + pinned job).

Owner-approved 30 October 2026. Copies the hash-pinned provisioner and
renewal job into /opt/enhanced-cognee-memory/fleet-renewal (refusing any
modification of an existing install), installs a hardened systemd
service+timer, enables the timer, and runs the service once immediately so
profiles already inside the 7-day window renew now. Idempotent: a repeat
run verifies and reports without changing files.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

DEPLOY = Path("/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020"
              "/launch-worktree-20261024/integrations/hermes/deployment")
VENV_PYTHON = Path("/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020"
                   "/.venv-deployment/bin/python")
RENEWAL_ROOT = Path("/opt/enhanced-cognee-memory/fleet-renewal")
SERVICE = Path("/etc/systemd/system/ec-hermes-memory-token-renew.service")
TIMER = Path("/etc/systemd/system/ec-hermes-memory-token-renew.timer")
UNIT_NAME = "ec-hermes-memory-token-renew"
# The first installed provisioner refused the unattended job (SUDO_USER-only
# operator check); the upgrade path accepts exactly that pinned predecessor.
PREVIOUS_PROVISIONER_SHA = "06ad220901f054b43a40e4ca7a6fae1b35f01e1be85ca2e905450fd5fb41903b"
SOURCES = {}  # filled in main from the live files below


def require(value, category="renewal_install_refused"):
    if not value:
        raise ValueError(category)


def pinned_sources():
    files = {"provision_gateway_profile_access.py": None,
             "renew_fleet_memory_tokens.py": None}
    for name in files:
        raw = (DEPLOY / name).read_bytes()
        require(0 < len(raw) <= 65536)
        files[name] = {"raw": raw, "sha256": hashlib.sha256(raw).hexdigest()}
    return files


def install_files(sources, upgrade):
    existing = RENEWAL_ROOT.is_dir() and any(RENEWAL_ROOT.iterdir())
    if not existing:
        RENEWAL_ROOT.mkdir(mode=0o755)
        for name, row in sources.items():
            target = RENEWAL_ROOT / name
            target.write_bytes(row["raw"])
            target.chmod(0o644)
        return True
    if not upgrade:
        for name, row in sources.items():
            current = (RENEWAL_ROOT / name).read_bytes()
            require(hashlib.sha256(current).hexdigest() == row["sha256"],
                    "existing_install_differs_use_upgrade")
        return False
    # Upgrade: each file must match its pinned predecessor (or already be
    # current) before replacement; state.json and backups stay untouched.
    for name, row in sources.items():
        current = (RENEWAL_ROOT / name).read_bytes()
        digest = hashlib.sha256(current).hexdigest()
        allowed = {row["sha256"]}
        if name == "provision_gateway_profile_access.py":
            allowed.add(PREVIOUS_PROVISIONER_SHA)
        require(digest in allowed, "upgrade_source_unknown:" + name)
    for name, row in sources.items():
        target = RENEWAL_ROOT / name
        if hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]:
            target.write_bytes(row["raw"])
            target.chmod(0o644)
    return False


def install_units():
    service = f"""[Unit]
Description=Renew Enhanced Cognee fleet memory tokens (7-day window)
After=network.target enhanced-cognee-api.service

[Service]
Type=oneshot
User=root
ExecStart={VENV_PYTHON} -I {RENEWAL_ROOT / 'renew_fleet_memory_tokens.py'}
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/home/vincentspereira/.hermes {RENEWAL_ROOT}
ProtectHome=no
"""
    timer = """[Timer]
OnCalendar=Mon *-*-* 04:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
"""
    for path, body, existing_ok in ((SERVICE, service, True), (TIMER, timer, True)):
        if path.exists():
            require(path.read_text() == body, "unit_differs_refusing_overwrite")
            continue
        path.write_text(body)
        path.chmod(0o644)


def systemctl(*args, timeout=60):
    process = subprocess.run(["/usr/bin/systemctl", *args],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return process.returncode, process.stdout.decode()[:4000]


def main():
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") == "vincentspereira"
            and os.uname().nodename == "Ubuntu-Hermes", "owner_sudo_on_gateway_host")
    require(sys.argv[1:] in ([], ["--upgrade"]), "usage: [--upgrade]")
    upgrade = sys.argv[1:] == ["--upgrade"]
    require(VENV_PYTHON.is_file(), "deployment_venv_missing")
    sources = pinned_sources()
    created = install_files(sources, upgrade)
    install_units()
    code, _ = systemctl("daemon-reload")
    require(code == 0, "daemon_reload_failed")
    code, out = systemctl("enable", "--now", UNIT_NAME + ".timer")
    require(code == 0, "timer_enable_failed:" + out[:120])
    # First run now: renews any profile already inside the window.
    code, run_out = systemctl("start", UNIT_NAME + ".service", timeout=600)
    started = code == 0
    code, timer_state = systemctl("is-active", UNIT_NAME + ".timer")
    summary = {"complete": True, "files_created": created,
               "timer_active": timer_state.strip() == "active",
               "first_run_started": started,
               "renewal_root": str(RENEWAL_ROOT),
               "pinned_sha256": {name: row["sha256"] for name, row in sources.items()},
               "schedule": "Mon *-*-* 04:00 (persistent, 5m jitter)",
               "state_file": str(RENEWAL_ROOT / "state.json")}
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False, "category": "renewal_install_refused",
                          "error_kind": type(exc).__name__,
                          "detail": str(exc)[:160] if isinstance(exc, ValueError) else ""},
                         sort_keys=True))
        raise SystemExit(1)
