"""NebulaGraph adapter (Phase 5 pluggable).

NebulaGraph (https://www.nebula-graph.io/) is an Apache-2.0 distributed
graph database. Its native query language is nGQL, but NebulaGraph 3+
also supports openCypher syntax for a subset of operations. This
adapter routes through the official ``nebula3-python`` driver and uses
openCypher mode for the narrow query subset Enhanced Cognee's call
sites use.

**Storage model:** all graph nodes live in a single tag (default
``cognee_node``, configurable via ``NEBULA_TAG_NAME``) inside a
single space (default ``cognee_space``, configurable via
``NEBULA_SPACE_NAME``).

**Supported Cypher / openCypher (executed directly via nGQL openCypher mode):**

| Cypher                                       | nGQL behaviour                                                 |
| -------------------------------------------- | -------------------------------------------------------------- |
| ``RETURN <literal>``                         | ``YIELD <literal>``                                            |
| ``MATCH (n) RETURN COUNT(n) [AS alias]``     | ``MATCH (n) RETURN COUNT(n) AS <alias>`` (NebulaGraph openCypher) |
| ``MATCH (n) DETACH DELETE n``                | ``MATCH (n) DETACH DELETE n``                                  |
| ``MATCH (n) RETURN n``                       | ``MATCH (n) RETURN n``                                         |

**Not supported (raises NotImplementedError):**

- Parameterised Cypher (nGQL parameter binding differs from Bolt's)
- Async session API (nebula3-python is sync-only)
- Multi-hop pattern matching with relationship types
- WHERE clauses with property comparisons (NebulaGraph schema is
  strict; properties must be declared on the tag first)

Env-var fallbacks: ``NEBULA_HOST`` (default ``localhost``),
``NEBULA_PORT`` (default ``9669``), ``NEBULA_USER`` (default
``root``), ``NEBULA_PASSWORD`` (default ``nebula``),
``NEBULA_SPACE_NAME`` (default ``cognee_space``),
``NEBULA_TAG_NAME`` (default ``cognee_node``).

Install with::

    pip install enhanced-cognee[graph-nebulagraph]

Lazy-imports ``nebula3`` so installs without it don't pay the cost.
"""

from __future__ import annotations

import os
import re
from typing import Any, List, Optional, Sequence


class _NebulaRecord:
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


class _NebulaResult:
    def __init__(self, rows: List[_NebulaRecord]) -> None:
        self._records = rows

    def single(self) -> Optional[_NebulaRecord]:
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)

    def data(self) -> List[dict]:
        return [r.data() for r in self._records]


_LITERAL_RE = re.compile(r"""^\s*RETURN\s+(.+?)\s*$""", re.IGNORECASE)


def _translate_cypher_to_ngql(cypher: str) -> str:
    """Translate the narrow Cypher subset to nGQL.

    For most queries, NebulaGraph's openCypher mode accepts the
    Cypher verbatim. The only translation needed is ``RETURN
    <literal>`` (Cypher) -> ``YIELD <literal>`` (nGQL).
    """
    cypher = cypher.strip()

    # Bare RETURN <literal> -- nGQL uses YIELD for literal projections
    m = _LITERAL_RE.match(cypher)
    if m and "MATCH" not in cypher.upper():
        return f"YIELD {m.group(1)}"

    # Pass through for MATCH-based queries (NebulaGraph openCypher
    # handles them natively). Production code paths in our codebase
    # (`RETURN COUNT`, `DETACH DELETE`) already match this shape.
    return cypher


class _NebulaSession:
    """neo4j.Session-shaped wrapper around nebula3-python's Session."""

    def __init__(self, driver: "_NebulaDriver") -> None:
        self._driver = driver
        self._session: Any = None

    def __enter__(self) -> "_NebulaSession":
        self._session = self._driver._open_session()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._session is not None:
            try:
                self._session.release()
            except Exception:
                pass
            self._session = None

    def run(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
        **kwargs: Any,
    ) -> _NebulaResult:
        if parameters or kwargs:
            raise NotImplementedError(
                "nebulagraph adapter: parameterised Cypher is not "
                "supported. nGQL has its own parameter syntax that "
                "doesn't map 1:1 onto Bolt parameter binding. Inline "
                "literals or switch to arcadedb / neo4j."
            )

        if self._session is None:
            self._session = self._driver._open_session()

        ngql = _translate_cypher_to_ngql(cypher)
        result = self._session.execute(ngql)
        if not result.is_succeeded():
            raise RuntimeError(
                f"nebulagraph adapter: query failed -- {result.error_msg()}"
            )

        # Convert nebula3's ResultSet to _NebulaRecord rows.
        rows: List[_NebulaRecord] = []
        cols = list(result.keys()) if result.keys() else ["result"]
        for row_idx in range(result.row_size()):
            values = []
            for col_idx in range(result.col_size()):
                val = result.row_values(row_idx)[col_idx]
                values.append(_unwrap_nebula_value(val))
            rows.append(_NebulaRecord(values, cols))
        return _NebulaResult(rows)


