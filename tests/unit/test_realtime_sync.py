"""
Unit Tests for Real-Time Sync Module
Tests Redis pub/sub, event broadcasting, agent synchronization
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, MagicMock
from src.realtime_sync import RealTimeMemorySync, SyncEvent


# ============================================================================
# Test RealTimeMemorySync Initialization
# ============================================================================

class TestRealTimeSyncInit:
    """Test RealTimeMemorySync initialization"""

    @pytest.mark.unit
    def test_init_with_valid_dependencies(self, mock_redis_client, mock_postgres_pool):
        """Test initialization with all dependencies"""
        sync = RealTimeMemorySync(mock_redis_client, mock_postgres_pool)

        assert sync.redis_client is not None
        assert sync.postgres_pool is not None
        assert sync.sync_channel == "enhanced_cognee:memory_updates"
        assert sync.subscriptions == {}


# ============================================================================
# Test Publishing Memory Events
# ============================================================================

class TestPublishMemoryEvent:
    """Test publish_memory_event method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_memory_added_event(self, realtime_sync):
        """Test publishing memory_added event"""
        realtime_sync.redis_client.publish = AsyncMock(return_value=1)

        result = await realtime_sync.publish_memory_event(
            event_type="memory_added",
            memory_id="mem-123",
            agent_id="agent-1",
            data={"test": "data"}
        )

        assert result["status"] == "success"
        assert result["event_type"] == "memory_added"
        assert result["memory_id"] == "mem-123"

        # Verify Redis publish was called
        realtime_sync.redis_client.publish.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_memory_updated_event(self, realtime_sync):
        """Test publishing memory_updated event"""
        realtime_sync.redis_client.publish = AsyncMock(return_value=2)

        result = await realtime_sync.publish_memory_event(
            event_type="memory_updated",
            memory_id="mem-456",
            agent_id="agent-2",
            data={"changes": ["content", "metadata"]}
        )

        assert result["status"] == "success"
        assert result["event_type"] == "memory_updated"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_memory_deleted_event(self, realtime_sync):
        """Test publishing memory_deleted event"""
        realtime_sync.redis_client.publish = AsyncMock(return_value=1)

        result = await realtime_sync.publish_memory_event(
            event_type="memory_deleted",
            memory_id="mem-789",
            agent_id="agent-3",
            data={"reason": "expired"}
        )

        assert result["status"] == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_event_serialization(self, realtime_sync):
        """Test event data is properly serialized"""
        realtime_sync.redis_client.publish = AsyncMock(return_value=1)

        result = await realtime_sync.publish_memory_event(
            event_type="memory_added",
            memory_id="mem-1",
            agent_id="agent-1",
            data={"nested": {"data": "value"}}
        )

        # Get the call arguments
        call_args = realtime_sync.redis_client.publish.call_args
        channel = call_args[0][0]
        message = call_args[0][1]

        assert channel == "enhanced_cognee:memory_updates"
        # Verify JSON serialization
        event_data = json.loads(message)
        assert event_data["memory_id"] == "mem-1"
        assert event_data["data"]["nested"]["data"] == "value"


# ============================================================================
# Test Subscribing to Updates
# ============================================================================

class TestSubscribeToUpdates:
    """Test subscribe_to_updates method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscribe_agent(self, realtime_sync):
        """Test subscribing an agent to updates"""
        callback = AsyncMock()

        result = await realtime_sync.subscribe_to_updates(
            agent_id="agent-1",
            callback=callback
        )

        assert result["status"] == "success"
        assert result["agent_id"] == "agent-1"
        assert "agent-1" in realtime_sync.subscriptions
        assert realtime_sync.subscriptions["agent-1"] == callback

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscribe_multiple_agents(self, realtime_sync):
        """Test subscribing multiple agents"""
        callback1 = AsyncMock()
        callback2 = AsyncMock()

        await realtime_sync.subscribe_to_updates("agent-1", callback1)
        await realtime_sync.subscribe_to_updates("agent-2", callback2)

        assert len(realtime_sync.subscriptions) == 2
        assert "agent-1" in realtime_sync.subscriptions
        assert "agent-2" in realtime_sync.subscriptions

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscribe_duplicate_agent(self, realtime_sync):
        """Test subscribing same agent twice replaces callback"""
        callback1 = AsyncMock()
        callback2 = AsyncMock()

        await realtime_sync.subscribe_to_updates("agent-1", callback1)
        await realtime_sync.subscribe_to_updates("agent-1", callback2)

        # Should replace callback
        assert realtime_sync.subscriptions["agent-1"] == callback2


# ============================================================================
# Test Event Handling
# ============================================================================

class TestHandleSyncEvent:
    """Test _handle_sync_event method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_event_notifies_subscribers(self, realtime_sync):
        """Test handling event notifies all subscribers except sender"""
        # Setup subscriptions
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        await realtime_sync.subscribe_to_updates("agent-1", callback1)
        await realtime_sync.subscribe_to_updates("agent-2", callback2)

        # Create event from agent-1
        event = {
            "event_type": "memory_added",
            "memory_id": "mem-1",
            "agent_id": "agent-1",
            "data": {}
        }

        await realtime_sync._handle_sync_event(event)

        # agent-1 should not be notified (sender)
        callback1.assert_not_called()

        # agent-2 should be notified
        callback2.assert_called_once_with(event)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_event_with_no_subscribers(self, realtime_sync):
        """Test handling event when no subscribers"""
        event = {
            "event_type": "memory_added",
            "memory_id": "mem-1",
            "agent_id": "agent-1",
            "data": {}
        }

        # Should not raise error
        await realtime_sync._handle_sync_event(event)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_event_callback_error(self, realtime_sync):
        """Test handling when callback raises error"""
        failing_callback = AsyncMock(side_effect=Exception("Callback failed"))
        working_callback = AsyncMock()

        await realtime_sync.subscribe_to_updates("agent-1", failing_callback)
        await realtime_sync.subscribe_to_updates("agent-2", working_callback)

        event = {
            "event_type": "memory_added",
            "memory_id": "mem-1",
            "agent_id": "agent-3",  # Different from subscribers
            "data": {}
        }

        # Should not raise, should continue working
        await realtime_sync._handle_sync_event(event)

        # Both callbacks should be attempted
        failing_callback.assert_called_once()
        working_callback.assert_called_once()


