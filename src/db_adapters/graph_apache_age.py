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
- **Parameterised Cypher** (``$param`` syntax) since 2026-05-20 --
  parameters are passed to AGE's ``cypher(graph, $$ ... $$, agtype_map)``
  three-arg form via psycopg2 binding. See ``docs/PROFILES.md`` for
  the security note on dollar-quote breakout.
- **Async session API** (``get_async_graph_driver()``) since
  2026-05-20 -- routes through ``asyncpg`` with the same agtype unwrap
  path. The async driver exposes ``.session()`` as an
  ``async with`` context manager.

**Native graph elements (since 2026-05-20):**
- ``::vertex`` agtype payloads decode to ``_AGENode`` objects shaped
  like ``neo4j.graph.Node`` (``node.id`` / ``node.labels`` /
  ``node["prop"]`` / ``dict(node)``).
- ``::edge`` agtype payloads decode to ``_AGERelationship`` shaped
  like ``neo4j.graph.Relationship`` (``rel.type`` / ``rel.start_node``
  / ``rel.end_node``).
- ``::path`` payloads decode to a ``List[_AGENode | _AGERelationship]``
  in vertex-edge-vertex-... order.

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
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Sequence, Tuple

from src.secure_config import require_secret


class _AGENode:
    """``neo4j.graph.Node``-shaped wrapper around an AGE vertex agtype.

    AGE returns vertices as JSON like
    ``{"id": 844424930131969, "label": "Person", "properties": {...}}``
    suffixed with ``::vertex``. This wrapper exposes the same surface
    the ``neo4j`` Python driver exposes on its ``Node`` objects so call
    sites that do ``node.labels`` / ``node["name"]`` / ``dict(node)``
    keep working when ``ENHANCED_GRAPH_PROVIDER=apache_age``.

    Supports both AGE's single-label (``"label": "Person"``) form *and*
    the multi-label list form some queries return.
    """

    __slots__ = ("_id", "_labels", "_props")

    def __init__(
        self,
        node_id: int,
        labels: Sequence[str] | str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._id = node_id
        if isinstance(labels, str):
            self._labels: FrozenSet[str] = frozenset((labels,)) if labels else frozenset()
        else:
            self._labels = frozenset(labels)
        self._props = dict(properties or {})

    @property
    def id(self) -> int:
        return self._id

    @property
    def element_id(self) -> str:
        return str(self._id)

    @property
    def labels(self) -> FrozenSet[str]:
        return self._labels

    def __getitem__(self, key: str) -> Any:
        return self._props[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._props.get(key, default)

    def keys(self) -> List[str]:
        return list(self._props.keys())

    def values(self) -> List[Any]:
        return list(self._props.values())

    def items(self) -> List[Tuple[str, Any]]:
        return list(self._props.items())

    def __iter__(self) -> Iterator[str]:
        return iter(self._props)

    def __contains__(self, key: object) -> bool:
        return key in self._props

    def __len__(self) -> int:
        return len(self._props)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _AGENode):
            return NotImplemented
        return self._id == other._id and self._labels == other._labels

    def __hash__(self) -> int:
        return hash(("_AGENode", self._id))

    def __repr__(self) -> str:
        label_str = ":".join(sorted(self._labels)) if self._labels else ""
        return f"<Node id={self._id} labels={{{label_str}}} properties={self._props!r}>"


class _AGERelationship:
    """``neo4j.graph.Relationship``-shaped wrapper around an AGE edge agtype.

    AGE returns edges as JSON like
    ``{"id": ..., "label": "KNOWS", "start_id": ..., "end_id": ...,
       "properties": {...}}`` suffixed with ``::edge``. The ``start_node``
    / ``end_node`` attributes are lazily-resolved ``_AGENode`` stubs
    that carry only the vertex id -- AGE's edge representation doesn't
    inline the endpoint labels/properties, so a caller that needs those
    must issue a second ``MATCH (n) WHERE id(n) = ...`` query.
    """

    __slots__ = ("_id", "_type", "_start_id", "_end_id", "_props")

    def __init__(
        self,
        rel_id: int,
        rel_type: str,
        start_id: int,
        end_id: int,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._id = rel_id
        self._type = rel_type
        self._start_id = start_id
        self._end_id = end_id
        self._props = dict(properties or {})

    @property
    def id(self) -> int:
        return self._id

    @property
    def element_id(self) -> str:
        return str(self._id)

    @property
    def type(self) -> str:
        return self._type

    @property
    def start_node(self) -> _AGENode:
        return _AGENode(self._start_id, ())

    @property
    def end_node(self) -> _AGENode:
        return _AGENode(self._end_id, ())

    @property
    def nodes(self) -> Tuple[_AGENode, _AGENode]:
        return (self.start_node, self.end_node)

    def __getitem__(self, key: str) -> Any:
        return self._props[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._props.get(key, default)

    def keys(self) -> List[str]:
        return list(self._props.keys())

    def values(self) -> List[Any]:
        return list(self._props.values())

    def items(self) -> List[Tuple[str, Any]]:
        return list(self._props.items())

    def __iter__(self) -> Iterator[str]:
        return iter(self._props)

    def __contains__(self, key: object) -> bool:
        return key in self._props

    def __len__(self) -> int:
        return len(self._props)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _AGERelationship):
            return NotImplemented
        return self._id == other._id and self._type == other._type

    def __hash__(self) -> int:
        return hash(("_AGERelationship", self._id))

    def __repr__(self) -> str:
        return (
            f"<Relationship id={self._id} type={self._type!r} "
            f"start={self._start_id} end={self._end_id} properties={self._props!r}>"
        )


def _agtype_to_element(parsed: Dict[str, Any], kind: str) -> Any:
    """Convert a parsed agtype dict into the matching graph element.

    Returns the parsed dict unchanged if the expected keys are absent;
    this keeps the path safe for malformed payloads (a rare-but-real
    happens-when-AGE-version-skews scenario).
    """
    if not isinstance(parsed, dict):
        return parsed
    node_id = parsed.get("id")
    if kind == "vertex" and node_id is not None and "label" in parsed:
        return _AGENode(node_id, parsed.get("label", ""), parsed.get("properties"))
    if (
        kind == "edge"
        and node_id is not None
        and "label" in parsed
        and "start_id" in parsed
        and "end_id" in parsed
    ):
        return _AGERelationship(
            node_id,
            parsed["label"],
            parsed["start_id"],
            parsed["end_id"],
            parsed.get("properties"),
        )
    return parsed


def _unwrap_agtype(value: Any) -> Any:
    """Best-effort parse of an AGE ``agtype`` value to a Python primitive.

    psycopg2 returns ``agtype`` as ``str`` (or bytes). AGE appends
    ``::vertex`` / ``::edge`` / ``::path`` for graph elements; strip
    those, JSON-decode what remains, then convert ``::vertex`` /
    ``::edge`` payloads into ``_AGENode`` / ``_AGERelationship`` (the
    ``neo4j.graph.{Node, Relationship}``-shaped wrappers above). Paths
    decode to ``List[Union[_AGENode, _AGERelationship]]``. If JSON
    decoding fails, the raw string is returned so the caller can
    inspect it.
    """
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        kind: Optional[str] = None
        for suffix in ("::vertex", "::edge", "::path"):
            if value.endswith(suffix):
                kind = suffix[2:]
                value = value[: -len(suffix)]
                break
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return value
        if kind in ("vertex", "edge"):
            return _agtype_to_element(parsed, kind)
        if kind == "path" and isinstance(parsed, list):
            # AGE path = alternating [vertex, edge, vertex, edge, ...].
            # Convert each element by inspecting its shape.
            out: List[Any] = []
            for idx, item in enumerate(parsed):
                if isinstance(item, dict) and "start_id" in item and "end_id" in item:
                    out.append(_agtype_to_element(item, "edge"))
                elif isinstance(item, dict) and "label" in item:
                    out.append(_agtype_to_element(item, "vertex"))
                else:
                    out.append(item)
            return out
        return parsed
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
        merged_params = _merge_params(parameters, kwargs)
        _validate_cypher_payload(cypher)

        cur = self._conn.cursor()
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        if merged_params:
            sql = (
                f"SELECT * FROM cypher(%s, $$ {cypher} $$, %s::agtype) "
                f"AS (result agtype);"
            )
            cur.execute(sql, (self._graph, json.dumps(merged_params)))
        else:
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
        or require_secret("POSTGRES_PASSWORD", dev_default="cognee_password")
    )
    graph_name = os.getenv("AGE_GRAPH_NAME", "cognee_graph")
    return _AGEDriver(host, port, database, user, password, graph_name)


def create_async_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> "_AsyncAGEDriver":
    """Return an asyncpg-backed AGE driver.

    Connection details come from AGE_* env vars (falling through to
    POSTGRES_*). ``uri`` is accepted for neo4j-driver shape compat but
    ignored -- AGE config is env-var-driven.
    """
    host = os.getenv("AGE_HOST") or os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("AGE_PORT") or os.getenv("POSTGRES_PORT", "25432"))
    database = os.getenv("AGE_DB") or os.getenv("POSTGRES_DB", "cognee_db")
    user = user or os.getenv("AGE_USER") or os.getenv("POSTGRES_USER", "cognee_user")
    password = (
        password
        or os.getenv("AGE_PASSWORD")
        or require_secret("POSTGRES_PASSWORD", dev_default="cognee_password")
    )
    graph_name = os.getenv("AGE_GRAPH_NAME", "cognee_graph")
    return _AsyncAGEDriver(host, port, database, user, password, graph_name)


