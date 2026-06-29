"""MySQL / MariaDB relational adapter (Phase 5 pluggable).

Exposes an ``asyncpg.Pool``-shape over the **asyncmy** Apache-2.0
driver. Targets:

  - **MySQL 8+** (Oracle's GPLv2 server -- the most widely deployed
    open-source RDBMS)
  - **MariaDB 10+** (MariaDB Foundation fork; GPLv2 + LGPL client
    libraries; default in most Linux distros)
  - **Percona Server** (drop-in MySQL replacement)
  - **Vitess / PlanetScale** (MySQL-wire-compatible) -- works via
    the same driver; just set the right connection parameters

The asyncmy driver was chosen over aiomysql because it's faster,
better-maintained as of 2026, and ships with PEP 517 wheels for
Python 3.10-3.14.

**Compatibility caveats vs asyncpg:**

- MySQL uses ``%s`` placeholders (DB-API style), not ``$1`` /
  ``$2``. This adapter passes args through unchanged -- if your
  queries hard-code Postgres positional placeholders they will
  not work.
- MySQL has no native array type; ``ARRAY[...]`` columns must be
  remodelled as ``JSON``.
- MySQL's ``UPSERT`` is ``INSERT ... ON DUPLICATE KEY UPDATE``,
  not ``INSERT ... ON CONFLICT DO UPDATE``.
- ``vector(N)`` columns require MariaDB 11.7+ (has vector type) or
  a pgvector-style external service; not part of MySQL 8.x.

When to pick MySQL / MariaDB over postgres:

- You already operate MySQL at scale and don't want a second
  RDBMS for RNR Enhanced Cognee specifically.
- Your hosting provider only offers managed MySQL (e.g. Aurora
  MySQL, Cloud SQL for MySQL, Azure DB for MySQL).
- You need MariaDB's vector type (MariaDB 11.7+).

Env-var fallbacks (in order):
    MYSQL_HOST       (default ``localhost``)
    MYSQL_PORT       (default ``3306``)
    MYSQL_DB         (default ``enhanced_cognee``)
    MYSQL_USER       (default ``cognee_user``)
    MYSQL_PASSWORD   (default ``cognee_password``)

Install with::

    pip install enhanced-cognee[relational-mysql]
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple

from src.secure_config import require_secret


class _MySQLConnection:
    """``asyncpg.Connection``-shaped wrapper around an asyncmy connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def _exec(self, sql: str, args: Tuple[Any, ...]) -> Any:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            return cur

    async def fetchval(self, sql: str, *args: Any) -> Any:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            row = await cur.fetchone()
            return row[0] if row else None

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Tuple[Any, ...]]:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            return await cur.fetchone()

    async def fetch(self, sql: str, *args: Any) -> List[Tuple[Any, ...]]:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall()
            return list(rows)

    async def execute(self, sql: str, *args: Any) -> str:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            await self._conn.commit()
            return f"OK rows={cur.rowcount}"

    async def executemany(self, sql: str, args_iter: Any) -> None:
        async with self._conn.cursor() as cur:
            await cur.executemany(sql, list(args_iter))
            await self._conn.commit()


class _MySQLAcquireCM:
    """async context manager returned by ``pool.acquire()``."""

    def __init__(self, pool: "_MySQLPool") -> None:
        self._pool = pool
        self._conn: Optional[_MySQLConnection] = None
        self._raw: Any = None

    async def __aenter__(self) -> _MySQLConnection:
        # asyncmy's `pool.acquire()` returns a Connection directly.
        # We wrap it to expose our asyncpg-shaped API.
        self._raw = await self._pool._raw_pool.acquire()
        self._conn = _MySQLConnection(self._raw)
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        if self._raw is not None:
            self._pool._raw_pool.release(self._raw)


class _MySQLPool:
    """asyncpg.Pool-shape over an asyncmy connection pool."""

    def __init__(self, raw_pool: Any) -> None:
        self._raw_pool = raw_pool

    def acquire(self) -> _MySQLAcquireCM:
        return _MySQLAcquireCM(self)

    async def close(self) -> None:
        self._raw_pool.close()
        await self._raw_pool.wait_closed()


async def create_pool(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    min_size: int = 1,
    max_size: int = 10,
    **kwargs: Any,
) -> _MySQLPool:
    """Create a MySQL / MariaDB pool via asyncmy.

    Falls back to MYSQL_* env vars when args are omitted.
    """
    import asyncmy

    host = host or os.getenv("MYSQL_HOST", "localhost")
    port = port or int(os.getenv("MYSQL_PORT", "3306"))
    database = database or os.getenv("MYSQL_DB", "enhanced_cognee")
    user = user or os.getenv("MYSQL_USER", "cognee_user")
    password = password or require_secret("MYSQL_PASSWORD", dev_default="cognee_password")

    raw_pool = await asyncmy.create_pool(
        host=host,
        port=port,
        db=database,
        user=user,
        password=password,
        minsize=min_size,
        maxsize=max_size,
        autocommit=False,
    )
    return _MySQLPool(raw_pool)
