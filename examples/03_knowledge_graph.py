#!/usr/bin/env python3
"""Direct knowledge-graph primitives: remember / recall / forget / improve.

Demonstrates Enhanced Cognee's v1.0.9-style KG tools that operate on
the graph directly rather than going through the semantic-search
cognify pipeline. Faster and more deterministic for cases where you
already know what fact you're inserting.

Run:
    python examples/03_knowledge_graph.py
"""

from __future__ import annotations

import sys
from typing import Any

import requests

MCP_BASE = "http://localhost:8080"
AGENT_ID = "example-agent-03"


def call(tool: str, **params: Any) -> Any:
    resp = requests.post(
        f"{MCP_BASE}/tools/{tool}", json=params, timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("isError"):
        raise RuntimeError(f"{tool}: {body}")
    return body.get("result", body)


def main() -> int:
    print("=== Enhanced Cognee: knowledge-graph primitives ===\n")

    # 1. Remember three facts. `remember` adds them to the graph with
    #    automatic entity extraction.
    print("[1/4] remember()-ing three facts...")
    fact_ids = []
    for fact in [
        "Phase 1 of the pluggable-DB migration shipped on 2026-05-19 in PR #19.",
        "Phase 2 (ArcadeDB default) shipped on 2026-05-19 in PR #20.",
        "Phase 3 (Apache AGE + lean profile) shipped on 2026-05-19 in PR #21.",
    ]:
        result = call("remember", fact=fact, agent_id=AGENT_ID)
        fact_ids.append(result)
        print(f"      remembered: {str(result)[:100]}")

    # 2. Recall -- semantic search restricted to the graph
    print("\n[2/4] recall()-ing facts about 'pluggable-DB migration'...")
    matches = call("recall", query="pluggable-DB migration", agent_id=AGENT_ID)
    print(f"      {str(matches)[:400]}")

    # 3. Improve -- the maintainer can edit / refine a remembered fact
    print(f"\n[3/4] improve()-ing the first fact ({fact_ids[0]})...")
    if isinstance(fact_ids[0], str):
        try:
            call(
                "improve",
                memory_id=fact_ids[0],
                update=("Phase 1 (pluggable DB plumbing) shipped on "
                        "2026-05-19 in PR #19, commit a3f25a3bf."),
                agent_id=AGENT_ID,
            )
            print("      improved.")
        except Exception as exc:
            print(f"      skipped (improve() rejected the call): {exc}")

    # 4. Forget -- prune the demo data
    print(f"\n[4/4] forget_memory() cleanup for {len(fact_ids)} facts...")
    for fid in fact_ids:
        if isinstance(fid, str):
            try:
                call("forget_memory", memory_id=fid, agent_id=AGENT_ID)
                print(f"      forgot: {fid}")
            except Exception as exc:
                print(f"      skipped ({fid}): {exc}")

    print("\nOK -- knowledge-graph demo complete.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.ConnectionError:
        print(
            f"ERR could not connect to MCP server at {MCP_BASE}.",
            file=sys.stderr,
        )
        sys.exit(2)
