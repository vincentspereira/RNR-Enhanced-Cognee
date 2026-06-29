"""Databricks SQL Warehouse adapter (Phase 5 pluggable).

Wraps the ``databricks-sql-connector`` (Apache-2.0) Python driver
against a Databricks SQL Warehouse endpoint. Useful when the
analytics workloads live in a Databricks lakehouse and you want
RNR Enhanced Cognee to share that data plane.

The connector is sync-only natively; we wrap calls in
``asyncio.to_thread`` so the async signature is honest. Same
``asyncpg.Pool``-shape as the rest of the relational tier.

**Compatibility caveats vs asyncpg:**

- Parameter substitution uses ``%(name)s`` for named parameters
  or ``?`` for positional, depending on the cursor mode. The
  connector defaults to positional ``?`` placeholders.
- SQL dialect is Spark SQL flavoured (mostly ANSI-standard with
  Databricks extensions like ``MERGE INTO`` and ``OPTIMIZE``).
- No JSONB type; use ``STRING`` (with JSON helper functions:
  ``parse_json``, ``json_query``) or the variant type in DBR 14+.
- No native pgvector; Databricks has a managed Vector Search
  service that's separate (and not exposed via SQL Warehouse).
- The endpoint URL contains the host name, HTTP path, and access
  token; auth is bearer-token based (no username/password).

When to pick Databricks:

- Your analytics + ML pipelines already live in Databricks.
- You want one data plane for memory analytics + downstream
  notebooks.
- You're using Unity Catalog for governance.

Env-var fallbacks (in order):
    DATABRICKS_SERVER_HOSTNAME    (required; e.g. ``abc-12345.cloud.databricks.com``)
    DATABRICKS_HTTP_PATH          (required; e.g. ``/sql/1.0/warehouses/abc123``)
    DATABRICKS_ACCESS_TOKEN       (required; personal access token or
                                   OAuth machine-to-machine token)
    DATABRICKS_CATALOG            (default ``hive_metastore``)
    DATABRICKS_SCHEMA             (default ``default``)

Install with::

    pip install enhanced-cognee[relational-databricks]
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, List, Optional, Tuple


class _DatabricksConnection:
    """``asyncpg.Connection``-shaped wrapper around a databricks.sql connection."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def fetchval(self, sql: str, *args: Any) -> Any:
        def _run() -> Any:
            with self._conn.cursor() as cur:
                cur.execute(sql, args if args else None)
                row = cur.fetchone()
                return row[0] if row else None

        return await asyncio.to_thread(_run)

    async def fetchrow(self, sql: str, *args: Any) -> Optional[Tuple[Any, ...]]:
        def _run() -> Optional[Tuple[Any, ...]]:
            with self._conn.cursor() as cur:
                cur.execute(sql, args if args else None)
                row = cur.fetchone()
                return tuple(row) if row else None

        return await asyncio.to_thread(_run)

    async def fetch(self, sql: str, *args: Any) -> List[Tuple[Any, ...]]:
        def _run() -> List[Tuple[Any, ...]]:
            with self._conn.cursor() as cur:
                cur.execute(sql, args if args else None)
                rows = cur.fetchall()
                return [tuple(r) for r in rows]

        return await asyncio.to_thread(_run)

    async def execute(self, sql: str, *args: Any) -> str:
        def _run() -> str:
            with self._conn.cursor() as cur:
                cur.execute(sql, args if args else None)
                # Databricks SQL doesn't expose a rowcount on DDL;
                # use the best-effort property when present.
                affected = getattr(cur, "rowcount", -1)
                return f"OK rows={affected}"

        return await asyncio.to_thread(_run)

    async def executemany(self, sql: str, args_iter: Any) -> None:
        rows = list(args_iter)

        def _run() -> None:
            with self._conn.cursor() as cur:
                # Databricks doesn't have a native executemany --
                # iterate the rows.
                for row in rows:
                    cur.execute(sql, row)

        await asyncio.to_thread(_run)


class _DatabricksAcquireCM:
    def __init__(self, pool: "_DatabricksPool") -> None:
        self._pool = pool
        self._raw: Any = None
        self._conn: Optional[_DatabricksConnection] = None

    async def __aenter__(self) -> _DatabricksConnection:
        from databricks import sql as databricks_sql

        def _open() -> Any:
            return databricks_sql.connect(
                server_hostname=self._pool._server_hostname,
                http_path=self._pool._http_path,
                access_token=self._pool._access_token,
                catalog=self._pool._catalog,
                schema=self._pool._schema,
            )

        self._raw = await asyncio.to_thread(_open)
        self._conn = _DatabricksConnection(self._raw)
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        if self._raw is not None:
            await asyncio.to_thread(self._raw.close)


class _DatabricksPool:
    """asyncpg.Pool-shape over per-acquire databricks.sql connections."""

    def __init__(
        self,
        server_hostname: str,
        http_path: str,
        access_token: str,
        catalog: str,
        schema: str,
    ) -> None:
        self._server_hostname = server_hostname
        self._http_path = http_path
        self._access_token = access_token
        self._catalog = catalog
        self._schema = schema

    def acquire(self) -> _DatabricksAcquireCM:
        return _DatabricksAcquireCM(self)

    async def close(self) -> None:
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
) -> _DatabricksPool:
    """Create a Databricks SQL Warehouse pool.

    ``host`` / ``port`` / ``user`` / ``password`` kwargs are ignored;
    Databricks uses server hostname + HTTP path + access token. Falls
    back to DATABRICKS_* env vars.
    """
    server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    access_token = os.getenv("DATABRICKS_ACCESS_TOKEN")
    if not (server_hostname and http_path and access_token):
        raise ValueError(
            "Databricks adapter: DATABRICKS_SERVER_HOSTNAME / "
            "DATABRICKS_HTTP_PATH / DATABRICKS_ACCESS_TOKEN must all be "
            "set before opening a pool."
        )

    catalog = os.getenv("DATABRICKS_CATALOG", "hive_metastore")
    schema = database or os.getenv("DATABRICKS_SCHEMA", "default")

    return _DatabricksPool(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token,
        catalog=catalog,
        schema=schema,
    )
