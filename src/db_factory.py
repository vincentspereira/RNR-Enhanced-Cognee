"""Pluggable DB provider factory.

Reads ENHANCED_*_PROVIDER env vars and dispatches to the matching adapter
under src/db_adapters/. Defaults preserve today's behaviour exactly
(postgres / qdrant / neo4j / valkey).

Phase 1 + 2 scope:
    - get_relational_pool   ENHANCED_RELATIONAL_PROVIDER=postgres  (default)
    - get_vector_client     ENHANCED_VECTOR_PROVIDER=qdrant        (default)
    - get_graph_driver      ENHANCED_GRAPH_PROVIDER=arcadedb       (default
                             since Phase 2; neo4j retained as pluggable
                             alternative for legacy compat -- DR-11)
    - get_cache_client      ENHANCED_CACHE_PROVIDER=valkey         (default)

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


_VALID_RELATIONAL = {
    "postgres", "postgresql",
    "sqlite",
    "duckdb",
    "mysql", "mariadb",
    # CockroachDB speaks the Postgres wire protocol; users select it
    # by setting ENHANCED_RELATIONAL_PROVIDER=postgres and pointing
    # POSTGRES_* at a Cockroach cluster. See docs/PROFILES.md.
}
_VALID_VECTOR = {"qdrant", "pgvector", "lancedb", "chroma", "weaviate", "milvus"}
_VALID_GRAPH = {
    "arcadedb", "neo4j", "apache_age",
    "memgraph", "kuzu", "networkx_inmemory",
    "arangodb", "nebulagraph", "ladybug",
}
_VALID_CACHE = {"valkey", "redis", "redis_compat", "in_memory", "memcached"}


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

    ``sqlite`` returns a file-backed shim suitable for the lean
    profile / tests; see ``docs/PROFILES.md`` for the compatibility
    caveats vs asyncpg.
    """
    provider = _resolve(
        "ENHANCED_RELATIONAL_PROVIDER", "RELATIONAL_BACKEND", "postgres"
    )
    if provider in ("postgres", "postgresql"):
        from src.db_adapters import relational_postgres

        return await relational_postgres.create_pool(**kwargs)
    if provider == "sqlite":
        from src.db_adapters import relational_sqlite

        return await relational_sqlite.create_pool(**kwargs)
    if provider == "duckdb":
        from src.db_adapters import relational_duckdb

        return await relational_duckdb.create_pool(**kwargs)
    if provider in ("mysql", "mariadb"):
        from src.db_adapters import relational_mysql

        return await relational_mysql.create_pool(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_RELATIONAL_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_RELATIONAL)}"
    )


def get_vector_client(**kwargs: Any):
    """Return a vector DB client for the configured provider.

    Default provider: qdrant (qdrant_client.QdrantClient).
    ``pgvector`` returns a Postgres-backed shim (Phase 5) exposing the
    narrow QdrantClient surface our call sites use; see
    ``docs/PROFILES.md`` for the supported-method matrix.
    """
    provider = _resolve("ENHANCED_VECTOR_PROVIDER", "VECTOR_BACKEND", "qdrant")
    if provider == "qdrant":
        from src.db_adapters import vector_qdrant

        return vector_qdrant.create_client(**kwargs)
    if provider == "pgvector":
        from src.db_adapters import vector_pgvector

        return vector_pgvector.create_client(**kwargs)
    if provider == "lancedb":
        from src.db_adapters import vector_lancedb

        return vector_lancedb.create_client(**kwargs)
    if provider == "chroma":
        from src.db_adapters import vector_chroma

        return vector_chroma.create_client(**kwargs)
    if provider == "weaviate":
        from src.db_adapters import vector_weaviate

        return vector_weaviate.create_client(**kwargs)
    if provider == "milvus":
        from src.db_adapters import vector_milvus

        return vector_milvus.create_client(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_VECTOR_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_VECTOR)}"
    )


