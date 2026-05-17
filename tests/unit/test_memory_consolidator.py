"""
Unit tests for src/memory_consolidator.py
Covers: MemoryConsolidator (all methods + fallback paths), singleton helpers.
All offline - asyncpg pool and Qdrant are fully mocked.
ASCII-only assertions.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Pool / connection helpers
# ---------------------------------------------------------------------------

class _AsyncCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_pool(fetch_return=None, fetchrow_return=None, fetchval_return=0, execute_return=None):
    """Build a minimal asyncpg-pool mock."""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=fetch_return or [])
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    mock_conn.fetchval = AsyncMock(return_value=fetchval_return)
    mock_conn.execute = AsyncMock(return_value=execute_return)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AsyncCtx(mock_conn))
    return pool, mock_conn


def _make_row(**kwargs):
    """Return a MagicMock that behaves like an asyncpg record."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: kwargs[key]
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


# ===========================================================================
# Import
# ===========================================================================

from src.memory_consolidator import (
    MemoryConsolidator,
    init_consolidator,
    get_consolidator,
    DEFAULT_SIMILARITY_THRESHOLD,
    MAX_CANDIDATES_PER_RUN,
)


# ===========================================================================
# TestMemoryConsolidatorInit
# ===========================================================================

class TestMemoryConsolidatorInit:

    @pytest.mark.unit
    def test_defaults(self):
        pool = MagicMock()
        mc = MemoryConsolidator(pool)
        assert mc.pool is pool
        assert mc.qdrant is None
        assert mc.similarity_threshold == DEFAULT_SIMILARITY_THRESHOLD
        assert mc.collection_name == "memories"

    @pytest.mark.unit
    def test_custom_params(self):
        pool = MagicMock()
        qdrant = MagicMock()
        mc = MemoryConsolidator(pool, qdrant, similarity_threshold=0.9, collection_name="custom")
        assert mc.qdrant is qdrant
        assert mc.similarity_threshold == 0.9
        assert mc.collection_name == "custom"

    @pytest.mark.unit
    def test_module_constants(self):
        assert DEFAULT_SIMILARITY_THRESHOLD == 0.75
        assert MAX_CANDIDATES_PER_RUN == 200


# ===========================================================================
# TestFindCandidates
# ===========================================================================

