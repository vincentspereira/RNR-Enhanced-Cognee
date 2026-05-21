"""ArcadeDB graph adapter (Phase 2 default).

ArcadeDB (https://arcadedb.com) is a multi-model database with an
openCypher implementation. The adapter speaks two transports
selectable via ``ARCADEDB_TRANSPORT``:

  ``bolt``  (default since Phase 2): uses the ``neo4j`` Python driver
     against ArcadeDB's optional Bolt plugin. Drop-in for existing
     NEO4J_URI=bolt://localhost:27687 setups. Requires the Bolt
     plugin to be enabled in the ArcadeDB server JVM options (see
     ``docs/ARCADEDB_MIGRATION.md`` for the docker-compose snippet).

  ``http``: uses ArcadeDB's built-in HTTP/JSON command API
     (``POST /api/v1/command/{db}``) with no extra plugins -- works
     against the stock ``arcadedata/arcadedb`` Docker image. Slightly
     higher per-request latency than Bolt due to HTTP framing, but
     the only viable option when the Bolt plugin isn't available
     (community images, sandboxed CI runners). The HTTP wrapper
     exposes the same ``neo4j.Driver``-shaped surface so call sites
     don't care which transport is in use.

Env-var fallbacks (in order):
    ARCADEDB_TRANSPORT  (default ``bolt``; values: ``bolt`` / ``http``)
    ARCADEDB_URI        (transport-dependent default; see below)
    ARCADEDB_HOST       (default ``localhost``)        # http transport
    ARCADEDB_HTTP_PORT  (default ``2480``)             # http transport
    ARCADEDB_DATABASE   (default ``cognee_graph``)     # http transport
    ARCADEDB_USER       (default ``root``)
    ARCADEDB_PASSWORD   (default ``cognee_password``)

The Bolt-default URI is ``bolt://localhost:27687``; the HTTP-default
endpoint is ``http://localhost:2480/api/v1/command/cognee_graph``.

For backwards compat, callers that still pass ``NEO4J_*`` env vars are
respected via explicit kwargs from the call site -- the adapter only
reads its own ARCADEDB_* env vars when the caller does not override.

Lazy-imports ``neo4j`` (for the Bolt path) and ``urllib`` /
``http.client`` (for the HTTP path) so each transport's deps remain
optional. Tests patching ``sys.modules['neo4j']`` keep working for
the Bolt path; the HTTP path uses ``urllib.request.urlopen`` which
tests can monkeypatch directly.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Transport selection
# ---------------------------------------------------------------------------


def _selected_transport() -> str:
    return os.getenv("ARCADEDB_TRANSPORT", "bolt").lower()


def _resolve_auth(
    uri: Optional[str],
    user: Optional[str],
    password: Optional[str],
) -> Tuple[str, Tuple[str, str]]:
    """Resolve Bolt-flavoured (uri, (user, password)) tuple."""
    uri = uri or os.getenv("ARCADEDB_URI", "bolt://localhost:27687")
    user = user or os.getenv("ARCADEDB_USER", "root")
    password = password or os.getenv("ARCADEDB_PASSWORD", "cognee_password")
    return uri, (user, password)


def _resolve_http_config(
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict[str, Any]:
    """Resolve HTTP-transport config -- host / port / database / auth."""
    return {
        "host": host or os.getenv("ARCADEDB_HOST", "localhost"),
        "port": int(port or os.getenv("ARCADEDB_HTTP_PORT", "2480")),
        "database": database or os.getenv("ARCADEDB_DATABASE", "cognee_graph"),
        "user": user or os.getenv("ARCADEDB_USER", "root"),
        "password": password or os.getenv("ARCADEDB_PASSWORD", "cognee_password"),
    }


# ---------------------------------------------------------------------------
# Bolt transport (existing behaviour)
# ---------------------------------------------------------------------------


def _create_bolt_driver(
    uri: Optional[str],
    user: Optional[str],
    password: Optional[str],
    **kwargs: Any,
):
    from neo4j import GraphDatabase

    resolved_uri, auth = _resolve_auth(uri, user, password)
    return GraphDatabase.driver(resolved_uri, auth=auth, **kwargs)


def _create_async_bolt_driver(
    uri: Optional[str],
    user: Optional[str],
    password: Optional[str],
    **kwargs: Any,
):
    from neo4j import AsyncGraphDatabase

    resolved_uri, auth = _resolve_auth(uri, user, password)
    return AsyncGraphDatabase.driver(resolved_uri, auth=auth, **kwargs)


# ---------------------------------------------------------------------------
# HTTP transport (new in 2026-05-20)
# ---------------------------------------------------------------------------


class _HTTPRecord:
    """``neo4j.Record``-shaped wrapper around a single JSON row."""

    __slots__ = ("_row", "_columns")

    def __init__(self, row: Dict[str, Any]) -> None:
        # ArcadeDB returns each row as {col_name: value, ...}. We
        # preserve insertion order so positional [0] access works.
        self._row = dict(row)
        self._columns = list(row.keys())

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._row[self._columns[key]]
        return self._row[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._row.values())

    def __len__(self) -> int:
        return len(self._row)

    def keys(self) -> List[str]:
        return list(self._columns)

    def values(self) -> tuple:
        return tuple(self._row.values())

    def data(self) -> Dict[str, Any]:
        return dict(self._row)


class _HTTPResult:
    """``neo4j.Result``-shaped wrapper around a list of JSON rows."""

    def __init__(self, rows: Sequence[Dict[str, Any]]) -> None:
        self._records: List[_HTTPRecord] = [_HTTPRecord(r) for r in rows]

    def single(self) -> Optional[_HTTPRecord]:
        return self._records[0] if self._records else None

    def __iter__(self) -> Iterator[_HTTPRecord]:
        return iter(self._records)

    def data(self) -> List[Dict[str, Any]]:
        return [r.data() for r in self._records]


class _HTTPSession:
    """``neo4j.Session``-shaped wrapper executing Cypher via HTTP."""

    def __init__(self, driver: "_HTTPDriver") -> None:
        self._driver = driver

    def __enter__(self) -> "_HTTPSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def run(self, cypher: str, parameters: Optional[Dict[str, Any]] = None, **kwargs: Any) -> _HTTPResult:
        merged = dict(parameters or {})
        merged.update(kwargs)
        rows = self._driver._execute_cypher(cypher, merged)
        return _HTTPResult(rows)


class _HTTPDriver:
    """``neo4j.Driver``-shaped wrapper over ArcadeDB's /api/v1/command HTTP API.

    Each ``session()`` call returns a context-manager that wraps a
    short-lived HTTP request stream (the ArcadeDB API is stateless).
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password

    def session(self, *args: Any, **kwargs: Any) -> _HTTPSession:
        return _HTTPSession(self)

    def close(self) -> None:
        return None

    def _execute_cypher(
        self, cypher: str, parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """POST /api/v1/command/{db} and parse the JSON response."""
        import base64
        from urllib.error import HTTPError, URLError
        from urllib.request import Request, urlopen

        endpoint = f"http://{self._host}:{self._port}/api/v1/command/{self._database}"
        body = {
            "language": "cypher",
            "command": cypher,
        }
        if parameters:
            body["params"] = parameters

        token = base64.b64encode(
            f"{self._user}:{self._password}".encode("utf-8")
        ).decode("ascii")
        req = Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            # ArcadeDB returns a 4xx with a JSON error body on Cypher
            # syntax errors -- surface the body so callers can debug.
            try:
                detail = json.loads(e.read().decode("utf-8")).get("error", str(e))
            except Exception:
                detail = str(e)
            raise RuntimeError(f"ArcadeDB HTTP {e.code}: {detail}") from None
        except URLError as e:
            raise RuntimeError(f"ArcadeDB connect error: {e.reason}") from None

        return _normalise_http_result(payload)


def _normalise_http_result(payload: Any) -> List[Dict[str, Any]]:
    """ArcadeDB's HTTP response shape: ``{"result": [<row>, ...]}``.

    Each row may be a dict, a primitive, or a vertex/edge document.
    We coerce primitives into ``{"value": <prim>}`` so the
    Record-shaped wrapper always gets a dict.
    """
    rows = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, dict):
            out.append(r)
        else:
            out.append({"value": r})
    return out


