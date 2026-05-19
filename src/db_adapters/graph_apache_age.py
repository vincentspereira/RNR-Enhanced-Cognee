"""Apache AGE graph adapter (Phase 3 pluggable).

Apache AGE (https://age.apache.org/) is a Postgres extension that adds
openCypher support via the SQL function ``cypher('graph', $$ ... $$)``.
This adapter exposes a minimal ``neo4j.Driver``-shaped surface so that
existing call sites in
``src/agent_memory_integration.py``, ``src/recovery_manager.py``, and
``src/backup_manager.py`` can switch between Neo4j / ArcadeDB and AGE
via ``ENHANCED_GRAPH_PROVIDER`` without code changes.

**Why a hand-rolled shim:** unlike ArcadeDB (Phase 2), AGE does *not*
expose a Bolt-compatible wire protocol. Queries run as SQL through
``psycopg2``, with the Cypher payload wrapped in ``cypher(...)``. AGE
also requires an explicit ``AS (col agtype)`` column-list on every
``cypher()`` call, so simple parameter-passing requires an out-of-band
conversion. To keep the adapter small we support a deliberately narrow
slice of behaviour; everything else raises ``NotImplementedError`` with
a pointer to ``docs/PROFILES.md``.

**Supported today:**
- Connectivity ping queries (``RETURN 1``).
- Simple scalar-projection queries (``MATCH (n) RETURN COUNT(n) AS c``).
- ``.session()`` context manager, ``.run(cypher)``, ``.single()``,
  iteration over result records, ``record[0]`` / ``record["alias"]``.

**Not yet supported (raises NotImplementedError):**
- Parameterised Cypher (``$param`` syntax).
- Async driver / session API.
- Returning whole graph elements as Python neo4j ``Node`` / ``Relationship``
  objects -- callers receive the AGE ``agtype`` value parsed as JSON.

Env-var fallbacks (in order): ``AGE_HOST`` / ``AGE_PORT`` / ``AGE_DB`` /
``AGE_USER`` / ``AGE_PASSWORD``, then ``POSTGRES_*`` (since AGE runs
inside our existing Postgres container). ``AGE_GRAPH_NAME`` defaults to
``cognee_graph``.

Lazy-imports ``psycopg2`` so callers patching it via ``sys.modules`` or
``psycopg2.connect`` keep working.

See ``docs/PROFILES.md`` for the supported-query matrix and the steps to
enable the AGE extension inside the Postgres container.
"""

from __future__ import annotations

import json
import os
from typing import Any, List, Optional, Sequence


def _unwrap_agtype(value: Any) -> Any:
    """Best-effort parse of an AGE ``agtype`` value to a Python primitive.

    psycopg2 returns ``agtype`` as ``str`` (or bytes). AGE appends
    ``::vertex`` / ``::edge`` / ``::path`` for graph elements; strip
    those and JSON-decode what remains. If decoding fails the raw
    string is returned so the caller can inspect it.
    """
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        for suffix in ("::vertex", "::edge", "::path"):
            if value.endswith(suffix):
                value = value[: -len(suffix)]
                break
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


class _AGERecord:
    """``neo4j.Record``-shaped wrapper around a psycopg2 row."""

    __slots__ = ("_row", "_columns")

    def __init__(self, row: Sequence[Any], columns: List[str]) -> None:
        self._row = tuple(_unwrap_agtype(v) for v in row)
        self._columns = columns

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._row[key]
        return self._row[self._columns.index(key)]

    def __iter__(self):
        return iter(self._row)

    def __len__(self) -> int:
        return len(self._row)

    def keys(self) -> List[str]:
        return list(self._columns)

    def values(self) -> tuple:
        return self._row

    def data(self) -> dict:
        return dict(zip(self._columns, self._row))


class _AGEResult:
    """``neo4j.Result``-shaped wrapper around a list of rows."""

    def __init__(self, rows: Sequence[Sequence[Any]], columns: List[str]) -> None:
        self._records = [_AGERecord(row, columns) for row in rows]

    def single(self) -> Optional[_AGERecord]:
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)

    def data(self) -> List[dict]:
        return [record.data() for record in self._records]


class _AGESession:
    """``neo4j.Session``-shaped wrapper executing Cypher via ``cypher()``."""

    def __init__(self, driver: "_AGEDriver", *, database: Optional[str] = None) -> None:
        self._driver = driver
        self._graph = database or driver._graph_name
        self._conn = driver._connect()

    def __enter__(self) -> "_AGESession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._conn.close()

    def run(self, cypher: str, parameters: Optional[dict] = None, **kwargs: Any) -> _AGEResult:
        if parameters:
            raise NotImplementedError(
                "ENHANCED_GRAPH_PROVIDER=apache_age does not support "
                "parameterised Cypher queries yet. Inline the values or "
                "use neo4j / arcadedb. See docs/PROFILES.md."
            )
        if kwargs:
            raise NotImplementedError(
                "ENHANCED_GRAPH_PROVIDER=apache_age does not support keyword "
                "Cypher parameters yet. See docs/PROFILES.md."
            )
        cur = self._conn.cursor()
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        sql = f"SELECT * FROM cypher(%s, $$ {cypher} $$) AS (result agtype);"
        cur.execute(sql, (self._graph,))
        rows = cur.fetchall() if cur.description else []
        return _AGEResult(rows, ["result"])


class _AGEDriver:
    """``neo4j.Driver``-shaped wrapper around a psycopg2 connection factory."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        graph_name: str,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._graph_name = graph_name

    def _connect(self):
        import psycopg2

        return psycopg2.connect(
            host=self._host,
            port=self._port,
            dbname=self._database,
            user=self._user,
            password=self._password,
        )

    def session(self, *args: Any, database: Optional[str] = None, **kwargs: Any) -> _AGESession:
        return _AGESession(self, database=database)

    def close(self) -> None:
        # Sessions own their connections; nothing persistent to close.
        return None


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _AGEDriver:
    """Return an ``_AGEDriver``. The ``uri`` arg is accepted for caller compat
    (it is ignored -- AGE config comes from AGE_* / POSTGRES_* env vars).
    """
    host = os.getenv("AGE_HOST") or os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("AGE_PORT") or os.getenv("POSTGRES_PORT", "25432"))
    database = os.getenv("AGE_DB") or os.getenv("POSTGRES_DB", "cognee_db")
    user = user or os.getenv("AGE_USER") or os.getenv("POSTGRES_USER", "cognee_user")
    password = (
        password
        or os.getenv("AGE_PASSWORD")
        or os.getenv("POSTGRES_PASSWORD", "cognee_password")
    )
    graph_name = os.getenv("AGE_GRAPH_NAME", "cognee_graph")
    return _AGEDriver(host, port, database, user, password, graph_name)


def create_async_driver(*args: Any, **kwargs: Any):
    """Async path is not implemented for AGE.

    Use the sync ``get_graph_driver()`` entry point, or switch to
    ``arcadedb`` / ``neo4j`` which provide a real ``AsyncDriver``.
    """
    raise NotImplementedError(
        "ENHANCED_GRAPH_PROVIDER=apache_age does not yet expose an async "
        "session API. Use the sync get_graph_driver() entry point, or "
        "switch to arcadedb / neo4j. See docs/PROFILES.md."
    )
