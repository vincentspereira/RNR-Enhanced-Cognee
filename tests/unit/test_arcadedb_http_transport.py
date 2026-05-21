"""Tests for the ArcadeDB HTTP transport.

The Bolt transport is exercised by ``tests/unit/test_db_factory.py``
under ``TestGraphFactory`` and ``TestAdapterEnvFallbacks``. This
module covers the HTTP transport that ships in PR #9 (2026-05-20)
and lets ArcadeDB run against the stock ``arcadedata/arcadedb``
Docker image (no Bolt plugin required).
"""

from __future__ import annotations

import base64
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from src.db_adapters import graph_arcadedb


# ---------------------------------------------------------------------------
# Transport selection
# ---------------------------------------------------------------------------


class TestTransportSelection:
    def test_default_transport_is_bolt(self, monkeypatch):
        monkeypatch.delenv("ARCADEDB_TRANSPORT", raising=False)
        assert graph_arcadedb._selected_transport() == "bolt"

    def test_http_transport_via_env(self, monkeypatch):
        monkeypatch.setenv("ARCADEDB_TRANSPORT", "http")
        assert graph_arcadedb._selected_transport() == "http"

    def test_transport_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("ARCADEDB_TRANSPORT", "HTTP")
        assert graph_arcadedb._selected_transport() == "http"

    def test_invalid_transport_raises(self, monkeypatch):
        monkeypatch.setenv("ARCADEDB_TRANSPORT", "smtp")
        with pytest.raises(ValueError, match="ARCADEDB_TRANSPORT"):
            graph_arcadedb.create_driver()


class TestHTTPConfigResolve:
    def test_defaults(self, monkeypatch):
        for v in (
            "ARCADEDB_HOST",
            "ARCADEDB_HTTP_PORT",
            "ARCADEDB_DATABASE",
            "ARCADEDB_USER",
            "ARCADEDB_PASSWORD",
        ):
            monkeypatch.delenv(v, raising=False)
        cfg = graph_arcadedb._resolve_http_config()
        assert cfg == {
            "host": "localhost",
            "port": 2480,
            "database": "cognee_graph",
            "user": "root",
            "password": "cognee_password",
        }

    def test_env_overrides(self, monkeypatch):
        monkeypatch.setenv("ARCADEDB_HOST", "arcadedb.internal")
        monkeypatch.setenv("ARCADEDB_HTTP_PORT", "9999")
        monkeypatch.setenv("ARCADEDB_DATABASE", "graph_v2")
        monkeypatch.setenv("ARCADEDB_USER", "admin")
        monkeypatch.setenv("ARCADEDB_PASSWORD", "s3cret")
        cfg = graph_arcadedb._resolve_http_config()
        assert cfg["host"] == "arcadedb.internal"
        assert cfg["port"] == 9999
        assert cfg["database"] == "graph_v2"
        assert cfg["user"] == "admin"
        assert cfg["password"] == "s3cret"

    def test_env_overrides_explicit_args(self, monkeypatch):
        """ARCADEDB_* env vars take precedence over caller kwargs.

        Rationale: callers like ``EnhancedCogneeMCPServer._init_neo4j`` pass
        legacy ``neo4j_user`` kwargs for backwards-compat even when the
        active provider is arcadedb. Letting the env var win means the
        operator can override credentials via ARCADEDB_* without editing
        the caller, which is the documented production deploy path.
        """
        monkeypatch.setenv("ARCADEDB_USER", "env_user")
        cfg = graph_arcadedb._resolve_http_config(user="explicit_user")
        assert cfg["user"] == "env_user"

    def test_kwarg_used_when_env_unset(self, monkeypatch):
        """When the ARCADEDB_* env var is NOT set, the kwarg is used."""
        monkeypatch.delenv("ARCADEDB_USER", raising=False)
        cfg = graph_arcadedb._resolve_http_config(user="kwarg_user")
        assert cfg["user"] == "kwarg_user"

    def test_hardcoded_default_when_no_env_or_kwarg(self, monkeypatch):
        """Falls back to the documented hardcoded default."""
        for k in (
            "ARCADEDB_HOST",
            "ARCADEDB_HTTP_PORT",
            "ARCADEDB_DATABASE",
            "ARCADEDB_USER",
            "ARCADEDB_PASSWORD",
        ):
            monkeypatch.delenv(k, raising=False)
        cfg = graph_arcadedb._resolve_http_config()
        assert cfg["user"] == "root"
        assert cfg["password"] == "cognee_password"
        assert cfg["database"] == "cognee_graph"
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 2480


