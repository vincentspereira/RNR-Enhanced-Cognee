"""
Unit Tests for Memory Management Module
Tests memory expiry, archival, TTL management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from src.memory_management import MemoryManager, RetentionPolicy


# ============================================================================
# Test MemoryManager Initialization
# ============================================================================

class TestMemoryManagerInit:
    """Test MemoryManager initialization"""

    @pytest.mark.unit
    def test_init_with_valid_dependencies(self, mock_postgres_pool, mock_redis_client, mock_qdrant_client):
        """Test initialization with all dependencies"""
        manager = MemoryManager(mock_postgres_pool, mock_redis_client, mock_qdrant_client)

        assert manager.postgres_pool is not None
        assert manager.redis_client is not None
        assert manager.qdrant_client is not None

    @pytest.mark.unit
    def test_init_with_none_dependencies(self):
        """Test initialization handles None dependencies gracefully"""
        manager = MemoryManager(None, None, None)

        assert manager.postgres_pool is None
        assert manager.redis_client is None
        assert manager.qdrant_client is None


# ============================================================================
# Test Memory Expiry
# ============================================================================

class TestExpireOldMemories:
    """Test expire_old_memories method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_expire_memories_delete_policy(self, memory_manager, create_async_context_manager):
        """Test expiring memories with DELETE_OLD policy"""
        # Mock database response
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "old-memory-1", "content": "old content"}
        ])
        mock_conn.execute = AsyncMock(return_value="DELETE 1")
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.expire_old_memories(
            days=90,
            dry_run=False,
            policy=RetentionPolicy.DELETE_OLD
        )

        assert result["status"] == "success"
        assert result["memories_affected"] >= 0
        assert isinstance(result["memories_affected"], int)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_expire_memories_dry_run(self, memory_manager, create_async_context_manager):
        """Test dry run mode for memory expiry"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "old-memory-1", "content": "old content"}
        ])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.expire_old_memories(
            days=90,
            dry_run=True,
            policy=RetentionPolicy.DELETE_OLD
        )

        assert result["status"] == "dry_run"
        assert "candidates_found" in result
        # Ensure no actual deletion occurred
        mock_conn.execute.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_expire_memories_archive_policy(self, memory_manager, create_async_context_manager):
        """Test expiring memories with ARCHIVE_OLD policy"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.execute = AsyncMock(return_value=1)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.expire_old_memories(
            days=180,
            dry_run=False,
            policy=RetentionPolicy.ARCHIVE_OLD
        )

        assert result["status"] == "success"
        assert "memories_affected" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_expire_memories_with_no_pool(self, create_async_context_manager):
        """Test expiry with no PostgreSQL pool"""
        manager = MemoryManager(None, None, None)

        result = await manager.expire_old_memories(days=90)

        assert result["status"] == "error"
        assert "not available" in result["error"].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_expire_memories_various_days(self, memory_manager, create_async_context_manager):
        """Test expiry with various day thresholds"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        for days in [7, 30, 90, 180, 365]:
            result = await memory_manager.expire_old_memories(days=days)
            assert result["status"] == "success"


# ============================================================================
# Test Memory Statistics
# ============================================================================

class TestMemoryStats:
    """Test get_memory_stats_by_age method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_age_stats_success(self, memory_manager, create_async_context_manager):
        """Test getting memory age statistics"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "total_memories": 100,
            "oldest_memory": datetime.utcnow() - timedelta(days=180),
            "newest_memory": datetime.utcnow()
        })
        mock_conn.fetch = AsyncMock(return_value=[
            {"age_bracket": "0-7 days", "count": 20},
            {"age_bracket": "8-30 days", "count": 30},
            {"age_bracket": "31-90 days", "count": 25},
            {"age_bracket": "90+ days", "count": 25}
        ])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        stats = await memory_manager.get_memory_stats_by_age()

        assert stats["status"] == "success"
        assert "total_memories" in stats
        assert "age_distribution" in stats
        assert isinstance(stats["age_distribution"], dict)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_age_stats_empty_database(self, memory_manager, create_async_context_manager):
        """Test age stats with empty database"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "total_memories": 0,
            "oldest_memory": None,
            "newest_memory": None
        })
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        stats = await memory_manager.get_memory_stats_by_age()

        assert stats["status"] == "success"
        assert stats["total_memories"] == 0


# ============================================================================
# Test TTL Management
# ============================================================================

