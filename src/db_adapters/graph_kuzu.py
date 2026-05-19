"""Kuzu graph adapter (Phase 5 pluggable).

Kuzu (https://kuzudb.com/) is an MIT-licensed embedded graph database
with native Cypher support. Unlike Neo4j / ArcadeDB / Memgraph, Kuzu
runs **in-process** -- there is no network protocol, no separate
container. The driver opens a file-system path and queries via the
``kuzu`` Python package's ``Connection.execute()`` API.

This adapter wraps Kuzu's native API in a minimal ``neo4j.Driver``
shape so callers in ``src/agent_memory_integration.py`` and friends
can switch between Kuzu and Bolt-based providers via
``ENHANCED_GRAPH_PROVIDER`` without code changes.

**Supported today:**

- Cypher queries through ``.session().run(cypher)``
- ``.single()`` / iteration / ``record[0]`` / ``record["alias"]``
- Cypher *parameters* via the second positional / kwargs arg
  (Kuzu has first-class parameter support, unlike AGE)

**Not yet supported (raises NotImplementedError):**

- Async driver / session API. Kuzu's Python package does not expose
  an asyncio interface; the workload is in-process anyway, so add
  ``asyncio.to_thread`` around the sync calls at the call site if you
  need to interleave with async I/O.

Env-var fallbacks: ``KUZU_DB_PATH`` (default ``./kuzu_data`` -- a
filesystem directory that Kuzu creates on first open).

Lazy-imports the ``kuzu`` package so installations that don't opt
into Kuzu don't pay the import cost. Install with::

    pip install enhanced-cognee[graph-kuzu]
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Sequence


class _KuzuRecord:
    """Minimal ``neo4j.Record``-shaped wrapper around a Kuzu result row."""

    __slots__ = ("_values", "_columns")

    def __init__(self, values: Sequence[Any], columns: List[str]) -> None:
        self._values = tuple(values)
        self._columns = columns

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._columns.index(key)]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def keys(self) -> List[str]:
        return list(self._columns)

    def values(self) -> tuple:
        return self._values

    def data(self) -> dict:
        return dict(zip(self._columns, self._values))


class _KuzuResult:
    """``neo4j.Result``-shape collecting all rows from a Kuzu query result."""

    def __init__(self, query_result: Any) -> None:
        # Kuzu QueryResult exposes get_column_names() + has_next()/get_next()
        columns: List[str] = list(query_result.get_column_names())
        rows: List[_KuzuRecord] = []
        while query_result.has_next():
            row = query_result.get_next()
            rows.append(_KuzuRecord(row, columns))
        self._records = rows

    def single(self) -> Optional[_KuzuRecord]:
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)

    def data(self) -> List[dict]:
        return [r.data() for r in self._records]


class _KuzuSession:
    """``neo4j.Session`` context manager around a Kuzu Connection."""

    def __init__(self, driver: "_KuzuDriver") -> None:
        self._driver = driver
        self._conn = driver._open_connection()

    def __enter__(self) -> "_KuzuSession":
        return self

    def __exit__(self, *args: Any) -> None:
        # Kuzu connections close when garbage-collected; explicit close
        # is fine but not strictly necessary.
        del self._conn

    def run(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
        **kwargs: Any,
    ) -> _KuzuResult:
        params = dict(parameters or {})
        params.update(kwargs)
        if params:
            query_result = self._conn.execute(cypher, params)
        else:
            query_result = self._conn.execute(cypher)
        return _KuzuResult(query_result)


class _KuzuDriver:
    """``neo4j.Driver``-shape over a Kuzu Database + per-session Connection."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._database = None  # lazy-init on first session

    def _open_connection(self):
        import kuzu

        if self._database is None:
            self._database = kuzu.Database(self._db_path)
        return kuzu.Connection(self._database)

    def session(self, *args: Any, **kwargs: Any) -> _KuzuSession:
        return _KuzuSession(self)

    def close(self) -> None:
        # Drop the Database reference so Kuzu releases the FS lock.
        self._database = None


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _KuzuDriver:
    """Create a Kuzu driver pointing at the configured DB path.

    ``uri``/``user``/``password`` are accepted for neo4j-driver shape
    compatibility but are ignored -- Kuzu is filesystem-backed.
    Override the DB path via the ``KUZU_DB_PATH`` env var.
    """
    db_path = os.getenv("KUZU_DB_PATH", "./kuzu_data")
    return _KuzuDriver(db_path)


def create_async_driver(*args: Any, **kwargs: Any):
    """Kuzu has no async API. Use the sync path or wrap with asyncio.to_thread."""
    raise NotImplementedError(
        "ENHANCED_GRAPH_PROVIDER=kuzu does not expose an async session API "
        "(Kuzu has no native asyncio support). Use the sync "
        "get_graph_driver() entry point, or wrap calls in "
        "asyncio.to_thread at the call site. See docs/PROFILES.md."
    )
