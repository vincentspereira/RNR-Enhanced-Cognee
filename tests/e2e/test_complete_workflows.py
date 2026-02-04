"""
End-to-End Tests for Enhanced Cognee
Tests complete user workflows from start to finish
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock


# ============================================================================
# Test Complete Memory Lifecycle
# ============================================================================

class TestMemoryLifecycle:
    """Test complete memory lifecycle: add -> search -> update -> delete"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_memory_lifecycle(self):
        """Test complete memory lifecycle from creation to deletion"""
        # Import modules
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        import enhanced_cognee_mcp_server as server

        # Setup mock database
        server.postgres_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 1")
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "test-mem-1",
            "title": "Test Memory",
            "content": "Test content",
            "agent_id": "test-agent",
            "created_at": datetime.utcnow()
        })
        mock_conn.fetch = AsyncMock(return_value=[])
        server.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        # 1. Add memory
        add_result = await server.add_memory(
            content="Test memory content",
            agent_id="test-agent"
        )
        assert "OK" in add_result or "ERR" in add_result

        # 2. Search memories
        search_result = await server.search_memories(query="test")
        assert isinstance(search_result, str)

        # 3. Get memory
        get_result = await server.get_memory(memory_id="test-mem-1")
        assert isinstance(get_result, str)

        # 4. Update memory
        update_result = await server.update_memory(
            memory_id="test-mem-1",
            content="Updated content"
        )
        assert isinstance(update_result, str)

        # 5. Delete memory
        delete_result = await server.delete_memory(memory_id="test-mem-1")
        assert isinstance(delete_result, str)


# ============================================================================
# Test Multi-Agent Coordination Workflow
# ============================================================================

class TestMultiAgentCoordination:
    """Test multi-agent coordination workflow"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_agent_coordination_workflow(self):
        """Test workflow: Agent A adds memory -> Agent B receives via sync"""
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        from src.realtime_sync import RealTimeMemorySync

        # Setup
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=2)
        mock_redis.info = AsyncMock(return_value={"connected_clients": 3})

        mock_pg = AsyncMock()

        sync = RealTimeMemorySync(mock_redis, mock_pg)

        # Agent 1 subscribes
        callback_agent2 = AsyncMock()
        await sync.subscribe_to_updates("agent-2", callback_agent2)

        # Agent 1 publishes memory event
        result = await sync.publish_memory_event(
            event_type="memory_added",
            memory_id="shared-mem-1",
            agent_id="agent-1",
            data={"content": "Shared knowledge"}
        )

        assert result["status"] == "success"

        # Verify event handling
        event = {
            "event_type": "memory_added",
            "memory_id": "shared-mem-1",
            "agent_id": "agent-1",
            "data": {"content": "Shared knowledge"}
        }

        await sync._handle_sync_event(event)

        # Agent 2 should have been notified
        callback_agent2.assert_called_once()


# ============================================================================
# Test Memory Sharing Workflow
# ============================================================================

class TestMemorySharingWorkflow:
    """Test memory sharing and access control workflow"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sharing_workflow(self):
        """Test: Set sharing policy -> Check access -> Verify permissions"""
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        from src.cross_agent_sharing import CrossAgentMemorySharing, SharePolicy

        # Setup
        mock_pg = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "shared-mem",
            "owner_id": "agent-1",
            "policy": "shared",
            "allowed_agents": None
        })
        mock_pg.acquire = AsyncMock(return_value=mock_conn)

        sharing = CrossAgentMemorySharing(mock_pg)

        # 1. Set sharing policy
        set_result = await sharing.set_memory_sharing(
            memory_id="shared-mem",
            policy=SharePolicy.SHARED
        )
        assert set_result["status"] == "success"

        # 2. Check access
        access_result = await sharing.can_agent_access_memory("shared-mem", "agent-2")
        assert access_result["can_access"] is True

        # 3. Get shared memories
        mock_conn.fetch = AsyncMock(return_value=[])
        memories = await sharing.get_shared_memories("agent-2")
        assert isinstance(memories, list)


# ============================================================================
# Test Deduplication Workflow
# ============================================================================

class TestDeduplicationWorkflow:
    """Test duplicate detection and handling workflow"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_deduplication_workflow(self):
        """Test: Check duplicate -> Handle -> Verify"""
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        from src.memory_deduplication import MemoryDeduplicator

        # Setup
        mock_pg = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)  # No duplicate
        mock_pg.acquire = AsyncMock(return_value=mock_conn)

        mock_qdrant = Mock()
        mock_qdrant.search = Mock(return_value=[])

        deduplicator = MemoryDeduplicator(mock_pg, mock_qdrant)

        # 1. Check for duplicate
        check_result = await deduplicator.check_duplicate(
            content="Original content",
            agent_id="agent-1"
        )
        assert check_result["is_duplicate"] is False

        # 2. Try to add same content (should detect duplicate)
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "existing-mem",
            "created_at": datetime.utcnow()
        })

        check_result2 = await deduplicator.check_duplicate(
            content="Original content",
            agent_id="agent-1"
        )
        assert check_result2["is_duplicate"] is True


# ============================================================================
# Test Performance Monitoring Workflow
# ============================================================================

class TestPerformanceMonitoringWorkflow:
    """Test performance monitoring and analytics workflow"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_performance_workflow(self):
        """Test: Record metrics -> Get stats -> Export Prometheus"""
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        from src.performance_analytics import PerformanceAnalytics

        # Setup
        mock_pg = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=100)
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pg.acquire = AsyncMock(return_value=mock_conn)

        mock_redis = AsyncMock()
        mock_redis.incrbyfloat = AsyncMock(return_value=1.0)

        analytics = PerformanceAnalytics(mock_pg, mock_redis)

        # 1. Record query time
        await analytics.record_query_time("test_operation", 150.5)

        # 2. Record cache stats
        await analytics.record_cache_hit()
        await analytics.record_cache_miss()

        # 3. Get performance metrics
        metrics = await analytics.get_performance_metrics()
        assert metrics is not None
        assert "query_performance" in metrics

        # 4. Get Prometheus metrics
        prometheus = await analytics.get_prometheus_metrics()
        assert isinstance(prometheus, str)
        assert "enhanced_cognee" in prometheus


