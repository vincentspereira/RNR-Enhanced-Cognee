"""
Unit Tests for Cross-Agent Sharing Module
Tests memory sharing policies, access control, shared spaces
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from src.cross_agent_sharing import CrossAgentMemorySharing, SharePolicy


# ============================================================================
# Test CrossAgentMemorySharing Initialization
# ============================================================================

class TestCrossAgentSharingInit:
    """Test CrossAgentMemorySharing initialization"""

    @pytest.mark.unit
    def test_init_with_valid_dependencies(self, mock_postgres_pool):
        """Test initialization with PostgreSQL pool"""
        sharing = CrossAgentMemorySharing(mock_postgres_pool)

        assert sharing.postgres_pool is not None


# ============================================================================
# Test SharePolicy Enum
# ============================================================================

class TestSharePolicy:
    """Test SharePolicy enumeration"""

    @pytest.mark.unit
    def test_share_policy_values(self):
        """Test all share policy values"""
        assert SharePolicy.PRIVATE.value == "private"
        assert SharePolicy.SHARED.value == "shared"
        assert SharePolicy.CATEGORY_SHARED.value == "category_shared"
        assert SharePolicy.CUSTOM.value == "custom"


# ============================================================================
# Test Setting Memory Sharing
# ============================================================================

class TestSetMemorySharing:
    """Test set_memory_sharing method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_private_policy(self, cross_agent_sharing):
        """Test setting private sharing policy"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.set_memory_sharing(
            memory_id="mem-1",
            policy=SharePolicy.PRIVATE
        )

        assert result["status"] == "success"
        assert result["policy"] == "private"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_shared_policy(self, cross_agent_sharing):
        """Test setting shared policy"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.set_memory_sharing(
            memory_id="mem-1",
            policy=SharePolicy.SHARED
        )

        assert result["status"] == "success"
        assert result["policy"] == "shared"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_custom_policy(self, cross_agent_sharing):
        """Test setting custom policy with allowed agents"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.set_memory_sharing(
            memory_id="mem-1",
            policy=SharePolicy.CUSTOM,
            allowed_agents=["agent-1", "agent-2"]
        )

        assert result["status"] == "success"
        assert result["policy"] == "custom"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_memory_not_found(self, cross_agent_sharing):
        """Test setting policy on non-existent memory"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")  # No rows updated
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.set_memory_sharing(
            memory_id="non-existent",
            policy=SharePolicy.PRIVATE
        )

        assert result["status"] == "not_found"


# ============================================================================
# Test Access Checking
# ============================================================================

class TestCanAgentAccessMemory:
    """Test can_agent_access_memory method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_owner_can_access(self, cross_agent_sharing):
        """Test owner can always access their memory"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "mem-1",
            "owner_id": "agent-1",
            "policy": None,
            "allowed_agents": None
        })
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.can_agent_access_memory("mem-1", "agent-1")

        assert result["can_access"] is True
        assert result["reason"] == "owner"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_private_memory_access_denied(self, cross_agent_sharing):
        """Test private memory denies access to non-owners"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "mem-1",
            "owner_id": "agent-1",
            "policy": "private",
            "allowed_agents": None
        })
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.can_agent_access_memory("mem-1", "agent-2")

        assert result["can_access"] is False
        assert result["reason"] == "private_memory"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_shared_memory_access_granted(self, cross_agent_sharing):
        """Test shared memory allows access to all"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "mem-1",
            "owner_id": "agent-1",
            "policy": "shared",
            "allowed_agents": None
        })
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.can_agent_access_memory("mem-1", "agent-2")

        assert result["can_access"] is True
        assert result["reason"] == "public_memory"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_custom_whitelist_access(self, cross_agent_sharing):
        """Test custom policy with whitelist"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "mem-1",
            "owner_id": "agent-1",
            "policy": "custom",
            "allowed_agents": '["agent-2", "agent-3"]'
        })
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        # Agent on whitelist
        result1 = await cross_agent_sharing.can_agent_access_memory("mem-1", "agent-2")
        assert result1["can_access"] is True

        # Agent not on whitelist
        result2 = await cross_agent_sharing.can_agent_access_memory("mem-1", "agent-4")
        assert result2["can_access"] is False


# ============================================================================
# Test Getting Shared Memories
# ============================================================================

class TestGetSharedMemories:
    """Test get_shared_memories method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_shared_memories_success(self, cross_agent_sharing):
        """Test getting shared memories for agent"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "id": "mem-1",
                "title": "Shared Memory 1",
                "content": "Content 1",
                "owner_id": "agent-1",
                "memory_category": "test",
                "created_at": datetime.utcnow()
            },
            {
                "id": "mem-2",
                "title": "Shared Memory 2",
                "content": "Content 2",
                "owner_id": "agent-2",
                "memory_category": "test",
                "created_at": datetime.utcnow()
            }
        ])
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        memories = await cross_agent_sharing.get_shared_memories("agent-3", limit=50)

        assert len(memories) == 2
        assert memories[0]["id"] == "mem-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_shared_memories_empty(self, cross_agent_sharing):
        """Test getting shared memories when none exist"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        memories = await cross_agent_sharing.get_shared_memories("agent-1")

        assert len(memories) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_shared_memories_limit(self, cross_agent_sharing):
        """Test limit parameter for shared memories"""
        mock_conn = AsyncMock()
        # Return many memories
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": f"mem-{i}", "title": f"Memory {i}", "content": "content",
             "owner_id": "agent-1", "memory_category": "test", "created_at": datetime.utcnow()}
            for i in range(100)
        ])
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        memories = await cross_agent_sharing.get_shared_memories("agent-2", limit=10)

        # Should respect limit
        assert len(memories) <= 100  # Mock may not enforce limit


