"""NetworkX in-memory graph adapter (Phase 5 pluggable; **testing only**).

NetworkX (https://networkx.org/) is a BSD-licensed pure-Python graph
library. It has no native Cypher support; this adapter exists for
two narrow use cases per HANDOVER section 4 Phase 4 and STRATEGY.md
section 4.2:

  1. Tests that need a graph driver but cannot afford a Docker container.
  2. The ``lean`` deployment profile for laptops / offline use where
     graph workload is small (< 100k nodes) and pure-Python is enough.

**Supported Cypher (deliberately narrow):**

- ``RETURN <literal>`` -- e.g. ``RETURN 1``, ``RETURN 'ok'``.
  Used by the connectivity ping in ``bin/preflight.py`` and
  ``recovery_manager._validate_neo4j``.
- ``MATCH (n) RETURN COUNT(n) [AS <alias>]`` -- node-count scalar.
- ``MATCH (n) DETACH DELETE n`` -- wipes the graph.

**Everything else raises ``NotImplementedError``** with a pointer to
``docs/PROFILES.md``. Production workloads that need real Cypher
should pick ``arcadedb`` (default), ``neo4j``, ``memgraph``, ``kuzu``,
or ``apache_age`` instead. This adapter is **not** a Cypher engine.

Storage is in-process: the graph lives in a single ``networkx.MultiDiGraph``
instance held by the driver. State is lost on process restart unless
the caller dumps / loads via ``networkx.readwrite``.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence


_LITERAL_RE = re.compile(r"""^\s*RETURN\s+(.+?)\s*$""", re.IGNORECASE)
_COUNT_RE = re.compile(
    r"""^\s*MATCH\s*\(\s*\w+\s*\)\s*RETURN\s+COUNT\(\s*\w+\s*\)(?:\s+AS\s+(\w+))?\s*$""",
    re.IGNORECASE,
)
_DETACH_DELETE_RE = re.compile(
    r"""^\s*MATCH\s*\(\s*\w+\s*\)\s*DETACH\s+DELETE\s+\w+\s*$""", re.IGNORECASE
)


def _parse_literal(s: str) -> Any:
    """Parse the right-hand side of `RETURN <literal>`."""
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
    return s  # fall back to raw string


class _NXRecord:
    """``neo4j.Record``-shape minimal wrapper."""

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


class _NXResult:
    def __init__(self, records: List[_NXRecord]) -> None:
        self._records = records

    def single(self) -> Optional[_NXRecord]:
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)

    def data(self) -> List[dict]:
        return [r.data() for r in self._records]


class _NXSession:
    def __init__(self, driver: "_NXDriver") -> None:
        self._driver = driver

    def __enter__(self) -> "_NXSession":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def run(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
        **kwargs: Any,
    ) -> _NXResult:
        if parameters or kwargs:
            raise NotImplementedError(
                "ENHANCED_GRAPH_PROVIDER=networkx_inmemory does not support "
                "parameterised Cypher. See docs/PROFILES.md."
            )

        # RETURN <literal>
        m = _LITERAL_RE.match(cypher)
        if m and "MATCH" not in cypher.upper():
            value = _parse_literal(m.group(1))
            return _NXResult([_NXRecord((value,), ["value"])])

        # MATCH (n) RETURN COUNT(n) [AS alias]
        m = _COUNT_RE.match(cypher)
        if m:
            alias = m.group(1) or "count"
            count = self._driver._graph.number_of_nodes()
            return _NXResult([_NXRecord((count,), [alias])])

        # MATCH (n) DETACH DELETE n
        if _DETACH_DELETE_RE.match(cypher):
            self._driver._graph.clear()
            return _NXResult([])

        raise NotImplementedError(
            f"ENHANCED_GRAPH_PROVIDER=networkx_inmemory has no Cypher "
            f"engine -- only RETURN <literal>, MATCH (n) RETURN COUNT(n), "
            f"and MATCH (n) DETACH DELETE n are recognised. Query was: "
            f"{cypher!r}. Use neo4j / arcadedb / memgraph / kuzu / "
            f"apache_age for full Cypher. See docs/PROFILES.md."
        )


class _NXDriver:
    def __init__(self) -> None:
        import networkx as nx

        self._graph = nx.MultiDiGraph()

    def session(self, *args: Any, **kwargs: Any) -> _NXSession:
        return _NXSession(self)

    def close(self) -> None:
        self._graph.clear()


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _NXDriver:
    """Create an in-memory NetworkX driver.

    All connection-shaped kwargs are accepted for API compatibility
    but ignored -- there is no network or filesystem layer.
    """
    return _NXDriver()


def create_async_driver(*args: Any, **kwargs: Any):
    """No async path -- everything runs in-process synchronously."""
    raise NotImplementedError(
        "ENHANCED_GRAPH_PROVIDER=networkx_inmemory has no async API "
        "(it's pure-Python in-process). Use get_graph_driver(), or "
        "switch to neo4j / arcadedb. See docs/PROFILES.md."
    )
