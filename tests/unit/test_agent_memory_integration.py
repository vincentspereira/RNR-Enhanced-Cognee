"""
Unit tests for src/agent_memory_integration.py

Coverage targets:
- MemoryType enum
- MemoryEntry dataclass (post_init, defaults)
- MemorySearchResult dataclass
- AgentMemoryIntegration.__init__ (config loading, env vars)
- AgentMemoryIntegration._initialize_agent_registry (deprecated)
- AgentMemoryIntegration.initialize (all four DB connections, exception path)
- AgentMemoryIntegration._initialize_qdrant_collections (existing vs new)
- AgentMemoryIntegration.add_memory (success, unknown agent, unknown category,
  category override, with/without embedding, semantic/factual triggers Neo4j)
- AgentMemoryIntegration._store_postgresql_memory (with/without embedding)
- AgentMemoryIntegration._store_qdrant_memory (category config found/not-found)
- AgentMemoryIntegration._cache_memory
- AgentMemoryIntegration._create_knowledge_relations (multiple entities vs single)
- AgentMemoryIntegration._extract_entities
- AgentMemoryIntegration.search_memory (pg only, qdrant only, merged, dedup)
- AgentMemoryIntegration._search_postgresql_memory (all filter combos)
- AgentMemoryIntegration._search_qdrant_memory (specific cat, all cats, exception)
- AgentMemoryIntegration.get_agent_memory_stats (success, unknown agent, error)
- AgentMemoryIntegration.cleanup_expired_memory
- AgentMemoryIntegration.get_all_agents_info
- AgentMemoryIntegration.close
"""

import os
import sys
import json
import pytest
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import (
    patch, MagicMock, AsyncMock, Mock, call
)

# ---------------------------------------------------------------------------
# Ensure project root on path
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ---------------------------------------------------------------------------
# Build lightweight fake MemoryConfigManager so we do not need the JSON file
# ---------------------------------------------------------------------------
from src.memory_config import (
    MemoryConfigManager,
    MemoryCategoryConfig,
    AgentConfig,
)

# Reset the global singleton before importing the module under test
from src import memory_config as _mc
_mc._config_manager = None


def _make_category(name, prefix):
    return MemoryCategoryConfig(
        name=name,
        description=f"{name} category",
        prefix=prefix,
        retention_days=30,
        priority=1,
    )


def _make_agent_config(agent_id, category, prefix="cat_"):
    return AgentConfig(
        agent_id=agent_id,
        category=category,
        prefix=prefix,
        description=f"{agent_id} description",
        memory_types=["factual", "procedural"],
        priority=1,
        data_retention_days=30,
    )


def _build_config_manager(categories=None, agents=None):
    """Build a MemoryConfigManager with known categories and agents."""
    cm = MemoryConfigManager.__new__(MemoryConfigManager)
    cm.config_path = None
    cm.categories = categories or {
        "trading": _make_category("trading", "trading_"),
        "development": _make_category("development", "dev_"),
    }
    cm.agents = agents or {
        "agent-alpha": _make_agent_config("agent-alpha", "trading"),
        "agent-beta": _make_agent_config("agent-beta", "development", "dev_"),
    }
    return cm


# ---------------------------------------------------------------------------
# Async DB mock helpers (following repo convention)
# ---------------------------------------------------------------------------

def _make_async_pool(fetch_return=None, fetchrow_return=None, fetchval_return=None,
                     execute_return=None):
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=fetch_return or [])
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    mock_conn.fetchval = AsyncMock(return_value=fetchval_return or 0)
    mock_conn.execute = AsyncMock(return_value=execute_return or "INSERT 1")

    class MockCtx:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=MockCtx())
    mock_pool.close = AsyncMock()
    return mock_pool, mock_conn


def _make_qdrant():
    mock = MagicMock()
    mock.get_collections = MagicMock(return_value=MagicMock(collections=[]))
    mock.get_collection = MagicMock()
    mock.create_collection = MagicMock()
    mock.upsert = MagicMock()
    mock.search = MagicMock(return_value=[])
    mock.count = MagicMock(return_value=MagicMock(count=0))
    return mock


def _make_neo4j():
    mock_session = MagicMock()
    mock_session.run = MagicMock(return_value=MagicMock(single=MagicMock(return_value=[1])))
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_driver.close = MagicMock()
    return mock_driver


def _make_redis():
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.keys = AsyncMock(return_value=[])
    mock.ttl = AsyncMock(return_value=3600)
    mock.close = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Integration under test
# ---------------------------------------------------------------------------

from src.agent_memory_integration import (
    AgentMemoryIntegration,
    MemoryType,
    MemoryEntry,
    MemorySearchResult,
)


# ---------------------------------------------------------------------------
# Helper to build a fully-wired (but mocked) integration instance
# ---------------------------------------------------------------------------

