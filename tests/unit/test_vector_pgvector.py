"""Tests for src/db_adapters/vector_pgvector.py.

Covers the narrow QdrantClient-shaped surface the call sites use, with
psycopg2 mocked so no live Postgres is needed. Confirms:

- Factory dispatch (ENHANCED_VECTOR_PROVIDER=pgvector)
- Env-var fallback chain (PGVECTOR_* primary, POSTGRES_* secondary)
- Distance-enum -> pgvector operator mapping
- Safe-table-name sanitisation (no SQL injection from collection name)
- get_collections / get_collection / count / create_collection / upsert
- search (returns ScoredPoint-shape hits with score from `1 - distance`)
- delete by ID list, by FilterSelector (single must FieldCondition),
  and NotImplementedError on complex filters
- query_filter in search() raises NotImplementedError
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src import db_factory
from src.db_adapters import vector_pgvector


# ===========================================================================
# Fake psycopg2 surface
# ===========================================================================


class _FakeCursor:
    """Minimal psycopg2 cursor stand-in. Tests prime it with rows."""

    def __init__(self):
        self.executed: list = []
        self._next_rows: list = []
        self.description = None

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._next_rows[0] if self._next_rows else None

    def fetchall(self):
        return list(self._next_rows)


class _FakeConn:
    """psycopg2 connection stand-in with a single cursor."""

    def __init__(self, cursor=None):
        self._cursor = cursor or _FakeCursor()
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None


# ===========================================================================
# Sanitisation + distance mapping
# ===========================================================================


class TestSafeTableName:
    def test_strips_special_chars(self):
        assert vector_pgvector._safe_table_name("ec_vec_", "cognee_ats memory!") == (
            "ec_vec_cognee_ats_memory"
        )

    def test_lowercases(self):
        assert vector_pgvector._safe_table_name("ec_vec_", "MixedCASE") == (
            "ec_vec_mixedcase"
        )

    def test_quote_injection_blocked(self):
        # Whatever the caller passes, the result is alphanumeric + underscore.
        evil = '"; DROP TABLE memories; --'
        out = vector_pgvector._safe_table_name("ec_vec_", evil)
        assert all(c.isalnum() or c == "_" for c in out)


class TestDistanceMapping:
    def test_cosine_operator(self):
        # Pass a string that mimics qdrant Distance.COSINE.__str__
        assert vector_pgvector._distance_to_operator("Distance.COSINE") == "<=>"

    def test_euclid_operator(self):
        assert vector_pgvector._distance_to_operator("Distance.EUCLID") == "<->"

    def test_dot_operator(self):
        assert vector_pgvector._distance_to_operator("Distance.DOT") == "<#>"

    def test_unknown_defaults_to_cosine(self):
        assert vector_pgvector._distance_to_operator("Distance.BANANA") == "<=>"

    def test_opclass_cosine(self):
        assert vector_pgvector._distance_to_opclass("Distance.COSINE") == (
            "vector_cosine_ops"
        )


class TestVectorToStr:
    def test_basic(self):
        out = vector_pgvector._vector_to_str([1.0, 2.5, -3.14])
        # Just confirm shape; exact repr depends on Python float formatting.
        assert out.startswith("[")
        assert out.endswith("]")
        assert out.count(",") == 2


# ===========================================================================
# Factory dispatch
# ===========================================================================


class TestPgVectorFactoryDispatch:
    def test_factory_returns_pgvector_client(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_VECTOR_PROVIDER", "pgvector")
        client = db_factory.get_vector_client()
        assert type(client).__name__ == "_PgVectorClient"

    def test_env_fallback_chain(self, monkeypatch):
        """PGVECTOR_* takes precedence; falls through to POSTGRES_*."""
        for v in ("PGVECTOR_HOST", "PGVECTOR_PORT", "PGVECTOR_DB",
                  "PGVECTOR_USER", "PGVECTOR_PASSWORD"):
            monkeypatch.delenv(v, raising=False)
        monkeypatch.setenv("POSTGRES_HOST", "pghost")
        monkeypatch.setenv("POSTGRES_PORT", "55432")
        client = vector_pgvector.create_client()
        assert client._conn_params["host"] == "pghost"
        assert client._conn_params["port"] == 55432

    def test_pgvector_env_overrides_postgres(self, monkeypatch):
        monkeypatch.setenv("PGVECTOR_HOST", "pgvecthost")
        monkeypatch.setenv("POSTGRES_HOST", "pghost")
        client = vector_pgvector.create_client()
        assert client._conn_params["host"] == "pgvecthost"

    def test_table_prefix_env(self, monkeypatch):
        monkeypatch.setenv("PGVECTOR_TABLE_PREFIX", "custom_")
        client = vector_pgvector.create_client()
        assert client._table_prefix == "custom_"


# ===========================================================================
# Collection CRUD
# ===========================================================================


def _make_client_with_cursor(cur):
    """Helper: build a _PgVectorClient whose _connect() returns a fake conn."""
    client = vector_pgvector._PgVectorClient(
        host="h", port=1, database="d", user="u", password="p",
        table_prefix="ec_vec_",
    )
    conn = _FakeConn(cursor=cur)
    client._connect = lambda: conn
    return client, conn


class TestCollectionCRUD:
    def test_get_collections_returns_qdrant_shape(self):
        cur = _FakeCursor()
        # pg_tables returns rows of (tablename,) -- the adapter strips
        # the prefix before exposing the collection name to callers.
        cur._next_rows = [("ec_vec_ats",), ("ec_vec_oma",)]
        client, _ = _make_client_with_cursor(cur)

        result = client.get_collections()

        assert hasattr(result, "collections")
        names = [c.name for c in result.collections]
        assert names == ["ats", "oma"]

    def test_get_collection_raises_when_missing(self):
        cur = _FakeCursor()
        cur._next_rows = [(False,)]
        client, _ = _make_client_with_cursor(cur)

        with pytest.raises(RuntimeError, match="not found"):
            client.get_collection("missing")

    def test_get_collection_returns_info_when_present(self):
        cur = _FakeCursor()
        cur._next_rows = [(True,)]
        client, _ = _make_client_with_cursor(cur)
        info = client.get_collection("ats")
        assert info.status == "green"

    def test_create_collection_emits_table_index_and_extension(self):
        cur = _FakeCursor()
        client, conn = _make_client_with_cursor(cur)

        VectorParams = MagicMock()
        VectorParams.size = 1024
        VectorParams.distance = "Distance.COSINE"

        client.create_collection("ats", vectors_config=VectorParams)

        # We expect at least: CREATE EXTENSION, CREATE TABLE, CREATE INDEX.
        sqls = [sql for sql, _ in cur.executed]
        assert any("CREATE EXTENSION" in s for s in sqls)
        assert any("CREATE TABLE" in s and "ec_vec_ats" in s for s in sqls)
        assert any("CREATE INDEX" in s and "vector_cosine_ops" in s for s in sqls)
        assert conn.committed is True
        # Distance is remembered for later search() calls.
        assert client._distance_by_table["ec_vec_ats"] == "Distance.COSINE"


# ===========================================================================
# Upsert + count + search
# ===========================================================================


class TestUpsertCountSearch:
    def test_upsert_writes_each_point(self):
        cur = _FakeCursor()
        client, conn = _make_client_with_cursor(cur)

        p1 = MagicMock(id="abc", vector=[0.1, 0.2], payload={"agent_id": "x"})
        p2 = MagicMock(id="def", vector=[0.3, 0.4], payload={"agent_id": "y"})
        client.upsert("ats", points=[p1, p2])

        inserts = [sql for sql, _ in cur.executed if "INSERT INTO" in sql]
        assert len(inserts) == 2
        assert "ec_vec_ats" in inserts[0]
        assert conn.committed is True

    def test_count_returns_count_result(self):
        cur = _FakeCursor()
        cur._next_rows = [(42,)]
        client, _ = _make_client_with_cursor(cur)
        result = client.count("ats")
        assert result.count == 42

    def test_search_returns_score_above_threshold(self):
        cur = _FakeCursor()
        # Simulated rows: (id, payload, score)
        cur._next_rows = [
            ("a", {"text": "hello"}, 0.9),
            ("b", {"text": "world"}, 0.5),
        ]
        client, _ = _make_client_with_cursor(cur)
        client._distance_by_table["ec_vec_ats"] = "Distance.COSINE"

        hits = client.search(
            "ats", query_vector=[0.1, 0.2], limit=10, score_threshold=0.7,
        )

        assert len(hits) == 1
        assert hits[0].id == "a"
        assert hits[0].score == pytest.approx(0.9)
        assert hits[0].payload == {"text": "hello"}

    def test_search_no_threshold_returns_all(self):
        cur = _FakeCursor()
        cur._next_rows = [
            ("a", {}, 0.9),
            ("b", {}, 0.5),
            ("c", {}, 0.1),
        ]
        client, _ = _make_client_with_cursor(cur)
        hits = client.search("ats", query_vector=[0.1], limit=5)
        assert [h.id for h in hits] == ["a", "b", "c"]

    def test_search_query_filter_compound_raises(self):
        # Compound filters are rejected by the shared filter translator.
        client, _ = _make_client_with_cursor(_FakeCursor())
        cond_a = MagicMock(key="a", match=MagicMock(value="x"))
        cond_b = MagicMock(key="b", match=MagicMock(value="y"))
        filt = MagicMock(must=[cond_a, cond_b], should=None, must_not=None)
        with pytest.raises(NotImplementedError, match="single"):
            client.search("ats", query_vector=[0.1], query_filter=filt)

    def test_search_query_filter_emits_where_clause(self):
        cur = _FakeCursor()
        client, _ = _make_client_with_cursor(cur)
        cond = MagicMock(key="user_id", match=MagicMock(value="u1"))
        filt = MagicMock(must=[cond], should=None, must_not=None)

        client.search("ats", query_vector=[0.1], query_filter=filt)

        sql = cur.executed[0][0]
        params = cur.executed[0][1]
        assert "WHERE payload ->> %s = %s" in sql
        # Param order: [vector, key, value, vector, limit]
        assert "user_id" in params
        assert "u1" in params


# ===========================================================================
# Delete -- ID list, FilterSelector, and unsupported shapes
# ===========================================================================


class TestDelete:
    def test_delete_by_id_list(self):
        cur = _FakeCursor()
        client, conn = _make_client_with_cursor(cur)
        client.delete("ats", points_selector=["id1", "id2", "id3"])
        sql = cur.executed[0][0]
        assert "DELETE FROM" in sql and "ec_vec_ats" in sql
        # Bound IDs are stringified
        assert cur.executed[0][1] == (["id1", "id2", "id3"],)
        assert conn.committed is True

    def test_delete_by_filter_selector_single_field_condition(self):
        cur = _FakeCursor()
        client, conn = _make_client_with_cursor(cur)

        # Build the same shape that gdpr_manager passes:
        # FilterSelector(filter=Filter(must=[FieldCondition(key="agent_id",
        #                                                   match=MatchValue(value=...))]))
        cond = MagicMock(key="agent_id", match=MagicMock(value="user-xyz"))
        filt = MagicMock(must=[cond], should=None, must_not=None)
        selector = MagicMock(filter=filt)

        client.delete("memories", points_selector=selector)

        sql, params = cur.executed[0]
        assert "DELETE FROM" in sql and "ec_vec_memories" in sql
        assert "payload ->>" in sql
        assert params == ("agent_id", "user-xyz")
        assert conn.committed is True

    def test_delete_filter_with_should_raises(self):
        client, _ = _make_client_with_cursor(_FakeCursor())
        cond = MagicMock(key="agent_id", match=MagicMock(value="x"))
        filt = MagicMock(
            must=[cond], should=[MagicMock()], must_not=None,
        )
        with pytest.raises(NotImplementedError, match="should"):
            client.delete("ats", points_selector=MagicMock(filter=filt))

    def test_delete_multi_must_raises(self):
        client, _ = _make_client_with_cursor(_FakeCursor())
        cond1 = MagicMock(key="a", match=MagicMock(value="x"))
        cond2 = MagicMock(key="b", match=MagicMock(value="y"))
        filt = MagicMock(must=[cond1, cond2], should=None, must_not=None)
        with pytest.raises(NotImplementedError):
            client.delete("ats", points_selector=MagicMock(filter=filt))

    def test_delete_empty_list_noop(self):
        cur = _FakeCursor()
        client, conn = _make_client_with_cursor(cur)
        client.delete("ats", points_selector=[])
        assert cur.executed == []
        assert conn.committed is False

    def test_delete_unsupported_selector_raises(self):
        client, _ = _make_client_with_cursor(_FakeCursor())
        with pytest.raises(NotImplementedError, match="unsupported"):
            client.delete("ats", points_selector="not-a-list")


# ===========================================================================
# Lifecycle
# ===========================================================================


class TestLifecycle:
    def test_close_is_noop(self):
        client, _ = _make_client_with_cursor(_FakeCursor())
        client.close()  # must not raise


# ===========================================================================
# Provider matrix
# ===========================================================================


class TestProviderMatrix:
    def test_pgvector_in_valid_vector_set(self):
        assert "pgvector" in db_factory._VALID_VECTOR

    def test_qdrant_still_default(self, monkeypatch):
        for v in (
            "ENHANCED_VECTOR_PROVIDER", "VECTOR_BACKEND",
        ):
            monkeypatch.delenv(v, raising=False)
        assert db_factory.get_provider_summary()["vector"] == "qdrant"
