"""Phase 3 adapter tests: Apache AGE graph + in-memory cache.

Covers the bits that don't fit neatly into ``test_db_factory.py``:
- AGE driver shape (.session() / .run() / .single() / iteration)
- AGE Cypher wrapping (SELECT * FROM cypher('graph', $$ ... $$))
- AGE record agtype unwrapping (JSON parse + ::vertex/::edge stripping)
- AGE NotImplementedError surfaces for parameterised queries and async
- in_memory cache full API surface (ping/get/set/delete/exists/expire/keys/flushdb/close)
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.db_adapters import cache_in_memory, graph_apache_age


# ===========================================================================
# Apache AGE adapter
# ===========================================================================


class _FakePsycopgCursor:
    """Minimal psycopg2.cursor stand-in for AGE adapter tests."""

    def __init__(self):
        self._rows = None
        self.description = None
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        # Default to no rows; tests can override via _set_rows()
        if sql.strip().upper().startswith("SELECT"):
            self.description = [("result",)]
            if self._rows is None:
                self._rows = []
        else:
            self.description = None

    def fetchall(self):
        return self._rows or []

    def _set_rows(self, rows):
        self._rows = rows


class _FakePsycopgConn:
    def __init__(self, cursor=None):
        self._cursor = cursor or _FakePsycopgCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class TestAGEDriverShape:
    """Confirm the AGE driver/session/result objects behave like neo4j."""

    def test_driver_session_returns_context_manager(self, monkeypatch):
        fake_conn = _FakePsycopgConn()
        with patch("psycopg2.connect", return_value=fake_conn):
            drv = graph_apache_age.create_driver()
            with drv.session() as session:
                assert session is not None
            # On clean exit the session commits and closes
            assert fake_conn.committed is True
            assert fake_conn.closed is True

    def test_session_rollback_on_exception(self, monkeypatch):
        fake_conn = _FakePsycopgConn()
        with patch("psycopg2.connect", return_value=fake_conn):
            drv = graph_apache_age.create_driver()
            with pytest.raises(RuntimeError):
                with drv.session():
                    raise RuntimeError("boom")
            assert fake_conn.rolled_back is True
            assert fake_conn.committed is False
            assert fake_conn.closed is True

    def test_session_run_wraps_in_cypher(self, monkeypatch):
        cur = _FakePsycopgCursor()
        cur._set_rows([("1",)])
        fake_conn = _FakePsycopgConn(cursor=cur)
        with patch("psycopg2.connect", return_value=fake_conn):
            drv = graph_apache_age.create_driver()
            with drv.session() as session:
                result = session.run("RETURN 1")
            assert result.single()[0] == 1
        # Confirm the SQL wrapped the cypher in cypher(...) AS (result agtype)
        cypher_call = next(
            (sql for sql, _ in cur.executed if "cypher(" in sql), None
        )
        assert cypher_call is not None
        assert "RETURN 1" in cypher_call
        assert "AS (result agtype)" in cypher_call

    def test_session_run_with_parameters(self, monkeypatch):
        """Phase 5 update: parameters now route through AGE's 3-arg cypher()."""
        cur = _FakePsycopgCursor()
        cur._set_rows([])
        fake_conn = _FakePsycopgConn(cursor=cur)
        with patch("psycopg2.connect", return_value=fake_conn):
            drv = graph_apache_age.create_driver()
            with drv.session() as session:
                session.run("MATCH (n {name: $name}) RETURN n", {"name": "alice"})
        # The dollar-quoted block must include the AS clause and the
        # third %s::agtype placeholder for the params map.
        cypher_call = next(
            (sql for sql, _ in cur.executed if "cypher(" in sql), None
        )
        assert cypher_call is not None
        assert "%s::agtype" in cypher_call
        # The bind tuple must be (graph_name, params_json_blob)
        params = next(
            (params for sql, params in cur.executed if "cypher(" in sql),
            None,
        )
        assert params is not None
        assert params[0] == "cognee_graph"  # default graph_name
        # The JSON-serialised params blob must round-trip
        import json as _json
        assert _json.loads(params[1]) == {"name": "alice"}

    def test_session_run_with_kwargs(self, monkeypatch):
        """Keyword-arg parameters merge into the params map."""
        cur = _FakePsycopgCursor()
        cur._set_rows([])
        fake_conn = _FakePsycopgConn(cursor=cur)
        with patch("psycopg2.connect", return_value=fake_conn):
            drv = graph_apache_age.create_driver()
            with drv.session() as session:
                session.run("RETURN $x", x=42)
        params = next(
            (p for sql, p in cur.executed if "cypher(" in sql),
            None,
        )
        import json as _json
        assert _json.loads(params[1]) == {"x": 42}

    def test_session_run_rejects_dollar_dollar_breakout(self, monkeypatch):
        """Cypher payloads with `$$` would break out of AGE's dollar-quote."""
        fake_conn = _FakePsycopgConn()
        with patch("psycopg2.connect", return_value=fake_conn):
            drv = graph_apache_age.create_driver()
            with drv.session() as session:
                with pytest.raises(ValueError, match=r"\$\$"):
                    session.run("RETURN 1 $$ ; DROP TABLE users ; SELECT 1 $$ ")

    def test_create_async_driver_returns_driver(self):
        """Phase 5 update: async path now returns a real asyncpg-backed driver."""
        drv = graph_apache_age.create_async_driver()
        assert type(drv).__name__ == "_AsyncAGEDriver"

    @pytest.mark.asyncio
    async def test_async_session_lifecycle_and_run(self):
        """End-to-end: async session opens / runs / commits / closes via mocked asyncpg."""

        # Build a fake asyncpg.connect coroutine that returns a fake connection
        executed: list = []
        fetched_with: list = []

        class _FakeConn:
            async def execute(self, sql, *args):
                executed.append((sql, args))

            async def fetch(self, sql, *args):
                fetched_with.append((sql, args))
                # Mimic asyncpg.Record by returning objects with .values()
                class _Rec:
                    def values(self_inner):
                        return ("1",)
                return [_Rec()]

            async def close(self):
                executed.append(("CLOSE", ()))

        async def _fake_connect(**kwargs):
            return _FakeConn()

        import asyncpg
        with patch.object(asyncpg, "connect", new=_fake_connect):
            drv = graph_apache_age.create_async_driver()
            async with drv.session() as session:
                result = await session.run("RETURN 1")
            assert result.single()[0] == 1
            # No params -> two-arg cypher() form (no %s::agtype)
            cypher_calls = [c for c in fetched_with if "cypher(" in c[0]]
            assert len(cypher_calls) == 1
            assert "%s::agtype" not in cypher_calls[0][0]
            # Connection was closed on context exit
            assert any(call[0] == "CLOSE" for call in executed)

    @pytest.mark.asyncio
    async def test_async_session_with_params(self):
        """Async path threads $param queries through AGE's three-arg form."""
        fetched_with: list = []

        class _FakeConn:
            async def execute(self, sql, *args):
                pass

            async def fetch(self, sql, *args):
                fetched_with.append((sql, args))
                return []

            async def close(self):
                pass

        async def _fake_connect(**kwargs):
            return _FakeConn()

        import asyncpg
        with patch.object(asyncpg, "connect", new=_fake_connect):
            drv = graph_apache_age.create_async_driver()
            async with drv.session() as session:
                await session.run("MATCH (n {id: $i}) RETURN n", i=42)

        cypher_call = next(
            (c for c in fetched_with if "cypher(" in c[0]), None
        )
        assert cypher_call is not None
        sql, args = cypher_call
        # Async path uses asyncpg's $1/$2 placeholders, not psycopg2's %s.
        assert "$1" in sql and "$2" in sql
        assert "::agtype" in sql
        # First arg is graph name, second is JSON-serialised params map
        import json as _json
        assert args[0] == "cognee_graph"
        assert _json.loads(args[1]) == {"i": 42}

    @pytest.mark.asyncio
    async def test_async_session_dollar_dollar_rejected(self):
        """Async path also rejects `$$` payloads."""
        class _FakeConn:
            async def execute(self, *a):
                pass

            async def fetch(self, *a):
                return []

            async def close(self):
                pass

        async def _fake_connect(**kwargs):
            return _FakeConn()

        import asyncpg
        with patch.object(asyncpg, "connect", new=_fake_connect):
            drv = graph_apache_age.create_async_driver()
            async with drv.session() as session:
                with pytest.raises(ValueError, match=r"\$\$"):
                    await session.run("RETURN $$ ; SELECT 1 $$ ")

    def test_driver_close_is_idempotent(self, monkeypatch):
        with patch("psycopg2.connect", return_value=_FakePsycopgConn()):
            drv = graph_apache_age.create_driver()
            drv.close()
            drv.close()  # second call must not raise


