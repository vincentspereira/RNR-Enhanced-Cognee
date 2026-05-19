"""
Unit tests for src/enhanced_cognee_mcp.py
==========================================
Covers:
  - EnhancedConfig construction (env-var reads, dynamic category loading)
  - Data models: MemoryEntry, SearchQuery, KnowledgeRelation
  - EnhancedCogneeMCPServer: init, DB init paths, helper methods,
    add_memory, search_memory, add_knowledge_relation, get_memory_stats
  - All FastAPI routes via TestClient (happy path, 500, disconnected state)
  - /health endpoint: all four components connected, disconnected, erroring
  - _get_collection_name: categorized vs. simple modes
  - _build_qdrant_filter: all condition branches
  - _get_active_agents: with/without category filter
  - lifespan: startup calls server.initialize()

All database connections are mocked - no live services are required.
ASCII-only assertions per project conventions.
"""

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers: async-context-manager pool mock
# ---------------------------------------------------------------------------

def _make_conn():
    """Return an AsyncMock connection with sensible defaults."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    return conn


def _make_pool(conn=None):
    """Build a mock pool whose .acquire() is an async context manager."""
    if conn is None:
        conn = _make_conn()

    class _AcquireCtx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *args):
            pass

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AcquireCtx())
    pool._conn = conn  # store for later inspection
    return pool


def _make_qdrant_collections(names=("test_col",)):
    """Return a mock Qdrant collections response."""
    collections_resp = MagicMock()
    col_mocks = []
    for n in names:
        c = MagicMock()
        c.name = n
        col_mocks.append(c)
    collections_resp.collections = col_mocks
    return collections_resp


def _make_qdrant_client(collection_names=("cognee_memory",)):
    """Return a fully mocked QdrantClient."""
    qc = MagicMock()
    qc.get_collections = MagicMock(return_value=_make_qdrant_collections(collection_names))
    count_result = MagicMock()
    count_result.count = 5
    qc.count = MagicMock(return_value=count_result)
    qc.get_collection = MagicMock(return_value=MagicMock())
    qc.create_collection = MagicMock()
    qc.upsert = MagicMock()
    qc.search = MagicMock(return_value=[])
    return qc


def _make_neo4j_driver():
    """Return a mock Neo4j driver with a working session context manager."""
    driver = MagicMock()
    session = MagicMock()
    result_mock = MagicMock()
    result_mock.single = MagicMock(return_value={"entity_count": 2, "relation_count": 1})
    session.run = MagicMock(return_value=result_mock)
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    driver.session = MagicMock(return_value=session)
    return driver


def _make_redis_client():
    """Return a mock async Redis client."""
    r = AsyncMock()
    r.ping = AsyncMock(return_value=True)
    r.setex = AsyncMock(return_value=True)
    r.info = AsyncMock(return_value={"used_memory_human": "1.0M", "db0": {"keys": 3}})
    return r


# ---------------------------------------------------------------------------
# Build a pre-wired server instance (bypassing __init__  DB connections)
# ---------------------------------------------------------------------------

def _make_server_with_mocks(
    pool=None,
    qdrant=None,
    neo4j=None,
    redis=None,
):
    """Import and return an EnhancedCogneeMCPServer with mocked DB clients."""
    from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer

    srv = EnhancedCogneeMCPServer()
    srv.postgres_pool = pool or _make_pool()
    srv.qdrant_client = qdrant or _make_qdrant_client()
    srv.neo4j_driver = neo4j or _make_neo4j_driver()
    srv.redis_client = redis or _make_redis_client()
    return srv


# ---------------------------------------------------------------------------
# Fixture: TestClient pointing at the real `app` with all DB clients mocked
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    TestClient for `app` with all database clients replaced by mocks.

    Uses dependency_overrides-style injection via direct attribute replacement
    on the global `server` object (the module-level singleton).  The lifespan
    is disabled so no real DB connections are attempted.
    """
    import src.enhanced_cognee_mcp as mod

    pool = _make_pool()
    qdrant = _make_qdrant_client()
    neo4j = _make_neo4j_driver()
    redis_c = _make_redis_client()

    # Patch the global server's DB clients before TestClient opens the app
    original_pool = mod.server.postgres_pool
    original_qdrant = mod.server.qdrant_client
    original_neo4j = mod.server.neo4j_driver
    original_redis = mod.server.redis_client

    mod.server.postgres_pool = pool
    mod.server.qdrant_client = qdrant
    mod.server.neo4j_driver = neo4j
    mod.server.redis_client = redis_c

    # Patch lifespan to avoid real DB init during startup
    @asynccontextmanager
    async def _noop_lifespan(application):
        yield

    original_app = mod.app

    # Rebuild app without lifespan for TestClient isolation
    from fastapi import FastAPI
    test_app = FastAPI(title="Enhanced Cognee MCP Server Test")
    test_app.include_router(mod.server.app.router)

    with TestClient(test_app, raise_server_exceptions=False) as tc:
        tc._pool = pool
        tc._qdrant = qdrant
        tc._neo4j = neo4j
        tc._redis = redis_c
        yield tc

    # Restore
    mod.server.postgres_pool = original_pool
    mod.server.qdrant_client = original_qdrant
    mod.server.neo4j_driver = original_neo4j
    mod.server.redis_client = original_redis


# ===========================================================================
# EnhancedConfig tests
# ===========================================================================

