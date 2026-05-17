"""
Unit tests for src.memory_importance_scorer
=============================================
Tests MemoryImportanceScorer, component functions, singleton helpers.
All database interactions are mocked. No real DB connections.
No Unicode characters in assertions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool(rows=None, fetchrow_result=None):
    """Build a mock asyncpg pool."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=rows or [])
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_result)

    class MockAcquireCtx:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=MockAcquireCtx())
    return mock_pool, mock_conn


def _make_row(**kwargs):
    """Create a dict-like row with dict() support."""
    return dict(kwargs)


# ---------------------------------------------------------------------------
# Component functions
# ---------------------------------------------------------------------------

class TestComponentAccess:
    def test_zero_count(self):
        from src.memory_importance_scorer import _component_access
        assert _component_access(0) == 0.0

    def test_at_max(self):
        from src.memory_importance_scorer import _component_access
        assert _component_access(50) == 1.0

    def test_above_max_capped_at_one(self):
        from src.memory_importance_scorer import _component_access
        assert _component_access(100) == 1.0

    def test_half_max(self):
        from src.memory_importance_scorer import _component_access
        assert _component_access(25) == pytest.approx(0.5)

    def test_one_access(self):
        from src.memory_importance_scorer import _component_access
        result = _component_access(1)
        assert 0.0 < result < 1.0


class TestComponentRecency:
    def test_none_returns_zero(self):
        from src.memory_importance_scorer import _component_recency
        assert _component_recency(None) == 0.0

    def test_just_accessed_returns_close_to_one(self):
        from src.memory_importance_scorer import _component_recency
        now = datetime.now(timezone.utc).isoformat()
        result = _component_recency(now)
        assert result > 0.99

    def test_one_year_ago_returns_zero(self):
        from src.memory_importance_scorer import _component_recency
        one_year_ago = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        result = _component_recency(one_year_ago)
        assert result == pytest.approx(0.0, abs=0.01)

    def test_two_years_ago_clamped_to_zero(self):
        from src.memory_importance_scorer import _component_recency
        two_years_ago = (datetime.now(timezone.utc) - timedelta(days=730)).isoformat()
        result = _component_recency(two_years_ago)
        assert result == 0.0

    def test_naive_datetime_handled(self):
        from src.memory_importance_scorer import _component_recency
        naive_dt = datetime.now()  # No timezone
        result = _component_recency(naive_dt)
        assert result >= 0.0

    def test_invalid_string_returns_zero(self):
        from src.memory_importance_scorer import _component_recency
        result = _component_recency("not-a-date")
        assert result == 0.0

    def test_datetime_object_works(self):
        from src.memory_importance_scorer import _component_recency
        recent = datetime.now(timezone.utc) - timedelta(days=10)
        result = _component_recency(recent)
        assert 0.0 < result <= 1.0

    def test_180_days_ago_returns_approx_half(self):
        from src.memory_importance_scorer import _component_recency
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=182)
        result = _component_recency(six_months_ago)
        assert 0.4 < result < 0.6


class TestComponentConfidence:
    def test_none_returns_neutral(self):
        from src.memory_importance_scorer import _component_confidence
        assert _component_confidence(None) == 0.5

    def test_zero_clamped_to_zero(self):
        from src.memory_importance_scorer import _component_confidence
        assert _component_confidence(0.0) == 0.0

    def test_one_stays_one(self):
        from src.memory_importance_scorer import _component_confidence
        assert _component_confidence(1.0) == 1.0

    def test_above_one_clamped(self):
        from src.memory_importance_scorer import _component_confidence
        assert _component_confidence(2.5) == 1.0

    def test_below_zero_clamped(self):
        from src.memory_importance_scorer import _component_confidence
        assert _component_confidence(-0.5) == 0.0

    def test_midpoint(self):
        from src.memory_importance_scorer import _component_confidence
        assert _component_confidence(0.7) == pytest.approx(0.7)