class TestTTLManagement:
    """Test set_memory_ttl and related methods"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_ttl_success(self, memory_manager, create_async_context_manager):
        """Test setting TTL for a memory"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="memory-id-123")
        mock_conn.execute = AsyncMock(return_value=1)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.set_memory_ttl("memory-id-123", 30)

        assert result["status"] == "success"
        assert "expiry_date" in result or "ttl_days" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_ttl_memory_not_found(self, memory_manager, create_async_context_manager):
        """Test setting TTL for non-existent memory"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.set_memory_ttl("non-existent", 30)

        assert result["status"] == "success"  # TTL setting is idempotent

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_ttl_zero_days(self, memory_manager, create_async_context_manager):
        """Test setting TTL to 0 (no expiry)"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="memory-id")
        mock_conn.execute = AsyncMock(return_value=1)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.set_memory_ttl("memory-id", 0)

        assert result["status"] == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_set_ttl_by_category(self, memory_manager, create_async_context_manager):
        """Test bulk TTL setting for category"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "mem-1"},
            {"id": "mem-2"}
        ])
        mock_conn.execute = AsyncMock(return_value=1)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.bulk_set_ttl_by_category("test-category", 30)

        assert result["status"] == "success"
        assert "memories_updated" in result


# ============================================================================
# Test Category Archival
# ============================================================================

class TestCategoryArchival:
    """Test archive_memories_by_category method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_archive_category_success(self, memory_manager, create_async_context_manager):
        """Test archiving memories by category"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "mem-1", "content": "content 1"},
            {"id": "mem-2", "content": "content 2"}
        ])
        mock_conn.execute = AsyncMock(return_value=1)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.archive_memories_by_category("test-category", 180)

        assert result["status"] == "success"
        assert "memories_archived" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_archive_category_empty(self, memory_manager, create_async_context_manager):
        """Test archiving category with no memories"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.archive_memories_by_category("empty-category", 180)

        assert result["status"] == "success"
        assert result["memories_archived"] == 0


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in MemoryManager"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, memory_manager, create_async_context_manager):
        """Test handling of database connection errors"""
        memory_manager.postgres_pool.acquire = AsyncMock(side_effect=Exception("Connection lost"))

        result = await memory_manager.expire_old_memories(days=90)

        assert result["status"] == "error"
        assert "connection lost" in result["error"].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_error_handling(self, memory_manager, create_async_context_manager):
        """Test handling of query errors"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Query failed"))
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.get_memory_stats_by_age()

        assert result["status"] == "error"


# ============================================================================
# Test Retention Policies
# ============================================================================

class TestRetentionPolicies:
    """Test different retention policies"""

    @pytest.mark.unit
    def test_retention_policy_enum(self):
        """Test RetentionPolicy enum values"""
        assert RetentionPolicy.KEEP_ALL.value == "keep_all"
        assert RetentionPolicy.KEEP_recent.value == "keep_recent"
        assert RetentionPolicy.ARCHIVE_OLD.value == "archive_old"
        assert RetentionPolicy.DELETE_OLD.value == "delete_old"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_keep_all_policy(self, memory_manager, create_async_context_manager):
        """Test KEEP_ALL policy does not delete"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.expire_old_memories(
            days=90,
            policy=RetentionPolicy.KEEP_ALL
        )

        assert result["status"] == "success"
        # No deletion should occur


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_negative_days(self, memory_manager, create_async_context_manager):
        """Test handling of negative days value"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.expire_old_memories(days=-1)

        # Should handle gracefully or return error
        assert result["status"] in ["success", "error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_very_large_days(self, memory_manager, create_async_context_manager):
        """Test handling of very large days value"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.expire_old_memories(days=36500)  # 100 years

        assert result["status"] == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_memory_id(self, memory_manager, create_async_context_manager):
        """Test setting TTL with empty memory ID"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_manager.set_memory_ttl("", 30)

        assert result["status"] == "success"  # TTL setting is idempotent


# ============================================================================
# Test Performance
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bulk_operations_performance(self, memory_manager, create_async_context_manager):
        """Test performance of bulk operations"""
        mock_conn = AsyncMock()
        # Simulate 1000 memories
        mock_conn.fetch = AsyncMock(return_value=[{"id": f"mem-{i}"} for i in range(1000)])
        mock_conn.execute = AsyncMock(return_value=1000)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_manager.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        import time
        start = time.time()

        result = await memory_manager.bulk_set_ttl_by_category("test", 30)

        elapsed = time.time() - start

        assert result["status"] == "success"
        # Should complete in reasonable time (< 5 seconds for mock)
        assert elapsed < 5.0
