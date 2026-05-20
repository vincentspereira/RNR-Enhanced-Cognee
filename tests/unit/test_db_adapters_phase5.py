"""Phase 5 adapter tests: memgraph + kuzu + networkx + memcached + sqlite.

Coverage:
- Factory dispatch for the 5 new providers
- Adapter shapes (driver / session / record / result) where applicable
- Env-var fallbacks (MEMGRAPH_*, KUZU_DB_PATH, MEMCACHED_*, SQLITE_DB_PATH)
- NotImplementedError surfaces for unsupported features
- The narrow NetworkX Cypher parser (RETURN literal / COUNT / DETACH DELETE)
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src import db_factory
from src.db_adapters import (
    cache_memcached,
    graph_memgraph,
    graph_networkx_inmemory,
    relational_sqlite,
)


# ===========================================================================
# Factory dispatch -- new providers
# ===========================================================================


class TestNewGraphFactoryDispatch:
    def test_memgraph(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "memgraph")
        for v in ("MEMGRAPH_URI", "MEMGRAPH_USER", "MEMGRAPH_PASSWORD"):
            monkeypatch.delenv(v, raising=False)
        with patch("neo4j.GraphDatabase.driver", return_value=MagicMock()) as drv:
            db_factory.get_graph_driver()
        args, kwargs = drv.call_args
        assert args[0] == "bolt://localhost:7687"  # memgraph default differs
        assert kwargs["auth"] == ("", "")

    def test_memgraph_async(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "memgraph")
        with patch(
            "neo4j.AsyncGraphDatabase.driver", return_value=MagicMock()
        ) as drv:
            db_factory.get_async_graph_driver()
        assert drv.called

    def test_kuzu(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "kuzu")
        driver = db_factory.get_graph_driver()
        assert type(driver).__name__ == "_KuzuDriver"

    def test_kuzu_async_raises(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "kuzu")
        with pytest.raises(NotImplementedError, match="kuzu"):
            db_factory.get_async_graph_driver()

    def test_networkx_inmemory(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "networkx_inmemory")
        driver = db_factory.get_graph_driver()
        assert type(driver).__name__ == "_NXDriver"

    def test_networkx_async_raises(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "networkx_inmemory")
        with pytest.raises(NotImplementedError, match="networkx_inmemory"):
            db_factory.get_async_graph_driver()


class TestNewCacheFactoryDispatch:
    def test_memcached(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_CACHE_PROVIDER", "memcached")
        # Skip if pymemcache isn't installed in the test environment;
        # the factory dispatch line itself is what we want to cover.
        pymemcache = pytest.importorskip("pymemcache")
        client = db_factory.get_cache_client()
        assert type(client).__name__ == "_MemcachedAsyncClient"

    def test_sync_memcached(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_CACHE_PROVIDER", "memcached")
        pytest.importorskip("pymemcache")
        client = db_factory.get_sync_cache_client()
        assert type(client).__name__ == "_MemcachedAsyncClient"


class TestNewRelationalFactoryDispatch:
    @pytest.mark.asyncio
    async def test_sqlite(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "sqlite")
        pool = await db_factory.get_relational_pool()
        assert type(pool).__name__ == "_SQLitePool"


# ===========================================================================
# Memgraph env-var fallback chain
# ===========================================================================


class TestMemgraphEnvFallback:
    def test_explicit_kwargs_win(self, monkeypatch):
        with patch("neo4j.GraphDatabase.driver", return_value=MagicMock()) as drv:
            graph_memgraph.create_driver(
                uri="bolt://x:9000", user="u", password="p"
            )
        args, kwargs = drv.call_args
        assert args[0] == "bolt://x:9000"
        assert kwargs["auth"] == ("u", "p")

    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv("MEMGRAPH_URI", "bolt://memgraph-host:9999")
        monkeypatch.setenv("MEMGRAPH_USER", "alice")
        monkeypatch.setenv("MEMGRAPH_PASSWORD", "shh")
        with patch("neo4j.GraphDatabase.driver", return_value=MagicMock()) as drv:
            graph_memgraph.create_driver()
        args, kwargs = drv.call_args
        assert args[0] == "bolt://memgraph-host:9999"
        assert kwargs["auth"] == ("alice", "shh")


# ===========================================================================
# NetworkX in-memory Cypher parser
# ===========================================================================


class TestNetworkXInMemory:
    def test_return_int_literal(self):
        drv = graph_networkx_inmemory.create_driver()
        with drv.session() as s:
            result = s.run("RETURN 1")
        assert result.single()[0] == 1

    def test_return_string_literal(self):
        drv = graph_networkx_inmemory.create_driver()
        with drv.session() as s:
            result = s.run("RETURN 'hello'")
        assert result.single()[0] == "hello"

    def test_return_float_literal(self):
        drv = graph_networkx_inmemory.create_driver()
        with drv.session() as s:
            result = s.run("RETURN 3.14")
        assert result.single()[0] == 3.14

    def test_return_bool_literal(self):
        drv = graph_networkx_inmemory.create_driver()
        with drv.session() as s:
            result = s.run("RETURN true")
        assert result.single()[0] is True

    def test_return_null_literal(self):
        drv = graph_networkx_inmemory.create_driver()
        with drv.session() as s:
            result = s.run("RETURN null")
        assert result.single()[0] is None

    def test_count_empty_graph(self):
        drv = graph_networkx_inmemory.create_driver()
        with drv.session() as s:
            result = s.run("MATCH (n) RETURN COUNT(n) AS c")
        rec = result.single()
        assert rec["c"] == 0

    def test_count_default_alias(self):
        drv = graph_networkx_inmemory.create_driver()
        # Pre-seed a node directly on the underlying NX graph
        drv._graph.add_node(1)
        with drv.session() as s:
            result = s.run("MATCH (n) RETURN COUNT(n)")
        # No alias -> default "count"
        assert result.single()["count"] == 1

    def test_detach_delete_clears_graph(self):
        drv = graph_networkx_inmemory.create_driver()
        drv._graph.add_node(1)
        drv._graph.add_node(2)
        with drv.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
        assert drv._graph.number_of_nodes() == 0

    def test_unsupported_query_raises(self):
        drv = graph_networkx_inmemory.create_driver()
        with drv.session() as s:
            with pytest.raises(NotImplementedError, match="networkx_inmemory"):
                s.run("MATCH (n:Person) RETURN n.name")

    def test_parameterised_query_raises(self):
        drv = graph_networkx_inmemory.create_driver()
        with drv.session() as s:
            with pytest.raises(NotImplementedError):
                s.run("RETURN $x", {"x": 1})

    def test_close_resets_graph(self):
        drv = graph_networkx_inmemory.create_driver()
        drv._graph.add_node(1)
        drv.close()
        assert drv._graph.number_of_nodes() == 0


# ===========================================================================
# Memcached adapter (mocked pymemcache)
# ===========================================================================


@pytest.mark.skipif(
    "pymemcache" not in sys.modules and not pytest.importorskip(
        "pymemcache", reason="pymemcache not installed"
    ),
    reason="pymemcache not installed",
)
class TestMemcached:
    @pytest.mark.asyncio
    async def test_ping(self, monkeypatch):
        client = cache_memcached.create_async_client()
        # Patch the underlying sync pymemcache client
        client._client.version = MagicMock(return_value=b"1.6.0")
        assert await client.ping() is True

    @pytest.mark.asyncio
    async def test_set_then_get(self, monkeypatch):
        client = cache_memcached.create_async_client()
        store = {}

        def _set(key, value, expire=0):
            store[key] = value
            return True

        def _get(key):
            return store.get(key)

        client._client.set = _set
        client._client.get = _get
        await client.set("k", "v")
        assert await client.get("k") == "v"

    @pytest.mark.asyncio
    async def test_keys_raises_not_implemented(self):
        client = cache_memcached.create_async_client()
        with pytest.raises(NotImplementedError, match="memcached"):
            await client.keys("*")

    @pytest.mark.asyncio
    async def test_flushdb_raises_not_implemented(self):
        client = cache_memcached.create_async_client()
        with pytest.raises(NotImplementedError, match="flush_all"):
            await client.flushdb()

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self):
        client = cache_memcached.create_async_client()
        client._client.get = MagicMock(return_value=None)
        assert await client.get("missing") is None

    @pytest.mark.asyncio
    async def test_exists_counts_hits(self):
        client = cache_memcached.create_async_client()
        store = {"a": b"1", "b": b"2"}
        client._client.get = MagicMock(side_effect=lambda k: store.get(k))
        assert await client.exists("a", "b", "missing") == 2

    @pytest.mark.asyncio
    async def test_close_is_noop(self):
        client = cache_memcached.create_async_client()
        client._client.close = MagicMock()
        await client.close()
        client._client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_await_client_returns_self(self):
        client = cache_memcached.create_async_client()
        assert (await client) is client


# ===========================================================================
# SQLite relational adapter
# ===========================================================================


class TestSQLiteRelational:
    @pytest.mark.asyncio
    async def test_pool_creation(self):
        pool = await relational_sqlite.create_pool(database=":memory:")
        assert pool._db_path == ":memory:"

    @pytest.mark.asyncio
    async def test_acquire_yields_connection(self):
        # Use a real :memory: SQLite via aiosqlite if available
        aiosqlite = pytest.importorskip("aiosqlite")
        pool = await relational_sqlite.create_pool(database=":memory:")
        async with pool.acquire() as conn:
            assert type(conn).__name__ == "_SQLiteConnection"
            # Real round-trip through aiosqlite
            value = await conn.fetchval("SELECT 1")
            assert value == 1

    @pytest.mark.asyncio
    async def test_fetch_and_execute(self):
        pytest.importorskip("aiosqlite")
        pool = await relational_sqlite.create_pool(database=":memory:")
        async with pool.acquire() as conn:
            await conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
            await conn.execute("INSERT INTO t VALUES (?, ?)", 1, "a")
            await conn.execute("INSERT INTO t VALUES (?, ?)", 2, "b")
            rows = await conn.fetch("SELECT * FROM t ORDER BY id")
            assert len(rows) == 2
            assert rows[0][0] == 1
            assert rows[1][1] == "b"
            single = await conn.fetchrow("SELECT * FROM t WHERE id = ?", 1)
            assert single[1] == "a"

    @pytest.mark.asyncio
    async def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv("SQLITE_DB_PATH", "/tmp/test_enhanced_cognee.db")
        pool = await relational_sqlite.create_pool()
        assert pool._db_path == "/tmp/test_enhanced_cognee.db"

    @pytest.mark.asyncio
    async def test_pool_close_is_noop(self):
        pool = await relational_sqlite.create_pool(database=":memory:")
        await pool.close()  # must not raise


# ===========================================================================
# Provider matrix validation
# ===========================================================================


class TestProviderMatrix:
    def test_valid_graph_set(self):
        # 3 new providers (arangodb / nebulagraph / ladybug) added 2026-05-20
        # for query-language coverage (AQL / nGQL) and the all-Python fallback.
        expected = {
            "arcadedb", "neo4j", "apache_age",
            "memgraph", "kuzu", "networkx_inmemory",
            "arangodb", "nebulagraph", "ladybug",
        }
        assert db_factory._VALID_GRAPH == expected

    def test_valid_cache_set(self):
        # `redis_compat` added 2026-05-20 as a labelled alias of valkey
        # for wire-compatible Redis forks (KeyDB / Garnet / Dragonfly).
        assert db_factory._VALID_CACHE == {
            "valkey", "redis", "redis_compat", "in_memory", "memcached",
        }

    def test_valid_relational_set(self):
        # PR 10 (2026-05-20) added duckdb + mysql + mariadb to the matrix.
        assert db_factory._VALID_RELATIONAL == {
            "postgres", "postgresql", "sqlite",
            "duckdb", "mysql", "mariadb",
        }

    def test_default_summary_unchanged(self, monkeypatch):
        for v in (
            "ENHANCED_RELATIONAL_PROVIDER", "ENHANCED_VECTOR_PROVIDER",
            "ENHANCED_GRAPH_PROVIDER", "ENHANCED_CACHE_PROVIDER",
            "RELATIONAL_BACKEND", "VECTOR_BACKEND", "GRAPH_BACKEND", "CACHE_BACKEND",
        ):
            monkeypatch.delenv(v, raising=False)
        assert db_factory.get_provider_summary() == {
            "relational": "postgres",
            "vector": "qdrant",
            "graph": "arcadedb",
            "cache": "valkey",
        }