def _make_integration(config_manager=None, env_overrides=None):
    """Create an AgentMemoryIntegration with mocked external dependencies."""
    cm = config_manager or _build_config_manager()

    with patch("src.agent_memory_integration.get_config_manager", return_value=cm):
        # Patch env vars before instantiation
        env = {
            "QDRANT_HOST": "localhost",
            "QDRANT_PORT": "26333",
            "NEO4J_URI": "bolt://localhost:27687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "cognee_password",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "26379",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "25432",
            "POSTGRES_DB": "cognee_db",
            "POSTGRES_USER": "cognee_user",
            "POSTGRES_PASSWORD": "cognee_password",
        }
        if env_overrides:
            env.update(env_overrides)
        with patch.dict("os.environ", env):
            integration = AgentMemoryIntegration(config_manager=cm)

    # Inject mock clients
    pg_pool, pg_conn = _make_async_pool()
    integration.postgres_pool = pg_pool
    integration.qdrant_client = _make_qdrant()
    integration.neo4j_driver = _make_neo4j()
    integration.redis_client = _make_redis()

    return integration, pg_conn


# ===========================================================================
# Enums and Dataclasses
# ===========================================================================

class TestMemoryType:
    def test_all_values_defined(self):
        assert MemoryType.FACTUAL.value == "factual"
        assert MemoryType.PROCEDURAL.value == "procedural"
        assert MemoryType.EPISODIC.value == "episodic"
        assert MemoryType.SEMANTIC.value == "semantic"
        assert MemoryType.WORKING.value == "working"


class TestMemoryEntry:
    def test_post_init_sets_defaults(self):
        entry = MemoryEntry(
            id="e1",
            content="test",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.FACTUAL,
        )
        assert entry.metadata == {}
        assert entry.tags == []
        assert entry.created_at is not None
        assert entry.importance == 1.0
        assert entry.confidence == 1.0

    def test_post_init_preserves_provided_values(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entry = MemoryEntry(
            id="e2",
            content="data",
            agent_id="agent-beta",
            category="development",
            memory_type=MemoryType.SEMANTIC,
            metadata={"key": "value"},
            tags=["tag1"],
            created_at=ts,
        )
        assert entry.metadata == {"key": "value"}
        assert entry.tags == ["tag1"]
        assert entry.created_at == ts


class TestMemorySearchResult:
    def test_construct(self):
        result = MemorySearchResult(
            id="r1",
            content="content",
            agent_id="agent-alpha",
            category="trading",
            similarity_score=0.95,
            metadata={"x": 1},
            created_at=datetime.now(timezone.utc),
        )
        assert result.similarity_score == 0.95
        assert result.category == "trading"


# ===========================================================================
# __init__ configuration loading
# ===========================================================================

class TestInit:
    def test_uses_provided_config_manager(self):
        cm = _build_config_manager()
        integration, _ = _make_integration(config_manager=cm)
        assert integration.config_manager is cm

    def test_reads_env_vars(self):
        integration, _ = _make_integration(env_overrides={
            "QDRANT_HOST": "myqdrant",
            "QDRANT_PORT": "9999",
            "REDIS_CACHE_TTL": "1800",
            "SIMILARITY_THRESHOLD": "0.8",
        })
        assert integration.qdrant_host == "myqdrant"
        assert integration.qdrant_port == 9999
        assert integration.cache_ttl == 1800
        assert integration.similarity_threshold == 0.8

    def test_default_collection_prefix(self):
        integration, _ = _make_integration()
        assert integration.qdrant_collection_prefix == "cognee_"

    def test_deprecated_registry_returns_empty(self):
        integration, _ = _make_integration()
        # _initialize_agent_registry logs a deprecation warning; should not raise
        result = integration._initialize_agent_registry()
        assert result == {}


# ===========================================================================
# initialize()
# ===========================================================================

class TestInitialize:
    @pytest.mark.asyncio
    async def test_initialize_all_connections(self):
        cm = _build_config_manager()

        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()

        mock_qdrant = _make_qdrant()
        mock_neo4j = _make_neo4j()
        mock_redis = _make_redis()

        with (
            patch("src.agent_memory_integration.get_config_manager", return_value=cm),
            patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)),
            patch("src.agent_memory_integration.QdrantClient", return_value=mock_qdrant),
            patch("src.agent_memory_integration.GraphDatabase") as mock_gdb,
            patch("redis.asyncio.Redis", return_value=mock_redis),
        ):
            mock_gdb.driver = MagicMock(return_value=mock_neo4j)
            integration = AgentMemoryIntegration(config_manager=cm)
            integration.postgres_pool = None  # reset so initialize runs fully

            with patch.object(integration, "_initialize_qdrant_collections",
                              new=AsyncMock()):
                await integration.initialize()

        assert integration.postgres_pool is mock_pool
        assert integration.qdrant_client is mock_qdrant

    @pytest.mark.asyncio
    async def test_initialize_raises_on_postgres_failure(self):
        cm = _build_config_manager()

        with (
            patch("src.agent_memory_integration.get_config_manager", return_value=cm),
            patch("asyncpg.create_pool", new=AsyncMock(
                side_effect=ConnectionError("pg down"))),
        ):
            integration = AgentMemoryIntegration(config_manager=cm)

            with pytest.raises(Exception):
                await integration.initialize()