class TestAGEAgtypeUnwrap:
    """Verify the agtype string-to-Python conversion."""

    def test_unwrap_none(self):
        assert graph_apache_age._unwrap_agtype(None) is None

    def test_unwrap_int_str(self):
        assert graph_apache_age._unwrap_agtype("42") == 42

    def test_unwrap_quoted_str(self):
        assert graph_apache_age._unwrap_agtype('"hello"') == "hello"

    def test_unwrap_json_object(self):
        v = graph_apache_age._unwrap_agtype('{"label": "n", "id": 1}')
        assert v == {"label": "n", "id": 1}

    def test_unwrap_vertex_suffix_stripped(self):
        v = graph_apache_age._unwrap_agtype('{"id": 1}::vertex')
        assert v == {"id": 1}

    def test_unwrap_edge_suffix_stripped(self):
        v = graph_apache_age._unwrap_agtype('{"id": 2}::edge')
        assert v == {"id": 2}

    def test_unwrap_path_suffix_stripped(self):
        v = graph_apache_age._unwrap_agtype('[]::path')
        assert v == []

    def test_unwrap_bytes(self):
        assert graph_apache_age._unwrap_agtype(b"true") is True

    def test_unwrap_unparseable_returns_str(self):
        v = graph_apache_age._unwrap_agtype("not_json_at_all")
        assert v == "not_json_at_all"

    def test_unwrap_passthrough_for_native_types(self):
        # Non-bytes/str values pass through unchanged
        assert graph_apache_age._unwrap_agtype(42) == 42
        assert graph_apache_age._unwrap_agtype([1, 2]) == [1, 2]