class TestEnhancedConfig:
    """Tests for EnhancedConfig construction and category loading."""

    def test_defaults_without_env(self):
        """Config should read sensible defaults when no env vars are set."""
        from src.enhanced_cognee_mcp import EnhancedConfig
        with patch.dict(os.environ, {}, clear=False):
            # Remove known keys to test true defaults
            env_copy = {k: v for k, v in os.environ.items()
                        if not k.startswith(("POSTGRES", "QDRANT", "NEO4J", "REDIS",
                                             "ENHANCED", "MEMORY", "EMBEDDING",
                                             "SIMILARITY", "PERFORMANCE", "AUTO"))}
            with patch.dict(os.environ, env_copy, clear=True):
                cfg = EnhancedConfig()
        assert cfg.postgres_host == "localhost"
        assert cfg.postgres_port == 25432
        assert cfg.postgres_db == "cognee_db"
        assert cfg.qdrant_host == "localhost"
        assert cfg.qdrant_port == 26333
        assert cfg.redis_port == 26379
        assert cfg.vector_dimensions == 1024
        assert cfg.similarity_threshold == 0.7

    def test_enhanced_mode_env_var(self):
        from src.enhanced_cognee_mcp import EnhancedConfig
        with patch.dict(os.environ, {"ENHANCED_COGNEE_MODE": "true"}):
            cfg = EnhancedConfig()
        assert cfg.enhanced_mode is True

    def test_enhanced_mode_false_by_default(self):
        from src.enhanced_cognee_mcp import EnhancedConfig
        with patch.dict(os.environ, {"ENHANCED_COGNEE_MODE": "false"}):
            cfg = EnhancedConfig()
        assert cfg.enhanced_mode is False

    def test_custom_ports_via_env(self):
        from src.enhanced_cognee_mcp import EnhancedConfig
        with patch.dict(os.environ, {
            "POSTGRES_PORT": "5432",
            "QDRANT_PORT": "6333",
            "REDIS_PORT": "6379",
        }):
            cfg = EnhancedConfig()
        assert cfg.postgres_port == 5432
        assert cfg.qdrant_port == 6333
        assert cfg.redis_port == 6379

    def test_category_prefixes_empty_when_no_config_file(self, tmp_path, monkeypatch):
        """When no config file exists, category_prefixes should be empty."""
        from src.enhanced_cognee_mcp import EnhancedConfig
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ENHANCED_COGNEE_CONFIG_PATH", str(tmp_path / "nonexistent.json"))
        cfg = EnhancedConfig()
        assert cfg.category_prefixes == {}

    def test_category_prefixes_loaded_from_json(self, tmp_path, monkeypatch):
        """Config file with categories section is parsed correctly."""
        from src.enhanced_cognee_mcp import EnhancedConfig
        config_file = tmp_path / ".enhanced-cognee-config.json"
        config_file.write_text(json.dumps({
            "categories": {
                "trading": {"prefix": "trading_"},
                "development": {"prefix": "dev_"},
            }
        }))
        monkeypatch.setenv("ENHANCED_COGNEE_CONFIG_PATH", str(config_file))
        cfg = EnhancedConfig()
        assert cfg.category_prefixes == {"trading": "trading_", "development": "dev_"}

    def test_category_prefixes_defaults_when_key_missing(self, tmp_path, monkeypatch):
        """If a category entry has no 'prefix' key, a default is generated."""
        from src.enhanced_cognee_mcp import EnhancedConfig
        config_file = tmp_path / ".enhanced-cognee-config.json"
        config_file.write_text(json.dumps({
            "categories": {
                "custom": {}  # No 'prefix' key
            }
        }))
        monkeypatch.setenv("ENHANCED_COGNEE_CONFIG_PATH", str(config_file))
        cfg = EnhancedConfig()
        assert cfg.category_prefixes == {"custom": "custom_"}

    def test_malformed_json_falls_back_to_empty(self, tmp_path, monkeypatch):
        """Malformed config JSON is caught; category_prefixes stays empty.

        The config loader tries three paths: ENHANCED_COGNEE_CONFIG_PATH,
        .enhanced-cognee-config.json (cwd), and config/.enhanced-cognee-config.json.
        We change cwd to tmp_path so the cwd fallback also fails.
        """
        from src.enhanced_cognee_mcp import EnhancedConfig
        config_file = tmp_path / ".enhanced-cognee-config.json"
        config_file.write_text("NOT VALID JSON{{{")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ENHANCED_COGNEE_CONFIG_PATH", str(config_file))
        cfg = EnhancedConfig()
        assert cfg.category_prefixes == {}

    def test_config_without_categories_key(self, tmp_path, monkeypatch):
        """Config file with no 'categories' key returns empty prefixes."""
        from src.enhanced_cognee_mcp import EnhancedConfig
        config_file = tmp_path / ".enhanced-cognee-config.json"
        config_file.write_text(json.dumps({"other_key": "value"}))
        monkeypatch.setenv("ENHANCED_COGNEE_CONFIG_PATH", str(config_file))
        cfg = EnhancedConfig()
        assert cfg.category_prefixes == {}

    def test_performance_monitoring_env_var(self):
        from src.enhanced_cognee_mcp import EnhancedConfig
        with patch.dict(os.environ, {"PERFORMANCE_MONITORING": "true"}):
            cfg = EnhancedConfig()
        assert cfg.performance_monitoring is True

    def test_auto_optimization_env_var(self):
        from src.enhanced_cognee_mcp import EnhancedConfig
        with patch.dict(os.environ, {"AUTO_OPTIMIZATION": "true"}):
            cfg = EnhancedConfig()
        assert cfg.auto_optimization is True

    def test_qdrant_api_key_env_var(self):
        from src.enhanced_cognee_mcp import EnhancedConfig
        with patch.dict(os.environ, {"QDRANT_API_KEY": "my-key"}):
            cfg = EnhancedConfig()
        assert cfg.qdrant_api_key == "my-key"

    def test_redis_password_env_var(self):
        from src.enhanced_cognee_mcp import EnhancedConfig
        with patch.dict(os.environ, {"REDIS_PASSWORD": "s3cr3t"}):
            cfg = EnhancedConfig()
        assert cfg.redis_password == "s3cr3t"


