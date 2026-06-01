"""IBM Db2 relational adapter (Phase 5 pluggable).

Wraps IBM's ``ibm_db`` driver (Apache-2.0 Python binding over the
proprietary CLI). Targets:

  - IBM Db2 LUW 11.5+
  - IBM Db2 on Cloud (managed)
  - IBM Db2 Warehouse on Cloud

``ibm_db`` is sync-only; all I/O is wrapped with
``asyncio.to_thread`` so the async signature is honest without
blocking the event loop. Same ``asyncpg.Pool``-shape as the rest
of the relational tier.

**Compatibility caveats vs asyncpg:**

- Parameter substitution uses ``?`` placeholders (DB-API). Not
  compatible with asyncpg's ``$1`` / ``$2``.
- Db2 SQL is largely ANSI-standard but with quirks:
    * Identifiers are uppercase by default
    * Limit clause is ``FETCH FIRST n ROWS ONLY``
    * ``GENERATED ALWAYS AS IDENTITY`` for auto-increment
    * Native JSON type exists in 11.1+; use ``BLOB`` if older
- The Db2 client library (CLI) must be installed; ibm_db bundles
  a minimal copy on Linux x86_64 (CPython) but other platforms
  may require a manual download from IBM.

When to pick Db2:

- You operate Db2 on IBM Z / Power Systems and want the same
  RDBMS for AI memory storage.
- Your enterprise license already covers Db2.
- You're on IBM Cloud and want first-party managed PaaS.

Env-var fallbacks (in order):
    DB2_HOST       (default ``localhost``)
    DB2_PORT       (default ``50000``)
    DB2_DB         (default ``ENHANCED``)
    DB2_USER       (default ``cognee_user``)
    DB2_PASSWORD   (default ``cognee_password``)
    DB2_PROTOCOL   (default ``TCPIP``)

Install with::

    pip install enhanced-cognee[relational-db2]
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, List, Optional, Tuple

from src.secure_config import require_secret


def _build_dsn(
    host: str, port: int, database: str, user: str, password: str, protocol: str
) -> str:
    return (
        f"DATABASE={database};"
        f"HOSTNAME={host};"
        f"PORT={port};"
        f"PROTOCOL={protocol};"
        f"UID={user};"
        f"PWD={password};"
    )


class _DB2Connection:
    """``asyncpg.Connection``-shaped wrapper around an ibm_db connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def fetchval(self, sql: str, *args: Any) -> Any:
        def _run() -> Any:
            import ibm_db

            stmt = ibm_db.prepare(self._conn, sql)
            ibm_db.execute(stmt, args)
            row = ibm_db.fetch_tuple(stmt)
            return row[0] if row else None

        return await asyncio.to_thread(_run)

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Tuple[Any, ...]]:
        def _run() -> Optional[Tuple[Any, ...]]:
            import ibm_db

            stmt = ibm_db.prepare(self._conn, sql)
            ibm_db.execute(stmt, args)
            row = ibm_db.fetch_tuple(stmt)
            return tuple(row) if row else None

        return await asyncio.to_thread(_run)

    async def fetch(self, sql: str, *args: Any) -> List[Tuple[Any, ...]]:
        def _run() -> List[Tuple[Any, ...]]:
            import ibm_db

            stmt = ibm_db.prepare(self._conn, sql)
            ibm_db.execute(stmt, args)
            rows: List[Tuple[Any, ...]] = []
            row = ibm_db.fetch_tuple(stmt)
            while row:
                rows.append(tuple(row))
                row = ibm_db.fetch_tuple(stmt)
            return rows

        return await asyncio.to_thread(_run)

    async def execute(self, sql: str, *args: Any) -> str:
        def _run() -> str:
            import ibm_db

            stmt = ibm_db.prepare(self._conn, sql)
            ibm_db.execute(stmt, args)
            affected = ibm_db.num_rows(stmt)
            ibm_db.commit(self._conn)
            return f"OK rows={affected}"

        return await asyncio.to_thread(_run)

    async def executemany(self, sql: str, args_iter: Any) -> None:
        rows_list = list(args_iter)

        def _run() -> None:
            import ibm_db

            stmt = ibm_db.prepare(self._conn, sql)
            for params in rows_list:
                ibm_db.execute(stmt, params)
            ibm_db.commit(self._conn)

        await asyncio.to_thread(_run)


class _DB2AcquireCM:
    def __init__(self, pool: "_DB2Pool") -> None:
        self._pool = pool
        self._conn: Optional[_DB2Connection] = None
        self._raw: Any = None

    async def __aenter__(self) -> _DB2Connection:
        import ibm_db

        def _open() -> Any:
            return ibm_db.connect(self._pool._dsn, "", "")

        self._raw = await asyncio.to_thread(_open)
        self._conn = _DB2Connection(self._raw)
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        if self._raw is not None:
            import ibm_db

            await asyncio.to_thread(ibm_db.close, self._raw)


class _DB2Pool:
    """asyncpg.Pool-shape over per-acquire ibm_db connections.

    ibm_db doesn't ship a built-in async pool, so we open + close a
    fresh connection per ``acquire()`` -- same compromise the SQLite
    adapter makes.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def acquire(self) -> _DB2AcquireCM:
        return _DB2AcquireCM(self)

    async def close(self) -> None:
        return None


async def create_pool(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    min_size: int = 1,
    max_size: int = 10,
    **kwargs: Any,
) -> _DB2Pool:
    """Create an IBM Db2 pool. Args fall back to DB2_* env vars."""
    host = host or os.getenv("DB2_HOST", "localhost")
    port = port or int(os.getenv("DB2_PORT", "50000"))
    database = database or os.getenv("DB2_DB", "ENHANCED")
    user = user or os.getenv("DB2_USER", "cognee_user")
    password = password or require_secret("DB2_PASSWORD", dev_default="cognee_password")
    protocol = os.getenv("DB2_PROTOCOL", "TCPIP")

    dsn = _build_dsn(host, port, database, user, password, protocol)
    return _DB2Pool(dsn)