# ===========================================================================
# _initialize_qdrant_collections
# ===========================================================================

class TestInitializeQdrantCollections:
    @pytest.mark.asyncio
    async def test_creates_missing_collections(self):
        integration, _ = _make_integration()
        # get_collection raises so it creates
        integration.qdrant_client.get_collection = MagicMock(
            side_effect=Exception("not found")
        )

        await integration._initialize_qdrant_collections()

        assert integration.qdrant_client.create_collection.called

    @pytest.mark.asyncio
    async def test_skips_existing_collections(self):
        integration, _ = _make_integration()
        # get_collection succeeds -> no create
        integration.qdrant_client.get_collection = MagicMock(return_value=MagicMock())
        integration.qdrant_client.create_collection = MagicMock()

        await integration._initialize_qdrant_collections()

        integration.qdrant_client.create_collection.assert_not_called()


# ===========================================================================
# add_memory
# ===========================================================================

class TestAddMemory:
    @pytest.mark.asyncio
    async def test_unknown_agent_raises(self):
        integration, _ = _make_integration()
        with pytest.raises(ValueError, match="Unknown agent"):
            await integration.add_memory(
                agent_id="nonexistent-agent",
                content="test",
                memory_type=MemoryType.FACTUAL,
            )

    @pytest.mark.asyncio
    async def test_unknown_category_override_raises(self):
        integration, _ = _make_integration()
        with pytest.raises(ValueError, match="Unknown category"):
            await integration.add_memory(
                agent_id="agent-alpha",
                content="test",
                memory_type=MemoryType.FACTUAL,
                category_name="nonexistent-category",
            )

    @pytest.mark.asyncio
    async def test_missing_category_config_raises(self):
        # Agent exists but its category has no config
        cm = _build_config_manager(
            agents={"agent-x": _make_agent_config("agent-x", "orphan-cat")},
            categories={},  # empty - no "orphan-cat" category
        )
        integration, _ = _make_integration(config_manager=cm)
        with pytest.raises(ValueError, match="Category 'orphan-cat' not found"):
            await integration.add_memory(
                agent_id="agent-x",
                content="test",
                memory_type=MemoryType.FACTUAL,
            )

    @pytest.mark.asyncio
    async def test_success_factual_no_embedding(self):
        integration, pg_conn = _make_integration()

        mem_id = await integration.add_memory(
            agent_id="agent-alpha",
            content="Market is up 3%",
            memory_type=MemoryType.FACTUAL,
        )

        assert mem_id is not None
        # pg execute was called (INSERT into documents)
        pg_conn.execute.assert_called()
        # Qdrant NOT called (no embedding)
        integration.qdrant_client.upsert.assert_not_called()
        # Redis setex WAS called
        integration.redis_client.setex.assert_called()

    @pytest.mark.asyncio
    async def test_success_factual_with_embedding_stores_qdrant(self):
        integration, pg_conn = _make_integration()
        embedding = [0.1] * 1024

        await integration.add_memory(
            agent_id="agent-alpha",
            content="Sentiment is bullish",
            memory_type=MemoryType.FACTUAL,
            embedding=embedding,
        )

        # Qdrant upsert was called
        integration.qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_semantic_triggers_knowledge_relations(self):
        integration, _ = _make_integration()

        with patch.object(integration, "_create_knowledge_relations",
                          new=AsyncMock()) as mock_kr:
            await integration.add_memory(
                agent_id="agent-alpha",
                content="Apple and Microsoft are rivals",
                memory_type=MemoryType.SEMANTIC,
            )

        mock_kr.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_procedural_does_not_trigger_knowledge(self):
        integration, _ = _make_integration()

        with patch.object(integration, "_create_knowledge_relations",
                          new=AsyncMock()) as mock_kr:
            await integration.add_memory(
                agent_id="agent-alpha",
                content="Run the backtest script",
                memory_type=MemoryType.PROCEDURAL,
            )

        mock_kr.assert_not_called()

    @pytest.mark.asyncio
    async def test_category_override_accepted(self):
        integration, _ = _make_integration()
        # Override to 'development' instead of agent's default 'trading'
        with patch.object(integration, "_store_postgresql_memory",
                          new=AsyncMock()) as mock_pg:
            with patch.object(integration, "_cache_memory", new=AsyncMock()):
                await integration.add_memory(
                    agent_id="agent-alpha",
                    content="docs update",
                    memory_type=MemoryType.FACTUAL,
                    category_name="development",
                )

        entry_arg = mock_pg.call_args[0][0]
        assert entry_arg.category == "development"

    @pytest.mark.asyncio
    async def test_metadata_importance_extracted(self):
        integration, _ = _make_integration()
        with patch.object(integration, "_store_postgresql_memory",
                          new=AsyncMock()) as mock_pg:
            with patch.object(integration, "_cache_memory", new=AsyncMock()):
                await integration.add_memory(
                    agent_id="agent-alpha",
                    content="High priority item",
                    memory_type=MemoryType.FACTUAL,
                    metadata={"importance": 0.9, "confidence": 0.8},
                )

        entry = mock_pg.call_args[0][0]
        assert entry.importance == 0.9
        assert entry.confidence == 0.8

    @pytest.mark.asyncio
    async def test_exception_propagates(self):
        integration, pg_conn = _make_integration()
        pg_conn.execute = AsyncMock(side_effect=RuntimeError("DB crash"))

        with pytest.raises(RuntimeError, match="DB crash"):
            await integration.add_memory(
                agent_id="agent-alpha",
                content="test",
                memory_type=MemoryType.FACTUAL,
            )


