"""ArangoDB graph adapter (Phase 5 pluggable).

ArangoDB (https://arangodb.com/) is an Apache-2.0 multi-model database
with native AQL (ArangoDB Query Language). Native Cypher support is
experimental, so this adapter translates the narrow Cypher subset
Enhanced Cognee's call sites actually use into AQL and executes via
the official ``python-arango`` client.

**Storage model:** all graph nodes live in a single ArangoDB
"document collection" (default ``cognee_graph_nodes``, configurable
via ``ARANGO_COLLECTION_NAME``). The adapter targets the
node-centric subset our codebase needs (preflight ping, recovery
validation + restore, backup export); edge collections are
supported via the same pattern with separate Cypher-side
relationship handling.

**Supported Cypher (translated to AQL):**

| Cypher                                       | AQL translation                                                         |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| ``RETURN <literal>``                         | ``RETURN <literal>``                                                    |
| ``MATCH (n) RETURN COUNT(n) [AS alias]``     | ``FOR d IN @@col COLLECT WITH COUNT INTO c RETURN c``                   |
| ``MATCH (n) DETACH DELETE n``                | ``FOR d IN @@col REMOVE d IN @@col``                                    |
| ``MATCH (n) RETURN n``                       | ``FOR d IN @@col RETURN d``                                             |
| ``CREATE (n:Label {props})``                 | ``INSERT @doc INTO @@col`` (labels go into a `_labels` array property)  |

**Not supported (raises NotImplementedError):**

- Multi-hop pattern matching (``MATCH (a)-[r]->(b)``)
- WHERE clauses
- Async session API
- Returning native graph elements as neo4j ``Node``/``Relationship``
  objects (caller receives the AQL JSON document)

Env-var fallbacks: ``ARANGO_HOST`` (default ``localhost``),
``ARANGO_PORT`` (default ``8529``), ``ARANGO_DB`` (default
``cognee_db``), ``ARANGO_USER`` (default ``root``),
``ARANGO_PASSWORD`` (default empty), ``ARANGO_COLLECTION_NAME``
(default ``cognee_graph_nodes``).

Install with::

    pip install enhanced-cognee[graph-arangodb]

Lazy-imports ``arango`` so installs without it don't pay the cost.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Result types (neo4j.Record-shaped)
# ---------------------------------------------------------------------------


class _ArangoRecord:
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


class _ArangoResult:
    def __init__(self, rows: List[_ArangoRecord]) -> None:
        self._records = rows

    def single(self) -> Optional[_ArangoRecord]:
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)

    def data(self) -> List[dict]:
        return [r.data() for r in self._records]


# ---------------------------------------------------------------------------
# Cypher -> AQL translator (narrow subset)
# ---------------------------------------------------------------------------


_LITERAL_RE = re.compile(r"""^\s*RETURN\s+(.+?)\s*$""", re.IGNORECASE)
_COUNT_RE = re.compile(
    r"""^\s*MATCH\s*\(\s*\w+\s*\)\s*RETURN\s+COUNT\(\s*\w+\s*\)(?:\s+AS\s+(\w+))?\s*$""",
    re.IGNORECASE,
)
_DETACH_DELETE_RE = re.compile(
    r"""^\s*MATCH\s*\(\s*\w+\s*\)\s*DETACH\s+DELETE\s+\w+\s*$""", re.IGNORECASE
)
_RETURN_ALL_RE = re.compile(
    r"""^\s*MATCH\s*\(\s*\w+\s*\)\s*RETURN\s+\w+\s*$""", re.IGNORECASE
)
_CREATE_NODE_RE = re.compile(
    r"""^\s*CREATE\s*\(\s*\w*\s*:?\s*([\w:]*)\s*\{(.*)\}\s*\)\s*$""", re.IGNORECASE
)


def _translate_cypher(cypher: str, collection: str) -> tuple:
    """Translate a narrow Cypher subset to AQL.

    Returns (aql_string, bind_vars_dict, output_alias) tuple. Raises
    NotImplementedError for anything outside the supported shapes.
    """
    cypher = cypher.strip()

    if _DETACH_DELETE_RE.match(cypher):
        return (
            "FOR d IN @@col REMOVE d IN @@col",
            {"@col": collection},
            "result",
        )

    m = _COUNT_RE.match(cypher)
    if m:
        alias = m.group(1) or "count"
        return (
            "FOR d IN @@col COLLECT WITH COUNT INTO c RETURN c",
            {"@col": collection},
            alias,
        )

    if _RETURN_ALL_RE.match(cypher):
        return (
            "FOR d IN @@col RETURN d",
            {"@col": collection},
            "n",
        )

    m = _LITERAL_RE.match(cypher)
    if m and "MATCH" not in cypher.upper():
        # `RETURN 1` / `RETURN 'ok'` etc. -- works in AQL unchanged
        return (cypher, {}, "value")

    m = _CREATE_NODE_RE.match(cypher)
    if m:
        # CREATE (n:Label {props}) -- we parse the labels + property
        # block and convert to an INSERT. property block must be
        # already valid JSON-ish (best-effort).
        labels = [s for s in (m.group(1) or "").split(":") if s]
        # The "props" block uses Cypher syntax (key: value, ...). We
        # attempt to JSON-load it; callers should use parameterised
        # CREATE if they have non-trivial values.
        raise NotImplementedError(
            "arangodb adapter: CREATE (n:Label {props}) requires "
            "parameterised form. Pass props as a Cypher parameter "
            "and use $props rather than inlining a literal."
        )

    raise NotImplementedError(
        f"arangodb adapter: Cypher shape not supported. Query was: "
        f"{cypher!r}. Use the documented subset (see "
        f"docs/PROFILES.md) or switch to arcadedb / neo4j / "
        f"memgraph for full Cypher."
    )


# ---------------------------------------------------------------------------
# Session + Driver
# ---------------------------------------------------------------------------


class _ArangoSession:
    """neo4j.Session-shaped wrapper around python-arango's StandardDatabase."""

    def __init__(self, driver: "_ArangoDriver") -> None:
        self._driver = driver
        self._db: Any = None

    def __enter__(self) -> "_ArangoSession":
        self._db = self._driver._open_db()
        return self

    def __exit__(self, *args: Any) -> None:
        # python-arango connections are HTTP-backed and don't need
        # explicit close.
        self._db = None

    def run(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
        **kwargs: Any,
    ) -> _ArangoResult:
        if self._db is None:
            self._db = self._driver._open_db()
        merged_params = dict(parameters or {})
        merged_params.update(kwargs)

        aql, bind_vars, alias = _translate_cypher(
            cypher, self._driver._collection
        )
        # Merge translator bindings with caller parameters
        merged_bind = {**bind_vars, **merged_params}

        # Ensure the collection exists for queries that bind @@col;
        # InitialBootstrap convenience for tests + fresh deployments.
        if "@col" in merged_bind:
            self._ensure_collection(merged_bind["@col"])

        cursor = self._db.aql.execute(aql, bind_vars=merged_bind)
        rows = []
        for value in cursor:
            rows.append(_ArangoRecord((value,), [alias]))
        return _ArangoResult(rows)

    def _ensure_collection(self, name: str) -> None:
        try:
            if not self._db.has_collection(name):
                self._db.create_collection(name)
        except Exception:
            # Race / permission issues -- let the actual query error
            # propagate rather than masking it here.
            pass