class TestAGENativeNode:
    """neo4j.graph.Node-shaped conversion of ::vertex agtype."""

    def test_vertex_returns_age_node(self):
        agtype = (
            '{"id": 844424930131969, "label": "Person", '
            '"properties": {"name": "Alice", "age": 30}}::vertex'
        )
        node = graph_apache_age._unwrap_agtype(agtype)

        assert isinstance(node, graph_apache_age._AGENode)
        assert node.id == 844424930131969
        assert node.element_id == "844424930131969"
        assert node.labels == frozenset({"Person"})
        assert node["name"] == "Alice"
        assert node["age"] == 30

    def test_node_dict_protocol(self):
        node = graph_apache_age._AGENode(1, "X", {"k": "v"})
        assert dict(node.items()) == {"k": "v"}
        assert node.keys() == ["k"]
        assert node.values() == ["v"]
        assert "k" in node
        assert "missing" not in node
        assert len(node) == 1
        assert list(iter(node)) == ["k"]
        assert node.get("k") == "v"
        assert node.get("missing", "default") == "default"

    def test_node_with_empty_label_str(self):
        # Stub endpoints (Relationship.start_node/end_node) construct
        # _AGENode with no label. The labels set should be empty.
        node = graph_apache_age._AGENode(42, "")
        assert node.labels == frozenset()

    def test_node_with_multi_label_list(self):
        node = graph_apache_age._AGENode(1, ["Person", "Employee"], {})
        assert node.labels == frozenset({"Person", "Employee"})

    def test_node_equality_and_hash(self):
        a = graph_apache_age._AGENode(1, "X", {"k": "v"})
        b = graph_apache_age._AGENode(1, "X", {"k": "different"})
        c = graph_apache_age._AGENode(2, "X", {"k": "v"})

        assert a == b
        assert a != c
        assert hash(a) == hash(b)
        assert (a == "not a node") is False

    def test_node_repr_round_trip(self):
        node = graph_apache_age._AGENode(1, "Person", {"name": "Bob"})
        r = repr(node)
        assert "Person" in r and "Bob" in r and "id=1" in r

    def test_vertex_without_label_returns_dict_for_safety(self):
        # Defensive path -- malformed payloads round-trip as dicts
        # rather than raising, so the caller can inspect them.
        v = graph_apache_age._unwrap_agtype('{"id": 1}::vertex')
        assert isinstance(v, dict)
        assert v == {"id": 1}


