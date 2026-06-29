"""Tests for the Phase 5 graph adapter trio: ArangoDB / NebulaGraph / Ladybug.

Each adapter translates the narrow Cypher subset RNR Enhanced Cognee's
call sites use into native AQL / nGQL / Ladybug calls. The underlying
SDKs are mocked so no live service is needed.

Coverage per adapter:
- Factory dispatch
- Env-var fallback chain
- Cypher subset translation (literal / count / detach-delete / return-all)
- NotImplementedError surfaces for unsupported features
- Async path raises clearly
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src import db_factory


# ===========================================================================
# Provider matrix
# ===========================================================================


class TestGraphProviderMatrix:
    def test_all_nine_providers_recognised(self):
        assert db_factory._VALID_GRAPH == {
            "arcadedb", "neo4j", "apache_age",
            "memgraph", "kuzu", "networkx_inmemory",
            "arangodb", "nebulagraph", "ladybug",
        }

    def test_arcadedb_still_default(self, monkeypatch):
        for v in ("ENHANCED_GRAPH_PROVIDER", "GRAPH_BACKEND"):
            monkeypatch.delenv(v, raising=False)
        assert db_factory.get_provider_summary()["graph"] == "arcadedb"


# ===========================================================================
# ArangoDB
# ===========================================================================


class TestArangoDBAdapter:
    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "arangodb")
        client = db_factory.get_graph_driver()
        assert type(client).__name__ == "_ArangoDriver"

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("ARANGO_HOST", "arango.internal")
        monkeypatch.setenv("ARANGO_PORT", "8530")
        monkeypatch.setenv("ARANGO_DB", "my_db")
        monkeypatch.setenv("ARANGO_USER", "myuser")
        monkeypatch.setenv("ARANGO_PASSWORD", "mypass")
        monkeypatch.setenv("ARANGO_COLLECTION_NAME", "custom_col")
        from src.db_adapters import graph_arangodb
        drv = graph_arangodb.create_driver()
        assert drv._host == "arango.internal"
        assert drv._port == 8530
        assert drv._database == "my_db"
        assert drv._user == "myuser"
        assert drv._password == "mypass"
        assert drv._collection == "custom_col"

    def test_async_returns_driver(self, monkeypatch):
        """Phase 5 update: async ArangoDB driver shipped via asyncio.to_thread."""
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "arangodb")
        driver = db_factory.get_async_graph_driver()
        assert type(driver).__name__ == "_AsyncArangoDriver"

    def test_translate_literal(self):
        from src.db_adapters.graph_arangodb import _translate_cypher
        aql, bind, alias = _translate_cypher("RETURN 1", "col")
        assert aql == "RETURN 1"
        assert bind == {}
        assert alias == "value"

    def test_translate_count(self):
        from src.db_adapters.graph_arangodb import _translate_cypher
        aql, bind, alias = _translate_cypher("MATCH (n) RETURN COUNT(n) AS c", "col")
        assert "COLLECT WITH COUNT" in aql
        assert bind == {"@col": "col"}
        assert alias == "c"

    def test_translate_count_default_alias(self):
        from src.db_adapters.graph_arangodb import _translate_cypher
        _, _, alias = _translate_cypher("MATCH (n) RETURN COUNT(n)", "col")
        assert alias == "count"

    def test_translate_detach_delete(self):
        from src.db_adapters.graph_arangodb import _translate_cypher
        aql, bind, alias = _translate_cypher("MATCH (n) DETACH DELETE n", "col")
        assert "REMOVE d IN @@col" in aql
        assert bind == {"@col": "col"}

    def test_translate_return_all(self):
        from src.db_adapters.graph_arangodb import _translate_cypher
        aql, bind, alias = _translate_cypher("MATCH (n) RETURN n", "col")
        assert "RETURN d" in aql
        assert alias == "n"

    def test_translate_unsupported_raises(self):
        from src.db_adapters.graph_arangodb import _translate_cypher
        with pytest.raises(NotImplementedError, match="not supported"):
            _translate_cypher("MATCH (a)-[r]->(b) RETURN a, b", "col")

    def test_translate_create_with_inline_props_raises(self):
        from src.db_adapters.graph_arangodb import _translate_cypher
        with pytest.raises(NotImplementedError, match="parameterised form"):
            _translate_cypher("CREATE (n:Person {name: 'alice'})", "col")

    def test_session_lifecycle_with_mocked_arango(self):
        """End-to-end: open session, run query, close. Mocked python-arango via sys.modules."""
        import sys
        from src.db_adapters import graph_arangodb

        fake_db = MagicMock()
        fake_db.has_collection.return_value = True
        fake_db.aql.execute.return_value = iter([1])
        fake_sys_db = MagicMock()
        fake_sys_db.has_database.return_value = True
        fake_client = MagicMock()
        fake_client.db.side_effect = (
            lambda dbname, **kw: fake_sys_db if dbname == "_system" else fake_db
        )

        # Inject a fake `arango` module so `from arango import ArangoClient`
        # inside _open_db() resolves to our mock.
        fake_arango_module = MagicMock()
        fake_arango_module.ArangoClient.return_value = fake_client
        with patch.dict(sys.modules, {"arango": fake_arango_module}):
            drv = graph_arangodb.create_driver()
            with drv.session() as s:
                r = s.run("RETURN 1")
        rec = r.single()
        assert rec[0] == 1


# ===========================================================================
# NebulaGraph
# ===========================================================================


class TestNebulaGraphAdapter:
    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "nebulagraph")
        client = db_factory.get_graph_driver()
        assert type(client).__name__ == "_NebulaDriver"

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("NEBULA_HOST", "nebula.internal")
        monkeypatch.setenv("NEBULA_PORT", "9670")
        monkeypatch.setenv("NEBULA_USER", "myuser")
        monkeypatch.setenv("NEBULA_PASSWORD", "mypass")
        monkeypatch.setenv("NEBULA_SPACE_NAME", "my_space")
        from src.db_adapters import graph_nebulagraph
        drv = graph_nebulagraph.create_driver()
        assert drv._host == "nebula.internal"
        assert drv._port == 9670
        assert drv._user == "myuser"
        assert drv._password == "mypass"
        assert drv._space_name == "my_space"

    def test_async_returns_driver(self, monkeypatch):
        """Phase 5 update: async NebulaGraph driver shipped via asyncio.to_thread."""
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "nebulagraph")
        driver = db_factory.get_async_graph_driver()
        assert type(driver).__name__ == "_AsyncNebulaDriver"

    def test_translate_literal_return(self):
        from src.db_adapters.graph_nebulagraph import _translate_cypher_to_ngql
        # `RETURN 1` becomes `YIELD 1` in nGQL
        assert _translate_cypher_to_ngql("RETURN 1") == "YIELD 1"
        assert _translate_cypher_to_ngql("RETURN 'ok'") == "YIELD 'ok'"

    def test_translate_match_passthrough(self):
        from src.db_adapters.graph_nebulagraph import _translate_cypher_to_ngql
        # MATCH-based queries pass through to NebulaGraph's openCypher mode
        out = _translate_cypher_to_ngql("MATCH (n) RETURN COUNT(n) AS c")
        assert out.startswith("MATCH")
        assert "COUNT(n)" in out

    def test_unwrap_value_with_string(self):
        from src.db_adapters.graph_nebulagraph import _unwrap_nebula_value
        val = MagicMock()
        val.as_int.side_effect = Exception("not int")
        val.as_double.side_effect = Exception("not double")
        val.as_bool.side_effect = Exception("not bool")
        val.as_string.return_value = "hello"
        assert _unwrap_nebula_value(val) == "hello"

    def test_unwrap_value_none(self):
        from src.db_adapters.graph_nebulagraph import _unwrap_nebula_value
        assert _unwrap_nebula_value(None) is None

    def test_session_run_rejects_parameters(self):
        """nGQL parameter binding differs from Bolt; reject for now."""
        from src.db_adapters import graph_nebulagraph
        drv = graph_nebulagraph.create_driver()
        session = graph_nebulagraph._NebulaSession(drv)
        with pytest.raises(NotImplementedError, match="parameterised"):
            session.run("RETURN $x", {"x": 1})


# ===========================================================================
# Ladybug
# ===========================================================================


class TestLadybugAdapter:
    def test_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "ladybug")
        client = db_factory.get_graph_driver()
        assert type(client).__name__ == "_LadybugDriver"

    def test_async_returns_driver(self, monkeypatch):
        """Phase 5 update: async Ladybug driver shipped via asyncio.to_thread."""
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "ladybug")
        driver = db_factory.get_async_graph_driver()
        assert type(driver).__name__ == "_AsyncLadybugDriver"

    @pytest.mark.asyncio
    async def test_async_session_lifecycle_no_graph_needed(self):
        """`RETURN 1` works through the async path without touching ladybug."""
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_async_driver()
        async with drv.session() as session:
            result = await session.run("RETURN 1")
        assert result.single()[0] == 1

    def test_env_db_path(self, monkeypatch):
        monkeypatch.setenv("LADYBUG_DB_PATH", "/tmp/ladybug.db")
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_driver()
        assert drv._db_path == "/tmp/ladybug.db"

    def test_session_return_literal_no_graph_needed(self):
        """`RETURN 1` doesn't touch the underlying graph; works without ladybug."""
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_driver()
        with drv.session() as s:
            result = s.run("RETURN 1")
        assert result.single()[0] == 1

    def test_session_count_with_mocked_graph(self):
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_driver()
        fake_graph = MagicMock()
        fake_graph.number_of_nodes = lambda: 42
        drv._graph_obj = fake_graph
        with drv.session() as s:
            result = s.run("MATCH (n) RETURN COUNT(n) AS c")
        assert result.single()["c"] == 42

    def test_session_detach_delete_clears_graph(self):
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_driver()
        fake_graph = MagicMock()
        drv._graph_obj = fake_graph
        with drv.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
        fake_graph.clear.assert_called_once()

    def test_session_return_all_iterates_nodes(self):
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_driver()
        fake_graph = MagicMock()
        fake_graph.nodes = MagicMock(return_value=["n1", "n2", "n3"])
        drv._graph_obj = fake_graph
        with drv.session() as s:
            result = s.run("MATCH (n) RETURN n")
        nodes = [r["n"] for r in result]
        assert nodes == ["n1", "n2", "n3"]

    def test_session_unsupported_query_raises(self):
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_driver()
        drv._graph_obj = MagicMock()
        with drv.session() as s:
            with pytest.raises(NotImplementedError, match="ladybug"):
                s.run("MATCH (a)-[r]->(b) RETURN a, b")

    def test_session_parameters_rejected(self):
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_driver()
        drv._graph_obj = MagicMock()
        with drv.session() as s:
            with pytest.raises(NotImplementedError, match="parameterised"):
                s.run("RETURN $x", {"x": 1})

    def test_parse_literal_int(self):
        from src.db_adapters.graph_ladybug import _parse_literal
        assert _parse_literal("42") == 42
        assert _parse_literal("3.14") == 3.14
        assert _parse_literal("'hello'") == "hello"
        assert _parse_literal('"hello"') == "hello"
        assert _parse_literal("true") is True
        assert _parse_literal("false") is False
        assert _parse_literal("null") is None

    def test_count_nodes_via_len(self):
        from src.db_adapters.graph_ladybug import _count_nodes

        class G:
            def __len__(self):
                return 7
        assert _count_nodes(G()) == 7

    def test_count_nodes_via_node_count_attr(self):
        from src.db_adapters.graph_ladybug import _count_nodes
        g = MagicMock()
        del g.number_of_nodes
        g.node_count = 5  # bare attribute, not callable
        assert _count_nodes(g) == 5

    def test_clear_graph_falls_through_attrs(self):
        from src.db_adapters.graph_ladybug import _clear_graph

        class G:
            def __init__(self):
                self.was_reset = False

            def reset(self):
                self.was_reset = True
        g = G()
        _clear_graph(g)
        assert g.was_reset


# ===========================================================================
# Driver close
# ===========================================================================


class TestDriverClose:
    def test_arangodb_close_idempotent(self):
        from src.db_adapters import graph_arangodb
        drv = graph_arangodb.create_driver()
        drv.close()
        drv.close()  # second call must not raise

    def test_nebulagraph_close_idempotent(self):
        from src.db_adapters import graph_nebulagraph
        drv = graph_nebulagraph.create_driver()
        drv.close()
        drv.close()

    def test_ladybug_close_clears_graph_ref(self):
        from src.db_adapters import graph_ladybug
        drv = graph_ladybug.create_driver()
        drv._graph_obj = MagicMock()
        drv.close()
        assert drv._graph_obj is None