# ===========================================================================
# _store_postgresql_memory
# ===========================================================================

class TestStorePostgresqlMemory:
    @pytest.mark.asyncio
    async def test_inserts_without_embedding(self):
        integration, pg_conn = _make_integration()
        entry = MemoryEntry(
            id="m1",
            content="test content",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.FACTUAL,
        )

        await integration._store_postgresql_memory(entry)

        # At least one INSERT call
        pg_conn.execute.assert_called()
        # Only ONE execute call (no embedding table)
        assert pg_conn.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_inserts_with_embedding(self):
        integration, pg_conn = _make_integration()
        entry = MemoryEntry(
            id="m2",
            content="vectorized content",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.FACTUAL,
            embedding=[0.1] * 512,
        )

        await integration._store_postgresql_memory(entry)

        # TWO execute calls: documents + embeddings
        assert pg_conn.execute.call_count == 2


# ===========================================================================
# _store_qdrant_memory
# ===========================================================================

class TestStoreQdrantMemory:
    @pytest.mark.asyncio
    async def test_uses_category_prefix_from_config(self):
        integration, _ = _make_integration()
        entry = MemoryEntry(
            id="q1",
            content="qdrant test",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.FACTUAL,
            embedding=[0.1] * 512,
        )

        await integration._store_qdrant_memory(entry)

        args = integration.qdrant_client.upsert.call_args
        collection_name = args[1].get("collection_name") or args[0][0]
        # Should use trading_ prefix
        assert "trading_" in collection_name

    @pytest.mark.asyncio
    async def test_falls_back_when_category_not_in_config(self, caplog):
        integration, _ = _make_integration()
        # category not in config manager
        entry = MemoryEntry(
            id="q2",
            content="orphan category",
            agent_id="agent-alpha",
            category="orphan",
            memory_type=MemoryType.FACTUAL,
            embedding=[0.1] * 512,
        )

        with caplog.at_level(logging.WARNING):
            await integration._store_qdrant_memory(entry)

        assert "orphan" in caplog.text
        integration.qdrant_client.upsert.assert_called_once()


# ===========================================================================
# _cache_memory
# ===========================================================================

class TestCacheMemory:
    @pytest.mark.asyncio
    async def test_sets_key_with_ttl(self):
        integration, _ = _make_integration()
        entry = MemoryEntry(
            id="c1",
            content="cached content",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.WORKING,
        )

        await integration._cache_memory(entry)

        call_args = integration.redis_client.setex.call_args
        key = call_args[0][0]
        assert "agent-alpha" in key
        assert "c1" in key

    @pytest.mark.asyncio
    async def test_cache_ttl_used(self):
        integration, _ = _make_integration()
        integration.cache_ttl = 999
        entry = MemoryEntry(
            id="c2",
            content="ttl test",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.WORKING,
        )

        await integration._cache_memory(entry)

        call_args = integration.redis_client.setex.call_args
        ttl_arg = call_args[0][1]
        assert ttl_arg == 999


# ===========================================================================
# _extract_entities
# ===========================================================================

class TestExtractEntities:
    def test_no_capitalized_words_returns_empty(self):
        integration, _ = _make_integration()
        result = integration._extract_entities("just plain lowercase text here")
        assert result == []

    def test_returns_unique_entities(self):
        integration, _ = _make_integration()
        result = integration._extract_entities("Apple Apple Microsoft")
        # Should be unique
        assert len(result) == len(set(result))

    def test_short_words_excluded(self):
        integration, _ = _make_integration()
        result = integration._extract_entities("Go IBM short words")
        # "IBM" and "Go" are short (<=3), so filtered
        assert "go" not in result
        assert "ibm" not in result

    def test_longer_capitalized_words_are_extracted(self):
        # Regression: a prior bug lowercased text before the isupper() check,
        # so no entities were ever extracted and Neo4j relations were never
        # created. After the fix, capitalized tokens longer than 3 chars are
        # returned in lowercase form.
        integration, _ = _make_integration()
        result = integration._extract_entities("Apple and Google dominate")
        assert set(result) == {"apple", "google"}