# ============================================================================
# Test Broadcast Memory Update
# ============================================================================

class TestBroadcastMemoryUpdate:
    """Test broadcast_memory_update method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_broadcast_to_all_agents(self, realtime_sync, create_async_context_manager):
        """Test broadcasting to all subscribed agents"""
        # Setup subscriptions
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        await realtime_sync.subscribe_to_updates("agent-1", callback1)
        await realtime_sync.subscribe_to_updates("agent-2", callback2)

        # Mock database query
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "mem-1",
            "content": "test content",
            "agent_id": "agent-1",
            "memory_category": "test"
        })
        ctx_mgr = create_async_context_manager(mock_conn)
        realtime_sync.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await realtime_sync.broadcast_memory_update(
            memory_id="mem-1",
            update_type="updated",
            agent_id="agent-1"
        )

        assert result["status"] == "success"
        assert result["agents_notified"] == 1  # Only agent-2 (not sender)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_broadcast_to_target_agents(self, realtime_sync, create_async_context_manager):
        """Test broadcasting to specific target agents"""
        # Setup subscriptions
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        callback3 = AsyncMock()
        await realtime_sync.subscribe_to_updates("agent-1", callback1)
        await realtime_sync.subscribe_to_updates("agent-2", callback2)
        await realtime_sync.subscribe_to_updates("agent-3", callback3)

        # Mock database
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "mem-1",
            "content": "content",
            "agent_id": "agent-1",
            "memory_category": "test"
        })
        ctx_mgr = create_async_context_manager(mock_conn)
        realtime_sync.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await realtime_sync.broadcast_memory_update(
            memory_id="mem-1",
            update_type="updated",
            agent_id="agent-1",
            target_agents=["agent-2"]  # Only notify agent-2
        )

        assert result["status"] == "success"
        callback1.assert_not_called()  # Sender
        callback2.assert_called_once()  # Target
        callback3.assert_not_called()  # Not in target list

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_broadcast_memory_not_found(self, realtime_sync, create_async_context_manager):
        """Test broadcasting non-existent memory"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        ctx_mgr = create_async_context_manager(mock_conn)
        realtime_sync.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await realtime_sync.broadcast_memory_update(
            memory_id="non-existent",
            update_type="updated",
            agent_id="agent-1"
        )

        assert result["status"] == "not_found"


# ============================================================================
# Test Agent State Synchronization
# ============================================================================

