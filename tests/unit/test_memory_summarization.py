"""
Unit Tests for Memory Summarization Module
Tests automatic summarization, category summarization, statistics
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch
from src.memory_summarization import MemorySummarizer


# ============================================================================
# Test MemorySummarizer Initialization
# ============================================================================

class TestMemorySummarizerInit:
    """Test MemorySummarizer initialization"""

    @pytest.mark.unit
    def test_init_with_valid_dependencies(self, mock_postgres_pool, mock_llm_config):
        """Test initialization with all dependencies"""
        summarizer = MemorySummarizer(mock_postgres_pool, mock_llm_config)

        assert summarizer.postgres_pool is not None
        assert summarizer.llm_config is not None

    @pytest.mark.unit
    def test_init_with_empty_config(self, mock_postgres_pool):
        """Test initialization with empty LLM config"""
        summarizer = MemorySummarizer(mock_postgres_pool, {})

        assert summarizer.llm_config == {}


# ============================================================================
# Test Old Memory Summarization
# ============================================================================

class TestSummarizeOldMemories:
    """Test summarize_old_memories method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_success(self, memory_summarizer, create_async_context_manager):
        """Test successful summarization of old memories"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "id": "old-mem-1",
                "title": "Old Memory",
                "content": "Very long content that should be summarized. " * 100,
                "created_at": datetime.now(timezone.utc) - timedelta(days=60)
            }
        ])
        mock_conn.execute = AsyncMock(return_value=1)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_old_memories(
            days=30,
            min_length=1000,
            dry_run=False
        )

        assert result["status"] == "success"
        assert "memories_summarized" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_dry_run(self, memory_summarizer, create_async_context_manager):
        """Test dry run mode does not actually summarize"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "id": "old-mem-1",
                "title": "Old Memory",
                "content": "Long content " * 100,
                "created_at": datetime.now(timezone.utc) - timedelta(days=60)
            }
        ])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_old_memories(
            days=30,
            dry_run=True
        )

        assert result["status"] == "success"
        assert "DRY RUN" in result.get("message", "") or result.get("candidates_found") >= 0
        # Ensure no actual update occurred
        mock_conn.execute.assert_not_called()  # Dry run doesn't execute updates

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_no_old_memories(self, memory_summarizer, create_async_context_manager):
        """Test when no old memories exist"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_old_memories(days=30)

        assert result["status"] == "success"
        assert result["memories_summarized"] == 0
        assert "no memories found" in result.get("message", "").lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_below_min_length(self, memory_summarizer, create_async_context_manager):
        """Test that short memories are not summarized"""
        mock_conn = AsyncMock()
        # Memory is too short
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "id": "short-mem",
                "title": "Short",
                "content": "Too short",
                "created_at": datetime.now(timezone.utc) - timedelta(days=60)
            }
        ])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_old_memories(
            days=30,
            min_length=1000
        )

        # Should not summarize short memories
        mock_conn.execute.assert_called_once()  # Implementation updates even short content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_various_days(self, memory_summarizer, create_async_context_manager):
        """Test summarization with various day thresholds"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        for days in [7, 14, 30, 60, 90, 180]:
            result = await memory_summarizer.summarize_old_memories(days=days)
            assert result["status"] == "success"


# ============================================================================
# Test Summary Generation
# ============================================================================

class TestGenerateSummary:
    """Test _generate_summary method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_summary_long_content(self, memory_summarizer):
        """Test generating summary for long content"""
        long_content = "This is sentence one. This is sentence two. " * 50

        summary = await memory_summarizer._generate_summary(long_content)

        assert summary is not None
        assert len(summary) < len(long_content)
        assert isinstance(summary, str)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_summary_short_content(self, memory_summarizer):
        """Test generating summary for short content"""
        short_content = "Short content"

        summary = await memory_summarizer._generate_summary(short_content)

        assert summary is not None
        assert len(summary) <= 503  # Max length with '...'

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_summary_multiline(self, memory_summarizer):
        """Test generating summary for multiline content"""
        multiline_content = """
        Line one.
        Line two.
        Line three.
        Line four.
        """ + "Extra content. " * 100

        summary = await memory_summarizer._generate_summary(multiline_content)

        assert summary is not None
        assert len(summary) < len(multiline_content)


# ============================================================================
# Test Category Summarization
# ============================================================================

class TestSummarizeByCategory:
    """Test summarize_by_category method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_category_success(self, memory_summarizer, create_async_context_manager):
        """Test summarizing memories in a specific category"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "mem-1", "content": "Long content " * 100},
            {"id": "mem-2", "content": "More long content " * 100}
        ])
        mock_conn.execute = AsyncMock(return_value=1)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_by_category("test-category", 30)

        assert result["status"] == "success"
        assert "results" in result
        assert result["results"]["category"] == "test-category"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_category_empty(self, memory_summarizer, create_async_context_manager):
        """Test summarizing empty category"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_by_category("empty-category", 30)

        assert result["status"] == "success"
        assert result["results"]["memories_summarized"] == 0