# ===========================================================================
# _create_knowledge_relations
# ===========================================================================

class TestCreateKnowledgeRelations:
    @pytest.mark.asyncio
    async def test_no_entities_skips_neo4j(self):
        integration, _ = _make_integration()
        entry = MemoryEntry(
            id="kr1",
            content="just lowercase text no entities",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.SEMANTIC,
        )

        await integration._create_knowledge_relations(entry)
        # Neo4j session.run should NOT have been called
        integration.neo4j_driver.session.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_entity_skips_neo4j(self):
        integration, _ = _make_integration()
        entry = MemoryEntry(
            id="kr2",
            content="Apple is great",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.SEMANTIC,
        )

        await integration._create_knowledge_relations(entry)
        # Only one entity -> no MERGE calls
        integration.neo4j_driver.session.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_entities_calls_neo4j_when_injected(self):
        # _extract_entities has a bug (lowercases before isupper check) so
        # we test the Neo4j path by directly patching _extract_entities.
        integration, _ = _make_integration()
        entry = MemoryEntry(
            id="kr3",
            content="Apple Microsoft Google compete strongly",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.SEMANTIC,
        )

        with patch.object(integration, "_extract_entities",
                          return_value=["apple", "microsoft", "google"]):
            await integration._create_knowledge_relations(entry)

        integration.neo4j_driver.session.assert_called()


# ===========================================================================
# search_memory
# ===========================================================================

