"""
Unit tests for src/graph_compactor.py
Covers: GraphCompactor (all methods), singleton helpers.
All offline - Neo4j and asyncpg are fully mocked.
ASCII-only assertions.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# ---------------------------------------------------------------------------
# Helpers - mock Neo4j session / driver
# ---------------------------------------------------------------------------

def _make_neo4j_result(record_dict: dict | None):
    """Return a mock Neo4j result whose .single() yields record_dict or None."""
    mock_result = MagicMock()
    if record_dict is None:
        mock_result.single.return_value = None
    else:
        mock_record = MagicMock()
        mock_record.__getitem__ = lambda self, key: record_dict[key]
        mock_result.single.return_value = mock_record
    return mock_result


def _make_driver(result_sequence: list):
    """
    Build a mock Neo4j driver whose session().run() returns results from
    result_sequence in order (cycling if necessary).
    """
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    call_iter = iter(result_sequence)

    def _run(cypher, **kwargs):
        try:
            return next(call_iter)
        except StopIteration:
            return _make_neo4j_result({"deleted": 0, "compacted": 0, "nodes": 0, "rels": 0, "orphans": 0})

    mock_session.run = MagicMock(side_effect=_run)
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    return mock_driver


class _AsyncCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_pool(rows=None):
    """Build a minimal asyncpg-pool mock whose .acquire() yields a conn."""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=rows or [])
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AsyncCtx(mock_conn))
    return pool, mock_conn


# ===========================================================================
# Import
# ===========================================================================

from src.graph_compactor import (
    GraphCompactor,
    init_graph_compactor,
    get_graph_compactor,
    _BATCH,
)


# ===========================================================================
# TestGraphCompactorInit
# ===========================================================================

class TestGraphCompactorInit:
    """Construction and attribute checks."""

    @pytest.mark.unit
    def test_init_with_driver_only(self):
        driver = MagicMock()
        gc = GraphCompactor(neo4j_driver=driver)
        assert gc.driver is driver
        assert gc.pool is None

    @pytest.mark.unit
    def test_init_with_driver_and_pool(self):
        driver = MagicMock()
        pool = MagicMock()
        gc = GraphCompactor(neo4j_driver=driver, postgres_pool=pool)
        assert gc.driver is driver
        assert gc.pool is pool


# ===========================================================================
# TestRemoveOrphanNodes
# ===========================================================================

class TestRemoveOrphanNodes:
    """Tests for remove_orphan_nodes()."""

    @pytest.mark.unit
    def test_returns_deleted_count(self):
        driver = _make_driver([_make_neo4j_result({"deleted": 7})])
        gc = GraphCompactor(driver)
        assert gc.remove_orphan_nodes() == 7

    @pytest.mark.unit
    def test_returns_zero_when_record_is_none(self):
        driver = _make_driver([_make_neo4j_result(None)])
        gc = GraphCompactor(driver)
        assert gc.remove_orphan_nodes() == 0

    @pytest.mark.unit
    def test_returns_zero_on_exception(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run = MagicMock(side_effect=RuntimeError("neo4j down"))
        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        gc = GraphCompactor(driver)
        assert gc.remove_orphan_nodes() == 0

    @pytest.mark.unit
    def test_returns_integer(self):
        driver = _make_driver([_make_neo4j_result({"deleted": 3})])
        gc = GraphCompactor(driver)
        result = gc.remove_orphan_nodes()
        assert isinstance(result, int)


# ===========================================================================
# TestPruneStaleRelations
# ===========================================================================

class TestPruneStaleRelations:
    """Tests for prune_stale_relations()."""

    @pytest.mark.unit
    def test_empty_list_returns_zero_without_db_call(self):
        driver = MagicMock()
        gc = GraphCompactor(driver)
        # No session should be opened for an empty list
        assert gc.prune_stale_relations([]) == 0
        driver.session.assert_not_called()

    @pytest.mark.unit
    def test_returns_deleted_count(self):
        driver = _make_driver([_make_neo4j_result({"deleted": 12})])
        gc = GraphCompactor(driver)
        assert gc.prune_stale_relations(["id-1", "id-2"]) == 12

    @pytest.mark.unit
    def test_returns_zero_when_record_is_none(self):
        driver = _make_driver([_make_neo4j_result(None)])
        gc = GraphCompactor(driver)
        assert gc.prune_stale_relations(["id-x"]) == 0

    @pytest.mark.unit
    def test_returns_zero_on_exception(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run = MagicMock(side_effect=RuntimeError("timeout"))
        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        gc = GraphCompactor(driver)
        assert gc.prune_stale_relations(["id-1"]) == 0

    @pytest.mark.unit
    def test_single_id(self):
        driver = _make_driver([_make_neo4j_result({"deleted": 1})])
        gc = GraphCompactor(driver)
        assert gc.prune_stale_relations(["only-one"]) == 1


# ===========================================================================
# TestCompactSimilarEdges
# ===========================================================================

class TestCompactSimilarEdges:
    """Tests for compact_similar_edges()."""

    @pytest.mark.unit
    def test_returns_compacted_count(self):
        driver = _make_driver([_make_neo4j_result({"compacted": 5})])
        gc = GraphCompactor(driver)
        assert gc.compact_similar_edges() == 5

    @pytest.mark.unit
    def test_returns_zero_when_record_is_none(self):
        driver = _make_driver([_make_neo4j_result(None)])
        gc = GraphCompactor(driver)
        assert gc.compact_similar_edges() == 0

    @pytest.mark.unit
    def test_returns_zero_on_exception(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run = MagicMock(side_effect=Exception("cypher error"))
        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        gc = GraphCompactor(driver)
        assert gc.compact_similar_edges() == 0


# ===========================================================================
# TestGetGraphStats
# ===========================================================================

class TestGetGraphStats:
    """Tests for get_graph_stats()."""

    @pytest.mark.unit
    def test_returns_expected_keys(self):
        results = [
            _make_neo4j_result({"nodes": 100}),
            _make_neo4j_result({"rels": 200}),
            _make_neo4j_result({"orphans": 5}),
        ]
        driver = _make_driver(results)
        gc = GraphCompactor(driver)
        stats = gc.get_graph_stats()
        assert "node_count" in stats
        assert "relationship_count" in stats
        assert "orphan_nodes" in stats
        assert "timestamp" in stats

    @pytest.mark.unit
    def test_returns_correct_values(self):
        results = [
            _make_neo4j_result({"nodes": 42}),
            _make_neo4j_result({"rels": 88}),
            _make_neo4j_result({"orphans": 3}),
        ]
        driver = _make_driver(results)
        gc = GraphCompactor(driver)
        stats = gc.get_graph_stats()
        assert stats["node_count"] == 42
        assert stats["relationship_count"] == 88
        assert stats["orphan_nodes"] == 3

    @pytest.mark.unit
    def test_returns_error_key_on_exception(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run = MagicMock(side_effect=Exception("db unavailable"))
        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        gc = GraphCompactor(driver)
        stats = gc.get_graph_stats()
        assert "error" in stats

    @pytest.mark.unit
    def test_timestamp_is_string(self):
        results = [
            _make_neo4j_result({"nodes": 0}),
            _make_neo4j_result({"rels": 0}),
            _make_neo4j_result({"orphans": 0}),
        ]
        driver = _make_driver(results)
        gc = GraphCompactor(driver)
        stats = gc.get_graph_stats()
        assert isinstance(stats["timestamp"], str)


# ===========================================================================
# TestRunCompaction
# ===========================================================================

class TestRunCompaction:
    """Tests for the async run_compaction() method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_pool_still_runs_all_steps(self):
        """Without a pool, archived_ids is empty.
        prune_stale_relations returns 0 immediately (no Cypher call).
        Then remove_orphan_nodes and compact_similar_edges run.
        """
        # Only 2 Cypher calls: orphan removal + compact
        results = [
            _make_neo4j_result({"deleted": 4}),   # remove_orphan_nodes
            _make_neo4j_result({"compacted": 2}), # compact_similar_edges
        ]
        driver = _make_driver(results)
        gc = GraphCompactor(driver)
        summary = await gc.run_compaction()

        assert "started_at" in summary
        assert "finished_at" in summary
        assert summary["orphans_removed"] == 4
        assert summary["similar_edges_compacted"] == 2
        assert isinstance(summary["errors"], list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_with_pool_fetches_archived_ids(self):
        """Pool is queried; returned doc IDs are passed to prune_stale_relations."""
        mock_rows = [{"id": "doc-abc"}, {"id": "doc-def"}]
        pool, mock_conn = _make_pool(rows=mock_rows)

        results = [
            _make_neo4j_result({"deleted": 2}),   # prune with 2 ids
            _make_neo4j_result({"deleted": 0}),   # remove_orphan_nodes
            _make_neo4j_result({"compacted": 0}), # compact_similar_edges
        ]
        driver = _make_driver(results)
        gc = GraphCompactor(driver, pool)
        summary = await gc.run_compaction()

        assert summary["stale_relations_pruned"] == 2
        assert summary["errors"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pool_db_exception_adds_to_errors(self):
        """DB error during archived_ids fetch is captured in errors."""
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("pool broken"))

        results = [
            _make_neo4j_result({"deleted": 0}),
            _make_neo4j_result({"deleted": 0}),
            _make_neo4j_result({"compacted": 0}),
        ]
        driver = _make_driver(results)
        gc = GraphCompactor(driver, pool)
        summary = await gc.run_compaction()
        assert len(summary["errors"]) >= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_summary_dict_structure(self):
        driver = _make_driver([
            _make_neo4j_result({"deleted": 0}),
            _make_neo4j_result({"deleted": 0}),
            _make_neo4j_result({"compacted": 0}),
        ])
        gc = GraphCompactor(driver)
        summary = await gc.run_compaction()
        for key in ("started_at", "finished_at", "orphans_removed",
                    "stale_relations_pruned", "similar_edges_compacted", "errors"):
            assert key in summary, f"Missing key: {key}"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_archived_ids_skips_prune_cypher(self):
        """When pool returns no rows, prune_stale_relations returns 0 immediately."""
        pool, _ = _make_pool(rows=[])
        # Only 2 cypher calls expected (orphan + compact), not 3
        results = [
            _make_neo4j_result({"deleted": 1}),   # remove_orphan_nodes
            _make_neo4j_result({"compacted": 0}), # compact_similar_edges
        ]
        driver = _make_driver(results)
        gc = GraphCompactor(driver, pool)
        summary = await gc.run_compaction()
        assert summary["stale_relations_pruned"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prune_step_exception_captured(self):
        """If prune_stale_relations raises (not caught internally), error is logged."""
        from unittest.mock import patch
        driver = _make_driver([
            _make_neo4j_result({"deleted": 2}),   # remove_orphan_nodes
            _make_neo4j_result({"compacted": 1}), # compact_similar_edges
        ])
        gc = GraphCompactor(driver)
        with patch.object(gc, "prune_stale_relations", side_effect=RuntimeError("prune boom")):
            summary = await gc.run_compaction()
        assert any("prune_stale_relations" in e for e in summary["errors"])

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_orphan_step_exception_captured(self):
        """If remove_orphan_nodes raises (not caught internally), error is logged."""
        from unittest.mock import patch
        driver = _make_driver([
            _make_neo4j_result({"compacted": 1}), # compact_similar_edges
        ])
        gc = GraphCompactor(driver)
        with patch.object(gc, "remove_orphan_nodes", side_effect=RuntimeError("orphan boom")):
            summary = await gc.run_compaction()
        assert any("remove_orphan_nodes" in e for e in summary["errors"])

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_compact_step_exception_captured(self):
        """If compact_similar_edges raises (not caught internally), error is logged."""
        from unittest.mock import patch
        driver = _make_driver([
            _make_neo4j_result({"deleted": 0}),   # remove_orphan_nodes
        ])
        gc = GraphCompactor(driver)
        with patch.object(gc, "compact_similar_edges", side_effect=RuntimeError("compact boom")):
            summary = await gc.run_compaction()
        assert any("compact_similar_edges" in e for e in summary["errors"])


# ===========================================================================
# TestSingleton
# ===========================================================================

class TestSingleton:
    """Tests for init_graph_compactor / get_graph_compactor helpers."""

    @pytest.mark.unit
    def test_init_returns_instance(self):
        driver = MagicMock()
        gc = init_graph_compactor(driver)
        assert isinstance(gc, GraphCompactor)

    @pytest.mark.unit
    def test_get_returns_same_instance(self):
        driver = MagicMock()
        gc1 = init_graph_compactor(driver)
        gc2 = get_graph_compactor()
        assert gc1 is gc2

    @pytest.mark.unit
    def test_init_with_pool(self):
        driver = MagicMock()
        pool = MagicMock()
        gc = init_graph_compactor(driver, pool)
        assert gc.pool is pool

    @pytest.mark.unit
    def test_reinit_replaces_instance(self):
        d1 = MagicMock()
        d2 = MagicMock()
        gc1 = init_graph_compactor(d1)
        gc2 = init_graph_compactor(d2)
        assert gc2 is get_graph_compactor()
        assert gc1 is not gc2


# ===========================================================================
# TestBatchConstant
# ===========================================================================

class TestBatchConstant:
    @pytest.mark.unit
    def test_batch_is_positive_int(self):
        assert isinstance(_BATCH, int)
        assert _BATCH > 0