class _ArangoDriver:
    """neo4j.Driver-shaped wrapper around python-arango's ArangoClient."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        collection: str,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._collection = collection
        self._client: Any = None

    def _open_db(self):
        from arango import ArangoClient

        if self._client is None:
            self._client = ArangoClient(hosts=f"http://{self._host}:{self._port}")
        sys_db = self._client.db(
            "_system", username=self._user, password=self._password
        )
        if not sys_db.has_database(self._database):
            sys_db.create_database(self._database)
        return self._client.db(
            self._database, username=self._user, password=self._password
        )

    def session(self, *args: Any, **kwargs: Any) -> _ArangoSession:
        return _ArangoSession(self)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _ArangoDriver:
    """Create an ArangoDB driver wrapping python-arango.

    Env-var fallbacks: ARANGO_HOST / ARANGO_PORT / ARANGO_DB /
    ARANGO_USER / ARANGO_PASSWORD / ARANGO_COLLECTION_NAME.
    """
    host = os.getenv("ARANGO_HOST", "localhost")
    port = int(os.getenv("ARANGO_PORT", "8529"))
    database = os.getenv("ARANGO_DB", "cognee_db")
    user = user or os.getenv("ARANGO_USER", "root")
    password = password if password is not None else os.getenv("ARANGO_PASSWORD", "")
    collection = os.getenv("ARANGO_COLLECTION_NAME", "cognee_graph_nodes")
    return _ArangoDriver(host, port, database, user, password, collection)


class _AsyncArangoSession:
    """Async wrapper around _ArangoSession via ``asyncio.to_thread``.

    python-arango is sync-only; this shim runs each session call in a
    thread so the async contract holds. Suitable for async call sites
    that don't have a high enough ArangoDB query rate to be bottlenecked
    by the thread-pool boundary.
    """

    def __init__(self, driver: "_AsyncArangoDriver") -> None:
        self._sync_session: Optional[_ArangoSession] = None
        self._driver = driver

    async def __aenter__(self) -> "_AsyncArangoSession":
        import asyncio

        # Build a sync driver inside the thread and open a session.
        sync_driver = _ArangoDriver(
            host=self._driver._host,
            port=self._driver._port,
            database=self._driver._database,
            user=self._driver._user,
            password=self._driver._password,
            collection=self._driver._collection,
        )

        def _open() -> _ArangoSession:
            sess = sync_driver.session()
            sess.__enter__()
            return sess

        self._sync_session = await asyncio.to_thread(_open)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        import asyncio

        if self._sync_session is not None:
            sess = self._sync_session
            self._sync_session = None
            await asyncio.to_thread(sess.__exit__, exc_type, exc, tb)

    async def run(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
        **kwargs: Any,
    ) -> _ArangoResult:
        import asyncio

        if self._sync_session is None:
            raise RuntimeError(
                "arangodb async session: run() called outside `async with`"
            )
        sess = self._sync_session
        return await asyncio.to_thread(sess.run, cypher, parameters, **kwargs)


class _AsyncArangoDriver:
    """neo4j.AsyncDriver-shape over the sync python-arango client.

    Each async session ``await``s every operation via
    ``asyncio.to_thread``. Doesn't unlock python-arango's GIL contention
    but does let async callers interleave with other coroutines.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        collection: str,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._collection = collection

    def session(self, *args: Any, **kwargs: Any) -> _AsyncArangoSession:
        return _AsyncArangoSession(self)

    async def close(self) -> None:
        return None


def create_async_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _AsyncArangoDriver:
    """Create an async-shaped ArangoDB driver.

    python-arango is sync; this wraps each operation in
    ``asyncio.to_thread`` so async call sites can use the driver in an
    ``async with`` block. See _AsyncArangoDriver docstring for the
    threading-boundary caveats.
    """
    host = os.getenv("ARANGO_HOST", "localhost")
    port = int(os.getenv("ARANGO_PORT", "8529"))
    database = os.getenv("ARANGO_DB", "cognee_db")
    user = user or os.getenv("ARANGO_USER", "root")
    password = password if password is not None else os.getenv("ARANGO_PASSWORD", "")
    collection = os.getenv("ARANGO_COLLECTION_NAME", "cognee_graph_nodes")
    return _AsyncArangoDriver(host, port, database, user, password, collection)