def get_graph_driver(**kwargs: Any):
    """Return a sync graph DB driver for the configured provider.

    Default provider: arcadedb (Apache-2.0, Bolt-compatible with the neo4j
    Python driver -- see ``docs/ARCADEDB_MIGRATION.md``). ``neo4j`` is
    retained as a pluggable alternative for legacy compat (DR-11).
    The returned object exposes ``.session()`` and ``.close()``.
    """
    provider = _resolve("ENHANCED_GRAPH_PROVIDER", "GRAPH_BACKEND", "arcadedb")
    if provider == "arcadedb":
        from src.db_adapters import graph_arcadedb

        return graph_arcadedb.create_driver(**kwargs)
    if provider == "neo4j":
        from src.db_adapters import graph_neo4j

        return graph_neo4j.create_driver(**kwargs)
    if provider == "apache_age":
        from src.db_adapters import graph_apache_age

        return graph_apache_age.create_driver(**kwargs)
    if provider == "memgraph":
        from src.db_adapters import graph_memgraph

        return graph_memgraph.create_driver(**kwargs)
    if provider == "kuzu":
        from src.db_adapters import graph_kuzu

        return graph_kuzu.create_driver(**kwargs)
    if provider == "networkx_inmemory":
        from src.db_adapters import graph_networkx_inmemory

        return graph_networkx_inmemory.create_driver(**kwargs)
    if provider == "arangodb":
        from src.db_adapters import graph_arangodb

        return graph_arangodb.create_driver(**kwargs)
    if provider == "nebulagraph":
        from src.db_adapters import graph_nebulagraph

        return graph_nebulagraph.create_driver(**kwargs)
    if provider == "ladybug":
        from src.db_adapters import graph_ladybug

        return graph_ladybug.create_driver(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_GRAPH_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_GRAPH)}"
    )


def get_async_graph_driver(**kwargs: Any):
    """Return an async graph DB driver for the configured provider.

    Default provider: arcadedb (Bolt via neo4j AsyncDriver).
    ``apache_age`` returns an asyncpg-backed driver (Phase 5; see
    ``docs/PROFILES.md``). Providers without an async surface
    (``kuzu``, ``networkx_inmemory``) raise ``NotImplementedError``.
    """
    provider = _resolve("ENHANCED_GRAPH_PROVIDER", "GRAPH_BACKEND", "arcadedb")
    if provider == "arcadedb":
        from src.db_adapters import graph_arcadedb

        return graph_arcadedb.create_async_driver(**kwargs)
    if provider == "neo4j":
        from src.db_adapters import graph_neo4j

        return graph_neo4j.create_async_driver(**kwargs)
    if provider == "apache_age":
        from src.db_adapters import graph_apache_age

        return graph_apache_age.create_async_driver(**kwargs)
    if provider == "memgraph":
        from src.db_adapters import graph_memgraph

        return graph_memgraph.create_async_driver(**kwargs)
    if provider == "kuzu":
        from src.db_adapters import graph_kuzu

        return graph_kuzu.create_async_driver(**kwargs)
    if provider == "networkx_inmemory":
        from src.db_adapters import graph_networkx_inmemory

        return graph_networkx_inmemory.create_async_driver(**kwargs)
    if provider == "arangodb":
        from src.db_adapters import graph_arangodb

        return graph_arangodb.create_async_driver(**kwargs)
    if provider == "nebulagraph":
        from src.db_adapters import graph_nebulagraph

        return graph_nebulagraph.create_async_driver(**kwargs)
    if provider == "ladybug":
        from src.db_adapters import graph_ladybug

        return graph_ladybug.create_async_driver(**kwargs)
    raise ValueError(
        f"Unknown ENHANCED_GRAPH_PROVIDER={provider!r}. "
        f"Supported: {sorted(_VALID_GRAPH)}"
    )


def get_cache_client(**kwargs: Any):
    """Return an async-capable cache client for the configured provider.

    Default provider: valkey (wire-compatible with redis, uses redis-py's
    ``redis.asyncio.Redis``). The constructor is synchronous; the
    connection pool is initialised lazily on the first command.
    ``in_memory`` returns a process-local dict-backed stub (no I/O).
    """
    provider = _resolve("ENHANCED_CACHE_PROVIDER", "CACHE_BACKEND", "valkey")
    if provider == "valkey":
        from src.db_adapters import cache_valkey

        return cache_valkey.create_async_client(**kwargs)
    if provider == "redis":
        from src.db_adapters import cache_redis

        return cache_redis.create_async_client(**kwargs)
    if provider == "redis_compat":
        from src.db_adapters import cache_redis_compat

        return cache_redis_compat.create_async_client(**kwargs)
    if provider == "in_memory":
        from src.db_adapters import cache_in_memory

        return cache_in_memory.create_async_client(**kwargs)
    if provider == "memcached":
        from src.db_adapters import cache_memcached

        return cache_memcached.create_async_client(**kwargs)
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
    if provider == "redis_compat":
        from src.db_adapters import cache_redis_compat

        return cache_redis_compat.create_sync_client(**kwargs)
    if provider == "in_memory":
        from src.db_adapters import cache_in_memory

        return cache_in_memory.create_sync_client(**kwargs)
    if provider == "memcached":
        from src.db_adapters import cache_memcached

        return cache_memcached.create_sync_client(**kwargs)
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
        "graph": _resolve("ENHANCED_GRAPH_PROVIDER", "GRAPH_BACKEND", "arcadedb"),
        "cache": _resolve("ENHANCED_CACHE_PROVIDER", "CACHE_BACKEND", "valkey"),
    }