# ---------------------------------------------------------------------------
# Helpers shared by sync + async paths
# ---------------------------------------------------------------------------


def _merge_params(parameters: Optional[dict], kwargs: dict) -> dict:
    merged: dict = {}
    if parameters:
        merged.update(parameters)
    if kwargs:
        merged.update(kwargs)
    return merged


def _validate_cypher_payload(cypher: str) -> None:
    """Reject Cypher payloads that would break out of the dollar-quoted block.

    AGE wraps Cypher in ``$$ ... $$`` to delimit it as a string literal
    inside SQL. A Cypher payload containing ``$$`` would close the block
    early and inject arbitrary SQL. Rather than dollar-tagging
    (``$AGE$ ... $AGE$``) we just reject the case -- no legitimate
    Cypher query needs a literal ``$$`` sequence.
    """
    if "$$" in cypher:
        raise ValueError(
            "Cypher payload contains '$$' which would break out of AGE's "
            "dollar-quoted block. Refactor the query to avoid the literal."
        )


# ---------------------------------------------------------------------------
# Async driver path (asyncpg-backed)
# ---------------------------------------------------------------------------


class _AsyncAGESession:
    """``neo4j.AsyncSession``-shaped wrapper executing Cypher via ``cypher()``.

    Opens a fresh asyncpg connection per ``async with`` block. Commits
    on clean exit, no-ops on exception (asyncpg auto-rolls-back on
    connection close mid-transaction).
    """

    def __init__(self, driver: "_AsyncAGEDriver", *, database: Optional[str] = None) -> None:
        self._driver = driver
        self._graph = database or driver._graph_name
        self._conn: Any = None

    async def __aenter__(self) -> "_AsyncAGESession":
        import asyncpg

        self._conn = await asyncpg.connect(
            host=self._driver._host,
            port=self._driver._port,
            database=self._driver._database,
            user=self._driver._user,
            password=self._driver._password,
        )
        await self._conn.execute("LOAD 'age'")
        await self._conn.execute("SET search_path = ag_catalog, public")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def run(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
        **kwargs: Any,
    ) -> _AGEResult:
        merged_params = _merge_params(parameters, kwargs)
        _validate_cypher_payload(cypher)

        if merged_params:
            # asyncpg uses $1, $2 ... placeholders; AGE's three-arg cypher()
            # form: cypher('graph', $$ ... $$, $1::agtype). The cypher body
            # itself is string-formatted into the SQL because it's a literal
            # inside the dollar-quoted block, not a SQL parameter.
            sql = (
                f"SELECT * FROM cypher($1, $$ {cypher} $$, $2::agtype) "
                f"AS (result agtype)"
            )
            rows = await self._conn.fetch(sql, self._graph, json.dumps(merged_params))
        else:
            sql = f"SELECT * FROM cypher($1, $$ {cypher} $$) AS (result agtype)"
            rows = await self._conn.fetch(sql, self._graph)

        # asyncpg returns asyncpg.Record objects; convert each to a tuple
        # of column values so _AGERecord's existing agtype-unwrap path
        # works unchanged.
        tuple_rows = [tuple(r.values()) for r in rows]
        return _AGEResult(tuple_rows, ["result"])


class _AsyncAGEDriver:
    """``neo4j.AsyncDriver``-shape over asyncpg."""

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

    def session(self, *args: Any, database: Optional[str] = None, **kwargs: Any) -> _AsyncAGESession:
        return _AsyncAGESession(self, database=database)

    async def close(self) -> None:
        # Sessions own their connections; nothing persistent to close.
        return None
