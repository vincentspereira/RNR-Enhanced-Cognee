#!/usr/bin/env python3
"""Issue scoped Enhanced Cognee tokens for every fleet role profile.

Human-operated, root-only operator convenience: iterates the gateway's role
profiles (excluding the app-level default profile and the two retained
canary profiles) and runs the reviewed per-profile provisioner for each,
continuing past failures so one bad role never blocks the batch. Prints one
JSON summary with per-role receipts; never prints token values. The gateway
config must already select memory.provider (roles fail closed until their
sessions load, which is the intended safe state).
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys

HOME = Path("/home/vincentspereira/.hermes")
PROFILES = HOME / "profiles"
EXCLUDED = {"enhanced-cognee-test", "enhanced-cognee-test-two", "default"}
PROVISIONER = Path(__file__).resolve().parent / "provision_gateway_profile_access.py"
MAX_ENV = 65536


def require(value, category="fleet_batch_provision_refused"):
    if not value:
        raise ValueError(category)


def role_names():
    require(PROFILES.is_dir())
    names = sorted(child.name for child in PROFILES.iterdir()
                   if child.is_dir() and (child / ".env").is_file()
                   and child.name not in EXCLUDED)
    require(1 <= len(names) <= 64, "fleet_role_count_invalid")
    return names


def run_provisioner(python: str, role: str, ttl_hours: int, fresh: bool):
    args = [python, "-I", str(PROVISIONER), "--profile", role,
            "--ttl-hours", str(ttl_hours)]
    if fresh:
        args.append("--fresh-namespace")
    process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=120)
    require(len(process.stdout) <= MAX_ENV)
    try:
        receipt = json.loads(process.stdout)
    except ValueError:
        receipt = {"complete": False, "category": "unparseable_output"}
    require(isinstance(receipt, dict) and "complete" in receipt)
    return receipt


def main():
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") == "vincentspereira"
            and os.uname().nodename == "Ubuntu-Hermes",
            "run_as_owner_sudo_on_gateway_host")
    args = sys.argv[1:]
    ttl, fresh = 720, False
    if "--ttl-hours" in args:
        index = args.index("--ttl-hours")
        require(len(args) >= index + 2, "usage: --ttl-hours N [--fresh-namespace]")
        ttl = int(args[index + 1])
        fresh = "--fresh-namespace" in args
        require(1 <= ttl <= 8760, "fleet_ttl_invalid")
    require("venv-deployment" in sys.executable,
            "needs_the_deployment_venv_interpreter_for_dotenv")
    roles = role_names()
    receipts, failed = {}, []
    for role in roles:
        receipt = run_provisioner(sys.executable, role, ttl, fresh)
        receipts[role] = {"complete": bool(receipt.get("complete")),
                          "expires_utc": receipt.get("expires_utc"),
                          "error": receipt.get("detail") or receipt.get("error_kind")}
        if not receipt.get("complete"):
            failed.append(role)
        print(json.dumps({"role": role, "complete": receipt.get("complete")}), flush=True)
    summary = {"complete": not failed, "roles_total": len(roles),
               "roles_failed": failed, "ttl_hours": ttl,
               "token_value_emitted": False, "fleet_admission_enabled": False,
               "receipts": receipts}
    out = HOME / "fleet-token-receipts.json"
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"summary_file": str(out), "roles_total": len(roles),
                      "roles_failed": failed, "complete": not failed}), flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        detail = str(exc)[:160] if isinstance(exc, ValueError) else ""
        print(json.dumps({"complete": False, "category": "fleet_batch_provision_refused",
                          "error_kind": type(exc).__name__, "detail": detail}), flush=True)
        raise SystemExit(1)