# ---------------------------------------------------------------------------
# Result + Record shape
# ---------------------------------------------------------------------------


class TestHTTPRecord:
    def test_int_index_access(self):
        r = graph_arcadedb._HTTPRecord({"a": 1, "b": 2})
        assert r[0] == 1
        assert r[1] == 2

    def test_key_index_access(self):
        r = graph_arcadedb._HTTPRecord({"a": 1, "b": 2})
        assert r["a"] == 1
        assert r["b"] == 2

    def test_keys_values_data(self):
        r = graph_arcadedb._HTTPRecord({"a": 1, "b": 2})
        assert r.keys() == ["a", "b"]
        assert r.values() == (1, 2)
        assert r.data() == {"a": 1, "b": 2}

    def test_iter_and_len(self):
        r = graph_arcadedb._HTTPRecord({"a": 1, "b": 2})
        assert list(r) == [1, 2]
        assert len(r) == 2


class TestHTTPResult:
    def test_single_empty(self):
        assert graph_arcadedb._HTTPResult([]).single() is None

    def test_single_first(self):
        res = graph_arcadedb._HTTPResult([{"a": 1}, {"a": 2}])
        assert res.single()["a"] == 1

    def test_iter(self):
        res = graph_arcadedb._HTTPResult([{"a": 1}, {"a": 2}])
        assert [r["a"] for r in res] == [1, 2]

    def test_data(self):
        res = graph_arcadedb._HTTPResult([{"a": 1}, {"a": 2}])
        assert res.data() == [{"a": 1}, {"a": 2}]


class TestNormaliseHTTPResult:
    def test_dict_rows_pass_through(self):
        payload = {"result": [{"id": 1}, {"id": 2}]}
        rows = graph_arcadedb._normalise_http_result(payload)
        assert rows == [{"id": 1}, {"id": 2}]

    def test_primitive_rows_wrapped_in_value(self):
        # `RETURN 1` round-trips as a primitive 1
        payload = {"result": [1, 2, 3]}
        rows = graph_arcadedb._normalise_http_result(payload)
        assert rows == [{"value": 1}, {"value": 2}, {"value": 3}]

    def test_empty_result_returns_empty_list(self):
        assert graph_arcadedb._normalise_http_result({"result": []}) == []

    def test_missing_result_key_returns_empty_list(self):
        assert graph_arcadedb._normalise_http_result({}) == []
        assert graph_arcadedb._normalise_http_result(None) == []


# ---------------------------------------------------------------------------
# Driver session round-trip (HTTP transport)
# ---------------------------------------------------------------------------


