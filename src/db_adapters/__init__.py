"""Pluggable database adapters for RNR Enhanced Cognee.

Each tier (relational / vector / graph / cache) has one adapter module per
provider. Adapters are thin factory functions that return the underlying
driver/client object the application expects, so that call sites can swap
providers via env vars without re-implementing every DB method.

Selection happens at `src/db_factory.py`, which reads the
ENHANCED_*_PROVIDER env vars and dispatches to the appropriate adapter.

Defaults (Phase 1):
    Relational: postgres   (ENHANCED_RELATIONAL_PROVIDER)
    Vector:     qdrant     (ENHANCED_VECTOR_PROVIDER)
    Graph:      neo4j      (ENHANCED_GRAPH_PROVIDER)  - flips to arcadedb in Phase 2
    Cache:      valkey     (ENHANCED_CACHE_PROVIDER)

See docs/STRATEGY.md section 4 for the full design.
"""