class _AsyncHTTPSession:
    """Async wrapper -- runs the sync HTTP path in a worker thread."""

    def __init__(self, driver: "_AsyncHTTPDriver") -> None:
        self._driver = driver
        self._sync_driver: Optional[_HTTPDriver] = None

    async def __aenter__(self) -> "_AsyncHTTPSession":
        self._sync_driver = _HTTPDriver(
            self._driver._host,
            self._driver._port,
            self._driver._database,
            self._driver._user,
            self._driver._password,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._sync_driver = None

    async def run(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "_AsyncHTTPResult":
        import asyncio

        merged = dict(parameters or {})
        merged.update(kwargs)
        assert self._sync_driver is not None
        rows = await asyncio.to_thread(
            self._sync_driver._execute_cypher, cypher, merged
        )
        return _AsyncHTTPResult(rows)


class _AsyncHTTPResult:
    def __init__(self, rows: Sequence[Dict[str, Any]]) -> None:
        self._records: List[_HTTPRecord] = [_HTTPRecord(r) for r in rows]

    async def single(self) -> Optional[_HTTPRecord]:
        return self._records[0] if self._records else None

    def __aiter__(self) -> "_AsyncHTTPResult":
        self._iter_idx = 0
        return self

    async def __anext__(self) -> _HTTPRecord:
        if self._iter_idx >= len(self._records):
            raise StopAsyncIteration
        rec = self._records[self._iter_idx]
        self._iter_idx += 1
        return rec

    def data(self) -> List[Dict[str, Any]]:
        return [r.data() for r in self._records]


class _AsyncHTTPDriver:
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password

    def session(self, *args: Any, **kwargs: Any) -> _AsyncHTTPSession:
        return _AsyncHTTPSession(self)

    async def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Public factory entry points
# ---------------------------------------------------------------------------


def create_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
):
    """Create a sync driver pointing at ArcadeDB.

    Transport selected by ``ARCADEDB_TRANSPORT`` env var:
      - ``bolt`` (default): returns a ``neo4j.Driver`` instance
      - ``http``: returns a ``_HTTPDriver`` instance that exposes the
        same ``.session()`` / ``.run()`` / ``.close()`` surface

    The HTTP path uses ARCADEDB_HOST + ARCADEDB_HTTP_PORT +
    ARCADEDB_DATABASE env vars; the Bolt path uses ARCADEDB_URI. Both
    paths share user/password.
    """
    transport = _selected_transport()
    if transport == "http":
        cfg = _resolve_http_config(user=user, password=password)
        return _HTTPDriver(**cfg)
    if transport == "bolt":
        return _create_bolt_driver(uri, user, password, **kwargs)
    raise ValueError(
        f"Unknown ARCADEDB_TRANSPORT={transport!r}. Supported: 'bolt', 'http'."
    )


def create_async_driver(
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any,
):
    """Async counterpart of ``create_driver()``.

    Returns a ``neo4j.AsyncDriver`` for the Bolt transport, or an
    ``_AsyncHTTPDriver`` for the HTTP transport.
    """
    transport = _selected_transport()
    if transport == "http":
        cfg = _resolve_http_config(user=user, password=password)
        return _AsyncHTTPDriver(**cfg)
    if transport == "bolt":
        return _create_async_bolt_driver(uri, user, password, **kwargs)
    raise ValueError(
        f"Unknown ARCADEDB_TRANSPORT={transport!r}. Supported: 'bolt', 'http'."
    )
