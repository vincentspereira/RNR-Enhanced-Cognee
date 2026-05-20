"""Microsoft SQL Server relational adapter (Phase 5 pluggable).

Wraps the ``aioodbc`` driver (Apache-2.0; built on pyodbc) against
the Microsoft ODBC Driver for SQL Server. Targets:

  - SQL Server 2019+
  - Azure SQL Database
  - Azure SQL Managed Instance

Exposes the same ``asyncpg.Pool``-shape as the rest of the relational
tier. The aioodbc driver handles connection pooling natively.

**Compatibility caveats vs asyncpg:**

- Parameter substitution uses ``?`` placeholders (DB-API). Not
  compatible with asyncpg's ``$1`` / ``$2``.
- T-SQL is similar to but not identical to PostgreSQL SQL. Common
  divergences:
    * ``TOP n`` instead of ``LIMIT n``
    * ``[brackets]`` for reserved identifier quoting (not ``""``)
    * ``IDENTITY(1,1)`` instead of ``SERIAL``
    * ``DATETIME2`` instead of ``TIMESTAMPTZ``
    * No native JSONB; use ``NVARCHAR(MAX)`` + ``OPENJSON()`` /
      ``JSON_VALUE()``
- The ODBC driver itself must be installed on the host -- this is
  a ~50MB Microsoft package, not a pure-Python wheel. See:
  https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server

When to pick MS SQL Server:

- You operate SQL Server elsewhere and want one operational
  surface for the team.
- Your enterprise license already covers SQL Server.
- You're on Azure and want first-party managed PaaS database
  integration.

Env-var fallbacks (in order):
    MSSQL_HOST       (default ``localhost``)
    MSSQL_PORT       (default ``1433``)
    MSSQL_DB         (default ``enhanced_cognee``)
    MSSQL_USER       (default ``sa``)
    MSSQL_PASSWORD   (default ``cognee_password``)
    MSSQL_DRIVER     (default ``ODBC Driver 18 for SQL Server``)

Install with::

    # Microsoft ODBC driver (per OS)
    # Linux: https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
    # macOS: brew install msodbcsql18
    # Windows: included in SQL Server Native Client

    pip install enhanced-cognee[relational-mssql]
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple


def _build_dsn(
    host: str, port: int, database: str, user: str, password: str, driver: str
) -> str:
    return (
        f"Driver={{{driver}}};"
        f"Server={host},{port};"
        f"Database={database};"
        f"UID={user};"
        f"PWD={password};"
        # TLS encryption is on by default in Driver 18; trust the
        # cert if the server is using a self-signed one (dev/test).
        "Encrypt=yes;TrustServerCertificate=yes;"
    )


class _MSSQLConnection:
    """``asyncpg.Connection``-shaped wrapper around an aioodbc connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def fetchval(self, sql: str, *args: Any) -> Any:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            row = await cur.fetchone()
            return row[0] if row else None

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Tuple[Any, ...]]:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            row = await cur.fetchone()
            return tuple(row) if row else None

    async def fetch(self, sql: str, *args: Any) -> List[Tuple[Any, ...]]:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall()
            return [tuple(r) for r in rows]

    async def execute(self, sql: str, *args: Any) -> str:
        async with self._conn.cursor() as cur:
            await cur.execute(sql, args)
            await self._conn.commit()
            return f"OK rows={cur.rowcount}"

    async def executemany(self, sql: str, args_iter: Any) -> None:
        async with self._conn.cursor() as cur:
            await cur.executemany(sql, list(args_iter))
            await self._conn.commit()


class _MSSQLAcquireCM:
    def __init__(self, pool: "_MSSQLPool") -> None:
        self._pool = pool
        self._raw: Any = None
        self._conn: Optional[_MSSQLConnection] = None

    async def __aenter__(self) -> _MSSQLConnection:
        self._raw = await self._pool._raw_pool.acquire()
        self._conn = _MSSQLConnection(self._raw)
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        if self._raw is not None:
            await self._pool._raw_pool.release(self._raw)


class _MSSQLPool:
    """asyncpg.Pool-shape over an aioodbc pool."""

    def __init__(self, raw_pool: Any) -> None:
        self._raw_pool = raw_pool

    def acquire(self) -> _MSSQLAcquireCM:
        return _MSSQLAcquireCM(self)

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
) -> _MSSQLPool:
    """Create an MS SQL Server pool via aioodbc."""
    import aioodbc

    host = host or os.getenv("MSSQL_HOST", "localhost")
    port = port or int(os.getenv("MSSQL_PORT", "1433"))
    database = database or os.getenv("MSSQL_DB", "enhanced_cognee")
    user = user or os.getenv("MSSQL_USER", "sa")
    password = password or os.getenv("MSSQL_PASSWORD", "cognee_password")
    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")

    dsn = _build_dsn(host, port, database, user, password, driver)

    raw_pool = await aioodbc.create_pool(
        dsn=dsn,
        minsize=min_size,
        maxsize=max_size,
        autocommit=False,
    )
    return _MSSQLPool(raw_pool)
