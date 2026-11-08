#!/usr/bin/env python3
"""Plan the staged credential rotation (phase A; read-only, sanitized).

Reads the staged summary values, maps each service to its live unit and
credential locations, and prints the exact apply plan: which files change,
which units restart, which verification runs per service. No credential
value is read into the plan; replacement-logins keys are mapped by name
only. The apply phase (B) is generated from this plan.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path("/var/lib/enhanced-cognee-rotation")
UNITS = ["enhanced-cognee-api.service", "enhanced-cognee-postgres.service",
         "enhanced-cognee-qdrant.service", "enhanced-cognee-graph.service",
         "enhanced-cognee-cache.service"]
LOGINS_KEYS = {"postgresql", "arcadedb", "qdrant", "valkey", "application"}


def require(value, category="rotation_plan_refused"):
    if not value:
        raise ValueError(category)


def systemctl_cat(unit):
    process = subprocess.run(["/usr/bin/systemctl", "cat", unit],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=15)
    return process.stdout.decode() if process.returncode == 0 else ""


def unit_facts(text):
    exec_start, credentials, working = [], [], None
    for line in text.splitlines():
        if line.startswith("ExecStart=") and not line.strip() == "ExecStart=":
            exec_start.append(line.split("=", 1)[1].strip()[:200])
        if line.startswith("LoadCredential="):
            credentials.append(line.split("=", 1)[1].strip())
        if line.startswith("WorkingDirectory="):
            working = line.split("=", 1)[1].strip()
    return {"exec_start": exec_start, "load_credentials": credentials,
            "working_directory": working}


def main():
    require(os.geteuid() == 0 and os.uname().nodename == "Ubuntu-Hermes",
            "root_on_gateway_host")
    candidates = sorted(d for d in ROOT.iterdir() if d.is_dir())
    require(len(candidates) == 1, "expected exactly one staged candidate")
    candidate = candidates[0]
    summary = json.loads((candidate / "summary.json").read_text())
    logins = json.loads((candidate / "replacement-logins.private.json").read_text())
    require(set(logins) <= LOGINS_KEYS, "unexpected login families")
    require(summary.get("credentials_activated") in (0, None, False),
            "candidate already activated; refusing to plan a replay")
    plan = {
        "candidate": candidate.name,
        "summary_state": {key: summary.get(key) for key in (
            "stage", "complete", "credentials_generated", "credentials_activated",
            "replacement_identity_count", "encryption_keys_changed",
            "recovery_keys_changed", "rollback_is_service_qualified",
            "service_changed", "profiles_changed")},
        "login_families_present": sorted(logins),
        "login_counts": {family: (len(value) if isinstance(value, (dict, list)) else 1)
                         for family, value in logins.items()},
        "staged_artifacts": sorted(child.name for child in candidate.iterdir()),
        "services": {},
    }
    for unit in UNITS:
        facts = unit_facts(systemctl_cat(unit))
        if facts["exec_start"] or facts["load_credentials"]:
            plan["services"][unit] = facts
    plan["apply_order"] = [
        "1. postgresql: rotate service + operator-backup roles, retire legacy "
        "login, verify with a fresh connection before proceeding",
        "2. valkey: rotate users (cache operator installation artifact), "
        "verify SET/GET and AUTH denial for the old user",
        "3. qdrant: rotate read + admin/write API keys, verify old keys are "
        "denied and the index worker reconnects",
        "4. arcadedb: recover operator access per graph-operator-recovery "
        "artifact (hashed server-user format), apply the staged users, "
        "verify authenticated readiness",
        "5. application: replace the issuer signing secret in the api "
        "credential file (this invalidates ALL fleet tokens; reissue via "
        "the fleet batch issuer immediately after restart)",
        "6. api + worker restart, health/readiness, fleet token reissue, "
        "canary-free spot verification under two role scopes",
    ]
    plan["rollback"] = str(candidate / "configuration-before")
    print(json.dumps(plan, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False, "category": "rotation_plan_refused",
                          "error_kind": type(exc).__name__,
                          "detail": str(exc)[:200] if isinstance(exc, ValueError)
                          else ""}), flush=True)
        raise SystemExit(1)