class TestComponentSourceType:
    def test_none_returns_unknown_weight(self):
        from src.memory_importance_scorer import _component_source_type, SOURCE_TYPE_WEIGHTS
        assert _component_source_type(None) == SOURCE_TYPE_WEIGHTS["unknown"]

    def test_empty_string_returns_unknown(self):
        from src.memory_importance_scorer import _component_source_type, SOURCE_TYPE_WEIGHTS
        assert _component_source_type("") == SOURCE_TYPE_WEIGHTS["unknown"]

    def test_verified_returns_highest(self):
        from src.memory_importance_scorer import _component_source_type
        assert _component_source_type("verified") == 1.0

    def test_agent_returns_correct_weight(self):
        from src.memory_importance_scorer import _component_source_type
        assert _component_source_type("agent") == 0.8

    def test_user_returns_correct_weight(self):
        from src.memory_importance_scorer import _component_source_type
        assert _component_source_type("user") == 0.7

    def test_system_returns_correct_weight(self):
        from src.memory_importance_scorer import _component_source_type
        assert _component_source_type("system") == 0.5

    def test_case_insensitive(self):
        from src.memory_importance_scorer import _component_source_type
        assert _component_source_type("VERIFIED") == 1.0
        assert _component_source_type("Agent") == 0.8

    def test_unknown_type_returns_half(self):
        from src.memory_importance_scorer import _component_source_type
        assert _component_source_type("mystery_type") == 0.5


# ---------------------------------------------------------------------------
# MemoryImportanceScorer._score_memory
# ---------------------------------------------------------------------------