class _FakeHTTPResponse:
    """Stand-in for the urlopen() context manager."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self) -> bytes:
        return self._body


class TestHTTPDriverRoundTrip:
    def test_session_run_posts_to_command_endpoint(self):
        driver = graph_arcadedb._HTTPDriver(
            host="localhost",
            port=2480,
            database="cognee_graph",
            user="root",
            password="pw",
        )

        captured: dict = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = req.data
            captured["headers"] = dict(req.headers)
            captured["method"] = req.get_method()
            return _FakeHTTPResponse(
                json.dumps({"result": [{"x": 42}]}).encode("utf-8")
            )

        with patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            with driver.session() as sess:
                result = sess.run("RETURN 42 AS x")
                row = result.single()

        assert row["x"] == 42
        assert captured["url"] == "http://localhost:2480/api/v1/command/cognee_graph"
        assert captured["method"] == "POST"
        body = json.loads(captured["body"].decode("utf-8"))
        assert body["language"] == "cypher"
        assert body["command"] == "RETURN 42 AS x"
        # Basic auth header present
        expected_token = base64.b64encode(b"root:pw").decode("ascii")
        # Case-insensitive header lookup
        auth = next(
            (v for k, v in captured["headers"].items() if k.lower() == "authorization"),
            None,
        )
        assert auth == f"Basic {expected_token}"

    def test_session_run_with_parameters(self):
        driver = graph_arcadedb._HTTPDriver(
            host="localhost",
            port=2480,
            database="cognee_graph",
            user="root",
            password="pw",
        )

        captured: dict = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeHTTPResponse(b'{"result": []}')

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with driver.session() as sess:
                sess.run(
                    "MATCH (n:Person {name: $name}) RETURN n",
                    parameters={"name": "Alice"},
                )

        assert captured["body"]["params"] == {"name": "Alice"}

    def test_session_run_with_kwargs(self):
        driver = graph_arcadedb._HTTPDriver(
            host="localhost",
            port=2480,
            database="cognee_graph",
            user="root",
            password="pw",
        )

        captured: dict = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeHTTPResponse(b'{"result": []}')

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with driver.session() as sess:
                sess.run("MATCH (n) RETURN n", name="Bob")

        assert captured["body"]["params"] == {"name": "Bob"}

    def test_http_error_surfaces_arcadedb_error_body(self):
        driver = graph_arcadedb._HTTPDriver(
            host="localhost",
            port=2480,
            database="cognee_graph",
            user="root",
            password="pw",
        )

        from urllib.error import HTTPError

        # Construct an HTTPError with a JSON error body
        err_body = b'{"error": "Cypher parse error"}'
        err = HTTPError(
            url="http://localhost:2480/api/v1/command/cognee_graph",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=BytesIO(err_body),
        )

        with patch("urllib.request.urlopen", side_effect=err):
            with driver.session() as sess:
                with pytest.raises(RuntimeError, match="Cypher parse error"):
                    sess.run("INVALID CYPHER")

    def test_url_error_surfaces_connect_failure(self):
        driver = graph_arcadedb._HTTPDriver(
            host="localhost",
            port=2480,
            database="cognee_graph",
            user="root",
            password="pw",
        )

        from urllib.error import URLError

        with patch(
            "urllib.request.urlopen",
            side_effect=URLError("Connection refused"),
        ):
            with driver.session() as sess:
                with pytest.raises(RuntimeError, match="connect error"):
                    sess.run("RETURN 1")


# ---------------------------------------------------------------------------
# Public factory entry points
# ---------------------------------------------------------------------------


class TestCreateDriverHTTPDispatch:
    def test_create_driver_http_returns_http_driver(self, monkeypatch):
        monkeypatch.setenv("ARCADEDB_TRANSPORT", "http")
        drv = graph_arcadedb.create_driver()
        assert isinstance(drv, graph_arcadedb._HTTPDriver)
        assert drv._host == "localhost"
        assert drv._port == 2480

    def test_create_async_driver_http_returns_async_http_driver(self, monkeypatch):
        monkeypatch.setenv("ARCADEDB_TRANSPORT", "http")
        drv = graph_arcadedb.create_async_driver()
        assert isinstance(drv, graph_arcadedb._AsyncHTTPDriver)


class TestAsyncHTTPDriverShape:
    @pytest.mark.asyncio
    async def test_async_session_run_round_trip(self):
        drv = graph_arcadedb._AsyncHTTPDriver(
            host="localhost",
            port=2480,
            database="cognee_graph",
            user="root",
            password="pw",
        )

        def fake_urlopen(req, timeout=None):
            return _FakeHTTPResponse(
                json.dumps({"result": [{"x": 1}]}).encode("utf-8")
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            async with drv.session() as sess:
                result = await sess.run("RETURN 1 AS x")
                row = await result.single()
                assert row["x"] == 1

    @pytest.mark.asyncio
    async def test_async_result_iteration(self):
        drv = graph_arcadedb._AsyncHTTPDriver(
            host="localhost",
            port=2480,
            database="cognee_graph",
            user="root",
            password="pw",
        )

        def fake_urlopen(req, timeout=None):
            return _FakeHTTPResponse(
                json.dumps({"result": [{"x": 1}, {"x": 2}, {"x": 3}]}).encode("utf-8")
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            async with drv.session() as sess:
                result = await sess.run("UNWIND [1, 2, 3] AS x RETURN x")
                xs = []
                async for record in result:
                    xs.append(record["x"])
                assert xs == [1, 2, 3]
