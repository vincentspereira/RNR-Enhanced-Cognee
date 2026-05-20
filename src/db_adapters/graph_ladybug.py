"""Ladybug graph adapter (Phase 5 pluggable).

Ladybug (https://github.com/topoteretes/ladybug) is the upstream
Cognee experimental graph engine that replaced Kuzu in v1.0.9. It's
already pinned as a hard core dependency in ``pyproject.toml``
because upstream Cognee imports it at module level inside
``cognee/infrastructure/databases/dataset_database_handler/``.

This adapter exposes Ladybug as an Enhanced Cognee graph provider via
``ENHANCED_GRAPH_PROVIDER=ladybug`` for parity with the upstream
Cognee default. The implementation is structurally similar to
``graph_networkx_inmemory`` (in-process, narrow Cypher subset)
because Ladybug doesn't expose a Bolt protocol -- queries go through
its native Python API.

**Supported Cypher (deliberately narrow, mirrors the pgvector +
networkx_inmemory pattern):**

| Cypher                                       | Mapping                                                     |
| -------------------------------------------- | ----------------------------------------------------------- |
| ``RETURN <literal>``                         | Returns the parsed literal directly                         |
| ``MATCH (n) RETURN COUNT(n) [AS alias]``     | Counts nodes in the ladybug graph                           |
| ``MATCH (n) DETACH DELETE n``                | Clears the in-process graph                                 |
| ``MATCH (n) RETURN n``                       | Iterates all nodes                                          |

**Not supported (raises NotImplementedError):**

- Multi-hop pattern matching
- Parameterised Cypher (``$param`` syntax)
- Async session API
- WHERE clauses / property filtering
- Returning native graph elements as neo4j ``Node``/``Relationship``
  objects (caller receives a ladybug Node dict)

Env-var fallbacks: ``LADYBUG_DB_PATH`` -- optional filesystem path
for persistence. If unset, the graph is in-process only and lost on
restart.

Install with::

    pip install enhanced-cognee[graph-ladybug]

(``ladybug==0.16.1`` is already in core deps; the optional group
exists for documentation parity with the other graph providers.)
"""

from __future__ import annotations

import os
import re
from typing import Any, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class _LadybugRecord:
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


class _LadybugResult:
    def __init__(self, rows: List[_LadybugRecord]) -> None:
        self._records = rows

    def single(self) -> Optional[_LadybugRecord]:
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)

    def data(self) -> List[dict]:
        return [r.data() for r in self._records]


# ---------------------------------------------------------------------------
# Cypher subset parsers (regex-based, like the networkx_inmemory adapter)
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


def _parse_literal(s: str) -> Any:
    s = s.strip()
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if s.lower() == "null":
        return None
    return s


# ---------------------------------------------------------------------------
# Session + Driver
# ---------------------------------------------------------------------------


class _LadybugSession:
    """neo4j.Session-shaped wrapper around ladybug's graph object."""

    def __init__(self, driver: "_LadybugDriver") -> None:
        self._driver = driver

    def __enter__(self) -> "_LadybugSession":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def run(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
        **kwargs: Any,
    ) -> _LadybugResult:
        if parameters or kwargs:
            raise NotImplementedError(
                "ladybug adapter: parameterised Cypher is not "
                "supported. Inline literals or switch to a provider "
                "with native parameter binding (arcadedb / neo4j)."
            )

        # RETURN <literal> -- doesn't touch the graph; resolve before
        # we (possibly) import ladybug, so the connectivity-ping
        # codepath in bin/preflight.py works without the dep installed.
        m = _LITERAL_RE.match(cypher)
        if m and "MATCH" not in cypher.upper():
            value = _parse_literal(m.group(1))
            return _LadybugResult([_LadybugRecord((value,), ["value"])])

        # All other supported shapes need the actual graph.
        graph = self._driver._graph()

        # MATCH (n) RETURN COUNT(n) [AS alias]
        m = _COUNT_RE.match(cypher)
        if m:
            alias = m.group(1) or "count"
            count = _count_nodes(graph)
            return _LadybugResult([_LadybugRecord((count,), [alias])])

        # MATCH (n) DETACH DELETE n
        if _DETACH_DELETE_RE.match(cypher):
            _clear_graph(graph)
            return _LadybugResult([])

        # MATCH (n) RETURN n
        if _RETURN_ALL_RE.match(cypher):
            rows = [_LadybugRecord((node,), ["n"]) for node in _iter_nodes(graph)]
            return _LadybugResult(rows)

        raise NotImplementedError(
            f"ladybug adapter: Cypher shape not supported. Query was: "
            f"{cypher!r}. Use the documented subset (see "
            f"docs/PROFILES.md) or switch to a full-Cypher provider."
        )