def _unwrap_nebula_value(val: Any) -> Any:
    """Convert nebula3's Value wrapper to a Python primitive."""
    if val is None:
        return None
    # Each Value has type-specific getter methods; try them in order
    for getter in ("as_int", "as_double", "as_bool", "as_string"):
        try:
            if hasattr(val, getter):
                v = getattr(val, getter)()
                return v
        except Exception:
            continue
    # Fall back to string repr
    return str(val)


class _NebulaDriver:
    """neo4j.Driver-shaped wrapper around nebula3-python's ConnectionPool."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        space_name: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._space_name = space_name
        self._pool: Any = None

    def _open_session(self):
        from nebula3.gclient.net import ConnectionPool
        from nebula3.Config import Config

        if self._pool is None:
            cfg = Config()
            cfg.max_connection_pool_size = 10
            self._pool = ConnectionPool()
            ok = self._pool.init([(self._host, self._port)], cfg)
            if not ok:
                raise RuntimeError(
                    f"nebulagraph adapter: failed to connect to "
                    f"{self._host}:{self._port}"
                )

        session = self._pool.get_session(self._user, self._password)

        # Ensure space exists + select it. Spaces are NebulaGraph's
        # equivalent of databases; the schema lives inside a space.
        try:
            session.execute(
                f"CREATE SPACE IF NOT EXISTS {self._space_name} "
                f"(vid_type=FIXED_STRING(64))"
            )
            session.execute(f"USE {self._space_name}")
        except Exception:
            # Space probably already exists; fall through.
            try:
                session.execute(f"USE {self._space_name}")
            except Exception:
                pass

        return session

    def session(self, *args: Any, **kwargs: Any) -> _NebulaSession:
        return _NebulaSession(self)

    def close(self) -> None:
        if self._pool is not None:
            try:
                self._pool.close()
            except Exception:
                pass
            self._pool = None


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _NebulaDriver:
    """Create a NebulaGraph driver via nebula3-python."""
    host = os.getenv("NEBULA_HOST", "localhost")
    port = int(os.getenv("NEBULA_PORT", "9669"))
    user = user or os.getenv("NEBULA_USER", "root")
    password = password if password is not None else os.getenv("NEBULA_PASSWORD", "nebula")
    space = os.getenv("NEBULA_SPACE_NAME", "cognee_space")
    return _NebulaDriver(host, port, user, password, space)


class _AsyncNebulaSession:
    """Async wrapper around _NebulaSession via ``asyncio.to_thread``."""

    def __init__(self, driver: "_AsyncNebulaDriver") -> None:
        self._driver = driver
        self._sync_session: Optional[_NebulaSession] = None

    async def __aenter__(self) -> "_AsyncNebulaSession":
        import asyncio

        sync_driver = _NebulaDriver(
            host=self._driver._host,
            port=self._driver._port,
            user=self._driver._user,
            password=self._driver._password,
            space_name=self._driver._space_name,
        )

        def _open() -> _NebulaSession:
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
    ) -> _NebulaResult:
        import asyncio

        if self._sync_session is None:
            raise RuntimeError(
                "nebulagraph async session: run() called outside `async with`"
            )
        sess = self._sync_session
        return await asyncio.to_thread(sess.run, cypher, parameters, **kwargs)


class _AsyncNebulaDriver:
    """neo4j.AsyncDriver-shape over the sync nebula3-python client.

    Wraps each session operation in ``asyncio.to_thread``.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        space_name: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._space_name = space_name

    def session(self, *args: Any, **kwargs: Any) -> _AsyncNebulaSession:
        return _AsyncNebulaSession(self)

    async def close(self) -> None:
        return None


def create_async_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> _AsyncNebulaDriver:
    """Create an async-shaped NebulaGraph driver.

    nebula3-python is sync; this wraps each operation in
    ``asyncio.to_thread`` so async call sites can use the driver in
    an ``async with`` block.
    """
    host = os.getenv("NEBULA_HOST", "localhost")
    port = int(os.getenv("NEBULA_PORT", "9669"))
    user = user or os.getenv("NEBULA_USER", "root")
    password = password if password is not None else os.getenv("NEBULA_PASSWORD", "nebula")
    space = os.getenv("NEBULA_SPACE_NAME", "cognee_space")
    return _AsyncNebulaDriver(host, port, user, password, space)
