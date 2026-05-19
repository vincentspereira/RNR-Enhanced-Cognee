"""Pluggable DB provider factory.

Reads ENHANCED_*_PROVIDER env vars and dispatches to the matching adapter
under src/db_adapters/. Defaults preserve today's behaviour exactly
(postgres / qdrant / neo4j / valkey).

Phase 1 scope:
    - get_relational_pool   ENHANCED_RELATIONAL_PROVIDER=postgres (default)
    - get_vector_client     ENHANCED_VECTOR_PROVIDER=qdrant       (default)
    - get_graph_driver      ENHANCED_GRAPH_PROVIDER=neo4j         (default;
                             flips to arcadedb in Phase 2)
    - get_cache_client      ENHANCED_CACHE_PROVIDER=valkey        (default)

Legacy env-var aliases (kept for backwards compatibility, lower precedence
than the canonical names): RELATIONAL_BACKEND, VECTOR_BACKEND,
GRAPH_BACKEND, CACHE_BACKEND. The earlier stub logic in
bin/enhanced_cognee_mcp_server.py predated the rename.

See docs/STRATEGY.md section 4 for the design and HANDOVER section 3.1 for
the env-var contract.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


_VALID_RELATIONAL = {"postgres", "postgresql"}
_VALID_VECTOR = {"qdrant"}
_VALID_GRAPH = {"neo4j"}
_VALID_CACHE = {"valkey", "redis"}


def _resolve(canonical_env: str, legacy_env: Optional[str], default: str) -> str:
    """Read canonical env var, then legacy, then default. Lower-cased."""
    value = os.getenv(canonical_env)
    if value is None and legacy_env is not None:
        value = os.getenv(legacy_env)
    if value is None:
        value = default
    return value.strip().lower()


async def get_relational_pool(**kwargs: Any):
    """Return a relational connection pool for the configured provider.

    Default provider: postgres (asyncpg pool). The pool exposes
    ``async with pool.acquire() as conn`` and the rest of asyncpg's API.
    """
    provider = _resolve(
        "ENHANCED_RELATIONAL_PROVIDER", "RELATIONAL_BACKEND", "postgres"
    )
    if provider in _VALID_RELATIONAL:
        from src.db_adapters import relational_postgres

        return await relational_postgres.create_pool(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_RELATIONAL_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_RELATIONAL)}"
    )


def get_vector_client(**kwargs: Any):
    """Return a vector DB client for the configured provider.

    Default provider: qdrant (qdrant_client.QdrantClient).
    """
    provider = _resolve("ENHANCED_VECTOR_PROVIDER", "VECTOR_BACKEND", "qdrant")
    if provider == "qdrant":
        from src.db_adapters import vector_qdrant

        return vector_qdrant.create_client(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_VECTOR_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_VECTOR)}"
    )


def get_graph_driver(**kwargs: Any):
    """Return a sync graph DB driver for the configured provider.

    Default provider: neo4j (neo4j.Driver). Will flip to arcadedb in
    Phase 2. The returned object exposes ``.session()`` and ``.close()``.
    """
    provider = _resolve("ENHANCED_GRAPH_PROVIDER", "GRAPH_BACKEND", "neo4j")
    if provider == "neo4j":
        from src.db_adapters import graph_neo4j

        return graph_neo4j.create_driver(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_GRAPH_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_GRAPH)}"
    )


def get_async_graph_driver(**kwargs: Any):
    """Return an async graph DB driver for the configured provider.

    Default provider: neo4j (neo4j.AsyncDriver).
    """
    provider = _resolve("ENHANCED_GRAPH_PROVIDER", "GRAPH_BACKEND", "neo4j")
    if provider == "neo4j":
        from src.db_adapters import graph_neo4j

        return graph_neo4j.create_async_driver(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_GRAPH_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_GRAPH)}"
    )


def get_cache_client(**kwargs: Any):
    """Return an async-capable cache client for the configured provider.

    Default provider: valkey (wire-compatible with redis, uses redis-py's
    ``redis.asyncio.Redis``). The constructor is synchronous; the
    connection pool is initialised lazily on the first command.
    """
    provider = _resolve("ENHANCED_CACHE_PROVIDER", "CACHE_BACKEND", "valkey")
    if provider == "valkey":
        from src.db_adapters import cache_valkey

        return cache_valkey.create_async_client(**kwargs)
    if provider == "redis":
        from src.db_adapters import cache_redis

        return cache_redis.create_async_client(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_CACHE_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_CACHE)}"
    )


def get_sync_cache_client(**kwargs: Any):
    """Return a sync cache client for the configured provider."""
    provider = _resolve("ENHANCED_CACHE_PROVIDER", "CACHE_BACKEND", "valkey")
    if provider == "valkey":
        from src.db_adapters import cache_valkey

        return cache_valkey.create_sync_client(**kwargs)
    if provider == "redis":
        from src.db_adapters import cache_redis

        return cache_redis.create_sync_client(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_CACHE_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_CACHE)}"
    )


def get_provider_summary() -> dict[str, str]:
    """Return the resolved provider for each tier (for logging / debug)."""
    return {
        "relational": _resolve(
            "ENHANCED_RELATIONAL_PROVIDER", "RELATIONAL_BACKEND", "postgres"
        ),
        "vector": _resolve("ENHANCED_VECTOR_PROVIDER", "VECTOR_BACKEND", "qdrant"),
        "graph": _resolve("ENHANCED_GRAPH_PROVIDER", "GRAPH_BACKEND", "neo4j"),
        "cache": _resolve("ENHANCED_CACHE_PROVIDER", "CACHE_BACKEND", "valkey"),
    }