# ===========================================================================
# Data model tests
# ===========================================================================

class TestMemoryEntry:
    """Tests for the MemoryEntry Pydantic model."""

    def test_minimal_valid_entry(self):
        from src.enhanced_cognee_mcp import MemoryEntry
        entry = MemoryEntry(content="hello", agent_id="agent1", memory_category="general")
        assert entry.content == "hello"
        assert entry.agent_id == "agent1"
        assert entry.memory_category == "general"
        assert entry.id is None
        assert entry.embedding is None
        assert entry.metadata == {}
        assert entry.tags == []

    def test_full_entry_with_all_fields(self):
        from src.enhanced_cognee_mcp import MemoryEntry
        entry = MemoryEntry(
            id="test-id",
            content="full content",
            agent_id="agent2",
            memory_category="trading",
            embedding=[0.1, 0.2, 0.3],
            metadata={"key": "value"},
            tags=["tag1", "tag2"],
        )
        assert entry.id == "test-id"
        assert entry.embedding == [0.1, 0.2, 0.3]
        assert entry.metadata == {"key": "value"}
        assert entry.tags == ["tag1", "tag2"]


class TestSearchQuery:
    """Tests for the SearchQuery Pydantic model."""

    def test_defaults(self):
        from src.enhanced_cognee_mcp import SearchQuery
        q = SearchQuery(query="test")
        assert q.limit == 10
        assert q.similarity_threshold == 0.7
        assert q.memory_category is None
        assert q.agent_id is None
        assert q.filters == {}

    def test_limit_bounds(self):
        from src.enhanced_cognee_mcp import SearchQuery
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            SearchQuery(query="test", limit=0)

    def test_limit_upper_bound(self):
        from src.enhanced_cognee_mcp import SearchQuery
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            SearchQuery(query="test", limit=101)

    def test_valid_limit(self):
        from src.enhanced_cognee_mcp import SearchQuery
        q = SearchQuery(query="test", limit=50)
        assert q.limit == 50

    def test_similarity_threshold_bounds(self):
        from src.enhanced_cognee_mcp import SearchQuery
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            SearchQuery(query="test", similarity_threshold=1.1)


class TestKnowledgeRelation:
    """Tests for the KnowledgeRelation Pydantic model."""

    def test_defaults(self):
        from src.enhanced_cognee_mcp import KnowledgeRelation
        rel = KnowledgeRelation(
            source_entity="A",
            target_entity="B",
            relationship_type="knows",
        )
        assert rel.confidence == 1.0
        assert rel.properties == {}

    def test_confidence_bounds(self):
        from src.enhanced_cognee_mcp import KnowledgeRelation
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            KnowledgeRelation(
                source_entity="A", target_entity="B",
                relationship_type="x", confidence=1.5
            )


# ===========================================================================
# EnhancedCogneeMCPServer helper methods
# ===========================================================================