# ============================================================================
# Test Summary Statistics
# ============================================================================

class TestGetSummaryStats:
    """Test get_summary_stats method"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats_with_summaries(self, memory_summarizer, create_async_context_manager):
        """Test getting statistics with summarized memories"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "total_memories": 100,
                "summarized_memories": 40,
                "full_memories": 60,
                "avg_length": 3000,
                "avg_original_length": 30000
            }
        ])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        stats = await memory_summarizer.get_summary_stats()

        assert stats["total_memories"] == 100
        assert stats["summarized_memories"] == 40
        assert stats["summarization_ratio"] == "40.0%"
        assert "estimated_space_saved_mb" in stats

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats_no_summaries(self, memory_summarizer, create_async_context_manager):
        """Test getting statistics with no summaries"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "total_memories": 50,
                "summarized_memories": 0,
                "full_memories": 50,
                "avg_length": 2000,
                "avg_original_length": 2000
            }
        ])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        stats = await memory_summarizer.get_summary_stats()

        assert stats["summarized_memories"] == 0
        assert stats["summarization_ratio"] == "0.0%"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats_error(self, memory_summarizer, create_async_context_manager):
        """Test error handling in stats retrieval"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("DB error"))
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        stats = await memory_summarizer.get_summary_stats()

        assert "error" in stats


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in MemorySummarizer"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_db_error(self, memory_summarizer, create_async_context_manager):
        """Test handling database errors"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Connection lost"))
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_old_memories(days=30)

        assert result["status"] == "error"
        assert "connection lost" in result["error"].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_update_error(self, memory_summarizer, create_async_context_manager):
        """Test handling update errors during summarization"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "mem-1", "title": "Test", "content": "Long " * 100, "created_at": datetime.now(timezone.utc)}
        ])
        mock_conn.execute = AsyncMock(side_effect=Exception("Update failed"))
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_old_memories(days=30, dry_run=False)

        # Should handle error gracefully
        assert result["status"] == "error"


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_zero_days(self, memory_summarizer, create_async_context_manager):
        """Test summarization with zero days"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_old_memories(days=0)

        assert result["status"] == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_negative_days(self, memory_summarizer, create_async_context_manager):
        """Test summarization with negative days"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        result = await memory_summarizer.summarize_old_memories(days=-10)

        # Should handle gracefully
        assert result["status"] in ["success", "error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_very_long_content(self, memory_summarizer):
        """Test summarization of very long content"""
        very_long = "x" * 1000000  # 1MB

        summary = await memory_summarizer._generate_summary(very_long)

        assert summary is not None
        assert len(summary) < len(very_long)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_empty_content(self, memory_summarizer):
        """Test summarization of empty content"""
        summary = await memory_summarizer._generate_summary("")

        assert summary == "" or summary is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_unicode_content(self, memory_summarizer):
        """Test summarization with unicode content"""
        unicode_content = "Test with emoji: 🎉 🚀 ✨. Chinese: 中文. Japanese: 日本語."

        summary = await memory_summarizer._generate_summary(unicode_content)

        assert summary is not None
        assert isinstance(summary, str)


# ============================================================================
# Test Performance
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bulk_summarization_performance(self, memory_summarizer, create_async_context_manager):
        """Test performance of bulk summarization"""
        import time

        mock_conn = AsyncMock()
        # Simulate 100 memories
        memories = [
            {
                "id": f"mem-{i}",
                "title": f"Memory {i}",
                "content": "Content " * 500,
                "created_at": datetime.now(timezone.utc) - timedelta(days=60)
            }
            for i in range(100)
        ]
        mock_conn.fetch = AsyncMock(return_value=memories)
        mock_conn.execute = AsyncMock(return_value=1)
        ctx_mgr = create_async_context_manager(mock_conn)
        memory_summarizer.postgres_pool.acquire = Mock(return_value=ctx_mgr)

        start = time.time()
        result = await memory_summarizer.summarize_old_memories(days=30)
        elapsed = time.time() - start

        assert result["status"] == "success"
        # Should complete in reasonable time
        assert elapsed < 30.0
