#!/usr/bin/env python3
"""Verify every fleet role's memory tools against the approved matrix.

Two checks per role: (1) the profile config's tool groups equal the
expected groups from the approved table; (2) a live spawn of the installed
MCP server with that role's own token and groups advertises exactly the
expected tool names. Prints one line per role plus a summary; rerunnable
anytime. Token values are passed through child env only, never printed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

DEPLOY = Path(__file__).resolve().parent
HOME = Path("/home/vincentspereira/.hermes")
PROFILES = HOME / "profiles"
INSTALL = HOME / "mcp-servers/enhanced-cognee/server.py"
PY = HOME / "tools/python-3.14.9+20261021-linux-x64/bin/python3"
PROTOCOL_SHA = "415ef81f50ca0c209d9afd08c6a685f70c6ab951bbd5b672c5b32128bff52c07"


def require(value, category="verify_refused"):
    if not value:
        raise ValueError(category)


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOY / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_tools(groups):
    import sys
    sys.path.insert(0, str(DEPLOY.parent / "enhanced_cognee_mcp"))
    from server import GROUPS
    names = set()
    for group in groups.split(","):
        names |= set(GROUPS[group.strip()])
    return names


def main():
    raw = (DEPLOY / "probe_main_local_mcp.py").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROTOCOL_SHA)
    scope = {"__name__": "protocol", "__file__": "probe"}
    exec(compile(raw, "probe", "exec"), scope)
    enablement = load("enable_fleet_memory_mcp")
    require(len(enablement.ROLE_GROUPS) == 40, "role_table_incomplete")
    rows, failures = [], []
    for role in sorted(enablement.ROLE_GROUPS):
        groups = enablement.ROLE_GROUPS[role]
        config = PROFILES / role / "config.yaml"
        import yaml
        entry = yaml.safe_load(config.read_text())["mcp_servers"].get(
            "enhanced_cognee")
        configured = entry["args"][-1] if entry else None
        env_file = PROFILES / role / ".env"
        token = ""
        for line in env_file.read_text().splitlines():
            if line.startswith("ENHANCED_COGNEE_ACCESS_TOKEN="):
                token = line.split("=", 1)[1].strip()
        home = Path(tempfile.mkdtemp(prefix="verify-role-"))
        env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
               "ENHANCED_COGNEE_ACCESS_TOKEN": token, "DO_NOT_TRACK": "1"}
        live = "spawn-failed"
        try:
            client = scope["Client"]([str(PY), "-I", str(INSTALL),
                                      "--tool-groups", groups], env, home)
            try:
                names = scope["handshake"](client)
                want = expected_tools(groups)
                live = "ok" if set(names) == want else \
                    "mismatch:%d-vs-%d" % (len(names), len(want))
            finally:
                client.close()
        except Exception as exc:
            live = "error:" + type(exc).__name__
        row_pass = configured == groups and live == "ok"
        rows.append({"role": role, "groups": groups, "configured": configured,
                     "live": live, "expected_tools": len(expected_tools(groups)),
                     "pass": row_pass})
        if not row_pass:
            failures.append(role)
        print("%-30s %-38s configured=%-38s live=%s" %
              (role, groups, configured, live), flush=True)
    print(json.dumps({"complete": not failures, "roles": len(rows),
                      "failures": failures}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False, "error_kind": type(exc).__name__,
                          "detail": str(exc)[:160]}), flush=True)
        raise SystemExit(1)