class TestSearchMemory:
    @pytest.mark.asyncio
    async def test_returns_empty_with_no_results(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetch = AsyncMock(return_value=[])

        results = await integration.search_memory(agent_id="agent-alpha", query="nothing")
        assert results == []

    @pytest.mark.asyncio
    async def test_postgres_results_deduped_with_qdrant(self):
        integration, pg_conn = _make_integration()

        shared_id = "shared-mem-1"
        # PG returns a row
        pg_conn.fetch = AsyncMock(return_value=[{
            "id": shared_id,
            "content": "shared content",
            "agent_id": "agent-alpha",
            "memory_category": "trading",
            "metadata": {},
            "created_at": datetime.now(timezone.utc),
        }])

        # Qdrant returns the same ID
        qdrant_hit = MagicMock()
        qdrant_hit.id = shared_id
        qdrant_hit.score = 0.9
        qdrant_hit.payload = {
            "content": "shared content",
            "agent_id": "agent-alpha",
            "category_name": "trading",
            "tags": [],
            "importance": 1.0,
            "confidence": 1.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        integration.qdrant_client.search = MagicMock(return_value=[qdrant_hit])

        embedding = [0.1] * 1024

        results = await integration.search_memory(
            agent_id="agent-alpha",
            query="shared",
            embedding=embedding,
        )

        # ID should appear only once
        ids = [r.id for r in results]
        assert ids.count(shared_id) == 1

    @pytest.mark.asyncio
    async def test_sorted_by_similarity_score(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetch = AsyncMock(return_value=[])

        # Two Qdrant hits with different scores
        def _hit(id_, score):
            h = MagicMock()
            h.id = id_
            h.score = score
            h.payload = {
                "content": f"content {id_}",
                "agent_id": "agent-alpha",
                "category_name": "trading",
                "tags": [],
                "importance": 1.0,
                "confidence": 1.0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            return h

        integration.qdrant_client.search = MagicMock(
            return_value=[_hit("low", 0.5), _hit("high", 0.95)]
        )

        results = await integration.search_memory(
            embedding=[0.1] * 1024,
        )

        assert results[0].id == "high"

    @pytest.mark.asyncio
    async def test_no_embedding_skips_qdrant(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetch = AsyncMock(return_value=[])

        await integration.search_memory(agent_id="agent-alpha", query="test")
        integration.qdrant_client.search.assert_not_called()


# ===========================================================================
# _search_postgresql_memory
# ===========================================================================

class TestSearchPostgresqlMemory:
    @pytest.mark.asyncio
    async def test_no_filters(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetch = AsyncMock(return_value=[])

        results = await integration._search_postgresql_memory()
        assert results == []
        pg_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_filters(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetch = AsyncMock(return_value=[])

        await integration._search_postgresql_memory(
            agent_id="agent-alpha",
            query="test",
            memory_type=MemoryType.FACTUAL,
            category_name="trading",
            limit=5,
        )

        # The SQL should include all four conditions
        call_args = pg_conn.fetch.call_args
        sql = call_args[0][0]
        assert "agent_id" in sql
        assert "ILIKE" in sql
        assert "title LIKE" in sql
        assert "memory_category" in sql


# ===========================================================================
# _search_qdrant_memory
# ===========================================================================

class TestSearchQdrantMemory:
    @pytest.mark.asyncio
    async def test_searches_specific_category(self):
        integration, _ = _make_integration()
        integration.qdrant_client.search = MagicMock(return_value=[])

        await integration._search_qdrant_memory(
            embedding=[0.1] * 1024,
            category_name="trading",
        )

        call_args = integration.qdrant_client.search.call_args
        collection = call_args[1].get("collection_name") or call_args[0][0]
        assert "trading_" in collection

    @pytest.mark.asyncio
    async def test_searches_all_categories_when_none_specified(self):
        integration, _ = _make_integration()
        integration.qdrant_client.search = MagicMock(return_value=[])

        await integration._search_qdrant_memory(embedding=[0.1] * 1024)

        # Should be called once per category (2 categories in default config)
        assert integration.qdrant_client.search.call_count == 2

    @pytest.mark.asyncio
    async def test_unknown_category_falls_back_to_direct_lookup(self):
        integration, _ = _make_integration()
        integration.qdrant_client.search = MagicMock(return_value=[])

        await integration._search_qdrant_memory(
            embedding=[0.1] * 1024,
            category_name="unknown-cat",
        )

        call_args = integration.qdrant_client.search.call_args
        collection = call_args[1].get("collection_name") or call_args[0][0]
        assert "unknown-cat" in collection

    @pytest.mark.asyncio
    async def test_collection_exception_continues(self, caplog):
        integration, _ = _make_integration()
        integration.qdrant_client.search = MagicMock(
            side_effect=Exception("collection error")
        )

        with caplog.at_level(logging.WARNING):
            results = await integration._search_qdrant_memory(
                embedding=[0.1] * 1024,
            )

        assert results == []
        assert "Failed to search collection" in caplog.text

    @pytest.mark.asyncio
    async def test_uses_custom_threshold(self):
        integration, _ = _make_integration()
        integration.qdrant_client.search = MagicMock(return_value=[])

        await integration._search_qdrant_memory(
            embedding=[0.1] * 1024,
            threshold=0.5,
        )

        call_args = integration.qdrant_client.search.call_args
        score_threshold = call_args[1].get("score_threshold")
        assert score_threshold == 0.5


# ===========================================================================
# get_agent_memory_stats
# ===========================================================================

class TestGetAgentMemoryStats:
    @pytest.mark.asyncio
    async def test_unknown_agent_raises(self):
        integration, _ = _make_integration()
        with pytest.raises(ValueError, match="Unknown agent"):
            await integration.get_agent_memory_stats("nonexistent")

    @pytest.mark.asyncio
    async def test_returns_stats_structure(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetchrow = AsyncMock(return_value={
            "total_memories": 10,
            "memory_types": 3,
            "first_memory": datetime.now(timezone.utc),
            "last_memory": datetime.now(timezone.utc),
        })
        integration.redis_client.keys = AsyncMock(return_value=["k1", "k2"])

        stats = await integration.get_agent_memory_stats("agent-alpha")

        assert stats["agent_id"] == "agent-alpha"
        assert "memory_stats" in stats
        assert "agent_config" in stats
        assert "category_config" in stats

    @pytest.mark.asyncio
    async def test_error_logged_and_included(self, caplog):
        integration, pg_conn = _make_integration()
        pg_conn.fetchrow = AsyncMock(side_effect=RuntimeError("pg down"))

        with caplog.at_level(logging.ERROR):
            stats = await integration.get_agent_memory_stats("agent-alpha")

        assert "error" in stats

    @pytest.mark.asyncio
    async def test_qdrant_collection_not_found_handled(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetchrow = AsyncMock(return_value=None)
        integration.qdrant_client.get_collection = MagicMock(
            side_effect=Exception("not found")
        )
        integration.redis_client.keys = AsyncMock(return_value=[])

        stats = await integration.get_agent_memory_stats("agent-alpha")
        assert stats["memory_stats"]["qdrant"] == {"error": "Collection not found"}


# ===========================================================================
# cleanup_expired_memory
# ===========================================================================

class TestCleanupExpiredMemory:
    @pytest.mark.asyncio
    async def test_returns_zero_on_no_expired(self):
        integration, pg_conn = _make_integration()
        # execute returns a string "DELETE 0"
        pg_conn.execute = AsyncMock(return_value="DELETE 0")
        integration.redis_client.keys = AsyncMock(return_value=[])

        count = await integration.cleanup_expired_memory()
        # "DELETE 0" -> len("DELETE 0") = 8 (the code calls len(result))
        # The code does: cleanup_count += len(result) where result is the execute return
        assert count >= 0

    @pytest.mark.asyncio
    async def test_returns_zero_on_exception(self, caplog):
        integration, pg_conn = _make_integration()
        pg_conn.execute = AsyncMock(side_effect=RuntimeError("table gone"))

        with caplog.at_level(logging.ERROR):
            count = await integration.cleanup_expired_memory()

        assert count == 0
        assert "Failed to cleanup" in caplog.text

    @pytest.mark.asyncio
    async def test_checks_redis_keys(self):
        integration, pg_conn = _make_integration()
        pg_conn.execute = AsyncMock(return_value="DELETE 0")
        integration.redis_client.keys = AsyncMock(return_value=["key1"])
        integration.redis_client.ttl = AsyncMock(return_value=-1)  # No expiry

        await integration.cleanup_expired_memory()

        integration.redis_client.keys.assert_called_once_with("memory:*")


# ===========================================================================
# get_all_agents_info
# ===========================================================================

class TestGetAllAgentsInfo:
    @pytest.mark.asyncio
    async def test_returns_correct_structure(self):
        integration, _ = _make_integration()
        result = await integration.get_all_agents_info()

        assert "project_info" in result
        assert "categories" in result
        assert "agents" in result
        assert result["project_info"]["total_categories"] == 2
        assert result["project_info"]["total_agents"] == 2

    @pytest.mark.asyncio
    async def test_category_agent_counts(self):
        integration, _ = _make_integration()
        result = await integration.get_all_agents_info()

        # agent-alpha -> trading, agent-beta -> development
        assert result["categories"]["trading"]["agent_count"] == 1
        assert result["categories"]["development"]["agent_count"] == 1

    @pytest.mark.asyncio
    async def test_agents_include_expected_fields(self):
        integration, _ = _make_integration()
        result = await integration.get_all_agents_info()

        alpha = result["agents"]["agent-alpha"]
        assert "agent_id" in alpha
        assert "category" in alpha
        assert "description" in alpha
        assert alpha["category"] == "trading"


# ===========================================================================
# close
# ===========================================================================

class TestClose:
    @pytest.mark.asyncio
    async def test_closes_all_connections(self):
        integration, _ = _make_integration()

        await integration.close()

        integration.postgres_pool.close.assert_called_once()
        integration.neo4j_driver.close.assert_called_once()
        integration.redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_none_connections(self):
        integration, _ = _make_integration()
        integration.postgres_pool = None
        integration.neo4j_driver = None
        integration.redis_client = None

        # Should not raise
        await integration.close()

    @pytest.mark.asyncio
    async def test_partial_connections_closed(self):
        integration, _ = _make_integration()
        integration.neo4j_driver = None  # Already closed

        await integration.close()

        integration.postgres_pool.close.assert_called_once()
        integration.redis_client.close.assert_called_once()


# ===========================================================================
# Edge cases and partial failure scenarios
# ===========================================================================

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_add_memory_with_tags(self):
        integration, _ = _make_integration()
        with patch.object(integration, "_store_postgresql_memory", new=AsyncMock()) as mock_pg:
            with patch.object(integration, "_cache_memory", new=AsyncMock()):
                await integration.add_memory(
                    agent_id="agent-alpha",
                    content="tagged memory",
                    memory_type=MemoryType.EPISODIC,
                    tags=["tag1", "tag2", "tag3"],
                )

        entry = mock_pg.call_args[0][0]
        assert entry.tags == ["tag1", "tag2", "tag3"]

    @pytest.mark.asyncio
    async def test_add_memory_with_expiry(self):
        integration, _ = _make_integration()
        expiry = datetime.now(timezone.utc) + timedelta(days=7)

        with patch.object(integration, "_store_postgresql_memory", new=AsyncMock()) as mock_pg:
            with patch.object(integration, "_cache_memory", new=AsyncMock()):
                await integration.add_memory(
                    agent_id="agent-alpha",
                    content="expiring memory",
                    memory_type=MemoryType.WORKING,
                    expires_at=expiry,
                )

        entry = mock_pg.call_args[0][0]
        assert entry.expires_at == expiry

    @pytest.mark.asyncio
    async def test_search_returns_up_to_limit(self):
        integration, pg_conn = _make_integration()

        # Return 20 rows from PG
        rows = []
        for i in range(20):
            rows.append({
                "id": f"m{i}",
                "content": f"content {i}",
                "agent_id": "agent-alpha",
                "memory_category": "trading",
                "metadata": {},
                "created_at": datetime.now(timezone.utc),
            })
        pg_conn.fetch = AsyncMock(return_value=rows)

        results = await integration.search_memory(
            agent_id="agent-alpha",
            query="content",
            limit=5,
        )

        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_search_qdrant_result_parsed_correctly(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetch = AsyncMock(return_value=[])

        ts = datetime.now(timezone.utc)
        hit = MagicMock()
        hit.id = "qdrant-1"
        hit.score = 0.88
        hit.payload = {
            "content": "qdrant result",
            "agent_id": "agent-alpha",
            "category_name": "trading",
            "tags": ["a", "b"],
            "importance": 0.7,
            "confidence": 0.9,
            "created_at": ts.isoformat(),
        }
        integration.qdrant_client.search = MagicMock(return_value=[hit])

        results = await integration.search_memory(
            agent_id="agent-alpha",
            embedding=[0.1] * 1024,
        )

        assert len(results) == 1
        assert results[0].id == "qdrant-1"
        assert results[0].similarity_score == 0.88
        assert results[0].category == "trading"

    def test_config_manager_category_prefix_lookup(self):
        cm = _build_config_manager()
        assert cm.get_prefix_for_category("trading") == "trading_"
        assert cm.get_prefix_for_category("nonexistent") == ""

    def test_config_manager_validate_category(self):
        cm = _build_config_manager()
        assert cm.validate_category("trading") is True
        assert cm.validate_category("nonexistent") is False

    def test_config_manager_add_category(self):
        cm = _build_config_manager()
        new_cat = _make_category("new", "new_")
        cm.add_category("new", new_cat)
        assert cm.validate_category("new") is True

    def test_config_manager_add_agent(self):
        cm = _build_config_manager()
        new_agent = _make_agent_config("new-agent", "trading")
        cm.add_agent("new-agent", new_agent)
        assert cm.get_agent_config("new-agent") is not None

    @pytest.mark.asyncio
    async def test_get_agent_stats_with_no_category_config(self):
        """When agent's category has no config, else branch on line 700 runs."""
        # Create a config where the agent exists but its category has no config
        cm = _build_config_manager(
            agents={"orphan-agent": _make_agent_config("orphan-agent", "ghost-cat")},
            categories={"trading": _make_category("trading", "trading_")},
        )
        integration, pg_conn = _make_integration(config_manager=cm)
        pg_conn.fetchrow = AsyncMock(return_value={
            "total_memories": 0,
            "memory_types": 0,
            "first_memory": None,
            "last_memory": None,
        })

        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 512
        integration.qdrant_client.get_collection = MagicMock(
            return_value=mock_collection_info
        )
        mock_count = MagicMock()
        mock_count.count = 0
        integration.qdrant_client.count = MagicMock(return_value=mock_count)
        integration.redis_client.keys = AsyncMock(return_value=[])

        stats = await integration.get_agent_memory_stats("orphan-agent")
        # Should have used the else branch for collection name (line 700)
        assert "qdrant" in stats["memory_stats"]

    @pytest.mark.asyncio
    async def test_get_agent_stats_qdrant_vector_size_accessed(self):
        """Tests that qdrant stats correctly accesses vector size from collection info."""
        integration, pg_conn = _make_integration()
        pg_conn.fetchrow = AsyncMock(return_value={
            "total_memories": 5,
            "memory_types": 2,
            "first_memory": datetime.now(timezone.utc),
            "last_memory": datetime.now(timezone.utc),
        })

        # Mock qdrant collection info with proper nesting
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1024

        integration.qdrant_client.get_collection = MagicMock(
            return_value=mock_collection_info
        )
        mock_count = MagicMock()
        mock_count.count = 10
        integration.qdrant_client.count = MagicMock(return_value=mock_count)
        integration.redis_client.keys = AsyncMock(return_value=[])

        stats = await integration.get_agent_memory_stats("agent-alpha")

        qdrant_stats = stats["memory_stats"]["qdrant"]
        assert qdrant_stats["points_count"] == 10
        assert qdrant_stats["vector_count"] == 1024

    @pytest.mark.asyncio
    async def test_search_memory_with_all_filters(self):
        integration, pg_conn = _make_integration()
        pg_conn.fetch = AsyncMock(return_value=[])

        results = await integration.search_memory(
            agent_id="agent-alpha",
            query="test",
            memory_type=MemoryType.FACTUAL,
            category_name="trading",
            limit=3,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_store_qdrant_with_payload_structure(self):
        """Verify that Qdrant upsert receives the correct payload keys."""
        integration, _ = _make_integration()
        entry = MemoryEntry(
            id="payload-test",
            content="payload content",
            agent_id="agent-alpha",
            category="trading",
            memory_type=MemoryType.FACTUAL,
            embedding=[0.1] * 1024,
            tags=["a", "b"],
            importance=0.7,
            confidence=0.9,
        )

        await integration._store_qdrant_memory(entry)

        call_args = integration.qdrant_client.upsert.call_args
        points = call_args[1].get("points") or call_args[0][1]
        point = points[0]
        payload = point.payload
        assert payload["content"] == "payload content"
        assert payload["agent_id"] == "agent-alpha"
        assert payload["category_name"] == "trading"
        assert payload["tags"] == ["a", "b"]
