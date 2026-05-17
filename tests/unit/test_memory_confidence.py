"""
Unit tests for src/memory_confidence.py
Target: >= 85% line coverage.

All database interactions are mocked - no live DB required.
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers for mocking asyncpg pool
# ---------------------------------------------------------------------------

def _make_pool(conn):
    """Build a minimal fake asyncpg pool whose acquire() is an async context."""
    class _AcquireCtx:
        async def __aenter__(self):
            return conn
        async def __aexit__(self, *args):
            pass

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AcquireCtx())
    return pool


# ---------------------------------------------------------------------------
# Module-level constants and _label helper
# ---------------------------------------------------------------------------

class TestConstants:
    def test_confidence_ground_truth(self):
        from src.memory_confidence import CONFIDENCE_GROUND_TRUTH
        assert CONFIDENCE_GROUND_TRUTH == 1.0

    def test_confidence_high(self):
        from src.memory_confidence import CONFIDENCE_HIGH
        assert CONFIDENCE_HIGH == 0.8

    def test_confidence_medium(self):
        from src.memory_confidence import CONFIDENCE_MEDIUM
        assert CONFIDENCE_MEDIUM == 0.5

    def test_confidence_low(self):
        from src.memory_confidence import CONFIDENCE_LOW
        assert CONFIDENCE_LOW == 0.3

    def test_confidence_uncertain(self):
        from src.memory_confidence import CONFIDENCE_UNCERTAIN
        assert CONFIDENCE_UNCERTAIN == 0.0


class TestLabelHelper:
    def test_high_label_at_1(self):
        from src.memory_confidence import _label
        assert _label(1.0) == "high"

    def test_high_label_at_boundary(self):
        from src.memory_confidence import _label
        assert _label(0.8) == "high"

    def test_medium_label(self):
        from src.memory_confidence import _label
        assert _label(0.6) == "medium"

    def test_medium_label_at_boundary(self):
        from src.memory_confidence import _label
        assert _label(0.5) == "medium"

    def test_low_label(self):
        from src.memory_confidence import _label
        assert _label(0.4) == "low"

    def test_low_label_at_boundary(self):
        from src.memory_confidence import _label
        assert _label(0.3) == "low"

    def test_uncertain_label(self):
        from src.memory_confidence import _label
        assert _label(0.0) == "uncertain"

    def test_uncertain_label_below_low(self):
        from src.memory_confidence import _label
        assert _label(0.1) == "uncertain"


# ---------------------------------------------------------------------------
# MemoryConfidenceManager.set_confidence
# ---------------------------------------------------------------------------

class TestSetConfidence:
    @pytest.mark.asyncio
    async def test_no_pool_returns_false(self):
        from src.memory_confidence import MemoryConfidenceManager
        mgr = MemoryConfidenceManager(None)
        result = await mgr.set_confidence("m1", 0.9)
        assert result is False

    @pytest.mark.asyncio
    async def test_success_returns_true(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.set_confidence("m1", 0.9)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_rows_updated_returns_false(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 0")
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.set_confidence("no-such-id", 0.5)
        assert result is False

    @pytest.mark.asyncio
    async def test_score_clamped_above_1(self):
        """Score > 1.0 must be clamped to 1.0."""
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        await mgr.set_confidence("m1", 5.0)
        call_args = conn.execute.call_args
        # First positional arg after the SQL is the score
        assert call_args[0][1] == 1.0

    @pytest.mark.asyncio
    async def test_score_clamped_below_0(self):
        """Score < 0.0 must be clamped to 0.0."""
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        await mgr.set_confidence("m1", -2.0)
        call_args = conn.execute.call_args
        assert call_args[0][1] == 0.0

    @pytest.mark.asyncio
    async def test_db_exception_returns_false(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("db exploded"))
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.set_confidence("m1", 0.7)
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_result_none_returns_false(self):
        """When execute returns None the updated count is treated as 0."""
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.set_confidence("m1", 0.9)
        assert result is False


# ---------------------------------------------------------------------------
# MemoryConfidenceManager.get_confidence
# ---------------------------------------------------------------------------

class TestGetConfidence:
    @pytest.mark.asyncio
    async def test_no_pool_returns_none(self):
        from src.memory_confidence import MemoryConfidenceManager
        mgr = MemoryConfidenceManager(None)
        result = await mgr.get_confidence("m1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_float_when_row_found(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=0.75)
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence("m1")
        assert result == 0.75

    @pytest.mark.asyncio
    async def test_returns_none_when_db_null(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_db_exception_returns_none(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=RuntimeError("boom"))
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence("m1")
        assert result is None


# ---------------------------------------------------------------------------
# MemoryConfidenceManager.get_low_confidence_memories
# ---------------------------------------------------------------------------

class TestGetLowConfidenceMemories:
    def _make_row(self, id, content, agent_id, confidence, created_at="2025-01-01"):
        row = MagicMock()
        row.__getitem__ = lambda self, k: {
            "id": id, "content": content, "agent_id": agent_id,
            "confidence": confidence, "created_at": created_at
        }[k]
        return row

    @pytest.mark.asyncio
    async def test_no_pool_returns_empty_list(self):
        from src.memory_confidence import MemoryConfidenceManager
        mgr = MemoryConfidenceManager(None)
        result = await mgr.get_low_confidence_memories()
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self):
        from src.memory_confidence import MemoryConfidenceManager
        row = self._make_row("m1", "short content", "agent1", 0.2)
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_low_confidence_memories()
        assert len(result) == 1
        assert result[0]["id"] == "m1"

    @pytest.mark.asyncio
    async def test_content_preview_truncated(self):
        from src.memory_confidence import MemoryConfidenceManager
        long_content = "x" * 200
        row = self._make_row("m1", long_content, "agent1", 0.1)
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_low_confidence_memories()
        assert result[0]["content_preview"].endswith("...")
        assert len(result[0]["content_preview"]) <= 123 + 3  # 120 + "..."

    @pytest.mark.asyncio
    async def test_short_content_not_truncated(self):
        from src.memory_confidence import MemoryConfidenceManager
        short = "short text"
        row = self._make_row("m1", short, "agent1", 0.1)
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_low_confidence_memories()
        assert result[0]["content_preview"] == short

    @pytest.mark.asyncio
    async def test_confidence_label_assigned(self):
        from src.memory_confidence import MemoryConfidenceManager
        row = self._make_row("m1", "data", "agent1", 0.1)
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_low_confidence_memories()
        assert result[0]["confidence_label"] == "uncertain"

    @pytest.mark.asyncio
    async def test_with_agent_id_filter(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_low_confidence_memories(agent_id="agent99")
        assert result == []
        # Verify fetch was called (agent_id branch)
        conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_null_confidence_in_row(self):
        """Rows with NULL confidence should have label 'unknown'."""
        from src.memory_confidence import MemoryConfidenceManager
        row = self._make_row("m1", "data", "agent1", None)
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_low_confidence_memories()
        assert result[0]["confidence"] is None
        assert result[0]["confidence_label"] == "unknown"

    @pytest.mark.asyncio
    async def test_db_exception_returns_empty(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=RuntimeError("boom"))
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_low_confidence_memories()
        assert result == []


# ---------------------------------------------------------------------------
# MemoryConfidenceManager.get_confidence_report
# ---------------------------------------------------------------------------

class TestGetConfidenceReport:
    def _make_report_row(self, total=10, high=3, medium=2, low=2, uncertain=1,
                         unscored=2, avg=0.65):
        row = MagicMock()
        row.get = lambda k, default=None: {
            "total": total, "high_count": high, "medium_count": medium,
            "low_count": low, "uncertain_count": uncertain,
            "unscored_count": unscored, "avg_confidence": avg
        }.get(k, default)
        row.__getitem__ = lambda self, k: {
            "total": total, "high_count": high, "medium_count": medium,
            "low_count": low, "uncertain_count": uncertain,
            "unscored_count": unscored, "avg_confidence": avg
        }[k]
        return row

    @pytest.mark.asyncio
    async def test_no_pool_returns_error_dict(self):
        from src.memory_confidence import MemoryConfidenceManager
        mgr = MemoryConfidenceManager(None)
        result = await mgr.get_confidence_report()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_report_structure(self):
        from src.memory_confidence import MemoryConfidenceManager
        row = self._make_report_row()
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence_report()
        assert "total_memories" in result
        assert "high_confidence" in result
        assert "medium_confidence" in result
        assert "low_confidence" in result
        assert "uncertain" in result
        assert "unscored" in result
        assert "average_confidence" in result
        assert "thresholds" in result

    @pytest.mark.asyncio
    async def test_agent_id_all_when_no_filter(self):
        from src.memory_confidence import MemoryConfidenceManager
        row = self._make_report_row()
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence_report()
        assert result["agent_id"] == "all"

    @pytest.mark.asyncio
    async def test_agent_id_preserved_when_filtered(self):
        from src.memory_confidence import MemoryConfidenceManager
        row = self._make_report_row()
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence_report(agent_id="agent1")
        assert result["agent_id"] == "agent1"

    @pytest.mark.asyncio
    async def test_average_none_when_null(self):
        from src.memory_confidence import MemoryConfidenceManager
        row = self._make_report_row(avg=None)
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence_report()
        assert result["average_confidence"] is None

    @pytest.mark.asyncio
    async def test_empty_rows_handled(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence_report()
        assert result["total_memories"] == 0

    @pytest.mark.asyncio
    async def test_db_exception_returns_error_dict(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=RuntimeError("boom"))
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.get_confidence_report()
        assert "error" in result


# ---------------------------------------------------------------------------
# MemoryConfidenceManager.bulk_set_confidence
# ---------------------------------------------------------------------------

class TestBulkSetConfidence:
    @pytest.mark.asyncio
    async def test_no_pool_returns_zero(self):
        from src.memory_confidence import MemoryConfidenceManager
        mgr = MemoryConfidenceManager(None)
        result = await mgr.bulk_set_confidence({"m1": 0.9})
        assert result == 0

    @pytest.mark.asyncio
    async def test_empty_scores_returns_zero(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        result = await mgr.bulk_set_confidence({})
        assert result == 0

    @pytest.mark.asyncio
    async def test_all_succeed_returns_count(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        scores = {"m1": 0.9, "m2": 0.5, "m3": 0.1}
        result = await mgr.bulk_set_confidence(scores)
        assert result == 3

    @pytest.mark.asyncio
    async def test_partial_failure_returns_partial_count(self):
        from src.memory_confidence import MemoryConfidenceManager
        conn = AsyncMock()
        # First call succeeds, second fails (no rows), third succeeds
        conn.execute = AsyncMock(side_effect=["UPDATE 1", "UPDATE 0", "UPDATE 1"])
        pool = _make_pool(conn)
        mgr = MemoryConfidenceManager(pool)
        scores = {"m1": 0.9, "m2": 0.5, "m3": 0.1}
        result = await mgr.bulk_set_confidence(scores)
        assert result == 2


# ---------------------------------------------------------------------------
# Module-level singleton: init_confidence_manager / get_confidence_manager
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_init_returns_manager_instance(self):
        from src.memory_confidence import init_confidence_manager, MemoryConfidenceManager
        pool = MagicMock()
        mgr = init_confidence_manager(pool)
        assert isinstance(mgr, MemoryConfidenceManager)

    def test_get_returns_initialized_manager(self):
        from src.memory_confidence import init_confidence_manager, get_confidence_manager
        pool = MagicMock()
        mgr = init_confidence_manager(pool)
        retrieved = get_confidence_manager()
        assert retrieved is mgr

    def test_get_before_init_returns_none_or_previous(self):
        """get_confidence_manager should not raise even if called before init."""
        import src.memory_confidence as mc
        # Reset the singleton to None for an isolated test
        original = mc._confidence_manager
        mc._confidence_manager = None
        try:
            result = mc.get_confidence_manager()
            assert result is None
        finally:
            mc._confidence_manager = original