class TestAGENativeRelationship:
    """neo4j.graph.Relationship-shaped conversion of ::edge agtype."""

    def test_edge_returns_age_relationship(self):
        agtype = (
            '{"id": 1407374883553281, "label": "KNOWS", '
            '"start_id": 844424930131969, "end_id": 844424930131970, '
            '"properties": {"since": 2020}}::edge'
        )
        rel = graph_apache_age._unwrap_agtype(agtype)

        assert isinstance(rel, graph_apache_age._AGERelationship)
        assert rel.id == 1407374883553281
        assert rel.element_id == "1407374883553281"
        assert rel.type == "KNOWS"
        assert rel["since"] == 2020

    def test_relationship_start_and_end_node_stubs(self):
        rel = graph_apache_age._AGERelationship(
            10, "KNOWS", 100, 200, {"since": 2020}
        )
        assert isinstance(rel.start_node, graph_apache_age._AGENode)
        assert rel.start_node.id == 100
        assert rel.start_node.labels == frozenset()
        assert isinstance(rel.end_node, graph_apache_age._AGENode)
        assert rel.end_node.id == 200
        # nodes tuple returns (start, end)
        s, e = rel.nodes
        assert s.id == 100 and e.id == 200

    def test_relationship_dict_protocol(self):
        rel = graph_apache_age._AGERelationship(1, "T", 2, 3, {"k": "v"})
        assert dict(rel.items()) == {"k": "v"}
        assert rel.keys() == ["k"]
        assert rel.values() == ["v"]
        assert "k" in rel
        assert len(rel) == 1
        assert list(iter(rel)) == ["k"]
        assert rel.get("k") == "v"
        assert rel.get("missing", "default") == "default"

    def test_relationship_equality_and_hash(self):
        a = graph_apache_age._AGERelationship(1, "T", 2, 3)
        b = graph_apache_age._AGERelationship(1, "T", 999, 999, {"different": True})
        c = graph_apache_age._AGERelationship(2, "T", 2, 3)

        assert a == b  # same id + type
        assert a != c  # different id
        assert hash(a) == hash(b)
        assert (a == "not a rel") is False

    def test_relationship_repr_round_trip(self):
        rel = graph_apache_age._AGERelationship(10, "KNOWS", 100, 200, {"since": 2020})
        r = repr(rel)
        assert "KNOWS" in r and "id=10" in r and "start=100" in r and "end=200" in r

    def test_edge_without_required_keys_returns_dict_for_safety(self):
        v = graph_apache_age._unwrap_agtype('{"id": 2}::edge')
        assert isinstance(v, dict)
        assert v == {"id": 2}


