"""SQLite relational adapter (Phase 5 pluggable; **testing / lean only**).

Provides an ``asyncpg.Pool``-shaped surface over ``aiosqlite``. Useful
for:

  1. Tests that need a real relational engine but cannot afford to
     boot Postgres.
  2. The ``lean`` deployment profile on machines where Postgres is
     overkill.

**Compatibility caveats vs asyncpg:**

- SQLite has no equivalent of Postgres's array / JSONB / pgvector
  types. Schemas that rely on those will not run unmodified.
- Parameter substitution uses ``?`` placeholders in plain SQLite,
  whereas asyncpg uses ``$1`` / ``$2`` / .... aiosqlite accepts the
  ``?`` style. If your queries hard-code ``$1`` they will not work
  here -- this adapter does **not** translate query syntax.
- No connection pooling in the classical sense -- this wrapper holds
  one connection per ``acquire()`` call, opened lazily. Concurrency
  is bounded by SQLite's write lock.

This adapter is **not** a Postgres-compatibility shim. It exists so
the ``lean`` profile can run on a single file. Production workloads
should always pick ``postgres``.

Env-var fallbacks: ``SQLITE_DB_PATH`` (default ``./enhanced_cognee.db``)
or ``POSTGRES_DB`` falls back to the same file naming convention.

Install with::

    pip install enhanced-cognee[relational-sqlite]

(``aiosqlite`` is pure-Python; the optional-deps group exists so
``deptry`` doesn't flag it on default installs.)
"""

from __future__ import annotations

import os
from typing import Any, Optional


class _SQLiteConnection:
    """``asyncpg.Connection``-shaped wrapper around an aiosqlite connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def fetchval(self, sql: str, *args: Any) -> Any:
        cur = await self._conn.execute(sql, args)
        try:
            row = await cur.fetchone()
            return row[0] if row else None
        finally:
            await cur.close()

    async def fetchrow(self, sql: str, *args: Any) -> Any:
        cur = await self._conn.execute(sql, args)
        try:
            return await cur.fetchone()
        finally:
            await cur.close()

    async def fetch(self, sql: str, *args: Any) -> list:
        cur = await self._conn.execute(sql, args)
        try:
            return await cur.fetchall()
        finally:
            await cur.close()

    async def execute(self, sql: str, *args: Any) -> str:
        cur = await self._conn.execute(sql, args)
        try:
            await self._conn.commit()
            return f"OK rows={cur.rowcount}"
        finally:
            await cur.close()

    async def executemany(self, sql: str, args_iter: Any) -> None:
        await self._conn.executemany(sql, args_iter)
        await self._conn.commit()


class _SQLiteAcquireCM:
    """async context manager returned by ``pool.acquire()``."""

    def __init__(self, pool: "_SQLitePool") -> None:
        self._pool = pool
        self._conn: Optional[_SQLiteConnection] = None

    async def __aenter__(self) -> _SQLiteConnection:
        import aiosqlite

        raw = await aiosqlite.connect(self._pool._db_path)
        self._conn = _SQLiteConnection(raw)
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        if self._conn is not None:
            await self._conn._conn.close()


class _SQLitePool:
    """Lightweight ``asyncpg.Pool``-shape over file-backed SQLite."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def acquire(self) -> _SQLiteAcquireCM:
        # Returns an async-context-manager (matches asyncpg's contract).
        return _SQLiteAcquireCM(self)

    async def close(self) -> None:
        # No persistent state to close.
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
) -> _SQLitePool:
    """Create a SQLite "pool" (single-connection-per-acquire).

    Connection-shaped kwargs are accepted for API compatibility but
    only ``database`` is consulted -- it's used as the SQLite file
    path. Falls back to ``SQLITE_DB_PATH`` env var, then to
    ``./enhanced_cognee.db``. Pass ``:memory:`` for an ephemeral
    in-process DB.
    """
    db_path = (
        database
        or os.getenv("SQLITE_DB_PATH")
        or os.getenv("POSTGRES_DB", "enhanced_cognee.db")
    )
    return _SQLitePool(db_path)
