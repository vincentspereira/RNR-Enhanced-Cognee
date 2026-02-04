"""
Unit Tests for Memory Deduplication Module
Tests duplicate detection, merging, and auto-deduplication
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, MagicMock
from src.memory_deduplication import MemoryDeduplicator


# ============================================================================
# Test MemoryDeduplicator Initialization
# ============================================================================

class TestMemoryDeduplicatorInit:
    """Test MemoryDeduplicator initialization"""

    @pytest.mark.unit
    def test_init_with_valid_dependencies(self, mock_postgres_pool, mock_qdrant_client):
        """Test initialization with all dependencies"""
        deduplicator = MemoryDeduplicator(mock_postgres_pool, mock_qdrant_client, 0.95)

        assert deduplicator.postgres_pool is not None
        assert deduplicator.qdrant_client is not None
        assert deduplicator.similarity_threshold == 0.95

    @pytest.mark.unit
    def test_init_custom_threshold(self, mock_postgres_pool, mock_qdrant_client):
        """Test initialization with custom similarity threshold"""
        custom_threshold = 0.90
        deduplicator = MemoryDeduplicator(
            mock_postgres_pool,
            mock_qdrant_client,
            custom_threshold
        )

        assert deduplicator.similarity_threshold == custom_threshold


# ============================================================================
# Test Duplicate Checking
# ============================================================================

class TestCheckDuplicate:
    """Test check_duplicate method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_duplicate_found(self, memory_deduplicator):
        """Test when no duplicate is found"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.check_duplicate(
            content="Unique new content",
            agent_id="test-agent"
        )

        assert result["is_duplicate"] is False
        assert result["action"] == "add"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exact_duplicate_found(self, memory_deduplicator):
        """Test detection of exact duplicate"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "existing-memory-id",
            "created_at": "2024-01-01"
        })
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.check_duplicate(
            content="Exact duplicate content",
            agent_id="test-agent"
        )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "exact"
        assert result["action"] == "skip"
        assert "existing_id" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vector_duplicate_found(self, memory_deduplicator):
        """Test detection of similar content via vector search"""
        # Mock no exact match
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        # Mock vector similarity match
        similar_result = Mock()
        similar_result.id = "similar-memory-id"
        similar_result.score = 0.97
        similar_result.payload = {"content": "similar content"}

        memory_deduplicator.qdrant_client.search = Mock(return_value=[similar_result])

        result = await memory_deduplicator.check_duplicate(
            content="Similar but not identical content",
            embedding=[0.1] * 1536,
            agent_id="test-agent"
        )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "similar"
        assert result["action"] == "merge"
        assert "similarity_score" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_below_similarity_threshold(self, memory_deduplicator):
        """Test content below similarity threshold is not duplicate"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        # Mock below threshold
        similar_result = Mock()
        similar_result.score = 0.90  # Below 0.95 threshold

        memory_deduplicator.qdrant_client.search = Mock(return_value=[similar_result])

        result = await memory_deduplicator.check_duplicate(
            content="Different enough content",
            embedding=[0.1] * 1536,
            agent_id="test-agent"
        )

        assert result["is_duplicate"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_with_no_embedding(self, memory_deduplicator):
        """Test duplicate check without vector embedding"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.check_duplicate(
            content="Content without embedding",
            agent_id="test-agent"
        )

        # Should not call vector search
        memory_deduplicator.qdrant_client.search.assert_not_called()
        assert result["is_duplicate"] is False


# ============================================================================
# Test Exact Match Checking
# ============================================================================

class TestCheckExactMatch:
    """Test _check_exact_match method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exact_match_found(self, memory_deduplicator):
        """Test finding exact text match"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "exact-match-id",
            "created_at": "2024-01-01"
        })
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator._check_exact_match(
            "Exact content to match",
            "test-agent"
        )

        assert result is not None
        assert result["id"] == "exact-match-id"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_exact_match(self, memory_deduplicator):
        """Test when no exact match exists"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator._check_exact_match(
            "Non-existent content",
            "test-agent"
        )

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exact_match_different_agent(self, memory_deduplicator):
        """Test exact match is scoped to agent"""
        mock_conn = AsyncMock()
        # First agent has the content
        mock_conn.fetchrow = AsyncMock(return_value={"id": "mem-1", "created_at": "2024-01-01"})
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator._check_exact_match(
            "Shared content",
            "agent-1"
        )

        assert result is not None

        # Second agent should not find the same content
        mock_conn.fetchrow = AsyncMock(return_value=None)

        result2 = await memory_deduplicator._check_exact_match(
            "Shared content",
            "agent-2"
        )

        assert result2 is None


# ============================================================================
# Test Vector Similarity Checking
# ============================================================================

class TestCheckVectorSimilarity:
    """Test _check_vector_similarity method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vector_similarity_above_threshold(self, memory_deduplicator):
        """Test vector similarity above threshold"""
        similar_result = Mock()
        similar_result.id = "similar-id"
        similar_result.score = 0.98
        similar_result.payload = {"content": "similar content"}

        memory_deduplicator.qdrant_client.search = Mock(return_value=[similar_result])

        result = await memory_deduplicator._check_vector_similarity(
            "content",
            [0.1] * 1536,
            "test-agent",
            "test-category"
        )

        assert result is not None
        assert result["id"] == "similar-id"
        assert result["score"] == 0.98

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vector_similarity_no_results(self, memory_deduplicator):
        """Test vector similarity with no results"""
        memory_deduplicator.qdrant_client.search = Mock(return_value=[])

        result = await memory_deduplicator._check_vector_similarity(
            "content",
            [0.1] * 1536,
            "test-agent",
            "test-category"
        )

        assert result is None