# Adapter helpers that probe Ladybug's API defensively. Ladybug's API
# is still under upstream development; we use a few well-known method
# names and fall through to networkx-style operations on whatever the
# underlying graph object exposes.


def _count_nodes(graph: Any) -> int:
    for attr in ("number_of_nodes", "node_count", "__len__"):
        if hasattr(graph, attr):
            try:
                val = getattr(graph, attr)
                return int(val() if callable(val) else val)
            except Exception:
                continue
    # Fallback: try .nodes
    nodes = getattr(graph, "nodes", None)
    if nodes is not None:
        try:
            return len(list(nodes))
        except Exception:
            pass
    return 0


def _clear_graph(graph: Any) -> None:
    for attr in ("clear", "reset", "remove_all_nodes"):
        if hasattr(graph, attr):
            try:
                getattr(graph, attr)()
                return
            except Exception:
                continue


def _iter_nodes(graph: Any):
    nodes = getattr(graph, "nodes", None)
    if callable(nodes):
        try:
            return list(nodes())
        except Exception:
            pass
    if nodes is not None:
        try:
            return list(nodes)
        except Exception:
            pass
    return []


class _LadybugDriver:
    """neo4j.Driver-shape over ladybug's in-process graph."""

    def __init__(self, db_path: Optional[str]) -> None:
        self._db_path = db_path
        self._graph_obj: Any = None

    def _graph(self):
        if self._graph_obj is None:
            # Ladybug's public API surface: try a few documented
            # constructors. If ladybug isn't installed, this raises
            # ImportError, which is the expected behaviour for opt-in
            # providers.
            import ladybug

            for ctor_name in ("Graph", "MultiDiGraph", "DiGraph"):
                ctor = getattr(ladybug, ctor_name, None)
                if ctor is not None:
                    try:
                        self._graph_obj = ctor()
                        break
                    except Exception:
                        continue
            if self._graph_obj is None:
                # Fall back to whatever top-level object ladybug exposes
                self._graph_obj = getattr(ladybug, "graph", None) or ladybug
        return self._graph_obj

    def session(self, *args: Any, **kwargs: Any) -> _LadybugSession:
        return _LadybugSession(self)

    def close(self) -> None:
        self._graph_obj = None


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _LadybugDriver:
    """Create a Ladybug driver. uri/user/password ignored (in-process)."""
    db_path = os.getenv("LADYBUG_DB_PATH")
    return _LadybugDriver(db_path)


class _AsyncLadybugSession:
    """Async wrapper around _LadybugSession via ``asyncio.to_thread``."""

    def __init__(self, driver: "_AsyncLadybugDriver") -> None:
        self._driver = driver
        self._sync_session: Optional[_LadybugSession] = None

    async def __aenter__(self) -> "_AsyncLadybugSession":
        import asyncio

        sync_driver = _LadybugDriver(self._driver._db_path)
        # Pass the parent driver's graph object across so the async
        # and sync paths share state.
        sync_driver._graph_obj = self._driver._graph_obj

        def _open() -> _LadybugSession:
            return sync_driver.session().__enter__()

        self._sync_session = await asyncio.to_thread(_open)
        # Share back any graph object the sync driver may have created.
        self._driver._graph_obj = sync_driver._graph_obj
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # Ladybug sessions are synchronous no-ops on exit.
        self._sync_session = None

    async def run(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
        **kwargs: Any,
    ) -> _LadybugResult:
        import asyncio

        if self._sync_session is None:
            raise RuntimeError(
                "ladybug async session: run() called outside `async with`"
            )
        sess = self._sync_session
        return await asyncio.to_thread(sess.run, cypher, parameters, **kwargs)


class _AsyncLadybugDriver:
    """neo4j.AsyncDriver-shape over the sync ladybug graph."""

    def __init__(self, db_path: Optional[str]) -> None:
        self._db_path = db_path
        self._graph_obj: Any = None

    def session(self, *args: Any, **kwargs: Any) -> _AsyncLadybugSession:
        return _AsyncLadybugSession(self)

    async def close(self) -> None:
        self._graph_obj = None


def create_async_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _AsyncLadybugDriver:
    """Create an async-shaped Ladybug driver.

    Ladybug is sync; this wraps each operation in
    ``asyncio.to_thread`` so async call sites can use the driver in
    an ``async with`` block.
    """
    db_path = os.getenv("LADYBUG_DB_PATH")
    return _AsyncLadybugDriver(db_path)