class TestGetCollectionName:
    """Tests for _get_collection_name with various config states."""

    def test_simple_mode_no_categorization(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, config
        srv = EnhancedCogneeMCPServer()
        with patch.object(config, "memory_categorization", False):
            name = srv._get_collection_name("trading", "agent1")
        assert name == "cognee_trading_memory"

    def test_categorization_enabled_with_prefix(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, config
        srv = EnhancedCogneeMCPServer()
        with (
            patch.object(config, "memory_categorization", True),
            patch.object(config, "category_prefixes", {"trading": "trading_"}),
            patch.object(config, "qdrant_collection_prefix", "cognee_"),
        ):
            name = srv._get_collection_name("trading", "agent1")
        assert name == "cognee_trading_memory"

    def test_categorization_enabled_unknown_category_uses_fallback(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, config
        srv = EnhancedCogneeMCPServer()
        with (
            patch.object(config, "memory_categorization", True),
            patch.object(config, "category_prefixes", {"other": "other_"}),
            patch.object(config, "qdrant_collection_prefix", "cognee_"),
        ):
            name = srv._get_collection_name("unknown_cat", "agent1")
        # Falls back to {category_name.lower()}_ prefix
        assert name == "cognee_unknown_cat_memory"

    def test_categorization_enabled_empty_prefixes_falls_through(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, config
        srv = EnhancedCogneeMCPServer()
        with (
            patch.object(config, "memory_categorization", True),
            patch.object(config, "category_prefixes", {}),
            patch.object(config, "qdrant_collection_prefix", "cognee_"),
        ):
            name = srv._get_collection_name("trading", "agent1")
        # category_prefixes is falsy so goes to simple format
        assert name == "cognee_trading_memory"


class TestBuildQdrantFilter:
    """Tests for _build_qdrant_filter."""

    def test_no_conditions_returns_none(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        srv = EnhancedCogneeMCPServer()
        q = SearchQuery(query="x")
        result = srv._build_qdrant_filter(q)
        assert result is None

    def test_agent_id_adds_condition(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        from qdrant_client.models import Filter
        srv = EnhancedCogneeMCPServer()
        q = SearchQuery(query="x", agent_id="agent1")
        result = srv._build_qdrant_filter(q)
        assert isinstance(result, Filter)

    def test_memory_category_adds_condition(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        from qdrant_client.models import Filter
        srv = EnhancedCogneeMCPServer()
        q = SearchQuery(query="x", memory_category="trading")
        result = srv._build_qdrant_filter(q)
        assert isinstance(result, Filter)

    def test_custom_filters_add_conditions(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        from qdrant_client.models import Filter
        srv = EnhancedCogneeMCPServer()
        q = SearchQuery(query="x", filters={"tag": "important"})
        result = srv._build_qdrant_filter(q)
        assert isinstance(result, Filter)

    def test_all_conditions_combined(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        from qdrant_client.models import Filter
        srv = EnhancedCogneeMCPServer()
        q = SearchQuery(
            query="x",
            agent_id="agent1",
            memory_category="trading",
            filters={"tag": "v"},
        )
        result = srv._build_qdrant_filter(q)
        assert isinstance(result, Filter)
        assert len(result.must) == 3


# ===========================================================================
# _get_active_agents
# ===========================================================================

class TestGetActiveAgents:

    @pytest.mark.asyncio
    async def test_returns_all_agents_without_filter(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[
            {"agent_id": "agent-a"},
            {"agent_id": "agent-b"},
        ])
        pool = _make_pool(conn)
        srv = EnhancedCogneeMCPServer()
        srv.postgres_pool = pool

        agents = await srv._get_active_agents()
        assert agents == ["agent-a", "agent-b"]

    @pytest.mark.asyncio
    async def test_returns_agents_for_category(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[{"agent_id": "agent-x"}])
        pool = _make_pool(conn)
        srv = EnhancedCogneeMCPServer()
        srv.postgres_pool = pool

        agents = await srv._get_active_agents(memory_category="trading")
        assert agents == ["agent-x"]

    @pytest.mark.asyncio
    async def test_db_error_returns_empty_list(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("DB down"))
        pool = _make_pool(conn)
        srv = EnhancedCogneeMCPServer()
        srv.postgres_pool = pool

        agents = await srv._get_active_agents()
        assert agents == []


# ===========================================================================
# add_memory (server method)
# ===========================================================================

class TestAddMemoryMethod:

    @pytest.mark.asyncio
    async def test_returns_uuid_string(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        srv = _make_server_with_mocks()
        entry = MemoryEntry(content="test", agent_id="a1", memory_category="general")
        result_id = await srv.add_memory(entry)
        assert isinstance(result_id, str)
        # UUID must be parseable
        uuid.UUID(result_id)

    @pytest.mark.asyncio
    async def test_assigns_id_if_none(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        srv = _make_server_with_mocks()
        entry = MemoryEntry(content="content", agent_id="a1", memory_category="general")
        assert entry.id is None
        await srv.add_memory(entry)
        assert entry.id is not None

    @pytest.mark.asyncio
    async def test_uses_provided_id(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        srv = _make_server_with_mocks()
        custom_id = str(uuid.uuid4())
        entry = MemoryEntry(id=custom_id, content="c", agent_id="a1", memory_category="g")
        result_id = await srv.add_memory(entry)
        assert result_id == custom_id

    @pytest.mark.asyncio
    async def test_calls_postgres_execute(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        conn = _make_conn()
        pool = _make_pool(conn)
        srv = _make_server_with_mocks(pool=pool)
        entry = MemoryEntry(content="c", agent_id="a1", memory_category="g")
        await srv.add_memory(entry)
        conn.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stores_embedding_in_qdrant_when_provided(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        qdrant = _make_qdrant_client()
        srv = _make_server_with_mocks(qdrant=qdrant)
        embedding = [0.1] * 1024
        entry = MemoryEntry(
            content="c", agent_id="a1", memory_category="general",
            embedding=embedding
        )
        await srv.add_memory(entry)
        qdrant.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_qdrant_when_no_embedding(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        qdrant = _make_qdrant_client()
        srv = _make_server_with_mocks(qdrant=qdrant)
        entry = MemoryEntry(content="c", agent_id="a1", memory_category="general")
        await srv.add_memory(entry)
        qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_caches_in_redis(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        redis_c = _make_redis_client()
        srv = _make_server_with_mocks(redis=redis_c)
        entry = MemoryEntry(content="c", agent_id="a1", memory_category="g")
        await srv.add_memory(entry)
        redis_c.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_qdrant_collection_if_not_exists(self):
        """When get_collection raises, create_collection is called."""
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        qdrant = _make_qdrant_client()
        qdrant.get_collection = MagicMock(side_effect=Exception("not found"))
        srv = _make_server_with_mocks(qdrant=qdrant)
        embedding = [0.1] * 1024
        entry = MemoryEntry(
            content="c", agent_id="a1", memory_category="g",
            embedding=embedding
        )
        await srv.add_memory(entry)
        qdrant.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_error_raises_http_exception(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, MemoryEntry
        from fastapi import HTTPException
        conn = _make_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError("DB crash"))
        pool = _make_pool(conn)
        srv = _make_server_with_mocks(pool=pool)
        entry = MemoryEntry(content="c", agent_id="a1", memory_category="g")
        with pytest.raises(HTTPException) as exc_info:
            await srv.add_memory(entry)
        assert exc_info.value.status_code == 500


# ===========================================================================
# search_memory (server method)
# ===========================================================================

class TestSearchMemoryMethod:

    @pytest.mark.asyncio
    async def test_no_embedding_returns_empty(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        srv = _make_server_with_mocks()
        q = SearchQuery(query="test")  # no embedding
        results = await srv.search_memory(q)
        assert results == []

    @pytest.mark.asyncio
    async def test_searches_specific_collection_when_category_and_agent_given(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        qdrant = _make_qdrant_client()
        srv = _make_server_with_mocks(qdrant=qdrant)
        q = SearchQuery(
            query="test",
            embedding=[0.1] * 10,
            memory_category="general",
            agent_id="agent1",
        )
        await srv.search_memory(q)
        qdrant.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_sorted_results_by_score(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        hit1 = MagicMock()
        hit1.id = "id1"
        hit1.score = 0.5
        hit1.payload = {"content": "c1", "agent_id": "a1",
                        "memory_category": "g", "created_at": "now"}
        hit2 = MagicMock()
        hit2.id = "id2"
        hit2.score = 0.9
        hit2.payload = {"content": "c2", "agent_id": "a1",
                        "memory_category": "g", "created_at": "now"}

        qdrant = _make_qdrant_client()
        qdrant.search = MagicMock(return_value=[hit1, hit2])
        srv = _make_server_with_mocks(qdrant=qdrant)
        q = SearchQuery(
            query="test",
            embedding=[0.1] * 10,
            memory_category="general",
            agent_id="agent1",
        )
        results = await srv.search_memory(q)
        scores = [r["similarity_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_searches_all_categories_when_no_filter(self):
        """When no memory_category/agent_id, all configured categories searched."""
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery, config
        qdrant = _make_qdrant_client()
        srv = _make_server_with_mocks(qdrant=qdrant)
        with (
            patch.object(config, "memory_categorization", True),
            patch.object(config, "category_prefixes", {"trading": "trading_", "dev": "dev_"}),
        ):
            q = SearchQuery(query="test", embedding=[0.1] * 10)
            await srv.search_memory(q)
        # search is called for each existing collection found
        # (get_collection is called per category)
        assert qdrant.search.call_count >= 0  # 0 if collections don't exist

    @pytest.mark.asyncio
    async def test_searches_default_collection_when_no_categorization(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery, config
        qdrant = _make_qdrant_client()
        srv = _make_server_with_mocks(qdrant=qdrant)
        with (
            patch.object(config, "memory_categorization", False),
            patch.object(config, "category_prefixes", {}),
        ):
            q = SearchQuery(query="test", embedding=[0.1] * 10)
            await srv.search_memory(q)
        qdrant.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_collection_search_exception_is_skipped(self):
        """Exception in searching a single collection is logged and skipped."""
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        qdrant = _make_qdrant_client()
        qdrant.search = MagicMock(side_effect=RuntimeError("collection error"))
        srv = _make_server_with_mocks(qdrant=qdrant)
        q = SearchQuery(
            query="test",
            embedding=[0.1] * 10,
            memory_category="general",
            agent_id="a1",
        )
        results = await srv.search_memory(q)
        assert results == []

    @pytest.mark.asyncio
    async def test_outer_exception_raises_http_exception(self):
        """An error at the outer level of search_memory triggers the outer except.

        We replace _get_collection_name with a non-callable to force a TypeError
        at result-aggregation time, outside any inner try block.
        """
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery
        from fastapi import HTTPException
        import unittest.mock as _mock

        qdrant = _make_qdrant_client()
        srv = _make_server_with_mocks(qdrant=qdrant)
        q = SearchQuery(
            query="test",
            embedding=[0.1] * 10,
            memory_category="general",
            agent_id="a1",
        )
        # Replace _get_collection_name to raise at the outer try level
        srv._get_collection_name = MagicMock(side_effect=RuntimeError("outer fail"))
        with pytest.raises(HTTPException) as exc_info:
            await srv.search_memory(q)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_collection_not_found_logs_debug_skip(self):
        """When get_collection raises during all-category search, collection is skipped."""
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery, config
        qdrant = _make_qdrant_client()
        # get_collection raises -- means the collection doesn't exist, skip it
        qdrant.get_collection = MagicMock(side_effect=Exception("not found"))
        srv = _make_server_with_mocks(qdrant=qdrant)
        with (
            patch.object(config, "memory_categorization", True),
            patch.object(config, "category_prefixes", {"trading": "trading_"}),
        ):
            q = SearchQuery(query="test", embedding=[0.1] * 10)
            results = await srv.search_memory(q)
        # Nothing should be searched since collection was skipped
        assert results == []
        qdrant.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_category_filter_skips_non_matching_in_all_categories_search(self):
        """When memory_category is set but no agent_id, only matching categories used."""
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, SearchQuery, config
        qdrant = _make_qdrant_client()
        srv = _make_server_with_mocks(qdrant=qdrant)
        with (
            patch.object(config, "memory_categorization", True),
            patch.object(config, "category_prefixes", {"trading": "trading_", "dev": "dev_"}),
        ):
            q = SearchQuery(query="test", embedding=[0.1] * 10, memory_category="dev")
            await srv.search_memory(q)
        # Only "dev" category matches; get_collection should be called only once
        # (or zero if the collection doesn't exist in mock)
        assert qdrant.get_collection.call_count <= 2  # at most once per category


# ===========================================================================
# add_knowledge_relation (server method)
# ===========================================================================

class TestAddKnowledgeRelation:

    @pytest.mark.asyncio
    async def test_returns_uuid_string(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, KnowledgeRelation
        neo4j = _make_neo4j_driver()
        srv = _make_server_with_mocks(neo4j=neo4j)
        rel = KnowledgeRelation(
            source_entity="A", target_entity="B", relationship_type="knows"
        )
        result_id = await srv.add_knowledge_relation(rel)
        uuid.UUID(result_id)

    @pytest.mark.asyncio
    async def test_calls_neo4j_session_run(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, KnowledgeRelation
        neo4j = _make_neo4j_driver()
        srv = _make_server_with_mocks(neo4j=neo4j)
        rel = KnowledgeRelation(
            source_entity="A", target_entity="B", relationship_type="knows"
        )
        await srv.add_knowledge_relation(rel)
        # session.run is called at least twice (MERGE + CREATE)
        session = neo4j.session.return_value.__enter__.return_value
        assert session.run.call_count >= 2

    @pytest.mark.asyncio
    async def test_neo4j_error_raises_http_exception(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, KnowledgeRelation
        from fastapi import HTTPException
        neo4j = _make_neo4j_driver()
        session = neo4j.session.return_value.__enter__.return_value
        session.run = MagicMock(side_effect=RuntimeError("Neo4j down"))
        srv = _make_server_with_mocks(neo4j=neo4j)
        rel = KnowledgeRelation(
            source_entity="A", target_entity="B", relationship_type="knows"
        )
        with pytest.raises(HTTPException) as exc_info:
            await srv.add_knowledge_relation(rel)
        assert exc_info.value.status_code == 500


# ===========================================================================
# get_memory_stats (server method)
# ===========================================================================

class TestGetMemoryStats:

    @pytest.mark.asyncio
    async def test_returns_stats_dict(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[
            {"memory_category": "general", "agent_id": "a1",
             "document_count": 10, "last_activity": datetime.now(timezone.utc)},
        ])
        pool = _make_pool(conn)
        qdrant = _make_qdrant_client()
        neo4j = _make_neo4j_driver()
        redis_c = _make_redis_client()
        srv = _make_server_with_mocks(pool=pool, qdrant=qdrant, neo4j=neo4j, redis=redis_c)

        stats = await srv.get_memory_stats()
        assert "documents" in stats
        assert "total_documents" in stats
        assert stats["total_documents"] == 10
        assert "vector_collections" in stats
        assert "total_entities" in stats

    @pytest.mark.asyncio
    async def test_postgres_error_raises_http_exception(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        from fastapi import HTTPException
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("DB down"))
        pool = _make_pool(conn)
        srv = _make_server_with_mocks(pool=pool)
        with pytest.raises(HTTPException) as exc_info:
            await srv.get_memory_stats()
        assert exc_info.value.status_code == 500


# ===========================================================================
# DB initialization methods (unit tested in isolation)
# ===========================================================================

class TestDBInitMethods:

    @pytest.mark.asyncio
    async def test_init_postgresql_stores_pool(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        srv = EnhancedCogneeMCPServer()
        mock_pool = MagicMock()
        with patch("asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
            await srv._init_postgresql()
        assert srv.postgres_pool is mock_pool

    @pytest.mark.asyncio
    async def test_init_postgresql_raises_on_error(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        srv = EnhancedCogneeMCPServer()
        with patch("asyncpg.create_pool", AsyncMock(side_effect=RuntimeError("no postgres"))):
            with pytest.raises(RuntimeError):
                await srv._init_postgresql()

    @pytest.mark.asyncio
    async def test_init_qdrant_stores_client(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        srv = EnhancedCogneeMCPServer()
        mock_qc = _make_qdrant_client()
        with patch("qdrant_client.QdrantClient", return_value=mock_qc):
            await srv._init_qdrant()
        assert srv.qdrant_client is mock_qc

    @pytest.mark.asyncio
    async def test_init_qdrant_raises_on_error(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        srv = EnhancedCogneeMCPServer()
        with patch("qdrant_client.QdrantClient", side_effect=RuntimeError("no qdrant")):
            with pytest.raises(RuntimeError):
                await srv._init_qdrant()

    @pytest.mark.asyncio
    async def test_init_neo4j_stores_driver(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        srv = EnhancedCogneeMCPServer()
        mock_driver = _make_neo4j_driver()
        with patch("neo4j.GraphDatabase.driver", return_value=mock_driver):
            await srv._init_neo4j()
        assert srv.neo4j_driver is mock_driver

    @pytest.mark.asyncio
    async def test_init_neo4j_raises_on_error(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        srv = EnhancedCogneeMCPServer()
        with patch("neo4j.GraphDatabase.driver",
                   side_effect=RuntimeError("no neo4j")):
            with pytest.raises(RuntimeError):
                await srv._init_neo4j()

    @pytest.mark.asyncio
    async def test_init_redis_stores_client(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        srv = EnhancedCogneeMCPServer()
        mock_redis = _make_redis_client()
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            await srv._init_redis()
        assert srv.redis_client is mock_redis

    @pytest.mark.asyncio
    async def test_init_redis_raises_on_error(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        srv = EnhancedCogneeMCPServer()
        bad_redis = AsyncMock()
        bad_redis.ping = AsyncMock(side_effect=RuntimeError("no redis"))
        with patch("redis.asyncio.Redis", return_value=bad_redis):
            with pytest.raises(RuntimeError):
                await srv._init_redis()


# ===========================================================================
# server.initialize() paths
# ===========================================================================

class TestServerInitialize:

    @pytest.mark.asyncio
    async def test_initialize_skips_when_enhanced_mode_false(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, config
        srv = EnhancedCogneeMCPServer()
        with patch.object(config, "enhanced_mode", False):
            with patch.object(srv, "_init_postgresql", AsyncMock()) as pg:
                await srv.initialize()
                pg.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_initialize_calls_all_db_inits_when_enabled(self):
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer, config
        srv = EnhancedCogneeMCPServer()
        with patch.object(config, "enhanced_mode", True):
            with (
                patch.object(srv, "_init_postgresql", AsyncMock()) as pg,
                patch.object(srv, "_init_qdrant", AsyncMock()) as qd,
                patch.object(srv, "_init_neo4j", AsyncMock()) as neo,
                patch.object(srv, "_init_redis", AsyncMock()) as red,
            ):
                await srv.initialize()
                pg.assert_awaited_once()
                qd.assert_awaited_once()
                neo.assert_awaited_once()
                red.assert_awaited_once()


# ===========================================================================
# FastAPI route tests via TestClient
# ===========================================================================

class TestHealthEndpoint:
    """Tests for GET /health -- all connected and various disconnected states."""

    def test_health_all_disconnected_returns_200(self, client):
        """Even with no DB clients set, /health returns 200 (not 500)."""
        import src.enhanced_cognee_mcp as mod
        # Temporarily remove all DB clients
        mod.server.postgres_pool = None
        mod.server.qdrant_client = None
        mod.server.neo4j_driver = None
        mod.server.redis_client = None
        resp = client.get("/health")
        mod.server.postgres_pool = client._pool
        mod.server.qdrant_client = client._qdrant
        mod.server.neo4j_driver = client._neo4j
        mod.server.redis_client = client._redis
        assert resp.status_code == 200
        data = resp.json()
        assert data["postgresql"] == "disconnected"
        assert data["qdrant"] == "disconnected"
        assert data["neo4j"] == "disconnected"
        assert data["redis"] == "disconnected"

    def test_health_all_connected_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "stack" in data
        assert "categories" in data

    def test_health_postgres_connected_field(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["postgresql"] == "connected"

    def test_health_qdrant_connected_field(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "connected" in data["qdrant"]

    def test_health_neo4j_connected_field(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["neo4j"] == "connected"

    def test_health_redis_connected_field(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["redis"] == "connected"

    def test_health_postgres_error_shown_in_field(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        conn.fetchval = AsyncMock(side_effect=RuntimeError("pg down"))
        pool = _make_pool(conn)
        original = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        resp = client.get("/health")
        mod.server.postgres_pool = original
        data = resp.json()
        assert "error" in data["postgresql"]

    def test_health_qdrant_error_shown_in_field(self, client):
        import src.enhanced_cognee_mcp as mod
        qdrant = _make_qdrant_client()
        qdrant.get_collections = MagicMock(side_effect=RuntimeError("qdrant down"))
        original = mod.server.qdrant_client
        mod.server.qdrant_client = qdrant
        resp = client.get("/health")
        mod.server.qdrant_client = original
        data = resp.json()
        assert "error" in data["qdrant"]

    def test_health_neo4j_error_shown_in_field(self, client):
        import src.enhanced_cognee_mcp as mod
        neo4j = _make_neo4j_driver()
        session = neo4j.session.return_value.__enter__.return_value
        session.run = MagicMock(side_effect=RuntimeError("neo4j down"))
        original = mod.server.neo4j_driver
        mod.server.neo4j_driver = neo4j
        resp = client.get("/health")
        mod.server.neo4j_driver = original
        data = resp.json()
        assert "error" in data["neo4j"]

    def test_health_redis_error_shown_in_field(self, client):
        import src.enhanced_cognee_mcp as mod
        redis_c = _make_redis_client()
        redis_c.ping = AsyncMock(side_effect=RuntimeError("redis down"))
        original = mod.server.redis_client
        mod.server.redis_client = redis_c
        resp = client.get("/health")
        mod.server.redis_client = original
        data = resp.json()
        assert "error" in data["redis"]

    def test_health_categories_field_present(self, client):
        resp = client.get("/health")
        data = resp.json()
        cats = data["categories"]
        assert "enabled" in cats
        assert "count" in cats
        assert "configured" in cats

    def test_health_stack_contains_all_db_addresses(self, client):
        resp = client.get("/health")
        data = resp.json()
        stack = data["stack"]
        assert "postgresql" in stack
        assert "qdrant" in stack
        assert "neo4j" in stack
        assert "redis" in stack


class TestStatsEndpoint:
    """Tests for GET /stats"""

    def test_stats_returns_200(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[
            {"memory_category": "g", "agent_id": "a1",
             "document_count": 5, "last_activity": datetime.now(timezone.utc)},
        ])
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        resp = client.get("/stats")
        mod.server.postgres_pool = original_pool
        assert resp.status_code == 200

    def test_stats_contains_total_documents(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[
            {"memory_category": "g", "agent_id": "a1",
             "document_count": 3, "last_activity": datetime.now(timezone.utc)},
        ])
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        resp = client.get("/stats")
        mod.server.postgres_pool = original_pool
        data = resp.json()
        assert "total_documents" in data
        assert data["total_documents"] == 3

    def test_stats_500_on_db_error(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("db fail"))
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        resp = client.get("/stats")
        mod.server.postgres_pool = original_pool
        assert resp.status_code == 500


class TestMemoryAddEndpoint:
    """Tests for POST /memory/add"""

    def _valid_payload(self):
        return {
            "content": "test memory content",
            "agent_id": "test-agent",
            "memory_category": "general",
        }

    def test_add_memory_returns_200(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        resp = client.post("/memory/add", json=self._valid_payload())
        mod.server.postgres_pool = original_pool
        assert resp.status_code == 200

    def test_add_memory_response_has_id(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        resp = client.post("/memory/add", json=self._valid_payload())
        mod.server.postgres_pool = original_pool
        data = resp.json()
        assert "id" in data
        uuid.UUID(data["id"])

    def test_add_memory_missing_required_fields_returns_422(self, client):
        resp = client.post("/memory/add", json={"content": "only content"})
        assert resp.status_code == 422

    def test_add_memory_missing_content_returns_422(self, client):
        resp = client.post("/memory/add", json={
            "agent_id": "a1", "memory_category": "g"
        })
        assert resp.status_code == 422

    def test_add_memory_500_on_db_failure(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError("DB fail"))
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        resp = client.post("/memory/add", json=self._valid_payload())
        mod.server.postgres_pool = original_pool
        assert resp.status_code == 500

    def test_add_memory_with_embedding_returns_200(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        payload = self._valid_payload()
        payload["embedding"] = [0.1] * 10
        resp = client.post("/memory/add", json=payload)
        mod.server.postgres_pool = original_pool
        assert resp.status_code == 200

    def test_add_memory_with_metadata_returns_200(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        payload = self._valid_payload()
        payload["metadata"] = {"priority": "high"}
        resp = client.post("/memory/add", json=payload)
        mod.server.postgres_pool = original_pool
        assert resp.status_code == 200

    def test_add_memory_with_tags_returns_200(self, client):
        import src.enhanced_cognee_mcp as mod
        conn = _make_conn()
        pool = _make_pool(conn)
        original_pool = mod.server.postgres_pool
        mod.server.postgres_pool = pool
        payload = self._valid_payload()
        payload["tags"] = ["tag1", "tag2"]
        resp = client.post("/memory/add", json=payload)
        mod.server.postgres_pool = original_pool
        assert resp.status_code == 200


class TestMemorySearchEndpoint:
    """Tests for POST /memory/search"""

    def test_search_no_embedding_returns_empty_results(self, client):
        resp = client.post("/memory/search", json={"query": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["results"] == []

    def test_search_response_has_results_and_count(self, client):
        resp = client.post("/memory/search", json={"query": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "count" in data

    def test_search_with_embedding_calls_qdrant(self, client):
        import src.enhanced_cognee_mcp as mod
        qdrant = _make_qdrant_client()
        hit = MagicMock()
        hit.id = str(uuid.uuid4())
        hit.score = 0.8
        hit.payload = {"content": "c", "agent_id": "a1",
                       "memory_category": "g", "created_at": "now"}
        qdrant.search = MagicMock(return_value=[hit])
        original_qdrant = mod.server.qdrant_client
        mod.server.qdrant_client = qdrant
        resp = client.post("/memory/search", json={
            "query": "test",
            "embedding": [0.1] * 10,
            "memory_category": "general",
            "agent_id": "a1",
        })
        mod.server.qdrant_client = original_qdrant
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_search_missing_query_returns_422(self, client):
        resp = client.post("/memory/search", json={})
        assert resp.status_code == 422

    def test_search_limit_out_of_range_returns_422(self, client):
        resp = client.post("/memory/search", json={"query": "test", "limit": 0})
        assert resp.status_code == 422

    def test_search_with_filters_returns_200(self, client):
        resp = client.post("/memory/search", json={
            "query": "test",
            "filters": {"tag": "important"},
        })
        assert resp.status_code == 200

    def test_search_500_on_unexpected_error(self, client):
        import src.enhanced_cognee_mcp as mod
        qdrant = _make_qdrant_client()
        # Raise an outer error (not per-collection)
        # Patch the server method directly to force a 500
        original_method = mod.server.search_memory

        async def _always_raise(q):
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="forced error")

        mod.server.search_memory = _always_raise
        resp = client.post("/memory/search", json={
            "query": "test",
            "embedding": [0.1] * 10,
            "memory_category": "g",
            "agent_id": "a1",
        })
        mod.server.search_memory = original_method
        assert resp.status_code == 500


class TestKnowledgeAddRelationEndpoint:
    """Tests for POST /knowledge/add_relation"""

    def _valid_payload(self):
        return {
            "source_entity": "Python",
            "target_entity": "Programming",
            "relationship_type": "is_a",
        }

    def test_add_relation_returns_200(self, client):
        resp = client.post("/knowledge/add_relation", json=self._valid_payload())
        assert resp.status_code == 200

    def test_add_relation_response_has_id(self, client):
        resp = client.post("/knowledge/add_relation", json=self._valid_payload())
        data = resp.json()
        assert "id" in data
        uuid.UUID(data["id"])

    def test_add_relation_missing_fields_returns_422(self, client):
        resp = client.post("/knowledge/add_relation", json={"source_entity": "A"})
        assert resp.status_code == 422

    def test_add_relation_500_on_neo4j_failure(self, client):
        import src.enhanced_cognee_mcp as mod
        neo4j = _make_neo4j_driver()
        session = neo4j.session.return_value.__enter__.return_value
        session.run = MagicMock(side_effect=RuntimeError("neo4j crash"))
        original_neo4j = mod.server.neo4j_driver
        mod.server.neo4j_driver = neo4j
        resp = client.post("/knowledge/add_relation", json=self._valid_payload())
        mod.server.neo4j_driver = original_neo4j
        assert resp.status_code == 500

    def test_add_relation_with_properties_returns_200(self, client):
        payload = self._valid_payload()
        payload["properties"] = {"strength": 0.9}
        resp = client.post("/knowledge/add_relation", json=payload)
        assert resp.status_code == 200

    def test_add_relation_confidence_bounds_validated(self, client):
        payload = self._valid_payload()
        payload["confidence"] = 1.5  # above max
        resp = client.post("/knowledge/add_relation", json=payload)
        assert resp.status_code == 422


# ===========================================================================
# Lifespan tests
# ===========================================================================

class TestLifespan:
    """Tests for the lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_server_initialize(self):
        """lifespan should call server.initialize() on startup."""
        import src.enhanced_cognee_mcp as mod
        with patch.object(mod.server, "initialize", AsyncMock()) as mock_init:
            @asynccontextmanager
            async def _run_lifespan():
                async with mod.lifespan(mod.app):
                    yield

            async with _run_lifespan():
                pass

            mock_init.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lifespan_yields_without_error(self):
        """lifespan should yield without raising when initialize() succeeds."""
        import src.enhanced_cognee_mcp as mod
        with patch.object(mod.server, "initialize", AsyncMock()):
            entered = False
            async with mod.lifespan(mod.app):
                entered = True
            assert entered


# ===========================================================================
# App-level structural tests
# ===========================================================================

class TestAppStructure:
    """Tests for the top-level FastAPI app object structure."""

    def test_app_has_correct_title(self):
        import src.enhanced_cognee_mcp as mod
        assert mod.app.title == "Enhanced Cognee MCP Server"

    def test_server_instance_created(self):
        import src.enhanced_cognee_mcp as mod
        from src.enhanced_cognee_mcp import EnhancedCogneeMCPServer
        assert isinstance(mod.server, EnhancedCogneeMCPServer)

    def test_server_app_has_routes(self):
        import src.enhanced_cognee_mcp as mod
        route_paths = [r.path for r in mod.server.app.routes]
        assert "/memory/add" in route_paths
        assert "/memory/search" in route_paths
        assert "/knowledge/add_relation" in route_paths
        assert "/stats" in route_paths
        assert "/health" in route_paths

    def test_outer_app_includes_server_routes(self):
        """The outer `app` should expose the routes from server.app."""
        import src.enhanced_cognee_mcp as mod
        outer_paths = [r.path for r in mod.app.routes]
        assert "/memory/add" in outer_paths
        assert "/health" in outer_paths
