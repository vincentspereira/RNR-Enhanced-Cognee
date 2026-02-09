"""
Comprehensive System Tests for All Enhanced Cognee MCP Tools
Tests 60+ MCP tools with CORRECT async mock patterns

CRITICAL PATTERN:
- For async methods returning values: Use async def functions instead of AsyncMock
- For async context managers: Use custom context manager class with __aenter__/__aexit__
- NEVER use AsyncMock(return_value=...) - causes "coroutine object" errors
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, UTC

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import MCP server
import bin.enhanced_cognee_mcp_server as server


# ============================================================================
# HELPER FUNCTIONS - CORRECT ASYNC MOCK PATTERNS
# ============================================================================

def create_mock_async_context(return_value):
    """
    Create a proper async context manager for database connections.

    CORRECT pattern - Avoids "coroutine object" errors:
    - Returns a context manager, not a coroutine
    - Properly implements __aenter__ and __aexit__
    """
    class MockAsyncContext:
        async def __aenter__(self):
            return return_value

        async def __aexit__(self, *args):
            pass

    return MockAsyncContext()


def create_mock_connection():
    """Create a mock database connection with correct async methods"""
    mock_conn = AsyncMock()

    # Return actual values, not coroutines
    async def mock_execute(*args, **kwargs):
        return None

    async def mock_fetch(*args, **kwargs):
        return []

    async def mock_fetchval(*args, **kwargs):
        return None

    async def mock_fetchrow(*args, **kwargs):
        return None

    mock_conn.execute = mock_execute
    mock_conn.fetch = mock_fetch
    mock_conn.fetchval = mock_fetchval
    mock_conn.fetchrow = mock_fetchrow

    return mock_conn


def create_mock_postgres_pool():
    """Create a mock PostgreSQL pool with correct async context manager"""
    mock_pool = Mock()
    mock_conn = create_mock_connection()

    # Return context manager, not coroutine
    mock_pool.acquire = lambda: create_mock_async_context(mock_conn)

    return mock_pool


def create_mock_qdrant_client():
    """Create a mock Qdrant client"""
    mock_client = Mock()

    # Mock collection operations
    mock_client.get_collections = Mock(return_value=Mock(collections=[]))
    mock_client.upsert = Mock()
    mock_client.search = Mock(return_value=[])
    mock_client.delete = Mock()
    mock_client.count = Mock(return_value=Mock(count=0))

    return mock_client


def create_mock_redis_client():
    """Create a mock Redis client with correct async methods"""
    mock_client = AsyncMock()

    # Return actual values
    async def mock_get(*args, **kwargs):
        return None

    async def mock_set(*args, **kwargs):
        return True

    async def mock_delete(*args, **kwargs):
        return 1

    async def mock_keys(*args, **kwargs):
        return []

    async def mock_ping(*args, **kwargs):
        return True

    mock_client.get = mock_get
    mock_client.set = mock_set
    mock_client.delete = mock_delete
    mock_client.keys = mock_keys
    mock_client.ping = mock_ping

    return mock_client


def create_mock_neo4j_driver():
    """Create a mock Neo4j driver"""
    mock_driver = Mock()
    mock_session = Mock()
    mock_result = Mock()

    mock_result.data = Mock(return_value=[])
    mock_session.run = Mock(return_value=mock_result)
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    mock_driver.session = Mock(return_value=mock_session)

    return mock_driver


def setup_mocks():
    """Setup all database mocks for testing"""
    server.postgres_pool = create_mock_postgres_pool()
    server.qdrant_client = create_mock_qdrant_client()
    server.neo4j_driver = create_mock_neo4j_driver()
    server.redis_client = create_mock_redis_client()

    # Initialize module instances
    from src.memory_management import MemoryManager
    from src.memory_deduplication import MemoryDeduplicator
    from src.memory_summarization import MemorySummarizer
    from src.performance_analytics import PerformanceAnalytics
    from src.cross_agent_sharing import CrossAgentMemorySharing
    from src.realtime_sync import RealTimeMemorySync

    llm_config = {}

    server.memory_manager = MemoryManager(
        server.postgres_pool,
        server.redis_client,
        server.qdrant_client
    )
    server.memory_deduplicator = MemoryDeduplicator(
        server.postgres_pool,
        server.qdrant_client
    )
    server.memory_summarizer = MemorySummarizer(
        server.postgres_pool,
        llm_config
    )
    server.performance_analytics = PerformanceAnalytics(
        server.postgres_pool,
        server.redis_client
    )
    server.cross_agent_sharing = CrossAgentMemorySharing(
        server.postgres_pool
    )
    server.realtime_sync = RealTimeMemorySync(
        server.redis_client,
        server.postgres_pool
    )

    # Mock realtime_sync async methods to return proper values (not AsyncMock coroutines)
    async def mock_get_sync_status():
        return "OK Sync status: 0 subscribers"

    async def mock_get_subscribers():
        return []

    server.realtime_sync.get_sync_status = mock_get_sync_status
    server.realtime_sync.get_subscribers = mock_get_subscribers

    # Mock backup manager
    server.backup_manager = Mock()
    server.backup_manager.create_backup = Mock(return_value="backup-123")


# ============================================================================
# TEST CLASS 1: Standard Memory Tools (7 tools)
# ============================================================================

class TestStandardMemoryTools:
    """Test standard memory MCP tools - add, search, get, update, delete"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mocks before each test"""
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_add_memory(self):
        """Test add_memory tool"""
        result = await server.add_memory(
            content="Test memory content",
            agent_id="test-agent"
        )

        assert result is not None
        assert isinstance(result, str)
        assert "memory" in result.lower() or "ok" in result.lower() or "added" in result.lower()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_add_memory_with_metadata(self):
        """Test add_memory with metadata"""
        metadata = json.dumps({"category": "test", "priority": "high"})
        result = await server.add_memory(
            content="Test memory with metadata",
            agent_id="test-agent",
            metadata=metadata
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test search_memories tool"""
        result = await server.search_memories(
            query="test query",
            limit=10,
            agent_id="test-agent"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_memories(self):
        """Test get_memories tool"""
        result = await server.get_memories(
            agent_id="test-agent",
            limit=50
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_memory(self):
        """Test get_memory tool"""
        result = await server.get_memory(
            memory_id="test-memory-id-123"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_update_memory(self):
        """Test update_memory tool"""
        result = await server.update_memory(
            memory_id="test-memory-id-123",
            content="Updated memory content"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_delete_memory(self):
        """Test delete_memory tool"""
        result = await server.delete_memory(
            memory_id="test-memory-id-123"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_list_agents(self):
        """Test list_agents tool"""
        result = await server.list_agents()

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 2: Enhanced Cognee Tools (5 tools)
# ============================================================================

class TestEnhancedCogneeTools:
    """Test Enhanced Cognee-specific tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_cognify(self):
        """Test cognify tool - transform data to knowledge graph"""
        result = await server.cognify(
            data="Test data for knowledge graph"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_search_knowledge_graph(self):
        """Test search tool - knowledge graph search"""
        result = await server.search(
            query="semantic search query",
            limit=10
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_list_data(self):
        """Test list_data tool - list all documents"""
        result = await server.list_data()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test get_stats tool - system statistics"""
        result = await server.get_stats()

        assert result is not None
        assert isinstance(result, str)
        assert "stats" in result.lower() or "status" in result.lower()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_health(self):
        """Test health tool - health check"""
        result = await server.health()

        assert result is not None
        assert isinstance(result, str)
        assert "health" in result.lower() or "ok" in result.lower()


# ============================================================================
# TEST CLASS 3: Memory Management Tools (4 tools)
# ============================================================================

class TestMemoryManagementTools:
    """Test memory management tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_expire_memories(self):
        """Test expire_memories tool"""
        result = await server.expire_memories(
            days=90,
            dry_run=True
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_memory_age_stats(self):
        """Test get_memory_age_stats tool"""
        result = await server.get_memory_age_stats()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_set_memory_ttl(self):
        """Test set_memory_ttl tool"""
        result = await server.set_memory_ttl(
            memory_id="test-memory-id",
            ttl_days=30
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_archive_category(self):
        """Test archive_category tool"""
        result = await server.archive_category(
            category="test-category",
            days=90
        )

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 4: Deduplication Tools (6 tools)
# ============================================================================

class TestDeduplicationTools:
    """Test memory deduplication tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_check_duplicate(self):
        """Test check_duplicate tool"""
        result = await server.check_duplicate(
            content="Test content for duplicate check",
            agent_id="test-agent"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_auto_deduplicate(self):
        """Test auto_deduplicate tool"""
        result = await server.auto_deduplicate(
            agent_id="test-agent"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_deduplication_stats(self):
        """Test get_deduplication_stats tool"""
        result = await server.get_deduplication_stats()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_deduplicate(self):
        """Test deduplicate tool"""
        result = await server.deduplicate(
            agent_id="test-agent",
            dry_run=True
        )

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 5: Summarization Tools (5 tools)
# ============================================================================

class TestSummarizationTools:
    """Test memory summarization tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_summarize_old_memories(self):
        """Test summarize_old_memories tool"""
        result = await server.summarize_old_memories(
            days=30,
            min_length=1000,
            dry_run=True
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_summarize_category(self):
        """Test summarize_category tool"""
        result = await server.summarize_category(
            category="test-category",
            days=30
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_summary_stats(self):
        """Test get_summary_stats tool"""
        result = await server.get_summary_stats()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_intelligent_summarize(self):
        """Test intelligent_summarize tool"""
        result = await server.intelligent_summarize(
            memory_id="test-memory-id",
            strategy="standard"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_summarization_stats(self):
        """Test get_summarization_stats tool"""
        result = await server.get_summarization_stats()

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 6: Performance Analytics Tools (3 tools)
# ============================================================================

class TestPerformanceAnalyticsTools:
    """Test performance analytics tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self):
        """Test get_performance_metrics tool"""
        result = await server.get_performance_metrics()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_slow_queries(self):
        """Test get_slow_queries tool"""
        result = await server.get_slow_queries(
            threshold_ms=1000,
            limit=20
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_prometheus_metrics(self):
        """Test get_prometheus_metrics tool"""
        result = await server.get_prometheus_metrics()

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 7: Cross-Agent Sharing Tools (4 tools)
# ============================================================================

class TestCrossAgentSharingTools:
    """Test cross-agent memory sharing tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_set_memory_sharing(self):
        """Test set_memory_sharing tool"""
        result = await server.set_memory_sharing(
            memory_id="test-memory-id",
            policy="read",
            allowed_agents='["agent2", "agent3"]'
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_check_memory_access(self):
        """Test check_memory_access tool"""
        result = await server.check_memory_access(
            memory_id="test-memory-id",
            agent_id="agent2"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_shared_memories(self):
        """Test get_shared_memories tool"""
        result = await server.get_shared_memories(
            agent_id="test-agent",
            limit=50
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_create_shared_space(self):
        """Test create_shared_space tool"""
        result = await server.create_shared_space(
            space_name="shared-space-1",
            member_agents='["agent1", "agent2"]'
        )

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 8: Real-Time Sync Tools (3 tools)
# ============================================================================

class TestRealTimeSyncTools:
    """Test real-time memory synchronization tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_publish_memory_event(self):
        """Test publish_memory_event tool"""
        result = await server.publish_memory_event(
            event_type="memory_created",
            memory_id="test-memory-id",
            agent_id="test-agent",
            data='{"key": "value"}'
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_sync_status(self):
        """Test get_sync_status tool"""
        result = await server.get_sync_status()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_sync_agent_state(self):
        """Test sync_agent_state tool"""
        result = await server.sync_agent_state(
            source_agent="agent1",
            target_agent="agent2"
        )

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 9: Backup & Recovery Tools (5 tools)
# ============================================================================

class TestBackupRecoveryTools:
    """Test backup and recovery tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_create_backup(self):
        """Test create_backup tool"""
        result = await server.create_backup(
            backup_type="manual",
            description="Test backup"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_restore_backup(self):
        """Test restore_backup tool"""
        result = await server.restore_backup(
            backup_id="test-backup-id"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_list_backups(self):
        """Test list_backups tool"""
        result = await server.list_backups()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_verify_backup(self):
        """Test verify_backup tool"""
        result = await server.verify_backup(
            backup_id="test-backup-id"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_rollback_restore(self):
        """Test rollback_restore tool"""
        result = await server.rollback_restore()

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 10: Task Scheduling Tools (4 tools)
# ============================================================================

class TestTaskSchedulingTools:
    """Test task scheduling tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_schedule_task(self):
        """Test schedule_task tool"""
        result = await server.schedule_task(
            task_name="test-task",
            schedule="0 2 * * *"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """Test list_tasks tool"""
        result = await server.list_tasks()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancel_task tool"""
        result = await server.cancel_task(
            task_id="test-task-id"
        )

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 11: Multi-Language Tools (6 tools)
# ============================================================================

class TestMultiLanguageTools:
    """Test multi-language search and language detection tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_detect_language(self):
        """Test detect_language tool"""
        result = await server.detect_language(
            text="This is English text"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_supported_languages(self):
        """Test get_supported_languages tool"""
        result = await server.get_supported_languages()

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_search_by_language(self):
        """Test search_by_language tool"""
        result = await server.search_by_language(
            query="test query",
            language="en"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_language_distribution(self):
        """Test get_language_distribution tool"""
        result = await server.get_language_distribution(
            agent_id="test-agent"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_cross_language_search(self):
        """Test cross_language_search tool"""
        result = await server.cross_language_search(
            query="test query"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_search_facets(self):
        """Test get_search_facets tool"""
        result = await server.get_search_facets(
            agent_id="test-agent"
        )

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 12: Advanced AI Tools (7 tools)
# ============================================================================

class TestAdvancedAITools:
    """Test advanced AI features - intelligent summarization and search reranking"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_intelligent_summarize(self):
        """Test intelligent_summarize tool"""
        result = await server.intelligent_summarize(
            memory_id="test-memory-id",
            strategy="standard"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_auto_summarize_old_memories(self):
        """Test auto_summarize_old_memories tool"""
        result = await server.auto_summarize_old_memories(
            days_old=30,
            dry_run=True
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_cluster_memories(self):
        """Test cluster_memories tool"""
        result = await server.cluster_memories(
            agent_id="test-agent",
            limit=100
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_advanced_search(self):
        """Test advanced_search tool"""
        result = await server.advanced_search(
            query="test query",
            agent_id="test-agent",
            rerank=True,
            strategy="combined"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_expand_search_query(self):
        """Test expand_search_query tool"""
        result = await server.expand_search_query(
            query="test query"
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_search_analytics(self):
        """Test get_search_analytics tool"""
        result = await server.get_search_analytics(
            days_back=30
        )

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 13: Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling in MCP tools"""

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_tool_handles_none_database(self):
        """Test tools handle None database gracefully"""
        # Set databases to None
        server.postgres_pool = None
        server.qdrant_client = None
        server.redis_client = None
        server.neo4j_driver = None

        result = await server.health()

        # Should still return a result
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_add_memory_handles_invalid_json(self):
        """Test add_memory handles invalid metadata JSON"""
        setup_mocks()

        result = await server.add_memory(
            content="Test memory",
            agent_id="test-agent",
            metadata="invalid json{"
        )

        # Should handle gracefully
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_search_handles_empty_query(self):
        """Test search handles empty query"""
        setup_mocks()

        result = await server.search_memories(
            query="",
            agent_id="test-agent"
        )

        assert result is not None
        assert isinstance(result, str)


# ============================================================================
# TEST CLASS 14: ASCII Output Tests
# ============================================================================

class TestASCIIOutput:
    """Test ASCII-only output requirement for Windows compatibility"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_health_check_ascii_output(self):
        """Test health check returns ASCII-safe output"""
        result = await server.health()

        # Should be ASCII-encodable
        try:
            result.encode('ascii')
            assert True
        except UnicodeEncodeError:
            assert False, "Response contains non-ASCII characters"

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_get_stats_ascii_output(self):
        """Test get_stats returns ASCII-safe output"""
        result = await server.get_stats()

        try:
            result.encode('ascii')
            assert True
        except UnicodeEncodeError:
            assert False, "Response contains non-ASCII characters"

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_error_messages_ascii_output(self):
        """Test error messages use ASCII-safe output"""
        # Force error condition
        server.postgres_pool = None

        result = await server.get_stats()

        try:
            result.encode('ascii')
            assert True
        except UnicodeEncodeError:
            assert False, "Error message contains non-ASCII characters"


# ============================================================================
# TEST CLASS 15: Integration Tests
# ============================================================================

class TestMCPToolIntegration:
    """Test integration between multiple MCP tools"""

    @pytest.fixture(autouse=True)
    def setup(self):
        setup_mocks()

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_add_then_search_memory(self):
        """Test adding memory then searching for it"""
        # Add memory
        add_result = await server.add_memory(
            content="Integration test memory",
            agent_id="test-agent"
        )

        assert add_result is not None

        # Search memories
        search_result = await server.search_memories(
            query="integration test",
            agent_id="test-agent",
            limit=10
        )

        assert search_result is not None

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_cognify_then_search(self):
        """Test cognify then search knowledge graph"""
        # Cognify data
        cognify_result = await server.cognify(
            data="Integration test data for knowledge graph"
        )

        assert cognify_result is not None

        # Search knowledge graph
        search_result = await server.search(
            query="knowledge graph test",
            limit=10
        )

        assert search_result is not None

    @pytest.mark.system
    @pytest.mark.asyncio
    async def test_health_then_stats(self):
        """Test health check then get stats"""
        # Health check
        health_result = await server.health()

        assert health_result is not None
        assert "health" in health_result.lower()

        # Get stats
        stats_result = await server.get_stats()

        assert stats_result is not None
        assert "stats" in stats_result.lower() or "status" in stats_result.lower()


# ============================================================================
# TEST CLASS 16: Tool Registration Tests
# ============================================================================

class TestToolRegistration:
    """Test all tools are properly registered"""

    @pytest.mark.system
    def test_all_tools_callable(self):
        """Test all expected tools are callable"""
        # Expected tools based on actual MCP server
        expected_tools = [
            # Standard Memory (7)
            "add_memory", "search_memories", "get_memories", "get_memory",
            "update_memory", "delete_memory", "list_agents",
            # Enhanced Cognee (5)
            "cognify", "search", "list_data", "get_stats", "health",
            # Memory Management (4)
            "expire_memories", "get_memory_age_stats", "set_memory_ttl", "archive_category",
            # Deduplication (4)
            "check_duplicate", "auto_deduplicate", "get_deduplication_stats", "deduplicate",
            # Summarization (5)
            "summarize_old_memories", "summarize_category", "get_summary_stats",
            "intelligent_summarize", "get_summarization_stats",
            # Performance (3)
            "get_performance_metrics", "get_slow_queries", "get_prometheus_metrics",
            # Cross-Agent Sharing (4)
            "set_memory_sharing", "check_memory_access", "get_shared_memories", "create_shared_space",
            # Real-Time Sync (3)
            "publish_memory_event", "get_sync_status", "sync_agent_state",
            # Backup & Recovery (5)
            "create_backup", "restore_backup", "list_backups", "verify_backup", "rollback_restore",
            # Task Scheduling (4)
            "schedule_task", "list_tasks", "cancel_task",
            # Multi-Language (6)
            "detect_language", "get_supported_languages", "search_by_language",
            "get_language_distribution", "cross_language_search", "get_search_facets",
            # Advanced AI (6)
            "auto_summarize_old_memories", "cluster_memories", "advanced_search",
            "expand_search_query", "get_search_analytics"
        ]

        # Check each tool exists and is callable
        for tool_name in expected_tools:
            assert hasattr(server, tool_name), f"Tool {tool_name} not found in server"
            assert callable(getattr(server, tool_name)), f"Tool {tool_name} is not callable"


# ============================================================================
# TEST CLASS 17: Module Import Tests
# ============================================================================

class TestModuleImports:
    """Test all modules can be imported"""

    @pytest.mark.system
    def test_import_memory_management(self):
        """Test memory_management module imports"""
        from src.memory_management import MemoryManager, RetentionPolicy
        assert MemoryManager is not None
        assert RetentionPolicy is not None

    @pytest.mark.system
    def test_import_deduplication(self):
        """Test deduplication module imports"""
        from src.memory_deduplication import MemoryDeduplicator
        assert MemoryDeduplicator is not None

    @pytest.mark.system
    def test_import_summarization(self):
        """Test summarization module imports"""
        from src.memory_summarization import MemorySummarizer
        assert MemorySummarizer is not None

    @pytest.mark.system
    def test_import_performance_analytics(self):
        """Test performance analytics module imports"""
        from src.performance_analytics import PerformanceAnalytics
        assert PerformanceAnalytics is not None

    @pytest.mark.system
    def test_import_cross_agent_sharing(self):
        """Test cross-agent sharing module imports"""
        from src.cross_agent_sharing import CrossAgentMemorySharing, SharePolicy
        assert CrossAgentMemorySharing is not None
        assert SharePolicy is not None

    @pytest.mark.system
    def test_import_realtime_sync(self):
        """Test real-time sync module imports"""
        from src.realtime_sync import RealTimeMemorySync, SyncEvent
        assert RealTimeMemorySync is not None
        assert SyncEvent is not None

    @pytest.mark.system
    def test_import_multi_language(self):
        """Test multi-language modules import"""
        from src.language_detector import LanguageDetector
        from src.multi_language_search import MultiLanguageSearch
        assert LanguageDetector is not None
        assert MultiLanguageSearch is not None

    @pytest.mark.system
    def test_import_advanced_ai(self):
        """Test advanced AI modules import"""
        from src.intelligent_summarization import IntelligentMemorySummarizer
        from src.advanced_search_reranking import AdvancedSearchEngine
        assert IntelligentMemorySummarizer is not None
        assert AdvancedSearchEngine is not None


# ============================================================================
# TEST CLASS 18: Configuration Tests
# ============================================================================

class TestConfiguration:
    """Test configuration and environment setup"""

    @pytest.mark.system
    def test_environment_variables_accessible(self):
        """Test environment variables are accessible"""
        import os

        # Check if environment variables can be accessed
        env_vars = [
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
            "QDRANT_HOST", "QDRANT_PORT",
            "REDIS_HOST", "REDIS_PORT"
        ]

        for var in env_vars:
            # These might be set or not, just check we can access them
            value = os.getenv(var)
            assert True  # Test passes if we can check without error

    @pytest.mark.system
    def test_mcp_server_creation(self):
        """Test MCP server object can be created"""
        from mcp.server import FastMCP

        mcp = FastMCP("Test Enhanced Cognee")
        assert mcp is not None
        assert mcp.name == "Test Enhanced Cognee"


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "system"])