class TestAGENativePath:
    """::path agtype decodes to a list of _AGENode / _AGERelationship."""

    def test_empty_path(self):
        v = graph_apache_age._unwrap_agtype("[]::path")
        assert v == []

    def test_single_hop_path(self):
        # AGE path = alternating [vertex, edge, vertex, ...]
        agtype = (
            '[{"id": 1, "label": "A", "properties": {}},'
            ' {"id": 10, "label": "REL", "start_id": 1, "end_id": 2, "properties": {}},'
            ' {"id": 2, "label": "B", "properties": {}}]::path'
        )
        path = graph_apache_age._unwrap_agtype(agtype)

        assert isinstance(path, list)
        assert len(path) == 3
        assert isinstance(path[0], graph_apache_age._AGENode)
        assert path[0].labels == frozenset({"A"})
        assert isinstance(path[1], graph_apache_age._AGERelationship)
        assert path[1].type == "REL"
        assert isinstance(path[2], graph_apache_age._AGENode)
        assert path[2].labels == frozenset({"B"})

    def test_path_with_malformed_element_passes_through(self):
        # Defensive: a path element that doesn't match vertex/edge
        # shape round-trips as the raw dict.
        agtype = '[{"random": "stuff"}]::path'
        path = graph_apache_age._unwrap_agtype(agtype)
        assert path == [{"random": "stuff"}]


class TestAGERecordAndResult:
    """Ensure neo4j.Record-style access works on _AGERecord."""

    def test_record_int_index(self):
        r = graph_apache_age._AGERecord(("1", "2"), ["a", "b"])
        assert r[0] == 1
        assert r[1] == 2

    def test_record_key_index(self):
        r = graph_apache_age._AGERecord(("1", "2"), ["a", "b"])
        assert r["a"] == 1
        assert r["b"] == 2

    def test_record_keys_and_values(self):
        r = graph_apache_age._AGERecord(("1", "2"), ["a", "b"])
        assert r.keys() == ["a", "b"]
        assert r.values() == (1, 2)
        assert r.data() == {"a": 1, "b": 2}

    def test_record_iter(self):
        r = graph_apache_age._AGERecord(("1", "2"), ["a", "b"])
        assert list(r) == [1, 2]

    def test_record_len(self):
        r = graph_apache_age._AGERecord(("1",), ["a"])
        assert len(r) == 1

    def test_result_single_empty(self):
        assert graph_apache_age._AGEResult([], ["x"]).single() is None

    def test_result_data(self):
        res = graph_apache_age._AGEResult([("1",), ("2",)], ["n"])
        assert res.data() == [{"n": 1}, {"n": 2}]


