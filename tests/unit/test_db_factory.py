"""Unit tests for src/db_factory.py and src/db_adapters/.

Phase 1 pluggable DB plumbing. These tests verify:
  - Env-var dispatch (ENHANCED_*_PROVIDER + legacy *_BACKEND aliases).
  - Default-provider behaviour (postgres / qdrant / neo4j / valkey).
  - Each adapter forwards to its underlying client constructor.
  - Unknown providers raise ValueError.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src import db_factory
from src.db_adapters import (
    cache_redis,
    cache_valkey,
    graph_arcadedb,
    graph_neo4j,
    relational_postgres,
    vector_qdrant,
)


# ---------------------------------------------------------------------------
# _resolve precedence and defaults
# ---------------------------------------------------------------------------


class TestResolve:
    def test_default_when_no_env(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_X_PROVIDER", raising=False)
        monkeypatch.delenv("X_BACKEND", raising=False)
        assert db_factory._resolve(
            "ENHANCED_X_PROVIDER", "X_BACKEND", "qdrant"
        ) == "qdrant"

    def test_canonical_env_wins(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_X_PROVIDER", "Foo")
        monkeypatch.setenv("X_BACKEND", "bar")
        assert db_factory._resolve(
            "ENHANCED_X_PROVIDER", "X_BACKEND", "qdrant"
        ) == "foo"

    def test_legacy_fallback(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_X_PROVIDER", raising=False)
        monkeypatch.setenv("X_BACKEND", "Bar")
        assert db_factory._resolve(
            "ENHANCED_X_PROVIDER", "X_BACKEND", "qdrant"
        ) == "bar"

    def test_legacy_none(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_X_PROVIDER", "Foo")
        assert db_factory._resolve("ENHANCED_X_PROVIDER", None, "qdrant") == "foo"

    def test_default_provider_summary(self, monkeypatch):
        for var in (
            "ENHANCED_RELATIONAL_PROVIDER", "ENHANCED_VECTOR_PROVIDER",
            "ENHANCED_GRAPH_PROVIDER", "ENHANCED_CACHE_PROVIDER",
            "RELATIONAL_BACKEND", "VECTOR_BACKEND", "GRAPH_BACKEND", "CACHE_BACKEND",
        ):
            monkeypatch.delenv(var, raising=False)
        summary = db_factory.get_provider_summary()
        assert summary == {
            "relational": "postgres",
            "vector": "qdrant",
            "graph": "arcadedb",
            "cache": "valkey",
        }


# ---------------------------------------------------------------------------
# get_relational_pool
# ---------------------------------------------------------------------------


class TestRelationalFactory:
    @pytest.mark.asyncio
    async def test_postgres_default(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_RELATIONAL_PROVIDER", raising=False)
        monkeypatch.delenv("RELATIONAL_BACKEND", raising=False)
        # Conftest sets POSTGRES_* test values; clear so we see the true defaults
        for var in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
                    "POSTGRES_USER", "POSTGRES_PASSWORD"):
            monkeypatch.delenv(var, raising=False)
        mock_pool = MagicMock()
        with patch(
            "asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)
        ) as create_pool:
            result = await db_factory.get_relational_pool(min_size=1, max_size=3)
        assert result is mock_pool
        create_pool.assert_awaited_once()
        kwargs = create_pool.await_args.kwargs
        assert kwargs["min_size"] == 1
        assert kwargs["max_size"] == 3
        assert kwargs["port"] == 25432  # default Enhanced port
        assert kwargs["database"] == "cognee_db"

    @pytest.mark.asyncio
    async def test_postgres_alias_postgresql(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "postgresql")
        with patch(
            "asyncpg.create_pool", new=AsyncMock(return_value=MagicMock())
        ):
            await db_factory.get_relational_pool()

    @pytest.mark.asyncio
    async def test_legacy_env_var(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_RELATIONAL_PROVIDER", raising=False)
        monkeypatch.setenv("RELATIONAL_BACKEND", "postgres")
        with patch(
            "asyncpg.create_pool", new=AsyncMock(return_value=MagicMock())
        ):
            await db_factory.get_relational_pool()

    @pytest.mark.asyncio
    async def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_RELATIONAL_PROVIDER", "sqlite")
        with pytest.raises(ValueError, match="ENHANCED_RELATIONAL_PROVIDER"):
            await db_factory.get_relational_pool()


# ---------------------------------------------------------------------------
# get_vector_client
# ---------------------------------------------------------------------------


class TestVectorFactory:
    def test_qdrant_default(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_VECTOR_PROVIDER", raising=False)
        mock_client = MagicMock()
        with patch(
            "qdrant_client.QdrantClient", return_value=mock_client
        ) as QC:
            result = db_factory.get_vector_client()
        assert result is mock_client
        QC.assert_called_once()
        kwargs = QC.call_args.kwargs
        assert kwargs["host"] == "localhost"
        assert kwargs["port"] == 26333

    def test_qdrant_url_form(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_VECTOR_PROVIDER", raising=False)
        with patch(
            "qdrant_client.QdrantClient", return_value=MagicMock()
        ) as QC:
            db_factory.get_vector_client(url="http://example:1234")
        kwargs = QC.call_args.kwargs
        assert kwargs["url"] == "http://example:1234"
        assert "host" not in kwargs
        assert "port" not in kwargs

    def test_qdrant_timeout_form(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_VECTOR_PROVIDER", raising=False)
        with patch(
            "qdrant_client.QdrantClient", return_value=MagicMock()
        ) as QC:
            db_factory.get_vector_client(timeout=5)
        assert QC.call_args.kwargs["timeout"] == 5

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_VECTOR_PROVIDER", "weaviate")
        with pytest.raises(ValueError, match="ENHANCED_VECTOR_PROVIDER"):
            db_factory.get_vector_client()


# ---------------------------------------------------------------------------
# get_graph_driver / get_async_graph_driver
# ---------------------------------------------------------------------------


class TestGraphFactory:
    def test_arcadedb_default(self, monkeypatch):
        """ArcadeDB is the default graph provider since Phase 2 (DR-11)."""
        monkeypatch.delenv("ENHANCED_GRAPH_PROVIDER", raising=False)
        monkeypatch.delenv("GRAPH_BACKEND", raising=False)
        for var in ("ARCADEDB_URI", "ARCADEDB_USER", "ARCADEDB_PASSWORD"):
            monkeypatch.delenv(var, raising=False)
        mock_driver = MagicMock()
        with patch(
            "neo4j.GraphDatabase.driver", return_value=mock_driver
        ) as drv:
            result = db_factory.get_graph_driver()
        assert result is mock_driver
        args, kwargs = drv.call_args
        assert args[0] == "bolt://localhost:27687"
        # ArcadeDB defaults to root admin (not neo4j)
        assert kwargs["auth"] == ("root", "cognee_password")

    def test_arcadedb_explicit_args(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_GRAPH_PROVIDER", raising=False)
        with patch("neo4j.GraphDatabase.driver", return_value=MagicMock()) as drv:
            db_factory.get_graph_driver(
                uri="bolt://arcadedb:7000", user="u", password="p"
            )
        args, kwargs = drv.call_args
        assert args[0] == "bolt://arcadedb:7000"
        assert kwargs["auth"] == ("u", "p")

    def test_async_arcadedb_default(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_GRAPH_PROVIDER", raising=False)
        with patch(
            "neo4j.AsyncGraphDatabase.driver", return_value=MagicMock()
        ) as drv:
            db_factory.get_async_graph_driver()
        assert drv.called

    def test_neo4j_pluggable(self, monkeypatch):
        """Neo4j retained as a pluggable alternative for legacy compat."""
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "neo4j")
        for var in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
            monkeypatch.delenv(var, raising=False)
        mock_driver = MagicMock()
        with patch(
            "neo4j.GraphDatabase.driver", return_value=mock_driver
        ) as drv:
            result = db_factory.get_graph_driver()
        assert result is mock_driver
        args, kwargs = drv.call_args
        assert args[0] == "bolt://localhost:27687"
        # Neo4j legacy adapter defaults to neo4j user
        assert kwargs["auth"] == ("neo4j", "cognee_password")

    def test_async_neo4j_pluggable(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "neo4j")
        with patch(
            "neo4j.AsyncGraphDatabase.driver", return_value=MagicMock()
        ) as drv:
            db_factory.get_async_graph_driver()
        assert drv.called

    def test_legacy_env_var(self, monkeypatch):
        """GRAPH_BACKEND legacy alias honoured at lower precedence."""
        monkeypatch.delenv("ENHANCED_GRAPH_PROVIDER", raising=False)
        monkeypatch.setenv("GRAPH_BACKEND", "neo4j")
        with patch("neo4j.GraphDatabase.driver", return_value=MagicMock()):
            db_factory.get_graph_driver()

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "apache_age")
        with pytest.raises(ValueError, match="ENHANCED_GRAPH_PROVIDER"):
            db_factory.get_graph_driver()

    def test_unknown_provider_raises_async(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_GRAPH_PROVIDER", "apache_age")
        with pytest.raises(ValueError, match="ENHANCED_GRAPH_PROVIDER"):
            db_factory.get_async_graph_driver()


# ---------------------------------------------------------------------------
# get_cache_client / get_sync_cache_client
# ---------------------------------------------------------------------------


class TestCacheFactory:
    def test_valkey_default(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_CACHE_PROVIDER", raising=False)
        monkeypatch.delenv("CACHE_BACKEND", raising=False)
        mock_client = MagicMock()
        with patch(
            "redis.asyncio.Redis", return_value=mock_client
        ) as R:
            result = db_factory.get_cache_client()
        assert result is mock_client
        kwargs = R.call_args.kwargs
        assert kwargs["host"] == "localhost"
        assert kwargs["port"] == 26379
        assert kwargs["decode_responses"] is True

    def test_redis_alias(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_CACHE_PROVIDER", "redis")
        with patch("redis.asyncio.Redis", return_value=MagicMock()) as R:
            db_factory.get_cache_client()
        assert R.called

    def test_sync_cache_default(self, monkeypatch):
        monkeypatch.delenv("ENHANCED_CACHE_PROVIDER", raising=False)
        with patch("redis.Redis", return_value=MagicMock()) as R:
            db_factory.get_sync_cache_client()
        kwargs = R.call_args.kwargs
        assert kwargs["host"] == "localhost"
        assert kwargs["port"] == 26379

    def test_sync_cache_redis(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_CACHE_PROVIDER", "redis")
        with patch("redis.Redis", return_value=MagicMock()) as R:
            db_factory.get_sync_cache_client()
        assert R.called

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_CACHE_PROVIDER", "memcached")
        with pytest.raises(ValueError, match="ENHANCED_CACHE_PROVIDER"):
            db_factory.get_cache_client()

    def test_sync_unknown_raises(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_CACHE_PROVIDER", "memcached")
        with pytest.raises(ValueError, match="ENHANCED_CACHE_PROVIDER"):
            db_factory.get_sync_cache_client()


# ---------------------------------------------------------------------------
# Adapter env-var fallbacks
# ---------------------------------------------------------------------------


class TestAdapterEnvFallbacks:
    def test_qdrant_env_fallback(self, monkeypatch):
        monkeypatch.setenv("QDRANT_HOST", "qhost")
        monkeypatch.setenv("QDRANT_PORT", "12345")
        monkeypatch.setenv("QDRANT_API_KEY", "secret")
        with patch("qdrant_client.QdrantClient", return_value=MagicMock()) as QC:
            vector_qdrant.create_client()
        kwargs = QC.call_args.kwargs
        assert kwargs["host"] == "qhost"
        assert kwargs["port"] == 12345
        assert kwargs["api_key"] == "secret"

    def test_neo4j_env_fallback(self, monkeypatch):
        monkeypatch.setenv("NEO4J_URI", "bolt://other:9999")
        monkeypatch.setenv("NEO4J_USER", "alice")
        monkeypatch.setenv("NEO4J_PASSWORD", "topsecret")
        with patch("neo4j.GraphDatabase.driver", return_value=MagicMock()) as drv:
            graph_neo4j.create_driver()
        args, kwargs = drv.call_args
        assert args[0] == "bolt://other:9999"
        assert kwargs["auth"] == ("alice", "topsecret")

    def test_async_neo4j_env_fallback(self, monkeypatch):
        monkeypatch.setenv("NEO4J_URI", "bolt://other:9999")
        with patch(
            "neo4j.AsyncGraphDatabase.driver", return_value=MagicMock()
        ) as drv:
            graph_neo4j.create_async_driver()
        args, _ = drv.call_args
        assert args[0] == "bolt://other:9999"

    def test_arcadedb_env_fallback(self, monkeypatch):
        monkeypatch.setenv("ARCADEDB_URI", "bolt://arc:9999")
        monkeypatch.setenv("ARCADEDB_USER", "bob")
        monkeypatch.setenv("ARCADEDB_PASSWORD", "shh")
        with patch("neo4j.GraphDatabase.driver", return_value=MagicMock()) as drv:
            graph_arcadedb.create_driver()
        args, kwargs = drv.call_args
        assert args[0] == "bolt://arc:9999"
        assert kwargs["auth"] == ("bob", "shh")

    def test_async_arcadedb_env_fallback(self, monkeypatch):
        monkeypatch.setenv("ARCADEDB_URI", "bolt://arc:9999")
        with patch(
            "neo4j.AsyncGraphDatabase.driver", return_value=MagicMock()
        ) as drv:
            graph_arcadedb.create_async_driver()
        args, _ = drv.call_args
        assert args[0] == "bolt://arc:9999"

    def test_arcadedb_default_user_is_root(self, monkeypatch):
        """ArcadeDB's built-in admin is root, not neo4j."""
        for var in ("ARCADEDB_URI", "ARCADEDB_USER", "ARCADEDB_PASSWORD"):
            monkeypatch.delenv(var, raising=False)
        with patch("neo4j.GraphDatabase.driver", return_value=MagicMock()) as drv:
            graph_arcadedb.create_driver()
        _, kwargs = drv.call_args
        assert kwargs["auth"][0] == "root"

    def test_valkey_env_fallback(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "rhost")
        monkeypatch.setenv("REDIS_PORT", "54321")
        monkeypatch.setenv("REDIS_PASSWORD", "shh")
        with patch("redis.asyncio.Redis", return_value=MagicMock()) as R:
            cache_valkey.create_async_client()
        kwargs = R.call_args.kwargs
        assert kwargs["host"] == "rhost"
        assert kwargs["port"] == 54321
        assert kwargs["password"] == "shh"

    def test_valkey_empty_password_treated_as_none(self, monkeypatch):
        monkeypatch.setenv("REDIS_PASSWORD", "")
        with patch("redis.asyncio.Redis", return_value=MagicMock()) as R:
            cache_valkey.create_async_client()
        assert R.call_args.kwargs["password"] is None

    def test_sync_valkey_env_fallback(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "rhost")
        with patch("redis.Redis", return_value=MagicMock()) as R:
            cache_valkey.create_sync_client()
        assert R.call_args.kwargs["host"] == "rhost"

    def test_cache_redis_alias_module(self, monkeypatch):
        with patch("redis.asyncio.Redis", return_value=MagicMock()) as R:
            cache_redis.create_async_client()
        assert R.called

    def test_cache_redis_alias_sync(self, monkeypatch):
        with patch("redis.Redis", return_value=MagicMock()) as R:
            cache_redis.create_sync_client()
        assert R.called

    @pytest.mark.asyncio
    async def test_postgres_env_fallback(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_HOST", "phost")
        monkeypatch.setenv("POSTGRES_PORT", "55432")
        monkeypatch.setenv("POSTGRES_DB", "mydb")
        monkeypatch.setenv("POSTGRES_USER", "u")
        monkeypatch.setenv("POSTGRES_PASSWORD", "p")
        with patch(
            "asyncpg.create_pool", new=AsyncMock(return_value=MagicMock())
        ) as cp:
            await relational_postgres.create_pool()
        kwargs = cp.await_args.kwargs
        assert kwargs["host"] == "phost"
        assert kwargs["port"] == 55432
        assert kwargs["database"] == "mydb"
        assert kwargs["user"] == "u"
        assert kwargs["password"] == "p"