class TestScoreMemory:
    def _make_scorer(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        return MemoryImportanceScorer()

    def test_all_defaults_returns_value_in_range(self):
        scorer = self._make_scorer()
        memory = {}
        score = scorer._score_memory(memory)
        assert 0.0 <= score <= 1.0

    def test_high_access_increases_score(self):
        scorer = self._make_scorer()
        low = scorer._score_memory({"access_count": 0})
        high = scorer._score_memory({"access_count": 50})
        assert high > low

    def test_recent_access_increases_score(self):
        scorer = self._make_scorer()
        now_str = datetime.now(timezone.utc).isoformat()
        old_str = (datetime.now(timezone.utc) - timedelta(days=300)).isoformat()
        recent = scorer._score_memory({"last_accessed_at": now_str})
        old = scorer._score_memory({"last_accessed_at": old_str})
        assert recent > old

    def test_high_confidence_increases_score(self):
        scorer = self._make_scorer()
        low = scorer._score_memory({"confidence_score": 0.0})
        high = scorer._score_memory({"confidence_score": 1.0})
        assert high > low

    def test_verified_source_increases_score(self):
        scorer = self._make_scorer()
        unknown = scorer._score_memory({"source_type": "unknown"})
        verified = scorer._score_memory({"source_type": "verified"})
        assert verified > unknown

    def test_source_type_from_metadata(self):
        """source_type nested in metadata should be found."""
        scorer = self._make_scorer()
        memory_with_meta = {"metadata": {"source_type": "verified"}}
        memory_bare = {"source_type": "verified"}
        score_meta = scorer._score_memory(memory_with_meta)
        score_bare = scorer._score_memory(memory_bare)
        assert score_meta == score_bare

    def test_score_is_rounded_to_6_decimals(self):
        scorer = self._make_scorer()
        score = scorer._score_memory({"access_count": 10})
        assert score == round(score, 6)

    def test_perfect_memory_score_close_to_one(self):
        scorer = self._make_scorer()
        now_str = datetime.now(timezone.utc).isoformat()
        memory = {
            "access_count": 50,
            "last_accessed_at": now_str,
            "confidence_score": 1.0,
            "source_type": "verified"
        }
        score = scorer._score_memory(memory)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_metadata_not_dict_handled(self):
        """Non-dict metadata should not crash."""
        scorer = self._make_scorer()
        memory = {"metadata": "not-a-dict"}
        score = scorer._score_memory(memory)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# MemoryImportanceScorer._breakdown
# ---------------------------------------------------------------------------

class TestBreakdown:
    def _make_scorer(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        return MemoryImportanceScorer()

    def test_breakdown_returns_all_keys(self):
        scorer = self._make_scorer()
        result = scorer._breakdown({})
        assert "access" in result
        assert "recency" in result
        assert "confidence" in result
        assert "source_type" in result

    def test_breakdown_values_in_range(self):
        scorer = self._make_scorer()
        result = scorer._breakdown({"access_count": 25, "confidence_score": 0.6})
        for val in result.values():
            assert 0.0 <= val <= 1.0

    def test_breakdown_source_from_metadata(self):
        scorer = self._make_scorer()
        memory = {"metadata": {"source_type": "agent"}}
        result = scorer._breakdown(memory)
        assert result["source_type"] == 0.8

    def test_breakdown_non_dict_metadata(self):
        scorer = self._make_scorer()
        result = scorer._breakdown({"metadata": "string"})
        assert "source_type" in result


# ---------------------------------------------------------------------------
# get_memory_importance - no pool
# ---------------------------------------------------------------------------

class TestGetMemoryImportanceNoPool:
    async def test_no_pool_returns_neutral(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        result = await scorer.get_memory_importance("mem-123")
        assert result["memory_id"] == "mem-123"
        assert result["importance_score"] == 0.5
        assert "note" in result

    async def test_no_pool_breakdown_structure(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        result = await scorer.get_memory_importance("mem-456")
        breakdown = result["breakdown"]
        assert "access" in breakdown
        assert "confidence" in breakdown


# ---------------------------------------------------------------------------
# get_memory_importance - with pool
# ---------------------------------------------------------------------------

class TestGetMemoryImportanceWithPool:
    async def test_pool_row_found_computes_score(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        now_str = datetime.now(timezone.utc).isoformat()
        row = _make_row(
            id="mem-1",
            content="test content",
            access_count=10,
            last_accessed_at=now_str,
            confidence_score=0.8,
            metadata=None
        )
        pool, conn = _make_pool(fetchrow_result=row)
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.get_memory_importance("mem-1")
        assert result["memory_id"] == "mem-1"
        assert 0.0 <= result["importance_score"] <= 1.0
        assert "breakdown" in result

    async def test_pool_row_not_found_returns_zero(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        pool, conn = _make_pool(fetchrow_result=None)
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.get_memory_importance("missing-id")
        assert result["importance_score"] == 0.0
        assert "note" in result

    async def test_pool_exception_returns_error(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(side_effect=Exception("DB error"))
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.get_memory_importance("err-id")
        assert result["importance_score"] == 0.5
        assert "error" in result


# ---------------------------------------------------------------------------
# update_importance_scores
# ---------------------------------------------------------------------------

class TestUpdateImportanceScores:
    async def test_no_pool_returns_zero(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        result = await scorer.update_importance_scores()
        assert result["updated"] == 0
        assert result["mean_score"] == 0.0

    async def test_with_pool_no_rows(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        pool, conn = _make_pool(rows=[])
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.update_importance_scores()
        assert result["updated"] == 0
        assert result["mean_score"] == 0.0

    async def test_with_pool_multiple_rows(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        now_str = datetime.now(timezone.utc).isoformat()
        rows = [
            _make_row(id="1", access_count=10, last_accessed_at=now_str, confidence_score=0.8, metadata=None),
            _make_row(id="2", access_count=20, last_accessed_at=now_str, confidence_score=0.9, metadata=None),
        ]
        pool, conn = _make_pool(rows=rows)
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.update_importance_scores()
        assert result["updated"] == 2
        assert result["mean_score"] >= 0.0

    async def test_with_agent_id_filter(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        now_str = datetime.now(timezone.utc).isoformat()
        rows = [
            _make_row(id="1", access_count=5, last_accessed_at=now_str, confidence_score=0.5, metadata=None),
        ]
        pool, conn = _make_pool(rows=rows)
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.update_importance_scores(agent_id="my-agent", limit=10)
        assert result["updated"] == 1

        # Verify agent_id was passed as query parameter
        fetch_calls = conn.fetch.call_args_list
        assert len(fetch_calls) == 1
        args = fetch_calls[0][0]
        assert "my-agent" in args

    async def test_exception_returns_error_dict(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        pool, conn = _make_pool()
        conn.execute = AsyncMock(side_effect=Exception("ALTER failed"))
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.update_importance_scores()
        assert result["updated"] == 0
        assert "error" in result


# ---------------------------------------------------------------------------
# get_top_important_memories
# ---------------------------------------------------------------------------

class TestGetTopImportantMemories:
    async def test_no_pool_returns_empty_list(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        scorer = MemoryImportanceScorer()
        result = await scorer.get_top_important_memories()
        assert result == []

    async def test_with_pool_no_rows(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        pool, conn = _make_pool(rows=[])
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.get_top_important_memories()
        assert result == []

    async def test_with_pool_returns_formatted_results(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        now_str = datetime.now(timezone.utc).isoformat()

        class MockRow(dict):
            pass

        row = MockRow(
            id="mem-1",
            agent_id="agent-1",
            content="This is test content that should appear normally",
            importance_score=0.85,
            confidence_score=0.9,
            access_count=20,
            last_accessed_at=now_str,
            created_at=now_str
        )
        pool, conn = _make_pool(rows=[row])
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.get_top_important_memories()
        assert len(result) == 1
        assert result[0]["id"] == "mem-1"
        assert result[0]["importance_score"] == pytest.approx(0.85)

    async def test_content_truncated_at_120_chars(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        long_content = "x" * 200

        class MockRow(dict):
            pass

        row = MockRow(
            id="m-1",
            agent_id="a-1",
            content=long_content,
            importance_score=0.5,
            confidence_score=None,
            access_count=0,
            last_accessed_at=None,
            created_at=None
        )
        pool, conn = _make_pool(rows=[row])
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.get_top_important_memories()
        assert result[0]["content_preview"].endswith("...")
        assert len(result[0]["content_preview"]) <= 123  # 120 + "..."

    async def test_with_agent_id_filter(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        pool, conn = _make_pool(rows=[])
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        await scorer.get_top_important_memories(agent_id="filter-agent", top_n=5)

        fetch_calls = conn.fetch.call_args_list
        args = fetch_calls[0][0]
        assert "filter-agent" in args

    async def test_exception_returns_empty_list(self):
        from src.memory_importance_scorer import MemoryImportanceScorer
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(side_effect=Exception("Query failed"))
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.get_top_important_memories()
        assert result == []

    async def test_null_importance_score_handled(self):
        from src.memory_importance_scorer import MemoryImportanceScorer

        class MockRow(dict):
            pass

        row = MockRow(
            id="m-1",
            agent_id="a-1",
            content="short",
            importance_score=None,
            confidence_score=None,
            access_count=None,
            last_accessed_at=None,
            created_at=None
        )
        pool, conn = _make_pool(rows=[row])
        scorer = MemoryImportanceScorer(postgres_pool=pool)
        result = await scorer.get_top_important_memories()
        assert result[0]["importance_score"] is None
        assert result[0]["access_count"] == 0


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------

class TestSingletonHelpers:
    def test_init_returns_instance(self):
        from src.memory_importance_scorer import init_importance_scorer, MemoryImportanceScorer
        scorer = init_importance_scorer()
        assert isinstance(scorer, MemoryImportanceScorer)

    def test_init_sets_singleton(self):
        from src.memory_importance_scorer import init_importance_scorer, get_importance_scorer
        s = init_importance_scorer()
        assert get_importance_scorer() is s

    def test_init_with_pool(self):
        from src.memory_importance_scorer import init_importance_scorer
        pool, _ = _make_pool()
        scorer = init_importance_scorer(postgres_pool=pool)
        assert scorer.pool is pool

    def test_get_before_init_returns_none_or_instance(self):
        from src.memory_importance_scorer import get_importance_scorer, MemoryImportanceScorer
        result = get_importance_scorer()
        assert result is None or isinstance(result, MemoryImportanceScorer)
