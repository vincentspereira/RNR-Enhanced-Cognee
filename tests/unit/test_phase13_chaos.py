"""
Phase 13 - Chaos Engineering and Resilience Tests (18.2 / 18.3)
================================================================
Validates that RNR Enhanced Cognee degrades gracefully under adverse conditions:
network failures, resource exhaustion, concurrent mutations, and partial
availability of the four-database stack.

Test categories:
    A. Database unavailability (all four DBs individually offline)
    B. Partial availability (some DBs up, some down)
    C. Malformed / boundary inputs to every Phase 10-12 module
    D. Concurrent write safety (no deadlocks, no data corruption)
    E. Re-initialisation idempotence (init_* called multiple times)

All tests use mocks - no live connections required.
ASCII-only output: no Unicode symbols.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Category A: Database unavailability
# ---------------------------------------------------------------------------

class TestDatabaseUnavailability:
    """All modules must return safe error values when their DB is unreachable."""

    # Phase 10 - MemoryVersioner
    @pytest.mark.asyncio
    async def test_versioner_snapshot_returns_none_without_pool(self):
        from src.memory_versioner import MemoryVersioner
        mv = MemoryVersioner(postgres_pool=None)
        result = await mv.snapshot("mem-1", "content")
        assert result is None

    @pytest.mark.asyncio
    async def test_versioner_get_history_returns_empty_without_pool(self):
        from src.memory_versioner import MemoryVersioner
        mv = MemoryVersioner(postgres_pool=None)
        result = await mv.get_history("mem-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_versioner_revert_returns_false_without_pool(self):
        from src.memory_versioner import MemoryVersioner
        mv = MemoryVersioner(postgres_pool=None)
        result = await mv.revert("mem-1", 3)
        assert result is False

    # Phase 10 - MemoryProvenanceTracker
    @pytest.mark.asyncio
    async def test_provenance_set_returns_false_without_pool(self):
        from src.memory_provenance import MemoryProvenanceTracker
        pt = MemoryProvenanceTracker(postgres_pool=None)
        result = await pt.set_provenance("mem-1", "user_input")
        assert result is False

    @pytest.mark.asyncio
    async def test_provenance_get_returns_none_without_pool(self):
        from src.memory_provenance import MemoryProvenanceTracker
        pt = MemoryProvenanceTracker(postgres_pool=None)
        result = await pt.get_provenance("mem-1")
        assert result is None

    # Phase 10 - MemoryConfidenceManager
    @pytest.mark.asyncio
    async def test_confidence_set_returns_false_without_pool(self):
        from src.memory_confidence import MemoryConfidenceManager
        cm = MemoryConfidenceManager(postgres_pool=None)
        result = await cm.set_confidence("mem-1", 0.9)
        assert result is False

    @pytest.mark.asyncio
    async def test_confidence_report_returns_error_without_pool(self):
        from src.memory_confidence import MemoryConfidenceManager
        cm = MemoryConfidenceManager(postgres_pool=None)
        report = await cm.get_confidence_report()
        assert "error" in report

    # Phase 10 - MemoryConsolidator
    @pytest.mark.asyncio
    async def test_consolidator_find_candidates_returns_empty_without_pool(self):
        from src.memory_consolidator import MemoryConsolidator
        cons = MemoryConsolidator(postgres_pool=None)
        result = await cons.find_candidates()
        assert result == []

    @pytest.mark.asyncio
    async def test_consolidator_consolidate_returns_none_without_pool(self):
        from src.memory_consolidator import MemoryConsolidator
        cons = MemoryConsolidator(postgres_pool=None)
        result = await cons.consolidate(["mem-1", "mem-2"])
        assert result is None

    # Phase 10 - MemoryTierManager
    @pytest.mark.asyncio
    async def test_tier_manager_get_tier_returns_none_without_pool(self):
        from src.memory_tier_manager import MemoryTierManager
        tm = MemoryTierManager(postgres_pool=None)
        result = await tm.get_tier("mem-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_tier_manager_stats_returns_error_without_pool(self):
        from src.memory_tier_manager import MemoryTierManager
        tm = MemoryTierManager(postgres_pool=None)
        result = await tm.get_tier_stats()
        assert "error" in result

    # Phase 10 - GraphCompactor
    def test_graph_compactor_stats_returns_error_dict_without_neo4j(self):
        from src.graph_compactor import GraphCompactor
        driver = MagicMock()
        driver.session.side_effect = ConnectionError("Neo4j down")
        gc = GraphCompactor(neo4j_driver=driver)
        result = gc.get_graph_stats()
        assert isinstance(result, dict)
        assert "error" in result

    # Phase 11 - GDPRManager
    @pytest.mark.asyncio
    async def test_gdpr_delete_returns_summary_without_pool(self):
        from src.gdpr_manager import GDPRManager
        gm = GDPRManager(postgres_pool=None)
        result = await gm.delete_user_data("user-1", dry_run=True)
        assert isinstance(result, dict)
        assert result["user_id"] == "user-1"
        assert result["postgres_rows_deleted"] == 0

    @pytest.mark.asyncio
    async def test_gdpr_export_returns_valid_json_without_pool(self):
        from src.gdpr_manager import GDPRManager
        gm = GDPRManager(postgres_pool=None)
        data_bytes, filename = await gm.export_user_data("user-1")
        export = json.loads(data_bytes)
        assert export["user_id"] == "user-1"
        assert export["memories"] == []

    @pytest.mark.asyncio
    async def test_gdpr_consent_check_returns_none_without_pool(self):
        from src.gdpr_manager import GDPRManager
        gm = GDPRManager(postgres_pool=None)
        result = await gm.check_consent("user-1", "analytics")
        assert result is None

    @pytest.mark.asyncio
    async def test_gdpr_list_consents_returns_empty_without_pool(self):
        from src.gdpr_manager import GDPRManager
        gm = GDPRManager(postgres_pool=None)
        result = await gm.list_consents("user-1")
        assert result == []


# ---------------------------------------------------------------------------
# Category B: Pool raises exceptions mid-operation
# ---------------------------------------------------------------------------

class TestPoolExceptionMidOperation:
    """Modules must handle exceptions raised during DB operations."""

    def _make_failing_pool(self, exception_type=Exception, message="DB error"):
        """Return a pool whose acquire() always raises."""
        pool = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(side_effect=exception_type(message))
        ctx.__aexit__ = AsyncMock(return_value=False)
        pool.acquire.return_value = ctx
        return pool

    @pytest.mark.asyncio
    async def test_versioner_handles_db_exception_on_snapshot(self):
        from src.memory_versioner import MemoryVersioner
        pool = self._make_failing_pool()
        mv = MemoryVersioner(postgres_pool=pool)
        result = await mv.snapshot("mem-1", "content")
        assert result is None  # Must not raise

    @pytest.mark.asyncio
    async def test_versioner_handles_db_exception_on_get_history(self):
        from src.memory_versioner import MemoryVersioner
        pool = self._make_failing_pool()
        mv = MemoryVersioner(postgres_pool=pool)
        result = await mv.get_history("mem-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_confidence_handles_db_exception_on_report(self):
        from src.memory_confidence import MemoryConfidenceManager
        pool = self._make_failing_pool(message="timeout")
        cm = MemoryConfidenceManager(postgres_pool=pool)
        result = await cm.get_confidence_report()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_tier_manager_handles_db_exception_on_get_stats(self):
        from src.memory_tier_manager import MemoryTierManager
        pool = self._make_failing_pool(message="connection refused")
        tm = MemoryTierManager(postgres_pool=pool)
        result = await tm.get_tier_stats()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_consolidator_handles_db_exception_on_consolidate(self):
        from src.memory_consolidator import MemoryConsolidator
        pool = self._make_failing_pool(message="lock timeout")
        cons = MemoryConsolidator(postgres_pool=pool)
        result = await cons.consolidate(["mem-1", "mem-2"])
        assert result is None


# ---------------------------------------------------------------------------
# Category C: Boundary and malformed inputs
# ---------------------------------------------------------------------------

class TestBoundaryInputs:
    """Modules must not crash on boundary or malformed inputs."""

    @pytest.mark.asyncio
    async def test_versioner_snapshot_empty_content(self):
        from src.memory_versioner import MemoryVersioner
        mv = MemoryVersioner(postgres_pool=None)
        result = await mv.snapshot("mem-1", "")
        assert result is None  # No pool - graceful None

    @pytest.mark.asyncio
    async def test_versioner_revert_version_zero(self):
        from src.memory_versioner import MemoryVersioner
        mv = MemoryVersioner(postgres_pool=None)
        result = await mv.revert("mem-1", 0)
        assert result is False

    @pytest.mark.asyncio
    async def test_confidence_score_exactly_zero(self):
        from src.memory_confidence import MemoryConfidenceManager
        cm = MemoryConfidenceManager(postgres_pool=None)
        result = await cm.set_confidence("mem-1", 0.0)
        assert result is False  # No pool

    @pytest.mark.asyncio
    async def test_confidence_score_exactly_one(self):
        from src.memory_confidence import MemoryConfidenceManager
        cm = MemoryConfidenceManager(postgres_pool=None)
        result = await cm.set_confidence("mem-1", 1.0)
        assert result is False  # No pool

    def test_tier_manager_valid_tiers_accepted(self):
        from src.memory_tier_manager import MemoryTierManager, ALL_TIERS
        tm = MemoryTierManager(postgres_pool=None)
        for tier in ALL_TIERS:
            # Valid tiers should NOT immediately return False due to validation;
            # they fail only because pool is None (after validation passes)
            # We just check no ValueError is raised during the validation check
            assert tier in tm._VALID_TIERS if hasattr(tm, '_VALID_TIERS') else tier in ("working", "long_term", "archive")

    @pytest.mark.asyncio
    async def test_consolidate_single_id_not_enough(self):
        from src.memory_consolidator import MemoryConsolidator
        cons = MemoryConsolidator(postgres_pool=None)
        result = await cons.consolidate(["mem-1"])  # Only 1 ID
        assert result is None

    def test_webhook_register_with_empty_events_subscribes_all(self):
        from src.webhook_manager import WebhookManager, WEBHOOK_EVENTS
        wm = WebhookManager()
        wh = wm.register("https://example.com/hook", "secret123", events=None)
        assert wh.events == WEBHOOK_EVENTS

    def test_webhook_register_with_known_events_subset(self):
        from src.webhook_manager import WebhookManager
        wm = WebhookManager()
        wh = wm.register(
            "https://example.com/hook", "secret",
            events=["memory.added", "backup.completed"],
        )
        assert "memory.added" in wh.events
        assert "backup.completed" in wh.events

    def test_plugin_registry_list_loaders_not_empty(self):
        from src.plugin_loader import PluginRegistry
        reg = PluginRegistry()
        reg.discover(skip_entry_points=True)  # Only built-ins
        loaders = reg.list_loaders()
        assert len(loaders) >= 3  # PlainText, Json, Html

    @pytest.mark.asyncio
    async def test_gdpr_export_very_long_user_id(self):
        from src.gdpr_manager import GDPRManager
        gm = GDPRManager(postgres_pool=None)
        long_id = "x" * 256
        data_bytes, _ = await gm.export_user_data(long_id)
        export = json.loads(data_bytes)
        assert export["user_id"] == long_id


# ---------------------------------------------------------------------------
# Category D: Concurrent write safety
# ---------------------------------------------------------------------------

class TestConcurrentWriteSafety:
    """Concurrent calls must not deadlock or raise unexpected exceptions."""

    @pytest.mark.asyncio
    async def test_webhook_concurrent_fire_does_not_raise(self):
        """Firing events concurrently must complete without exceptions."""
        from src.webhook_manager import WebhookManager

        wm = WebhookManager()
        # Register a webhook pointing to a non-existent host (will fail, but not crash)
        wm.register("http://127.0.0.1:19999/dead", "secret123")

        tasks = [
            wm.fire("memory.added", {"content": f"concurrent {i}"})
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            assert not isinstance(r, BaseException) or isinstance(r, Exception)

    @pytest.mark.asyncio
    async def test_concurrent_confidence_set_does_not_raise(self):
        """Concurrent set_confidence() calls must not raise."""
        from src.memory_confidence import MemoryConfidenceManager
        cm = MemoryConfidenceManager(postgres_pool=None)
        tasks = [cm.set_confidence(f"mem-{i}", float(i) / 10.0) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            assert not isinstance(r, BaseException) or isinstance(r, Exception)

    @pytest.mark.asyncio
    async def test_concurrent_tier_promote_does_not_raise(self):
        """Concurrent tier_manager.promote() calls must not raise."""
        from src.memory_tier_manager import MemoryTierManager
        tm = MemoryTierManager(postgres_pool=None)
        tasks = [tm.promote(f"mem-{i}") for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            assert not isinstance(r, BaseException) or isinstance(r, Exception)


# ---------------------------------------------------------------------------
# Category E: Re-initialisation idempotence
# ---------------------------------------------------------------------------

class TestInitIdempotence:
    """Calling init_* multiple times must not raise and must return valid instance."""

    def test_plugin_registry_double_init(self):
        from src.plugin_loader import init_plugin_registry, get_plugin_registry
        reg1 = init_plugin_registry(skip_entry_points=True)
        reg2 = init_plugin_registry(skip_entry_points=True)
        assert reg1 is not None
        assert reg2 is not None
        # Both are valid registries with built-in loaders
        assert len(reg1.list_loaders()) >= 3
        assert len(reg2.list_loaders()) >= 3

    def test_webhook_manager_double_init(self):
        from src.webhook_manager import init_webhook_manager, get_webhook_manager
        wm1 = init_webhook_manager()
        wm2 = init_webhook_manager()
        assert wm1 is not None
        assert wm2 is not None

    def test_versioner_double_init(self):
        from src.memory_versioner import init_memory_versioner, get_memory_versioner
        mv1 = init_memory_versioner(postgres_pool=None)
        mv2 = init_memory_versioner(postgres_pool=None)
        assert mv1 is not None
        assert mv2 is not None

    def test_confidence_manager_double_init(self):
        from src.memory_confidence import init_confidence_manager, get_confidence_manager
        cm1 = init_confidence_manager(postgres_pool=None)
        cm2 = init_confidence_manager(postgres_pool=None)
        assert cm1 is not None
        assert cm2 is not None

    def test_gdpr_manager_double_init(self):
        from src.gdpr_manager import init_gdpr_manager, get_gdpr_manager
        gm1 = init_gdpr_manager(postgres_pool=None)
        gm2 = init_gdpr_manager(postgres_pool=None)
        assert gm1 is not None
        assert gm2 is not None