class TestFindCandidates:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_pool(self):
        mc = MemoryConsolidator(postgres_pool=None)
        result = await mc.find_candidates()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_postgres_when_no_qdrant(self):
        pool, mock_conn = _make_pool(fetch_return=[])
        mc = MemoryConsolidator(pool, qdrant_client=None)
        result = await mc.find_candidates()
        assert isinstance(result, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_qdrant_when_available(self):
        pool, mock_conn = _make_pool(fetch_return=[])
        qdrant = MagicMock()
        mc = MemoryConsolidator(pool, qdrant)
        # Pool returns no anchors, so result should be []
        result = await mc.find_candidates()
        assert isinstance(result, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_candidates_with_agent_id_qdrant(self):
        row = _make_row(id="mem-1", content="Some content about trading")
        pool, mock_conn = _make_pool(fetch_return=[row])
        qdrant = MagicMock()
        qdrant.search = MagicMock(return_value=[])  # no hits
        mc = MemoryConsolidator(pool, qdrant)
        result = await mc.find_candidates(agent_id="agent-x", limit=10)
        assert isinstance(result, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_candidates_qdrant_returns_hits(self):
        anchor_row = _make_row(id="anchor-1", content="A" * 120)
        hit_payload = {"doc_id": "hit-1"}
        hit = MagicMock()
        hit.payload = hit_payload
        hit.score = 0.88

        pool, mock_conn = _make_pool(fetch_return=[anchor_row])
        qdrant = MagicMock()
        qdrant.search = MagicMock(return_value=[hit])
        mc = MemoryConsolidator(pool, qdrant)
        result = await mc.find_candidates()
        # One group expected
        assert len(result) == 1
        assert result[0]["anchor_id"] == "anchor-1"
        assert len(result[0]["candidates"]) == 1
        assert result[0]["candidates"][0]["id"] == "hit-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_find_candidates_qdrant_exception_returns_empty(self):
        """Pool exception during qdrant candidate fetch returns []."""
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("db error"))
        qdrant = MagicMock()
        mc = MemoryConsolidator(pool, qdrant)
        result = await mc.find_candidates()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_candidates_via_postgres_no_agent_id(self):
        """_candidates_via_postgres path with no agent_id."""
        row = _make_row(aid="a1", acontent="Hello " * 20, bid="b1", bcontent="World " * 20)
        pool, mock_conn = _make_pool(fetch_return=[row])
        mc = MemoryConsolidator(pool, qdrant_client=None)
        result = await mc.find_candidates()
        assert len(result) == 1
        assert result[0]["anchor_id"] == "a1"
        assert result[0]["candidates"][0]["id"] == "b1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_candidates_via_postgres_with_agent_id(self):
        """_candidates_via_postgres path with agent_id filter."""
        row = _make_row(aid="a2", acontent="X " * 60, bid="b2", bcontent="Y " * 60)
        pool, mock_conn = _make_pool(fetch_return=[row])
        mc = MemoryConsolidator(pool, qdrant_client=None)
        result = await mc.find_candidates(agent_id="agent-y")
        assert len(result) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_candidates_via_postgres_exception_returns_empty(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("pg_trgm missing"))
        mc = MemoryConsolidator(pool, qdrant_client=None)
        result = await mc.find_candidates()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_qdrant_hit_missing_doc_id_skipped(self):
        """Hits with no doc_id in payload must be silently skipped."""
        anchor_row = _make_row(id="anchor-2", content="B" * 50)
        hit = MagicMock()
        hit.payload = {}  # no doc_id
        hit.score = 0.95

        pool, mock_conn = _make_pool(fetch_return=[anchor_row])
        qdrant = MagicMock()
        qdrant.search = MagicMock(return_value=[hit])
        mc = MemoryConsolidator(pool, qdrant)
        result = await mc.find_candidates()
        # No candidates because hit_id is None
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_qdrant_search_exception_treated_as_no_hits(self):
        """If qdrant.search raises, the anchor is simply skipped (no candidates)."""
        anchor_row = _make_row(id="anchor-3", content="C" * 80)
        pool, mock_conn = _make_pool(fetch_return=[anchor_row])
        qdrant = MagicMock()
        qdrant.search = MagicMock(side_effect=RuntimeError("qdrant down"))
        mc = MemoryConsolidator(pool, qdrant)
        result = await mc.find_candidates()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_seen_ids_not_repeated(self):
        """Anchor IDs already in 'seen' must be skipped."""
        row1 = _make_row(id="dup-1", content="D" * 50)
        row2 = _make_row(id="dup-1", content="D" * 50)  # duplicate anchor

        hit = MagicMock()
        hit.payload = {"doc_id": "hit-dup"}
        hit.score = 0.80

        pool, mock_conn = _make_pool(fetch_return=[row1, row2])
        qdrant = MagicMock()
        qdrant.search = MagicMock(return_value=[hit])
        mc = MemoryConsolidator(pool, qdrant)
        result = await mc.find_candidates()
        # dup-1 processed once; second occurrence skipped
        assert len(result) == 1


# ===========================================================================
# TestConsolidate
# ===========================================================================

class TestConsolidate:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_none_when_no_pool(self):
        mc = MemoryConsolidator(postgres_pool=None)
        result = await mc.consolidate(["id-1", "id-2"])
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_none_when_empty_ids(self):
        pool = MagicMock()
        mc = MemoryConsolidator(pool)
        result = await mc.consolidate([])
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_none_when_no_rows_found(self):
        pool, mock_conn = _make_pool(fetch_return=[])
        mc = MemoryConsolidator(pool)
        result = await mc.consolidate(["nonexistent-id"])
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_consolidation_returns_uuid(self):
        row = _make_row(id="mem-a", content="Memory A content", agent_id="agent-1", metadata="{}")
        pool, mock_conn = _make_pool(fetch_return=[row])
        mc = MemoryConsolidator(pool)
        result = await mc.consolidate(["mem-a"])
        assert result is not None
        # Result should be a UUID string
        assert len(result) > 0
        assert "-" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_summary_content_when_provided(self):
        row = _make_row(id="mem-b", content="Original content", agent_id="agent-2", metadata="{}")
        pool, mock_conn = _make_pool(fetch_return=[row])
        mc = MemoryConsolidator(pool)
        result = await mc.consolidate(["mem-b"], summary_content="Custom summary")
        assert result is not None
        # Check that execute was called with the summary content
        calls = [str(call) for call in mock_conn.execute.call_args_list]
        assert any("Custom summary" in c for c in calls)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concatenates_multiple_memories(self):
        rows = [
            _make_row(id="m1", content="Part one", agent_id="ag", metadata="{}"),
            _make_row(id="m2", content="Part two", agent_id="ag", metadata="{}"),
        ]
        pool, mock_conn = _make_pool(fetch_return=rows)
        mc = MemoryConsolidator(pool)
        result = await mc.consolidate(["m1", "m2"])
        assert result is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_passed_agent_id(self):
        row = _make_row(id="mem-c", content="Content", agent_id=None, metadata="{}")
        pool, mock_conn = _make_pool(fetch_return=[row])
        mc = MemoryConsolidator(pool)
        result = await mc.consolidate(["mem-c"], agent_id="override-agent")
        assert result is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_none_on_db_exception(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("insert failed"))
        mc = MemoryConsolidator(pool)
        result = await mc.consolidate(["some-id"])
        assert result is None


# ===========================================================================
# TestGetConsolidationReport
# ===========================================================================

class TestGetConsolidationReport:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_error_when_no_pool(self):
        mc = MemoryConsolidator(postgres_pool=None)
        result = await mc.get_consolidation_report()
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_correct_structure(self):
        pool, mock_conn = _make_pool()
        mock_conn.fetchval = AsyncMock(side_effect=[100, 20, 8])
        mc = MemoryConsolidator(pool)
        report = await mc.get_consolidation_report()
        for key in ("agent_id", "total_memories", "consolidated_out",
                    "consolidation_targets", "active_memories", "consolidation_ratio"):
            assert key in report, f"Missing key: {key}"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_active_memories_calculation(self):
        pool, mock_conn = _make_pool()
        mock_conn.fetchval = AsyncMock(side_effect=[100, 30, 10])
        mc = MemoryConsolidator(pool)
        report = await mc.get_consolidation_report()
        assert report["active_memories"] == 70  # 100 - 30
        assert report["total_memories"] == 100
        assert report["consolidated_out"] == 30

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_consolidation_ratio_calculation(self):
        pool, mock_conn = _make_pool()
        mock_conn.fetchval = AsyncMock(side_effect=[200, 50, 20])
        mc = MemoryConsolidator(pool)
        report = await mc.get_consolidation_report()
        assert report["consolidation_ratio"] == round(50 / 200, 4)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_with_agent_id_filter(self):
        pool, mock_conn = _make_pool()
        mock_conn.fetchval = AsyncMock(side_effect=[40, 10, 5])
        mc = MemoryConsolidator(pool)
        report = await mc.get_consolidation_report(agent_id="specific-agent")
        assert report["agent_id"] == "specific-agent"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_agent_id_none_shows_all(self):
        pool, mock_conn = _make_pool()
        mock_conn.fetchval = AsyncMock(side_effect=[10, 0, 0])
        mc = MemoryConsolidator(pool)
        report = await mc.get_consolidation_report(agent_id=None)
        assert report["agent_id"] == "all"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_zero_total_no_division_error(self):
        pool, mock_conn = _make_pool()
        mock_conn.fetchval = AsyncMock(side_effect=[0, 0, 0])
        mc = MemoryConsolidator(pool)
        report = await mc.get_consolidation_report()
        # Should not raise ZeroDivisionError
        assert report["consolidation_ratio"] == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_error_on_db_exception(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("query failed"))
        mc = MemoryConsolidator(pool)
        report = await mc.get_consolidation_report()
        assert "error" in report


# ===========================================================================
# TestSingleton
# ===========================================================================

class TestSingleton:

    @pytest.mark.unit
    def test_init_returns_instance(self):
        pool = MagicMock()
        consolidator = init_consolidator(pool)
        assert isinstance(consolidator, MemoryConsolidator)

    @pytest.mark.unit
    def test_get_returns_same_instance(self):
        pool = MagicMock()
        c1 = init_consolidator(pool)
        c2 = get_consolidator()
        assert c1 is c2

    @pytest.mark.unit
    def test_init_with_qdrant(self):
        pool = MagicMock()
        qdrant = MagicMock()
        c = init_consolidator(pool, qdrant)
        assert c.qdrant is qdrant

    @pytest.mark.unit
    def test_reinit_replaces_instance(self):
        p1 = MagicMock()
        p2 = MagicMock()
        c1 = init_consolidator(p1)
        c2 = init_consolidator(p2)
        assert get_consolidator() is c2
        assert c1 is not c2
