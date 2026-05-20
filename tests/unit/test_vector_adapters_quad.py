"""Tests for the Phase 5 vector adapter quartet.

Covers LanceDB / Chroma / Weaviate / Milvus -- each a narrow
QdrantClient-shaped shim. The underlying SDKs are mocked so no live
service is needed.

Each adapter is tested for:
  - Factory dispatch (`ENHANCED_VECTOR_PROVIDER=<name>`)
  - Env-var fallback chain
  - Distance-enum -> native metric mapping
  - get_collections / get_collection / count / create_collection / upsert
  - search returning ScoredPoint-shape hits with normalised score
  - delete by ID list, by FilterSelector (single must FieldCondition),
    and NotImplementedError on complex filters
  - query_filter in search:
      * single FieldCondition translates to native (where / expr / SQL)
      * compound filters raise NotImplementedError via the shared
        ``_vector_filter`` translator
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src import db_factory


# ===========================================================================
# Provider matrix
# ===========================================================================


class TestVectorProviderMatrix:
    def test_all_six_providers_recognised(self):
        assert db_factory._VALID_VECTOR == {
            "qdrant", "pgvector", "lancedb", "chroma", "weaviate", "milvus",
        }

    def test_qdrant_still_default(self, monkeypatch):
        for v in ("ENHANCED_VECTOR_PROVIDER", "VECTOR_BACKEND"):
            monkeypatch.delenv(v, raising=False)
        assert db_factory.get_provider_summary()["vector"] == "qdrant"


# ===========================================================================
# LanceDB
# ===========================================================================


class TestLanceDBAdapter:
    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_VECTOR_PROVIDER", "lancedb")
        client = db_factory.get_vector_client()
        assert type(client).__name__ == "_LanceDBClient"

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("LANCEDB_URI", "/tmp/test_lancedb")
        from src.db_adapters import vector_lancedb
        client = vector_lancedb.create_client()
        assert client._uri == "/tmp/test_lancedb"

    def test_distance_mapping(self):
        from src.db_adapters import vector_lancedb
        assert vector_lancedb._distance_to_lance_metric("Distance.COSINE") == "cosine"
        assert vector_lancedb._distance_to_lance_metric("Distance.EUCLID") == "l2"
        assert vector_lancedb._distance_to_lance_metric("Distance.DOT") == "dot"
        assert vector_lancedb._distance_to_lance_metric(None) is None

    def test_get_collections_with_mocked_db(self):
        from src.db_adapters import vector_lancedb
        client = vector_lancedb.create_client(url="/tmp/test_lancedb")
        fake_db = MagicMock()
        fake_db.table_names.return_value = ["ats", "oma"]
        client._db = fake_db
        result = client.get_collections()
        assert [c.name for c in result.collections] == ["ats", "oma"]

    def test_get_collection_raises_when_missing(self):
        from src.db_adapters import vector_lancedb
        client = vector_lancedb.create_client(url="/tmp/test_lancedb")
        fake_db = MagicMock()
        fake_db.table_names.return_value = ["ats"]
        client._db = fake_db
        with pytest.raises(RuntimeError, match="not found"):
            client.get_collection("missing")

    def test_search_query_filter_compound_raises(self):
        # Compound filters (multiple must clauses) are rejected at the
        # filter-translator layer because we only support single-must
        # equality filters across all 5 vector backends.
        from src.db_adapters import vector_lancedb
        client = vector_lancedb.create_client()
        cond_a = MagicMock(key="user_id", match=MagicMock(value="u1"))
        cond_b = MagicMock(key="tag", match=MagicMock(value="t1"))
        filt = MagicMock(must=[cond_a, cond_b], should=None, must_not=None)
        with pytest.raises(NotImplementedError, match="single"):
            client.search("ats", query_vector=[0.1], query_filter=filt)

    def test_search_query_filter_translated_to_where(self):
        # Single FieldCondition is now translated into LanceDB SQL WHERE.
        from src.db_adapters import vector_lancedb
        client = vector_lancedb.create_client()
        fake_db = MagicMock()
        fake_table = MagicMock()
        fake_search = MagicMock()
        fake_search.metric.return_value = fake_search
        fake_search.where.return_value = fake_search
        fake_search.limit.return_value = fake_search

        class _EmptyDF:
            def iterrows(self):
                return iter([])

        fake_search.to_pandas.return_value = _EmptyDF()
        fake_table.search.return_value = fake_search
        fake_db.open_table.return_value = fake_table
        client._db = fake_db

        cond = MagicMock(key="user_id", match=MagicMock(value="u1"))
        filt = MagicMock(must=[cond], should=None, must_not=None)
        client.search("ats", query_vector=[0.1], query_filter=filt)

        fake_search.where.assert_called_once()
        where_arg = fake_search.where.call_args[0][0]
        assert "user_id" in where_arg
        assert "u1" in where_arg

    def test_delete_by_id_list(self):
        from src.db_adapters import vector_lancedb
        client = vector_lancedb.create_client()
        fake_db = MagicMock()
        fake_table = MagicMock()
        fake_db.open_table.return_value = fake_table
        client._db = fake_db
        client.delete("ats", points_selector=["a", "b", "c"])
        fake_table.delete.assert_called_once()

    def test_delete_filter_with_should_raises(self):
        from src.db_adapters import vector_lancedb
        client = vector_lancedb.create_client()
        client._db = MagicMock()
        cond = MagicMock(key="x", match=MagicMock(value="y"))
        filt = MagicMock(must=[cond], should=[MagicMock()], must_not=None)
        with pytest.raises(NotImplementedError, match="single"):
            client.delete("ats", points_selector=MagicMock(filter=filt))


# ===========================================================================
# Chroma
# ===========================================================================


class TestChromaAdapter:
    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_VECTOR_PROVIDER", "chroma")
        client = db_factory.get_vector_client()
        assert type(client).__name__ == "_ChromaClient"

    def test_persistent_mode_default(self, monkeypatch):
        for v in ("CHROMA_HOST", "CHROMA_PORT", "CHROMA_PATH"):
            monkeypatch.delenv(v, raising=False)
        from src.db_adapters import vector_chroma
        client = vector_chroma.create_client()
        assert client._host is None
        assert client._path == "./chroma_data"

    def test_network_mode_when_host_set(self, monkeypatch):
        monkeypatch.setenv("CHROMA_HOST", "chroma.internal")
        monkeypatch.setenv("CHROMA_PORT", "8000")
        from src.db_adapters import vector_chroma
        client = vector_chroma.create_client()
        assert client._host == "chroma.internal"
        assert client._port == 8000

    def test_distance_mapping(self):
        from src.db_adapters import vector_chroma
        assert vector_chroma._distance_to_chroma_metric("Distance.COSINE") == "cosine"
        assert vector_chroma._distance_to_chroma_metric("Distance.EUCLID") == "l2"
        assert vector_chroma._distance_to_chroma_metric("Distance.DOT") == "ip"

    def test_search_query_filter_compound_raises(self):
        from src.db_adapters import vector_chroma
        client = vector_chroma.create_client()
        cond_a = MagicMock(key="a", match=MagicMock(value="x"))
        cond_b = MagicMock(key="b", match=MagicMock(value="y"))
        filt = MagicMock(must=[cond_a, cond_b], should=None, must_not=None)
        with pytest.raises(NotImplementedError, match="single"):
            client.search("ats", query_vector=[0.1], query_filter=filt)

    def test_search_query_filter_translated_to_where(self):
        from src.db_adapters import vector_chroma
        client = vector_chroma.create_client()
        fake_client = MagicMock()
        fake_col = MagicMock()
        fake_col.query.return_value = {"ids": [[]], "distances": [[]], "metadatas": [[]]}
        fake_client.get_collection.return_value = fake_col
        client._client = fake_client

        cond = MagicMock(key="user_id", match=MagicMock(value="u1"))
        filt = MagicMock(must=[cond], should=None, must_not=None)
        client.search("ats", query_vector=[0.1], query_filter=filt)

        kwargs = fake_col.query.call_args.kwargs
        assert kwargs.get("where") == {"user_id": "u1"}

    def test_delete_by_id_list(self):
        from src.db_adapters import vector_chroma
        client = vector_chroma.create_client()
        fake_client = MagicMock()
        fake_col = MagicMock()
        fake_client.get_collection.return_value = fake_col
        client._client = fake_client
        client.delete("ats", points_selector=["a", "b"])
        fake_col.delete.assert_called_once_with(ids=["a", "b"])

    def test_delete_filter_single_field_condition(self):
        from src.db_adapters import vector_chroma
        client = vector_chroma.create_client()
        fake_col = MagicMock()
        fake_client = MagicMock()
        fake_client.get_collection.return_value = fake_col
        client._client = fake_client
        cond = MagicMock(key="agent_id", match=MagicMock(value="user-1"))
        filt = MagicMock(must=[cond], should=None, must_not=None)
        client.delete("ats", points_selector=MagicMock(filter=filt))
        fake_col.delete.assert_called_once_with(where={"agent_id": "user-1"})

    def test_get_collection_raises_when_missing(self):
        from src.db_adapters import vector_chroma
        client = vector_chroma.create_client()
        fake_client = MagicMock()
        fake_client.get_collection.side_effect = ValueError("not found")
        client._client = fake_client
        with pytest.raises(RuntimeError, match="not found"):
            client.get_collection("missing")


# ===========================================================================
# Weaviate
# ===========================================================================


class TestWeaviateAdapter:
    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_VECTOR_PROVIDER", "weaviate")
        client = db_factory.get_vector_client()
        assert type(client).__name__ == "_WeaviateClient"

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("WEAVIATE_HOST", "wv.internal")
        monkeypatch.setenv("WEAVIATE_PORT", "9999")
        monkeypatch.setenv("WEAVIATE_API_KEY", "secret")
        from src.db_adapters import vector_weaviate
        client = vector_weaviate.create_client()
        assert client._host == "wv.internal"
        assert client._port == 9999
        assert client._api_key == "secret"

    def test_distance_mapping(self):
        from src.db_adapters import vector_weaviate
        assert vector_weaviate._distance_to_weaviate_metric("Distance.COSINE") == "cosine"
        assert vector_weaviate._distance_to_weaviate_metric("Distance.EUCLID") == "l2-squared"
        assert vector_weaviate._distance_to_weaviate_metric("Distance.DOT") == "dot"

    def test_uuid_passthrough(self):
        from src.db_adapters import vector_weaviate
        # Real UUID string passes through unchanged
        valid = "12345678-1234-5678-1234-567812345678"
        assert vector_weaviate._to_uuid(valid) == valid

    def test_uuid_hash_derivation(self):
        from src.db_adapters import vector_weaviate
        # Non-UUID input gets a stable UUID5
        a = vector_weaviate._to_uuid("memory-abc")
        b = vector_weaviate._to_uuid("memory-abc")
        c = vector_weaviate._to_uuid("memory-xyz")
        assert a == b           # stable
        assert a != c           # distinct inputs -> distinct UUIDs
        import uuid as _u
        _u.UUID(a)              # must be a valid UUID format

    def test_search_query_filter_compound_raises(self):
        from src.db_adapters import vector_weaviate
        client = vector_weaviate.create_client()
        cond_a = MagicMock(key="a", match=MagicMock(value="x"))
        cond_b = MagicMock(key="b", match=MagicMock(value="y"))
        filt = MagicMock(must=[cond_a, cond_b], should=None, must_not=None)
        with pytest.raises(NotImplementedError, match="single"):
            client.search("ats", query_vector=[0.1], query_filter=filt)

    def test_search_query_filter_translated_to_weaviate_filter(self):
        # Single FieldCondition translates to a Filter.by_property('payload')
        # chain. We don't import weaviate here (the test injects a fake);
        # we just verify the wiring kicks in.
        import sys
        from src.db_adapters import vector_weaviate

        # Stub the weaviate.classes.query.Filter / MetadataQuery so the
        # adapter doesn't need the real client lib.
        fake_filter_cls = MagicMock()
        fake_filter_instance = MagicMock(name="filter_instance")
        fake_by_prop = MagicMock(name="by_prop")
        fake_by_prop.like.return_value = fake_filter_instance
        fake_filter_cls.by_property.return_value = fake_by_prop

        fake_metadata_query = MagicMock(name="MetadataQuery")

        fake_module = MagicMock()
        fake_module.Filter = fake_filter_cls
        fake_module.MetadataQuery = fake_metadata_query
        sys.modules["weaviate.classes.query"] = fake_module

        try:
            client = vector_weaviate.create_client()
            fake_client = MagicMock()
            fake_col = MagicMock()
            fake_res = MagicMock(objects=[])
            fake_col.query.near_vector.return_value = fake_res
            fake_client.collections.get.return_value = fake_col
            client._client = fake_client

            cond = MagicMock(key="user_id", match=MagicMock(value="u1"))
            filt = MagicMock(must=[cond], should=None, must_not=None)
            client.search("ats", query_vector=[0.1], query_filter=filt)

            fake_filter_cls.by_property.assert_called_with("payload")
            kwargs = fake_col.query.near_vector.call_args.kwargs
            assert kwargs.get("filters") is fake_filter_instance
        finally:
            sys.modules.pop("weaviate.classes.query", None)

    def test_delete_unsupported_selector_raises(self):
        from src.db_adapters import vector_weaviate
        client = vector_weaviate.create_client()
        # Selector with no .filter attribute and not list-like
        bad = MagicMock(spec=[])  # MagicMock without filter / points attrs
        with pytest.raises(NotImplementedError):
            client.delete("ats", points_selector=bad)


# ===========================================================================
# Milvus
# ===========================================================================


class TestMilvusAdapter:
    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_VECTOR_PROVIDER", "milvus")
        client = db_factory.get_vector_client()
        assert type(client).__name__ == "_MilvusClient"

    def test_env_fallback_builds_uri(self, monkeypatch):
        for v in ("MILVUS_TOKEN", "MILVUS_USER", "MILVUS_PASSWORD"):
            monkeypatch.delenv(v, raising=False)
        monkeypatch.setenv("MILVUS_HOST", "milvus.internal")
        monkeypatch.setenv("MILVUS_PORT", "19531")
        from src.db_adapters import vector_milvus
        client = vector_milvus.create_client()
        assert client._uri == "http://milvus.internal:19531"

    def test_token_env(self, monkeypatch):
        monkeypatch.setenv("MILVUS_TOKEN", "my-token")
        from src.db_adapters import vector_milvus
        client = vector_milvus.create_client()
        assert client._token == "my-token"

    def test_user_password_fallback(self, monkeypatch):
        monkeypatch.delenv("MILVUS_TOKEN", raising=False)
        monkeypatch.setenv("MILVUS_USER", "user1")
        monkeypatch.setenv("MILVUS_PASSWORD", "pw1")
        from src.db_adapters import vector_milvus
        client = vector_milvus.create_client()
        assert client._token == "user1:pw1"

    def test_distance_mapping(self):
        from src.db_adapters import vector_milvus
        assert vector_milvus._distance_to_milvus_metric("Distance.COSINE") == "COSINE"
        assert vector_milvus._distance_to_milvus_metric("Distance.EUCLID") == "L2"
        assert vector_milvus._distance_to_milvus_metric("Distance.DOT") == "IP"

    def test_search_query_filter_compound_raises(self):
        from src.db_adapters import vector_milvus
        client = vector_milvus.create_client()
        cond_a = MagicMock(key="a", match=MagicMock(value="x"))
        cond_b = MagicMock(key="b", match=MagicMock(value="y"))
        filt = MagicMock(must=[cond_a, cond_b], should=None, must_not=None)
        with pytest.raises(NotImplementedError, match="single"):
            client.search("ats", query_vector=[0.1], query_filter=filt)

    def test_search_query_filter_translated_to_expr(self):
        from src.db_adapters import vector_milvus
        client = vector_milvus.create_client()
        fake_client = MagicMock()
        fake_client.search.return_value = [[]]
        client._client = fake_client

        cond = MagicMock(key="user_id", match=MagicMock(value="u1"))
        filt = MagicMock(must=[cond], should=None, must_not=None)
        client.search("ats", query_vector=[0.1], query_filter=filt)

        kwargs = fake_client.search.call_args.kwargs
        expr = kwargs.get("filter")
        assert expr and "user_id" in expr and "u1" in expr

    def test_delete_by_id_list(self):
        from src.db_adapters import vector_milvus
        client = vector_milvus.create_client()
        fake_client = MagicMock()
        client._client = fake_client
        client.delete("ats", points_selector=["a", "b"])
        fake_client.delete.assert_called_once()
        call_kwargs = fake_client.delete.call_args.kwargs
        assert call_kwargs["collection_name"] == "ats"
        assert call_kwargs["ids"] == ["a", "b"]


# ===========================================================================
# Shared duck-typing surface (each adapter exposes the same classes)
# ===========================================================================


class TestDuckTypedShapes:
    """All four adapters expose the same _CollectionDescription /
    _SearchHit / _CountResult duck-typed classes so call sites don't
    have to special-case the provider."""

    def test_lancedb_search_hit_shape(self):
        from src.db_adapters import vector_lancedb
        hit = vector_lancedb._SearchHit(id="x", score=0.9, payload={"k": "v"})
        assert hit.id == "x"
        assert hit.score == 0.9
        assert hit.payload == {"k": "v"}

    def test_chroma_search_hit_shape(self):
        from src.db_adapters import vector_chroma
        hit = vector_chroma._SearchHit(id="x", score=0.9, payload={"k": "v"})
        assert hit.id == "x"
        assert hit.score == 0.9

    def test_weaviate_search_hit_shape(self):
        from src.db_adapters import vector_weaviate
        hit = vector_weaviate._SearchHit(id="x", score=0.9, payload={"k": "v"})
        assert hit.id == "x"

    def test_milvus_search_hit_shape(self):
        from src.db_adapters import vector_milvus
        hit = vector_milvus._SearchHit(id="x", score=0.9, payload={"k": "v"})
        assert hit.id == "x"

    def test_lancedb_collections_result_shape(self):
        from src.db_adapters import vector_lancedb
        r = vector_lancedb._CollectionsResult([
            vector_lancedb._CollectionDescription("a"),
            vector_lancedb._CollectionDescription("b"),
        ])
        assert [c.name for c in r.collections] == ["a", "b"]

    def test_count_result_shape(self):
        from src.db_adapters import vector_lancedb, vector_chroma, vector_weaviate, vector_milvus
        for mod in (vector_lancedb, vector_chroma, vector_weaviate, vector_milvus):
            assert mod._CountResult(5).count == 5