class TestAGEEnvFallback:
    def test_age_env_then_postgres_env(self, monkeypatch):
        # Clear all, set only POSTGRES_*; expect those to be used.
        for v in ("AGE_HOST", "AGE_PORT", "AGE_DB", "AGE_USER", "AGE_PASSWORD", "AGE_GRAPH_NAME"):
            monkeypatch.delenv(v, raising=False)
        monkeypatch.setenv("POSTGRES_HOST", "pg-host")
        monkeypatch.setenv("POSTGRES_PORT", "55432")
        monkeypatch.setenv("POSTGRES_DB", "pg-db")
        monkeypatch.setenv("POSTGRES_USER", "pg-user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "pg-pass")
        drv = graph_apache_age.create_driver()
        assert drv._host == "pg-host"
        assert drv._port == 55432
        assert drv._database == "pg-db"
        assert drv._user == "pg-user"
        assert drv._password == "pg-pass"
        assert drv._graph_name == "cognee_graph"

    def test_age_env_overrides_postgres(self, monkeypatch):
        monkeypatch.setenv("AGE_HOST", "age-host")
        monkeypatch.setenv("AGE_PORT", "9999")
        monkeypatch.setenv("AGE_DB", "age-db")
        monkeypatch.setenv("AGE_USER", "age-user")
        monkeypatch.setenv("AGE_PASSWORD", "age-pass")
        monkeypatch.setenv("AGE_GRAPH_NAME", "my_graph")
        monkeypatch.setenv("POSTGRES_HOST", "pg-host")
        drv = graph_apache_age.create_driver()
        assert drv._host == "age-host"
        assert drv._port == 9999
        assert drv._database == "age-db"
        assert drv._graph_name == "my_graph"


# ===========================================================================
# In-memory cache adapter
# ===========================================================================


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if asyncio.get_event_loop().is_running() else asyncio.run(coro)


class TestInMemoryCache:
    @pytest.mark.asyncio
    async def test_ping(self):
        c = cache_in_memory.create_async_client()
        assert await c.ping() is True

    @pytest.mark.asyncio
    async def test_set_then_get(self):
        c = cache_in_memory.create_async_client()
        assert await c.set("foo", "bar") is True
        assert await c.get("foo") == "bar"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self):
        c = cache_in_memory.create_async_client()
        assert await c.get("never_set") is None

    @pytest.mark.asyncio
    async def test_delete_returns_count(self):
        c = cache_in_memory.create_async_client()
        await c.set("a", 1)
        await c.set("b", 2)
        assert await c.delete("a", "b", "missing") == 2
        assert await c.get("a") is None

    @pytest.mark.asyncio
    async def test_exists(self):
        c = cache_in_memory.create_async_client()
        await c.set("k", "v")
        assert await c.exists("k") == 1
        assert await c.exists("k", "missing") == 1

    @pytest.mark.asyncio
    async def test_expire_then_get_returns_none(self):
        # Set ex=0 so it expires immediately on the next monotonic tick.
        c = cache_in_memory.create_async_client()
        await c.set("k", "v")
        await c.expire("k", 0)
        # Sleep a hair to push monotonic past the expiry
        await asyncio.sleep(0.01)
        assert await c.get("k") is None

    @pytest.mark.asyncio
    async def test_set_with_ex(self):
        c = cache_in_memory.create_async_client()
        await c.set("k", "v", ex=300)
        assert await c.get("k") == "v"

    @pytest.mark.asyncio
    async def test_expire_returns_false_when_key_missing(self):
        c = cache_in_memory.create_async_client()
        assert await c.expire("missing", 60) is False

    @pytest.mark.asyncio
    async def test_keys_pattern(self):
        c = cache_in_memory.create_async_client()
        await c.set("user:1", "a")
        await c.set("user:2", "b")
        await c.set("other", "c")
        all_keys = await c.keys("*")
        assert set(all_keys) == {"user:1", "user:2", "other"}
        user_keys = await c.keys("user:*")
        assert set(user_keys) == {"user:1", "user:2"}

    @pytest.mark.asyncio
    async def test_flushdb(self):
        c = cache_in_memory.create_async_client()
        await c.set("k", "v")
        assert await c.flushdb() is True
        assert await c.get("k") is None

    @pytest.mark.asyncio
    async def test_close_is_noop(self):
        c = cache_in_memory.create_async_client()
        await c.close()  # must not raise

    @pytest.mark.asyncio
    async def test_decode_responses_bytes_become_str(self):
        c = cache_in_memory.create_async_client(decode_responses=True)
        await c.set("k", b"bytes_value")
        assert await c.get("k") == "bytes_value"

    @pytest.mark.asyncio
    async def test_decode_responses_false_keeps_bytes(self):
        c = cache_in_memory.create_async_client(decode_responses=False)
        await c.set("k", b"raw_bytes")
        assert await c.get("k") == b"raw_bytes"

    @pytest.mark.asyncio
    async def test_await_client_returns_self(self):
        """redis-py callers sometimes `await client` to force connection init.
        Our shim must mirror that to avoid breaking those patterns.
        """
        c = cache_in_memory.create_async_client()
        result = await c
        assert result is c

    def test_create_sync_client_returns_same_shape(self):
        c = cache_in_memory.create_sync_client()
        # Same class as the async client (methods are coroutines either way)
        assert type(c).__name__ == "_InMemoryAsyncClient"
