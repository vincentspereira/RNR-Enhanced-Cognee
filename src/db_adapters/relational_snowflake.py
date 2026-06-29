"""Snowflake cloud data warehouse adapter (Phase 5 pluggable).

Wraps Snowflake's ``snowflake-connector-python`` (Apache-2.0).
Snowflake is a cloud-native columnar analytical warehouse with
massive horizontal scale; this adapter lets RNR Enhanced Cognee target
it as the relational backend when the workload is primarily
analytical (LLM cost roll-ups, embedding-store analytics, agent-
activity time series).

The connector is sync-only natively; we wrap calls in
``asyncio.to_thread`` so the async signature is honest. Same
``asyncpg.Pool``-shape as the rest of the relational tier.

**Compatibility caveats vs asyncpg:**

- Parameter substitution uses ``%s`` (DB-API) or ``%(name)s`` for
  named parameters. Not compatible with asyncpg's ``$1`` / ``$2``.
- Snowflake SQL is broadly Postgres-compatible but with cloud-DW
  extensions (``COPY INTO``, ``MERGE``, ``QUALIFY``, ``MATCH_RECOGNIZE``).
- No native vector type as of 2026-05; pair with a separate vector
  backend (e.g. qdrant) if you need similarity search.
- No native JSONB; ``VARIANT`` is Snowflake's semi-structured type
  (essentially JSON with schema-on-read).
- Identifiers are uppercase unless double-quoted -- same as Oracle.
- Connection is per-warehouse + per-database; pooling is at the
  application layer (the connector's pool isn't async-aware so we
  open + close per acquire).

When to pick Snowflake:

- Your analytics live in Snowflake already and you want to keep
  RNR Enhanced Cognee's relational tier there.
- Need cross-region replication, time-travel queries, or compute/
  storage separation.

Env-var fallbacks (in order):
    SNOWFLAKE_ACCOUNT     (required; e.g. ``abc12345.us-east-1``)
    SNOWFLAKE_USER        (required)
    SNOWFLAKE_PASSWORD    (required; or use SNOWFLAKE_PRIVATE_KEY)
    SNOWFLAKE_WAREHOUSE   (default ``COMPUTE_WH``)
    SNOWFLAKE_DATABASE    (default ``ENHANCED_COGNEE``)
    SNOWFLAKE_SCHEMA      (default ``PUBLIC``)
    SNOWFLAKE_ROLE        (default unset)

Install with::

    pip install enhanced-cognee[relational-snowflake]
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple


class _SnowflakeConnection:
    """``asyncpg.Connection``-shaped wrapper around a snowflake.connector connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def fetchval(self, sql: str, *args: Any) -> Any:
        def _run() -> Any:
            cur = self._conn.cursor()
            try:
                cur.execute(sql, args if args else None)
                row = cur.fetchone()
                return row[0] if row else None
            finally:
                cur.close()

        return await asyncio.to_thread(_run)

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Tuple[Any, ...]]:
        def _run() -> Optional[Tuple[Any, ...]]:
            cur = self._conn.cursor()
            try:
                cur.execute(sql, args if args else None)
                row = cur.fetchone()
                return tuple(row) if row else None
            finally:
                cur.close()

        return await asyncio.to_thread(_run)

    async def fetch(self, sql: str, *args: Any) -> List[Tuple[Any, ...]]:
        def _run() -> List[Tuple[Any, ...]]:
            cur = self._conn.cursor()
            try:
                cur.execute(sql, args if args else None)
                rows = cur.fetchall()
                return [tuple(r) for r in rows]
            finally:
                cur.close()

        return await asyncio.to_thread(_run)

    async def execute(self, sql: str, *args: Any) -> str:
        def _run() -> str:
            cur = self._conn.cursor()
            try:
                cur.execute(sql, args if args else None)
                self._conn.commit()
                return f"OK rows={cur.rowcount}"
            finally:
                cur.close()

        return await asyncio.to_thread(_run)

    async def executemany(self, sql: str, args_iter: Any) -> None:
        rows = list(args_iter)

        def _run() -> None:
            cur = self._conn.cursor()
            try:
                cur.executemany(sql, rows)
                self._conn.commit()
            finally:
                cur.close()

        await asyncio.to_thread(_run)


class _SnowflakeAcquireCM:
    def __init__(self, pool: "_SnowflakePool") -> None:
        self._pool = pool
        self._raw: Any = None
        self._conn: Optional[_SnowflakeConnection] = None

    async def __aenter__(self) -> _SnowflakeConnection:
        import snowflake.connector

        def _open() -> Any:
            return snowflake.connector.connect(**self._pool._connect_kwargs)

        self._raw = await asyncio.to_thread(_open)
        self._conn = _SnowflakeConnection(self._raw)
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        if self._raw is not None:
            await asyncio.to_thread(self._raw.close)


class _SnowflakePool:
    """asyncpg.Pool-shape over per-acquire snowflake.connector connections."""

    def __init__(self, connect_kwargs: Dict[str, Any]) -> None:
        self._connect_kwargs = connect_kwargs

    def acquire(self) -> _SnowflakeAcquireCM:
        return _SnowflakeAcquireCM(self)

    async def close(self) -> None:
        return None


async def create_pool(
    host: Optional[str] = None,   # ignored for Snowflake -- uses SNOWFLAKE_ACCOUNT
    port: Optional[int] = None,   # ignored
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    min_size: int = 1,
    max_size: int = 1,
    **kwargs: Any,
) -> _SnowflakePool:
    """Create a Snowflake pool.

    The standard ``host`` / ``port`` kwargs are ignored -- Snowflake
    is accessed via the account locator (``SNOWFLAKE_ACCOUNT``),
    not by host/port. Falls back to SNOWFLAKE_* env vars.
    """
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    if not account:
        raise ValueError(
            "Snowflake adapter: SNOWFLAKE_ACCOUNT env var is required "
            "(e.g. 'abc12345.us-east-1'). Set it before opening a pool."
        )

    connect_kwargs: Dict[str, Any] = {
        "account": account,
        "user": user or os.getenv("SNOWFLAKE_USER", ""),
        "password": password or os.getenv("SNOWFLAKE_PASSWORD", ""),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        "database": database or os.getenv("SNOWFLAKE_DATABASE", "ENHANCED_COGNEE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    }
    role = os.getenv("SNOWFLAKE_ROLE")
    if role:
        connect_kwargs["role"] = role

    return _SnowflakePool(connect_kwargs)
