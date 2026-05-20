"""DuckDB relational adapter (Phase 5 pluggable).

DuckDB (https://duckdb.org) is an MIT-licensed embedded columnar
analytical database -- think SQLite for OLAP workloads. Great fit for
agents that build up large in-memory cohorts (LLM cost roll-ups,
embedding-store analytics) where the existing Postgres OLTP path is
overkill but SQLite's row-store throughput is the bottleneck.

This adapter exposes the same ``asyncpg.Pool``-shape that the SQLite
adapter does. Underlying ``duckdb`` is sync-only, so all I/O is
wrapped with ``asyncio.to_thread`` to keep the async signature
honest without blocking the event loop.

**Compatibility caveats vs asyncpg:**

- DuckDB SQL is largely Postgres-compatible (it deliberately mimics
  Postgres) but has its own type system (``BIGINT``, ``DECIMAL`` vs
  asyncpg's typed return values). Schemas using ``UUID DEFAULT
  gen_random_uuid()`` work; ``JSONB`` becomes plain ``JSON``;
  ``pgvector``-style operators don't exist.
- Parameter substitution uses ``?`` placeholders (positional), same
  as SQLite. If your queries hard-code ``$1`` they will not work
  unchanged.
- DuckDB has no built-in concurrent-writer support; one open file
  = one writer. Use ``:memory:`` or a per-process file path for
  workloads with > 1 writer.

When to pick DuckDB over postgres or sqlite:

- Analytics-heavy workloads (group-by, aggregate, window functions)
  where the columnar engine is 10-100x faster than SQLite.
- Single-process / single-host deployments where you want OLAP
  power without an extra database server.
- "Embedded warehouse" use cases -- the Superset dashboards in
  ``monitoring/superset-dashboards/`` can target DuckDB directly
  if you don't want a separate Postgres for analytics.

Env-var fallbacks:
    DUCKDB_DB_PATH      (default ``./enhanced_cognee.duckdb``)
    DUCKDB_READ_ONLY    (default ``false``)

Install with::

    pip install enhanced-cognee[relational-duckdb]

(``duckdb`` ships a self-contained wheel; no external libraries.)
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, List, Optional, Tuple


class _DuckDBConnection:
    """``asyncpg.Connection``-shaped wrapper around a duckdb connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def fetchval(self, sql: str, *args: Any) -> Any:
        def _run() -> Any:
            row = self._conn.execute(sql, list(args)).fetchone()
            return row[0] if row else None

        return await asyncio.to_thread(_run)

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Tuple[Any, ...]]:
        def _run() -> Optional[Tuple[Any, ...]]:
            return self._conn.execute(sql, list(args)).fetchone()

        return await asyncio.to_thread(_run)

    async def fetch(self, sql: str, *args: Any) -> List[Tuple[Any, ...]]:
        def _run() -> List[Tuple[Any, ...]]:
            return self._conn.execute(sql, list(args)).fetchall()

        return await asyncio.to_thread(_run)

    async def execute(self, sql: str, *args: Any) -> str:
        def _run() -> str:
            cur = self._conn.execute(sql, list(args))
            # DuckDB doesn't expose rowcount the same way as DB-API;
            # use the result-set length as a best-effort proxy.
            try:
                affected = len(cur.fetchall())
            except Exception:
                affected = 0
            return f"OK rows={affected}"

        return await asyncio.to_thread(_run)

    async def executemany(self, sql: str, args_iter: Any) -> None:
        # DuckDB's executemany takes a list-of-lists for parameters.
        params = [list(row) if not isinstance(row, list) else row for row in args_iter]

        def _run() -> None:
            self._conn.executemany(sql, params)

        await asyncio.to_thread(_run)


class _DuckDBAcquireCM:
    """async context manager returned by ``pool.acquire()``."""

    def __init__(self, pool: "_DuckDBPool") -> None:
        self._pool = pool
        self._conn: Optional[_DuckDBConnection] = None

    async def __aenter__(self) -> _DuckDBConnection:
        import duckdb

        def _open() -> Any:
            return duckdb.connect(
                database=self._pool._db_path,
                read_only=self._pool._read_only,
            )

        raw = await asyncio.to_thread(_open)
        self._conn = _DuckDBConnection(raw)
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        if self._conn is not None:
            await asyncio.to_thread(self._conn._conn.close)


class _DuckDBPool:
    """Lightweight ``asyncpg.Pool``-shape over file-backed DuckDB."""

    def __init__(self, db_path: str, read_only: bool = False) -> None:
        self._db_path = db_path
        self._read_only = read_only

    def acquire(self) -> _DuckDBAcquireCM:
        return _DuckDBAcquireCM(self)

    async def close(self) -> None:
        # No persistent state to close -- each acquire opens a fresh handle.
        return None


async def create_pool(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    min_size: int = 1,
    max_size: int = 1,
    **kwargs: Any,
) -> _DuckDBPool:
    """Create a DuckDB "pool" (single-connection-per-acquire).

    Connection-shaped kwargs are accepted for API compat; only
    ``database`` is consulted -- it's the DuckDB file path. Falls
    back to ``DUCKDB_DB_PATH`` env var, then to
    ``./enhanced_cognee.duckdb``. Pass ``:memory:`` for an ephemeral
    in-process DB.

    ``read_only`` defaults to False; set ``DUCKDB_READ_ONLY=true``
    to open the file read-only (useful for Superset / BI consumers).
    """
    db_path = (
        database
        or os.getenv("DUCKDB_DB_PATH")
        or os.getenv("POSTGRES_DB", "enhanced_cognee.duckdb")
    )
    read_only = os.getenv("DUCKDB_READ_ONLY", "false").lower() in ("true", "1", "yes")
    return _DuckDBPool(db_path, read_only=read_only)
