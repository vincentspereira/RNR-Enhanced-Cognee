#!/usr/bin/env python3
"""Consolidated fleet verification: one command, every layer, green/red.

Checks: memory backend services, API health + authenticated status, the
memory provider selection and MCP tool groups for all 40 roles plus the
main assistant (config + live server spawn per role), the token renewal
timer, the daily fleet backup timer, and the credential rotation receipts
for all five families. Prints one line per check and a final verdict.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

DEPLOY = Path("/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020"
              "/launch-worktree-20261024/integrations/hermes/deployment")
HOME = Path("/home/vincentspereira/.hermes")
PROFILES = HOME / "profiles"
INSTALL = HOME / "mcp-servers/enhanced-cognee/server.py"
PY = HOME / "tools/python-3.14.9+20261021-linux-x64/bin/python3"
PROTOCOL_SHA = "415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07"
HOME_GROUPS = "memory_read,ingest,analysis,coordination"
BACKENDS = ["enhanced-cognee-api.service", "enhanced-cognee-postgres.service",
            "enhanced-cognee-qdrant.service", "enhanced-cognee-graph.service",
            "enhanced-cognee-cache.service"]
ROTATION_ROOT = Path("/var/lib/enhanced-cognee-rotation")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%-4s %-52s %s" % ("OK" if ok else "ERR", name, detail), flush=True)


def api(method, path, token=None, body=None, timeout=10):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request("http://127.0.0.1:28080" + path, data=data,
                      method=method, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"{}")
    except HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except Exception:
            return exc.code, {}


def role_token(env_path):
    for line in Path(env_path).read_text().splitlines():
        if line.startswith("ENHANCED_COGNEE_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


def main():
    spec = importlib.util.spec_from_file_location(
        "enable", DEPLOY / "enable_fleet_memory_mcp.py")
    enable = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(enable)
    import yaml

    print("== Backend services ==")
    for unit in BACKENDS:
        state = subprocess.run(["systemctl", "is-active", unit],
                               capture_output=True, text=True).stdout.strip()
        check(unit, state == "active", state)

    code, health = api("GET", "/health/ready")
    check("memory API health", code == 200 and health.get("ready") is True)

    token = role_token(HOME / ".env")
    code, status = api("GET", "/v1/memories/status", token)
    check("main assistant memory status", code == 200
          and status.get("project_id") == "default", str(status.get("project_id")))

    print("== Provider + MCP tools per role (live) ==")
    raw = (DEPLOY / "probe_main_local_mcp.py").read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA:
        check("protocol pin", False, "hash changed")
        scope = {}
    else:
        scope = {"__name__": "protocol", "__file__": "probe"}
        exec(compile(raw, "probe", "exec"), scope)
        check("protocol pin", True)
    sys.path.insert(0, str(DEPLOY.parent / "enhanced_cognee_mcp"))
    from server import GROUPS

    def expected_tools(groups):
        names = set()
        for group in groups.split(","):
            names |= set(GROUPS[group.strip()])
        return names

    def live_role(name, env_path, groups):
        entry = yaml.safe_load(Path(
            PROFILES / name / "config.yaml").read_text())["mcp_servers"].get(
            "enhanced_cognee") if name else yaml.safe_load(
            (HOME / "config.yaml").read_text())["mcp_servers"]["enhanced_cognee"]
        if not entry or entry["args"][-1] != groups:
            return False, "config mismatch"
        tkn = role_token(env_path)
        home = Path(tempfile.mkdtemp(prefix="consolidated-"))
        env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
               "ENHANCED_COGNEE_ACCESS_TOKEN": tkn, "DO_NOT_TRACK": "1"}
        client = scope["Client"]([str(PY), "-I", str(INSTALL),
                                  "--tool-groups", groups], env, home)
        try:
            names = scope["handshake"](client)
            return set(names) == expected_tools(groups), "%d tools" % len(names)
        finally:
            client.close()

    for role in sorted(enable.ROLE_GROUPS):
        groups = enable.ROLE_GROUPS[role]
        ok, detail = live_role(role, PROFILES / role / ".env", groups)
        check("role %s" % role, ok, detail)
    ok, detail = live_role(None, HOME / ".env", HOME_GROUPS)
    check("main assistant tools", ok, detail)

    print("== Automation and rotation ==")
    timer = subprocess.run(["systemctl", "is-active",
                            "ec-hermes-memory-token-renew.timer"],
                           capture_output=True, text=True).stdout.strip()
    check("token renewal timer", timer == "active", timer)
    nxt = subprocess.run(["systemctl", "list-timers",
                          "enhanced-cognee-qualified-fleet-backup-v2.timer",
                          "--no-legend"], capture_output=True, text=True)
    check("daily fleet backup timer", "enhanced-cognee" in nxt.stdout,
          nxt.stdout.split("\n")[0][:40] if nxt.stdout else "not listed")

    if ROTATION_ROOT.is_dir():
        candidates = [d for d in ROTATION_ROOT.iterdir() if d.is_dir()]
        if len(candidates) == 1:
            latest = {}
            for receipt in candidates[0].glob("execution-*.json"):
                body = json.loads(receipt.read_text())
                family = body.get("family")
                stamp = receipt.name  # stamps sort chronologically
                if family not in latest or stamp > latest[family][0]:
                    latest[family] = (stamp, body.get("complete"))
            families = {family: complete
                        for family, (_, complete) in latest.items()}
            for family in ("postgresql", "valkey", "qdrant", "application"):
                check("rotation: %s" % family, families.get(family) is True,
                      str(families.get(family)))
            check("rotation: arcadedb",
                  families.get("arcadedb") is True
                  or families.get("arcadedb-apply") is True,
                  "pending" if families.get("arcadedb") is None else
                  str(families.get("arcadedb")))
        else:
            check("rotation candidates", False, "expected one candidate")
    else:
        check("rotation receipts", False, "root-only; run via sudo")

    failed = [name for name, ok, _ in results if not ok]
    print(json.dumps({"complete": not failed, "checks": len(results),
                      "failed": failed}, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False, "error_kind": type(exc).__name__,
                          "detail": str(exc)[:200]}), flush=True)
        raise SystemExit(1)
