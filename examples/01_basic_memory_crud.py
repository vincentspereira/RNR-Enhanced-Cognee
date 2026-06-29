#!/usr/bin/env python3
"""Basic memory CRUD: add / get / search / update / delete.

Demonstrates the standard memory MCP interface that Claude Code uses.
Bring the RNR Enhanced Cognee stack + MCP server up first; see examples/README.md.

Run:
    python examples/01_basic_memory_crud.py
"""

from __future__ import annotations

import json
import sys
from typing import Any

import requests

MCP_BASE = "http://localhost:8080"
AGENT_ID = "example-agent-01"


def call(tool: str, **params: Any) -> Any:
    """Invoke an MCP tool and return its result, raising on error."""
    resp = requests.post(
        f"{MCP_BASE}/tools/{tool}", json=params, timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("isError"):
        raise RuntimeError(f"{tool}: {body}")
    return body.get("result", body)


def main() -> int:
    print("=== RNR Enhanced Cognee: basic memory CRUD ===\n")

    # 1. Add three memories under a single agent_id
    print("[1/5] Adding memories...")
    ids = []
    for content in [
        "The maintainer prefers Conventional Commits with co-author trailers.",
        "Branch protection on main requires 4 status checks before merge.",
        "ArcadeDB is the default graph DB since Phase 2 (2026-05-19).",
    ]:
        result = call(
            "add_memory",
            content=content,
            agent_id=AGENT_ID,
            metadata=json.dumps({"category": "project", "source": "example"}),
        )
        memory_id = result if isinstance(result, str) else result.get("id", result)
        ids.append(memory_id)
        print(f"      added: {memory_id}")

    # 2. Search by free text
    print("\n[2/5] Searching for 'ArcadeDB'...")
    results = call(
        "search_memories",
        query="ArcadeDB",
        agent_id=AGENT_ID,
        limit=3,
    )
    print(f"      result preview:\n{str(results)[:400]}")

    # 3. Retrieve one specific memory by ID
    print(f"\n[3/5] Fetching memory {ids[0]} by ID...")
    detail = call("get_memory", memory_id=ids[0])
    print(f"      {str(detail)[:200]}")

    # 4. Update its content
    print(f"\n[4/5] Updating memory {ids[0]}...")
    call(
        "update_memory",
        memory_id=ids[0],
        content="The maintainer prefers Conventional Commits AND ASCII-only output.",
    )
    print("      updated. Re-fetching to confirm:")
    print(f"      {str(call('get_memory', memory_id=ids[0]))[:200]}")

    # 5. Cleanup -- delete every memory we created
    print(f"\n[5/5] Deleting {len(ids)} memories...")
    for memory_id in ids:
        call("delete_memory", memory_id=memory_id)
        print(f"      deleted: {memory_id}")

    print("\nOK -- CRUD cycle complete.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.ConnectionError:
        print(
            f"ERR could not connect to MCP server at {MCP_BASE}.\n"
            "    Bring the stack up:  docker compose -f "
            "docker/docker-compose-enhanced-cognee.yml up -d\n"
            "    Start the MCP:       python bin/enhanced_cognee_mcp_server.py",
            file=sys.stderr,
        )
        sys.exit(2)