class TestSyncAgentState:
    """Test sync_agent_state method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_all_memories(self, realtime_sync, create_async_context_manager):
        """Test syncing all memories between agents"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "mem-1", "content": "content1", "metadata": {}},
            {"id": "mem-2", "content": "content2", "metadata": {}}
        ])
        mock_conn.execute = AsyncMock(return_value="INSERT 1")
        ctx_mgr = create_async_context_manager(mock_conn)
        realtime_sync.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await realtime_sync.sync_agent_state(
            source_agent_id="agent-1",
            target_agent_id="agent-2"
        )

        assert result["status"] == "success"
        assert result["source_agent"] == "agent-1"
        assert result["target_agent"] == "agent-2"
        assert result["memories_synced"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_with_category_filter(self, realtime_sync, create_async_context_manager):
        """Test syncing with category filter"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "mem-1", "content": "content", "metadata": {}}
        ])
        mock_conn.execute = AsyncMock(return_value="INSERT 1")
        ctx_mgr = create_async_context_manager(mock_conn)
        realtime_sync.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await realtime_sync.sync_agent_state(
            source_agent_id="agent-1",
            target_agent_id="agent-2",
            memory_category="requirements"
        )

        assert result["status"] == "success"
        # Verify category was used in query
        fetch_call = mock_conn.fetch.call_args
        assert "requirements" in str(fetch_call)


# ============================================================================
# Test Sync Status
# ============================================================================

class TestGetSyncStatus:
    """Test get_sync_status method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_sync_status_active(self, realtime_sync):
        """Test getting sync status with active subscriptions"""
        # Add some subscriptions
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        await realtime_sync.subscribe_to_updates("agent-1", callback1)
        await realtime_sync.subscribe_to_updates("agent-2", callback2)

        realtime_sync.redis_client.info = AsyncMock(return_value={
            "connected_clients": 5
        })

        status = await realtime_sync.get_sync_status()

        assert status["status"] == "active"
        assert status["subscribers_count"] == 2
        assert "agent-1" in status["subscribed_agents"]
        assert "agent-2" in status["subscribed_agents"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_sync_status_empty(self, realtime_sync):
        """Test getting sync status with no subscriptions"""
        realtime_sync.redis_client.info = AsyncMock(return_value={
            "connected_clients": 1
        })

        status = await realtime_sync.get_sync_status()

        assert status["status"] == "active"
        assert status["subscribers_count"] == 0
        assert len(status["subscribed_agents"]) == 0


# ============================================================================
# Test Conflict Resolution
# ============================================================================

class TestResolveConflict:
    """Test resolve_conflict method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resolve_keep_newest(self, realtime_sync, create_async_context_manager):
        """Test resolving conflict with keep_newest strategy"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        ctx_mgr = create_async_context_manager(mock_conn)
        realtime_sync.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await realtime_sync.resolve_conflict(
            memory_id="mem-1",
            conflict_data={"type": "concurrent_update"},
            resolution_strategy="keep_newest"
        )

        assert result["status"] == "success"
        assert result["resolution"] == "keep_newest"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resolve_merge(self, realtime_sync, create_async_context_manager):
        """Test resolving conflict with merge strategy"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        ctx_mgr = create_async_context_manager(mock_conn)
        realtime_sync.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await realtime_sync.resolve_conflict(
            memory_id="mem-1",
            conflict_data={"type": "concurrent_update"},
            resolution_strategy="merge"
        )

        assert result["status"] == "success"
        assert result["resolution"] == "merge"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resolve_unknown_strategy(self, realtime_sync):
        """Test resolving conflict with unknown strategy"""
        result = await realtime_sync.resolve_conflict(
            memory_id="mem-1",
            conflict_data={},
            resolution_strategy="unknown"
        )

        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in RealTimeMemorySync"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_error(self, realtime_sync):
        """Test handling publish errors"""
        realtime_sync.redis_client.publish = AsyncMock(
            side_effect=Exception("Redis connection lost")
        )

        result = await realtime_sync.publish_memory_event(
            event_type="memory_added",
            memory_id="mem-1",
            agent_id="agent-1",
            data={}
        )

        assert result["status"] == "error"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscribe_error(self, realtime_sync):
        """Test handling subscribe errors"""
        # Force an error
        with pytest.raises(Exception):
            await realtime_sync.subscribe_to_updates(None, None)


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_memory_id(self, realtime_sync, create_async_context_manager):
        """Test broadcasting with empty memory ID"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        ctx_mgr = create_async_context_manager(mock_conn)
        realtime_sync.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await realtime_sync.broadcast_memory_update(
            memory_id="",
            update_type="updated",
            agent_id="agent-1"
        )

        assert result["status"] == "not_found"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_very_long_data(self, realtime_sync):
        """Test publishing event with very large data"""
        realtime_sync.redis_client.publish = AsyncMock(return_value=1)

        large_data = {"data": "x" * 1000000}

        result = await realtime_sync.publish_memory_event(
            event_type="memory_added",
            memory_id="mem-1",
            agent_id="agent-1",
            data=large_data
        )

        assert result["status"] == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_special_characters_in_event(self, realtime_sync):
        """Test event with special characters"""
        realtime_sync.redis_client.publish = AsyncMock(return_value=1)

        result = await realtime_sync.publish_memory_event(
            event_type="memory_added",
            memory_id="mem-1",
            agent_id="agent-1",
            data={"text": "Emoji: 🎉, Unicode: 中文, Symbols: ©®"}
        )

        assert result["status"] == "success"


# ============================================================================
# Test SyncEvent Dataclass
# ============================================================================

class TestSyncEventDataclass:
    """Test SyncEvent dataclass"""

    @pytest.mark.unit
    def test_sync_event_creation(self):
        """Test creating SyncEvent instance"""
        event = SyncEvent(
            event_type="memory_added",
            memory_id="mem-1",
            agent_id="agent-1",
            timestamp=datetime.utcnow(),
            data={"test": "data"}
        )

        assert event.event_type == "memory_added"
        assert event.memory_id == "mem-1"
        assert event.agent_id == "agent-1"
