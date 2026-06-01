"""Oracle Database relational adapter (Phase 5 pluggable).

Wraps Oracle's official ``oracledb`` driver (Universal Permissive
License, the successor to cx_Oracle since 2022). Targets:

  - Oracle Database 19c / 21c / 23ai
  - Autonomous Database (OCI managed)
  - Exadata

``oracledb`` ships with a native async API, so we expose the same
``asyncpg.Pool``-shape directly without a sync->async wrapper.

**Compatibility caveats vs asyncpg:**

- Parameter substitution uses ``:1`` / ``:2`` / ... (Oracle bind
  variable syntax) or named ``:param_name``. Not compatible with
  asyncpg's ``$1`` / ``$2``.
- Oracle SQL differs from PostgreSQL in many places:
    * Limit clause is ``FETCH FIRST n ROWS ONLY`` or ``ROWNUM``
      depending on version
    * Empty string is treated as ``NULL`` (the historic NULL/'' gotcha)
    * Identifiers are uppercase unless double-quoted
    * No native JSONB; use ``JSON`` (21c+) or ``CLOB``
- The Oracle client thick-mode driver requires the Oracle Instant
  Client libraries on the host. The thin-mode driver (Python-only)
  works without them but has reduced feature set. This adapter uses
  thin mode by default; set ``ORACLE_THICK_MODE=true`` and ensure
  Instant Client is installed if you need:
    - Database resident connection pooling (DRCP)
    - Application continuity
    - Advanced queueing
    - LDAP server-side connect-strings

When to pick Oracle:

- You operate Oracle Database elsewhere and the team standardises
  on it.
- Your enterprise license already covers Oracle.
- You're using Oracle Autonomous Database on OCI.

Env-var fallbacks (in order):
    ORACLE_DSN          (default ``localhost/free``; Oracle "easy connect"
                         format ``host:port/service_name``)
    ORACLE_USER         (default ``cognee_user``)
    ORACLE_PASSWORD     (default ``cognee_password``)
    ORACLE_THICK_MODE   (default ``false``)
    ORACLE_LIB_DIR      (default unset; only used in thick mode)

Install with::

    pip install enhanced-cognee[relational-oracle]
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple

from src.secure_config import require_secret


class _OracleConnection:
    """``asyncpg.Connection``-shaped wrapper around an oracledb async connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def fetchval(self, sql: str, *args: Any) -> Any:
        cur = self._conn.cursor()
        try:
            await cur.execute(sql, args)
            row = await cur.fetchone()
            return row[0] if row else None
        finally:
            cur.close()

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Tuple[Any, ...]]:
        cur = self._conn.cursor()
        try:
            await cur.execute(sql, args)
            row = await cur.fetchone()
            return tuple(row) if row else None
        finally:
            cur.close()

    async def fetch(self, sql: str, *args: Any) -> List[Tuple[Any, ...]]:
        cur = self._conn.cursor()
        try:
            await cur.execute(sql, args)
            rows = await cur.fetchall()
            return [tuple(r) for r in rows]
        finally:
            cur.close()

    async def execute(self, sql: str, *args: Any) -> str:
        cur = self._conn.cursor()
        try:
            await cur.execute(sql, args)
            await self._conn.commit()
            return f"OK rows={cur.rowcount}"
        finally:
            cur.close()

    async def executemany(self, sql: str, args_iter: Any) -> None:
        cur = self._conn.cursor()
        try:
            await cur.executemany(sql, list(args_iter))
            await self._conn.commit()
        finally:
            cur.close()


class _OracleAcquireCM:
    def __init__(self, pool: "_OraclePool") -> None:
        self._pool = pool
        self._raw: Any = None
        self._conn: Optional[_OracleConnection] = None

    async def __aenter__(self) -> _OracleConnection:
        self._raw = await self._pool._raw_pool.acquire()
        self._conn = _OracleConnection(self._raw)
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        if self._raw is not None:
            await self._pool._raw_pool.release(self._raw)


class _OraclePool:
    """asyncpg.Pool-shape over an oracledb async connection pool."""

    def __init__(self, raw_pool: Any) -> None:
        self._raw_pool = raw_pool

    def acquire(self) -> _OracleAcquireCM:
        return _OracleAcquireCM(self)

    async def close(self) -> None:
        await self._raw_pool.close()


async def create_pool(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    min_size: int = 1,
    max_size: int = 10,
    **kwargs: Any,
) -> _OraclePool:
    """Create an Oracle Database pool via oracledb's async API.

    Accepts the standard relational-adapter kwargs for API compat but
    Oracle's connection string is normally a single DSN
    (``host:port/service_name``) -- ``ORACLE_DSN`` takes precedence
    over the individual host/port/database kwargs.
    """
    import oracledb

    thick_mode = os.getenv("ORACLE_THICK_MODE", "false").lower() in (
        "true", "1", "yes",
    )
    if thick_mode:
        lib_dir = os.getenv("ORACLE_LIB_DIR")
        if lib_dir:
            oracledb.init_oracle_client(lib_dir=lib_dir)
        else:
            oracledb.init_oracle_client()

    dsn = (
        os.getenv("ORACLE_DSN")
        or (f"{host or 'localhost'}:{port or 1521}/{database or 'free'}")
    )
    user = user or os.getenv("ORACLE_USER", "cognee_user")
    password = password or require_secret("ORACLE_PASSWORD", dev_default="cognee_password")

    raw_pool = oracledb.create_pool_async(
        user=user,
        password=password,
        dsn=dsn,
        min=min_size,
        max=max_size,
        increment=1,
    )
    return _OraclePool(raw_pool)
