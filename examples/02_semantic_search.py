#!/usr/bin/env python3
"""Semantic search over a knowledge graph built from free text.

Demonstrates `cognify` (text -> knowledge graph) + `search` (semantic
query against the graph). This is the "cognee" flow proper -- the
classical RAG-with-knowledge-graph pattern.

Run:
    python examples/02_semantic_search.py
"""

from __future__ import annotations

import sys
import time
from typing import Any

import requests

MCP_BASE = "http://localhost:8080"


def call(tool: str, **params: Any) -> Any:
    resp = requests.post(
        f"{MCP_BASE}/tools/{tool}", json=params, timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("isError"):
        raise RuntimeError(f"{tool}: {body}")
    return body.get("result", body)


# A small corpus that the knowledge graph can chew on. Multi-sentence
# paragraphs give the cognify pipeline material to extract entities
# and relationships from.
CORPUS = [
    """Enhanced Cognee is a fork of topoteretes/cognee that adds 122 MCP
    tools, a 4-database stack (PostgreSQL + Qdrant + ArcadeDB + Valkey),
    and GDPR / audit / encryption primitives. The project is licensed
    under Apache-2.0.""",

    """ArcadeDB replaced Neo4j as the default graph database in Phase 2
    of the migration on 2026-05-19. ArcadeDB exposes a Bolt-compatible
    endpoint so the existing neo4j Python driver works against it
    unchanged. Neo4j is retained as a pluggable alternative via the
    ENHANCED_GRAPH_PROVIDER environment variable.""",

    """Valkey 8 (Apache-2.0) replaced Redis 7+ in Phase 1 because Redis's
    licence shift to BSL/SSPL was incompatible with Apache-2.0
    redistribution. Valkey is wire-compatible with the redis-py client
    library.""",
]


def main() -> int:
    print("=== Enhanced Cognee: semantic search ===\n")

    # 1. Cognify -- send each corpus item through the knowledge-graph
    #    extraction pipeline. Returns a document/job ID per item.
    print(f"[1/2] Cognifying {len(CORPUS)} documents...")
    for i, text in enumerate(CORPUS, 1):
        result = call("cognify", data=text.strip())
        print(f"      doc {i}/{len(CORPUS)}: {str(result)[:120]}")

    # Cognify is async on the backend; give the pipeline a moment to
    # finish before we search.
    print("\n      waiting 5s for the pipeline to settle...")
    time.sleep(5)

    # 2. Search semantically -- the query doesn't need to share exact
    #    keywords with the corpus.
    print("\n[2/2] Running semantic searches...\n")
    queries = [
        "Which graph database is the default?",
        "Why did Redis get replaced?",
        "What MCP tools does Enhanced Cognee expose?",
    ]
    for q in queries:
        print(f"  Q: {q}")
        result = call("search", query=q, limit=3)
        # The result format depends on the underlying retrieval; for
        # demo purposes we just print the head.
        snippet = str(result)[:300].replace("\n", " ")
        print(f"  A: {snippet}\n")

    print("OK -- semantic-search demo complete.")
    print("\nNote: this script doesn't clean up the cognified data.")
    print("To wipe the demo state, call `list_data` then `delete_memory`")
    print("on each returned document ID, or recreate the stack.")
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
