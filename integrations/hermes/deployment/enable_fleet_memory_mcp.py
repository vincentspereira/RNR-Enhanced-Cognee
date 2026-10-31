#!/usr/bin/env python3
"""Install the Stage C memory MCP server and enable it for fleet profiles.

User-space (no root). Copies the hash-pinned server into the gateway home,
then adds the enhanced_cognee MCP definition to each profile's config.yaml
with the profile-appropriate tool groups, using ruamel round-trip editing
so comments survive. Timestamped backups; safe_load readback verification;
profiles with the definition already present are reported and untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

HOME = Path("/home/vincentspereira/.hermes")
PROFILES = HOME / "profiles"
SERVER_NAME = "enhanced_cognee"
SOURCE = Path(__file__).resolve().parent.parent / "enhanced_cognee_mcp" / "server.py"
INSTALL_DIR = HOME / "mcp-servers" / "enhanced-cognee"
GATEWAY_PYTHON = HOME / "tools/python-3.14.9+20261021-linux-x64/bin/python3"
DEFAULT_GROUPS = "memory_read"
HOME_CONFIG = HOME / "config.yaml"
# The main Hermes assistant (app-level default profile, gateway home
# config) acts as the fleet's chief coordinator: full toolset.
HOME_GROUPS = "memory_read,ingest,analysis,coordination"
# Full per-table enablement (owner-approved 31 Oct): analysis for every
# role marked N or G in the matrix; ingest where N or G; coordination for
# the four coordinators; the ops family stays read-only by design.
_INGEST_ANALYSIS = "memory_read,ingest,analysis"
_ANALYSIS_ONLY = "memory_read,analysis"
_COORDINATION = "memory_read,analysis,coordination"
ROLE_GROUPS = {
    # Research and content: ingest + analysis
    "web-researcher": _INGEST_ANALYSIS,
    "deep-research-specialist": _INGEST_ANALYSIS,
    "niche-hunter": _INGEST_ANALYSIS,
    "educational-content-author": _INGEST_ANALYSIS,
    "fiction-content-author": _INGEST_ANALYSIS,
    "theology-content-author": _INGEST_ANALYSIS,
    "technical-writer": _INGEST_ANALYSIS,
    "technical-consultant": _INGEST_ANALYSIS,
    "marketing-social-manager": _INGEST_ANALYSIS,
    "customer-feedback-analyst": _INGEST_ANALYSIS,
    "ecommerce-kdp-publisher": _INGEST_ANALYSIS,
    "print-merch-designer": _INGEST_ANALYSIS,
    "multimedia-producer": _INGEST_ANALYSIS,
    "uxui-engineer": _INGEST_ANALYSIS,
    "github-collaborator": _INGEST_ANALYSIS,
    "context-engineer": _INGEST_ANALYSIS,
    "aiml-engineer": _INGEST_ANALYSIS,
    "data-engineer": _INGEST_ANALYSIS,
    "data-gen-rl": _INGEST_ANALYSIS,
    # Engineering and specialist: analysis only
    "backend-developer": _ANALYSIS_ONLY,
    "frontend-developer": _ANALYSIS_ONLY,
    "mobile-developer": _ANALYSIS_ONLY,
    "code-implementer": _ANALYSIS_ONLY,
    "code-reviewer": _ANALYSIS_ONLY,
    "debug-specialist": _ANALYSIS_ONLY,
    "test-engineer": _ANALYSIS_ONLY,
    "integration-specialist": _ANALYSIS_ONLY,
    "software-architect": _ANALYSIS_ONLY,
    "security-specialist": _ANALYSIS_ONLY,
    "governance-privacy": _ANALYSIS_ONLY,
    "ai-safety-guardrails": _ANALYSIS_ONLY,
    # Coordination: analysis + shared-space publication
    "chief-of-staff": _COORDINATION,
    "project-orchestrator": _COORDINATION,
    "cross-project-collaborator": _COORDINATION,
    "deliberation-moderator": _COORDINATION,
    # Ops family: read-only by design (matrix: analysis NR)
    "devops-engineer": "memory_read",
    "deployment-engineer": "memory_read",
    "cloud-engineer": "memory_read",
    "observability-specialist": "memory_read",
    "performance-optimiser": "memory_read",
}


def require(value, category="stage_c_enablement_refused"):
    if not value:
        raise ValueError(category)


def install_server() -> str:
    require(SOURCE.is_file(), "server_source_missing")
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    target = INSTALL_DIR / "server.py"
    if target.exists():
        require(hashlib.sha256(target.read_bytes()).hexdigest() == digest,
                "installed_server_differs_refusing_overwrite")
    else:
        shutil.copy2(SOURCE, target)
        target.chmod(0o644)
    require(GATEWAY_PYTHON.is_file(), "gateway_python_missing")
    return digest


def enable_profile(config_path: Path, groups: str) -> str:
    """Add or update the MCP definition; returns 'changed' or 'already'."""
    from ruamel.yaml import YAML
    import yaml as safe_yaml
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(config_path.read_text())
    require(isinstance(data, dict), "config_not_mapping")
    servers = data.setdefault("mcp_servers", {})
    require(isinstance(servers, dict), "mcp_servers_not_mapping")
    desired = {
        "command": str(GATEWAY_PYTHON),
        "args": ["-I", str(INSTALL_DIR / "server.py"), "--tool-groups", groups],
        "env": {"ENHANCED_COGNEE_ACCESS_TOKEN": "${ENHANCED_COGNEE_ACCESS_TOKEN}"},
    }
    if servers.get(SERVER_NAME) == desired:
        return "already"
    backup = config_path.with_name(
        "config.yaml-before-memory-mcp-" + uuid.uuid4().hex[:12])
    shutil.copy2(config_path, backup)
    servers[SERVER_NAME] = desired
    import io
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    config_path.write_text(buffer.getvalue())
    verify = safe_yaml.safe_load(config_path.read_text())
    entry = verify["mcp_servers"][SERVER_NAME]
    require(entry["command"] == str(GATEWAY_PYTHON)
            and entry["env"]["ENHANCED_COGNEE_ACCESS_TOKEN"]
            == "${ENHANCED_COGNEE_ACCESS_TOKEN}"
            and entry["args"][-1] == groups, "readback_failed")
    return "changed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="enable a single profile (pilot)")
    parser.add_argument("--groups", default=DEFAULT_GROUPS)
    args = parser.parse_args()
    require(sys.argv[1:].count("--groups") <= 1 and not args.groups == "",
            "invalid_groups")
    digest = install_server()
    changed, already = [], []
    if args.only:
        targets = [args.only]
        require((PROFILES / args.only / "config.yaml").is_file(), "profile_missing")
    else:
        targets = sorted(child.name for child in PROFILES.iterdir()
                         if (child / "config.yaml").is_file())
    for name in targets:
        result = enable_profile(PROFILES / name / "config.yaml",
                                ROLE_GROUPS.get(name, args.groups))
        (changed if result == "changed" else already).append(name)
    home_result = "skipped"
    if HOME_CONFIG.is_file():
        home_result = enable_profile(HOME_CONFIG, HOME_GROUPS)
    print(json.dumps({"complete": True, "server_sha256": digest,
                      "install_dir": str(INSTALL_DIR),
                      "changed": changed, "already": already,
                      "home_config": home_result,
                      "groups_default": args.groups}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"complete": False,
                          "category": "stage_c_enablement_refused",
                          "error_kind": type(exc).__name__,
                          "detail": str(exc)[:160] if isinstance(exc, ValueError) else ""},
                         sort_keys=True))
        raise SystemExit(1)