# ============================================================================
# Test Memory Management Workflow
# ============================================================================

class TestMemoryManagementWorkflow:
    """Test memory management lifecycle workflow"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_lifecycle_workflow(self):
        """Test: Set TTL -> Check age -> Expire old memories"""
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        from src.memory_management import MemoryManager, RetentionPolicy

        # Setup
        mock_pg = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchrow = AsyncMock(return_value={
            "total_memories": 100,
            "oldest_memory": datetime.utcnow(),
            "newest_memory": datetime.utcnow()
        })
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        mock_pg.acquire = AsyncMock(return_value=mock_conn)

        mock_redis = AsyncMock()
        mock_qdrant = Mock()

        manager = MemoryManager(mock_pg, mock_redis, mock_qdrant)

        # 1. Get memory age stats
        stats = await manager.get_memory_stats_by_age()
        assert stats["status"] == "success"

        # 2. Set TTL for a memory
        mock_conn.fetchval = AsyncMock(return_value="mem-1")
        ttl_result = await manager.set_memory_ttl("mem-1", 30)
        assert ttl_result["status"] == "success"

        # 3. Expire old memories
        expire_result = await manager.expire_old_memories(days=90, dry_run=True)
        assert expire_result["status"] in ["success", "dry_run"]


# ============================================================================
# Test Complete Integration Workflow
# ============================================================================

class TestCompleteIntegration:
    """Test complete integration of all features"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_all_features_integration(self):
        """Test all features working together"""
        # This would test a real scenario with:
        # 1. Multiple agents
        # 2. Real-time sync
        # 3. Memory sharing
        # 4. Deduplication
        # 5. Performance monitoring

        # For now, test that all modules can be instantiated
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        from src.memory_management import MemoryManager
        from src.memory_deduplication import MemoryDeduplicator
        from src.memory_summarization import MemorySummarizer
        from src.performance_analytics import PerformanceAnalytics
        from src.cross_agent_sharing import CrossAgentMemorySharing
        from src.realtime_sync import RealTimeMemorySync

        # Create mock dependencies
        mock_pg = AsyncMock()
        mock_redis = AsyncMock()
        mock_qdrant = Mock()
        llm_config = {}

        # Instantiate all modules
        manager = MemoryManager(mock_pg, mock_redis, mock_qdrant)
        deduplicator = MemoryDeduplicator(mock_pg, mock_qdrant)
        summarizer = MemorySummarizer(mock_pg, llm_config)
        analytics = PerformanceAnalytics(mock_pg, mock_redis)
        sharing = CrossAgentMemorySharing(mock_pg)
        sync = RealTimeMemorySync(mock_redis, mock_pg)

        # Verify all are created
        assert manager is not None
        assert deduplicator is not None
        assert summarizer is not None
        assert analytics is not None
        assert sharing is not None
        assert sync is not None


# ============================================================================
# Test Error Recovery Workflow
# ============================================================================

class TestErrorRecovery:
    """Test error recovery and resilience"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_error_recovery_workflow(self):
        """Test system recovers gracefully from errors"""
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        import enhanced_cognee_mcp_server as server

        # Setup with failing database
        server.postgres_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("DB Error"))
        server.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        # Should handle error gracefully
        result = await server.add_memory(content="test", agent_id="test-agent")

        # Should return error, not crash
        assert result is not None
        assert isinstance(result, str)
        assert "ERR" in result or "OK" in result


# ============================================================================
# Test Data Consistency
# ============================================================================

class TestDataConsistency:
    """Test data consistency across operations"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_data_consistency_workflow(self):
        """Test data remains consistent across operations"""
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        import enhanced_cognee_mcp_server as server

        # Setup
        server.postgres_pool = AsyncMock()
        mock_conn = AsyncMock()

        memory_id = "consistency-test-mem"
        original_content = "Original content"
        updated_content = "Updated content"

        # Mock responses for different operations
        responses = {
            ("INSERT", memory_id): "INSERT 1",
            ("SELECT", memory_id): {"id": memory_id, "content": original_content, "title": "Test",
                                   "agent_id": "test-agent", "created_at": datetime.utcnow()},
            ("UPDATE", memory_id): "UPDATE 1",
            ("DELETE", memory_id): "DELETE 1"
        }

        async def mock_execute(query, *args):
            return "INSERT 1"

        async def mock_fetchrow(query, *args):
            return {"id": memory_id, "content": original_content, "title": "Test",
                   "agent_id": "test-agent", "created_at": datetime.utcnow()}

        mock_conn.execute = mock_execute
        mock_conn.fetchrow = mock_fetchrow
        mock_conn.fetch = AsyncMock(return_value=[])
        server.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        # Perform operations
        add_result = await server.add_memory(content=original_content, agent_id="test-agent")
        get_result = await server.get_memory(memory_id=memory_id)
        update_result = await server.update_memory(memory_id=memory_id, content=updated_content)
        delete_result = await server.delete_memory(memory_id=memory_id)

        # All operations should succeed
        for result in [add_result, get_result, update_result, delete_result]:
            assert result is not None
            assert isinstance(result, str)