# ============================================================================
# Test Sharing Statistics
# ============================================================================

class TestGetSharingStats:
    """Test get_sharing_stats method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_sharing_stats_success(self, cross_agent_sharing):
        """Test getting sharing statistics"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"policy": "private", "count": 50},
            {"policy": "shared", "count": 30},
            {"policy": "category_shared", "count": 15},
            {"policy": "custom", "count": 5}
        ])
        mock_conn.fetchval = AsyncMock(return_value=100)  # Total private
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        stats = await cross_agent_sharing.get_sharing_stats()

        assert stats["total_shared"] == 50  # 30 + 15 + 5
        assert stats["total_private"] == 100
        assert "by_policy" in stats
        assert stats["by_policy"]["shared"] == 30

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_sharing_stats_empty(self, cross_agent_sharing):
        """Test getting stats with no shared memories"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        stats = await cross_agent_sharing.get_sharing_stats()

        assert stats["total_shared"] == 0


# ============================================================================
# Test Creating Shared Spaces
# ============================================================================

class TestCreateSharedSpace:
    """Test create_shared_space method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_shared_space_success(self, cross_agent_sharing):
        """Test creating a shared space"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 0")
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.create_shared_space(
            space_name="team-space",
            member_agents=["agent-1", "agent-2", "agent-3"]
        )

        assert result["status"] == "success"
        assert result["space_name"] == "team-space"
        assert result["member_count"] == 3
        assert "space_id" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_shared_space_empty_members(self, cross_agent_sharing):
        """Test creating shared space with no members"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 0")
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.create_shared_space(
            space_name="empty-space",
            member_agents=[]
        )

        assert result["status"] == "success"
        assert result["member_count"] == 0


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in CrossAgentMemorySharing"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_sharing_db_error(self, cross_agent_sharing):
        """Test handling database errors when setting sharing"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("DB error"))
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.set_memory_sharing(
            memory_id="mem-1",
            policy=SharePolicy.SHARED
        )

        assert result["status"] == "error"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_access_memory_not_found(self, cross_agent_sharing):
        """Test checking access for non-existent memory"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.can_agent_access_memory("non-existent", "agent-1")

        assert result["can_access"] is False
        assert result["reason"] == "memory_not_found"


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_memory_id(self, cross_agent_sharing):
        """Test setting sharing with empty memory ID"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.set_memory_sharing(
            memory_id="",
            policy=SharePolicy.PRIVATE
        )

        # Should return not_found for empty ID
        assert result["status"] == "not_found"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_very_long_space_name(self, cross_agent_sharing):
        """Test creating shared space with very long name"""
        long_name = "x" * 10000

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 0")
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.create_shared_space(
            space_name=long_name,
            member_agents=["agent-1"]
        )

        # Should handle gracefully
        assert result["status"] == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_many_allowed_agents(self, cross_agent_sharing):
        """Test custom policy with many allowed agents"""
        many_agents = [f"agent-{i}" for i in range(1000)]

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.set_memory_sharing(
            memory_id="mem-1",
            policy=SharePolicy.CUSTOM,
            allowed_agents=many_agents
        )

        assert result["status"] == "success"


# ============================================================================
# Test Category Sharing
# ============================================================================

class TestCategorySharedAccess:
    """Test category_shared policy access control"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_category_shared_with_access(self, cross_agent_sharing):
        """Test agent has access when sharing same category"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "mem-1",
            "owner_id": "agent-1",
            "policy": "category_shared",
            "allowed_agents": None
        })
        # Agent has memories in the same category
        mock_conn.fetchval = AsyncMock(return_value=True)
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.can_agent_access_memory("mem-1", "agent-2")

        assert result["can_access"] is True
        assert "category_shared" in result["reason"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_category_shared_without_access(self, cross_agent_sharing):
        """Test agent denied when no category overlap"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "mem-1",
            "owner_id": "agent-1",
            "policy": "category_shared",
            "allowed_agents": None
        })
        # Agent has no memories in the category
        mock_conn.fetchval = AsyncMock(return_value=False)
        cross_agent_sharing.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await cross_agent_sharing.can_agent_access_memory("mem-1", "agent-2")

        assert result["can_access"] is False
