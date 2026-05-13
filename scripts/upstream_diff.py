"""
upstream_diff.py
================
Compares the local Enhanced Cognee fork against the latest topoteretes/cognee
upstream release and produces a structured diff report.

Usage
-----
    python scripts/upstream_diff.py [--check-only] [--output PATH] [--token GITHUB_TOKEN]

Flags
-----
--check-only    Exit 1 if a new upstream release exists, 0 otherwise.
                Use in CI to fail fast and trigger the email workflow.
--output PATH   Write JSON report to PATH (default: .upstream-sync/last_diff_report.json)
--token TOKEN   GitHub personal access token for higher rate limits.
                Falls back to GITHUB_TOKEN env var.

Exit codes
----------
0  No new upstream release (or report written successfully)
1  New upstream release detected (--check-only) or fatal error

Output report structure (JSON)
-------------------------------
{
  "generated_at": "2026-05-13T12:34:56Z",
  "local_baseline": "v1.0.9",
  "upstream_latest": "v1.1.0",
  "new_release": true,
  "delta": {
    "new_tasks": ["tasks/foo_task.py"],
    "new_api_routes": ["/v1/bar"],
    "new_search_types": ["FUZZY"],
    "new_pipeline_steps": ["extract_baz"],
    "changed_files": ["cognee/api/v1/cognify.py"],
    "notes": []
  }
}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UPSTREAM_OWNER = "topoteretes"
UPSTREAM_REPO = "cognee"
UPSTREAM_BASE_URL = f"https://api.github.com/repos/{UPSTREAM_OWNER}/{UPSTREAM_REPO}"
SYNC_DIR = Path(__file__).parent.parent / ".upstream-sync"
DEFAULT_OUTPUT = SYNC_DIR / "last_diff_report.json"
LAST_SEEN_FILE = SYNC_DIR / "last_seen_release.txt"

# Patterns for identifying MCP-relevant additions
TASK_FILE_RE = re.compile(r"^cognee/tasks/.+\.py$")
API_ROUTE_RE = re.compile(r'router\.(get|post|put|delete|patch)\("(/v\d[^"]*)"', re.IGNORECASE)
SEARCH_TYPE_RE = re.compile(r"\bSearchType\.\w+\b")
PIPELINE_STEP_RE = re.compile(r'run_tasks_parallel|run_tasks|"step":\s*"(\w+)"')


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def _gh_get(path: str, token: str | None = None) -> Any:
    """GET from GitHub API; returns parsed JSON or raises."""
    url = path if path.startswith("http") else UPSTREAM_BASE_URL + path
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "enhanced-cognee-sync/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API error {exc.code}: {exc.reason} ({url})") from exc


def get_latest_upstream_tag(token: str | None = None) -> str:
    """Return the name of the most recent upstream tag (e.g. 'v1.1.0')."""
    data = _gh_get("/releases/latest", token=token)
    return data.get("tag_name", "")


def get_tag_tree(tag: str, token: str | None = None) -> list[dict]:
    """Return flat list of blob/tree entries for a given tag."""
    tag_data = _gh_get(f"/git/refs/tags/{tag}", token=token)
    sha = tag_data["object"]["sha"]
    obj_type = tag_data["object"]["type"]
    # If it's an annotated tag, resolve to the commit
    if obj_type == "tag":
        resolved = _gh_get(f"/git/tags/{sha}", token=token)
        sha = resolved["object"]["sha"]
    # Get the tree recursively
    commit_data = _gh_get(f"/git/commits/{sha}", token=token)
    tree_sha = commit_data["tree"]["sha"]
    tree_data = _gh_get(f"/git/trees/{tree_sha}?recursive=1", token=token)
    return tree_data.get("tree", [])


def get_local_tag_tree(tag: str, token: str | None = None) -> list[dict]:
    """Return the tree for the local baseline tag (fetched from upstream)."""
    return get_tag_tree(tag, token=token)


def get_file_content(sha: str, token: str | None = None) -> str:
    """Fetch raw blob content by sha."""
    data = _gh_get(f"/git/blobs/{sha}", token=token)
    import base64
    content = data.get("content", "")
    encoding = data.get("encoding", "base64")
    if encoding == "base64":
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return content


# ---------------------------------------------------------------------------
# Diff helpers
# ---------------------------------------------------------------------------

def build_path_map(tree: list[dict]) -> dict[str, str]:
    """Map file path -> blob sha for quick lookup."""
    return {entry["path"]: entry.get("sha", "") for entry in tree if entry["type"] == "blob"}


def find_new_tasks(old_paths: set[str], new_paths: set[str]) -> list[str]:
    """Return list of task file paths added in new release."""
    added = new_paths - old_paths
    return sorted(p for p in added if TASK_FILE_RE.match(p))


def find_changed_cognee_files(
    old_map: dict[str, str], new_map: dict[str, str]
) -> list[str]:
    """Return cognee/ files whose sha changed between releases."""
    changed = []
    for path in new_map:
        if not path.startswith("cognee/"):
            continue
        old_sha = old_map.get(path)
        new_sha = new_map.get(path)
        if old_sha and new_sha and old_sha != new_sha:
            changed.append(path)
    return sorted(changed)


def extract_search_types_from_content(content: str) -> set[str]:
    """Extract SearchType enum member names from Python source."""
    types: set[str] = set()
    # Match class-body assignments like `SUMMARIES = "SUMMARIES"`
    enum_member_re = re.compile(r"^\s+([A-Z][A-Z_0-9]+)\s*=\s*['\"]", re.MULTILINE)
    for m in enum_member_re.finditer(content):
        types.add(m.group(1))
    return types


def extract_api_routes_from_content(content: str) -> list[str]:
    """Extract FastAPI route paths from router definitions."""
    routes = []
    for m in API_ROUTE_RE.finditer(content):
        routes.append(m.group(2))
    return routes


def find_new_search_types(
    old_map: dict[str, str],
    new_map: dict[str, str],
    token: str | None = None,
) -> list[str]:
    """Compare SearchType enum between releases."""
    enum_path = "cognee/shared/data_models.py"
    alt_path = "cognee/modules/retrieval/search_types.py"

    def _get_types(path_map: dict[str, str]) -> set[str]:
        sha = path_map.get(enum_path) or path_map.get(alt_path)
        if not sha:
            return set()
        try:
            content = get_file_content(sha, token=token)
            return extract_search_types_from_content(content)
        except Exception:
            return set()

    old_types = _get_types(old_map)
    new_types = _get_types(new_map)
    return sorted(new_types - old_types)


def find_new_api_routes(
    old_map: dict[str, str],
    new_map: dict[str, str],
    token: str | None = None,
) -> list[str]:
    """Detect new FastAPI route paths in cognee/api/**."""
    new_routes: set[str] = set()
    old_routes: set[str] = set()

    for path_map, route_set in [(old_map, old_routes), (new_map, new_routes)]:
        for filepath, sha in path_map.items():
            if not filepath.startswith("cognee/api/"):
                continue
            if not filepath.endswith(".py"):
                continue
            try:
                content = get_file_content(sha, token=token)
                for route in extract_api_routes_from_content(content):
                    route_set.add(route)
            except Exception:
                pass

    return sorted(new_routes - old_routes)


# ---------------------------------------------------------------------------
# Local SearchType inventory
# ---------------------------------------------------------------------------

def read_local_search_types() -> set[str]:
    """Read _VALID_SEARCH_TYPES from the local MCP server file."""
    server_path = Path(__file__).parent.parent / "bin" / "enhanced_cognee_mcp_server.py"
    if not server_path.exists():
        return set()
    content = server_path.read_text(encoding="utf-8", errors="replace")
    # Match the set literal: _VALID_SEARCH_TYPES = { "A", "B", ... }
    m = re.search(r"_VALID_SEARCH_TYPES\s*=\s*\{([^}]+)\}", content, re.DOTALL)
    if not m:
        return set()
    body = m.group(1)
    return {s.strip().strip('"').strip("'") for s in body.split(",") if s.strip()}


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def build_report(
    local_baseline: str,
    upstream_latest: str,
    token: str | None = None,
) -> dict:
    """Build the full diff report between local_baseline and upstream_latest."""
    print(f"INFO Fetching tree for baseline {local_baseline} ...")
    old_tree = get_tag_tree(local_baseline, token=token)
    print(f"INFO Fetching tree for upstream  {upstream_latest} ...")
    new_tree = get_tag_tree(upstream_latest, token=token)

    old_map = build_path_map(old_tree)
    new_map = build_path_map(new_tree)
    old_paths = set(old_map)
    new_paths = set(new_map)

    print("INFO Computing new tasks ...")
    new_tasks = find_new_tasks(old_paths, new_paths)

    print("INFO Computing changed cognee/ files ...")
    changed_files = find_changed_cognee_files(old_map, new_map)

    print("INFO Scanning for new SearchType values ...")
    new_search_types = find_new_search_types(old_map, new_map, token=token)
    # Filter out ones already in local MCP server
    local_types = read_local_search_types()
    genuinely_new_search_types = [t for t in new_search_types if t not in local_types]

    print("INFO Scanning for new API routes ...")
    new_api_routes = find_new_api_routes(old_map, new_map, token=token)

    notes = []
    if not new_tasks and not new_search_types and not new_api_routes:
        notes.append("No MCP-relevant additions detected.")
    if new_search_types and not genuinely_new_search_types:
        notes.append(
            "Upstream SearchType additions are already covered in local _VALID_SEARCH_TYPES."
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "local_baseline": local_baseline,
        "upstream_latest": upstream_latest,
        "new_release": upstream_latest != local_baseline,
        "delta": {
            "new_tasks": new_tasks,
            "new_api_routes": new_api_routes,
            "new_search_types": genuinely_new_search_types,
            "all_new_search_types_upstream": new_search_types,
            "changed_files_count": len(changed_files),
            "changed_files": changed_files[:50],  # cap to avoid huge reports
            "notes": notes,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compare Enhanced Cognee fork against latest upstream topoteretes/cognee release."
    )
    p.add_argument(
        "--check-only",
        action="store_true",
        help="Exit 1 if a new upstream release is available, 0 otherwise. No report written.",
    )
    p.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Path for JSON report (default: {DEFAULT_OUTPUT})",
    )
    p.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN", ""),
        help="GitHub personal access token (default: $GITHUB_TOKEN env var).",
    )
    p.add_argument(
        "--baseline",
        default=None,
        help="Override local baseline tag (default: read from .upstream-sync/last_seen_release.txt).",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    token = args.token or None

    # Determine local baseline
    if args.baseline:
        local_baseline = args.baseline
    elif LAST_SEEN_FILE.exists():
        local_baseline = LAST_SEEN_FILE.read_text().strip()
    else:
        print("ERR .upstream-sync/last_seen_release.txt not found. Use --baseline to specify.")
        return 1

    print(f"INFO Local baseline : {local_baseline}")

    try:
        upstream_latest = get_latest_upstream_tag(token=token)
    except RuntimeError as exc:
        print(f"ERR Failed to fetch latest upstream tag: {exc}")
        return 1

    print(f"INFO Upstream latest: {upstream_latest}")

    if not upstream_latest:
        print("ERR Could not determine upstream latest release tag.")
        return 1

    if args.check_only:
        if upstream_latest != local_baseline:
            print(f"WARN New upstream release detected: {upstream_latest} (local: {local_baseline})")
            return 1
        print(f"OK Local baseline matches upstream latest ({local_baseline})")
        return 0

    # Full diff mode
    try:
        report = build_report(local_baseline, upstream_latest, token=token)
    except RuntimeError as exc:
        print(f"ERR Failed to build diff report: {exc}")
        return 1

    # Write report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"OK Report written to {output_path}")

    # Summary
    d = report["delta"]
    print(f"INFO new_tasks         : {len(d['new_tasks'])}")
    print(f"INFO new_api_routes    : {len(d['new_api_routes'])}")
    print(f"INFO new_search_types  : {len(d['new_search_types'])}")
    print(f"INFO changed_files     : {d['changed_files_count']}")
    for note in d["notes"]:
        print(f"INFO {note}")

    if report["new_release"]:
        print(
            f"WARN New upstream release {upstream_latest} differs from local baseline {local_baseline}."
            " Run scripts/auto_port.py to generate stub MCP tools."
        )
        return 0  # success - report is written, CI email step decides what to do

    print("OK Enhanced Cognee is current with upstream.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