# ============================================================================
# Test Duplicate Merging
# ============================================================================

class TestMergeDuplicates:
    """Test merge_duplicates method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_merge_keep_newest(self, memory_deduplicator):
        """Test merging with keep_newest strategy"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.merge_duplicates(
            memory_id="mem-1",
            new_content="Updated content",
            merge_strategy="keep_newest"
        )

        assert result["status"] == "success"
        assert result["action"] == "updated"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_merge_append(self, memory_deduplicator):
        """Test merging with append strategy"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.merge_duplicates(
            memory_id="mem-1",
            new_content="Additional content",
            merge_strategy="append"
        )

        assert result["status"] == "success"
        assert result["action"] == "appended"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_merge_unknown_strategy(self, memory_deduplicator):
        """Test merging with unknown strategy"""
        mock_conn = AsyncMock()
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.merge_duplicates(
            memory_id="mem-1",
            new_content="content",
            merge_strategy="unknown_strategy"
        )

        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()


# ============================================================================
# Test Auto Deduplication
# ============================================================================

class TestAutoDeduplicate:
    """Test auto_deduplicate method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auto_deduplicate_success(self, memory_deduplicator):
        """Test automatic deduplication finds and removes duplicates"""
        mock_conn = AsyncMock()

        # Mock memories with duplicates
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "mem-1", "content": "same content", "agent_id": "agent-1", "memory_category": "test"},
            {"id": "mem-2", "content": "same content", "agent_id": "agent-1", "memory_category": "test"},
            {"id": "mem-3", "content": "unique content", "agent_id": "agent-1", "memory_category": "test"}
        ])

        # Mock exact duplicate detection
        async def mock_fetchrow(*args, **kwargs):
            return {"id": "mem-1", "created_at": "2024-01-01"}

        # First call finds duplicate, subsequent calls don't
        call_count = [0]
        async def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"id": "mem-1", "created_at": "2024-01-01"}
            return None

        mock_conn.fetchrow = AsyncMock(side_effect=side_effect)
        mock_conn.execute = AsyncMock(return_value="DELETE 1")
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.auto_deduplicate("agent-1")

        assert result["status"] == "success"
        assert "results" in result
        assert "duplicates_found" in result["results"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auto_deduplicate_all_agents(self, memory_deduplicator):
        """Test auto deduplication across all agents"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.auto_deduplicate()  # No agent_id = all agents

        assert result["status"] == "success"
        assert result["results"]["processed"] >= 0


# ============================================================================
# Test Deduplication Statistics
# ============================================================================

class TestDeduplicationStats:
    """Test get_deduplication_stats method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats_with_duplicates(self, memory_deduplicator):
        """Test getting statistics when duplicates exist"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"total": 110, "unique_content": 100}  # 10 duplicates
        ])
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        stats = await memory_deduplicator.get_deduplication_stats()

        assert "similarity_threshold" in stats
        assert stats["total_duplicates_prevented"] == 10
        assert stats["exact_duplicates_found"] == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats_no_duplicates(self, memory_deduplicator):
        """Test getting statistics with no duplicates"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"total": 100, "unique_content": 100}  # No duplicates
        ])
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        stats = await memory_deduplicator.get_deduplication_stats()

        assert stats["total_duplicates_prevented"] == 0
        assert stats["exact_duplicates_found"] == 0


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in MemoryDeduplicator"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_duplicate_db_error(self, memory_deduplicator):
        """Test handling database errors during duplicate check"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Database error"))
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.check_duplicate("content", "agent")

        # Should return not duplicate on error to not block operations
        assert result["is_duplicate"] is False
        assert result["action"] == "add"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vector_search_error(self, memory_deduplicator):
        """Test handling vector search errors"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        memory_deduplicator.qdrant_client.search = Mock(side_effect=Exception("Qdrant error"))

        result = await memory_deduplicator.check_duplicate(
            "content",
            embedding=[0.1] * 1536,
            agent_id="test-agent"
        )

        # Should handle gracefully and not block
        assert result["is_duplicate"] is False


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_content(self, memory_deduplicator):
        """Test checking duplicate with empty content"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.check_duplicate("", "agent")

        assert result["is_duplicate"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_very_long_content(self, memory_deduplicator):
        """Test checking duplicate with very long content"""
        long_content = "x" * 1000000  # 1MB of content

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.check_duplicate(long_content, "agent")

        assert result["is_duplicate"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_special_characters(self, memory_deduplicator):
        """Test content with special characters"""
        special_content = "Test with emoji: 🎉, symbols: ©®, and unicode: 中文"

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        memory_deduplicator.postgres_pool.acquire = AsyncMock(return_value=mock_conn)

        result = await memory_deduplicator.check_duplicate(special_content, "agent")

        assert result["is_duplicate"] is False


# ============================================================================
# Test Configuration
# ============================================================================

class TestConfiguration:
    """Test different configuration options"""

    @pytest.mark.unit
    def test_different_similarity_thresholds(self, mock_postgres_pool, mock_qdrant_client):
        """Test different similarity threshold configurations"""
        for threshold in [0.85, 0.90, 0.95, 0.99]:
            deduplicator = MemoryDeduplicator(
                mock_postgres_pool,
                mock_qdrant_client,
                threshold
            )
            assert deduplicator.similarity_threshold == threshold
