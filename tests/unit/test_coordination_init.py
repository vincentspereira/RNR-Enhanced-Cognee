"""
Unit tests for src/coordination/__init__.py
Target: >= 85% line coverage.

Heavy sub-module imports (SubAgentCoordinator, TaskOrchestrationEngine,
DistributedDecisionMaker, app) are already exercised by import; the
async functions in this __init__ are exercised via mocks.
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Module-level metadata
# ---------------------------------------------------------------------------

class TestModuleMetadata:
    def test_version_string(self):
        from src.coordination import __version__
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_author_string(self):
        from src.coordination import __author__
        assert isinstance(__author__, str)

    def test_coordination_system_info_is_dict(self):
        from src.coordination import COORDINATION_SYSTEM_INFO
        assert isinstance(COORDINATION_SYSTEM_INFO, dict)

    def test_info_has_name(self):
        from src.coordination import COORDINATION_SYSTEM_INFO
        assert "name" in COORDINATION_SYSTEM_INFO

    def test_info_has_version(self):
        from src.coordination import COORDINATION_SYSTEM_INFO
        assert "version" in COORDINATION_SYSTEM_INFO

    def test_info_has_components(self):
        from src.coordination import COORDINATION_SYSTEM_INFO
        assert "components" in COORDINATION_SYSTEM_INFO
        assert isinstance(COORDINATION_SYSTEM_INFO["components"], dict)

    def test_dunder_all_exports(self):
        from src.coordination import __all__
        assert "SubAgentCoordinator" in __all__
        assert "TaskOrchestrationEngine" in __all__
        assert "DistributedDecisionMaker" in __all__
        assert "app" in __all__

    def test_classes_importable(self):
        from src.coordination import (
            SubAgentCoordinator,
            TaskOrchestrationEngine,
            DistributedDecisionMaker,
        )
        assert SubAgentCoordinator is not None
        assert TaskOrchestrationEngine is not None
        assert DistributedDecisionMaker is not None


# ---------------------------------------------------------------------------
# get_coordination_system_info
# ---------------------------------------------------------------------------

class TestGetCoordinationSystemInfo:
    def test_returns_dict(self):
        from src.coordination import get_coordination_system_info
        result = get_coordination_system_info()
        assert isinstance(result, dict)

    def test_same_as_constant(self):
        from src.coordination import get_coordination_system_info, COORDINATION_SYSTEM_INFO
        result = get_coordination_system_info()
        assert result is COORDINATION_SYSTEM_INFO

    def test_contains_name(self):
        from src.coordination import get_coordination_system_info
        info = get_coordination_system_info()
        assert "name" in info


# ---------------------------------------------------------------------------
# _load_coordination_settings (internal, exercised via warm-up)
# ---------------------------------------------------------------------------

class TestLoadCoordinationSettings:
    @pytest.mark.asyncio
    async def test_does_not_raise(self):
        """_load_coordination_settings is a pass-through and must not raise."""
        from src.coordination import _load_coordination_settings
        mock_coordinator = MagicMock()
        # Should complete without error
        await _load_coordination_settings(mock_coordinator)


# ---------------------------------------------------------------------------
# _warm_up_coordination_system
# ---------------------------------------------------------------------------

class TestWarmUpCoordinationSystem:
    @pytest.mark.asyncio
    async def test_success_path(self, capsys):
        from src.coordination import _warm_up_coordination_system
        coordinator = AsyncMock()
        coordinator.register_agent_capability = AsyncMock()
        orchestrator = MagicMock()
        decision_maker = MagicMock()
        await _warm_up_coordination_system(coordinator, orchestrator, decision_maker)
        out = capsys.readouterr().out
        assert "warmed up" in out.lower() or "Coordination system" in out

    @pytest.mark.asyncio
    async def test_failure_path_prints_warning(self, capsys):
        """When _register_default_capabilities raises, warm-up catches and prints warning."""
        from src.coordination import _warm_up_coordination_system
        coordinator = MagicMock()
        orchestrator = MagicMock()
        decision_maker = MagicMock()

        with patch(
            "src.coordination._register_default_capabilities",
            new=AsyncMock(side_effect=RuntimeError("boom"))
        ):
            await _warm_up_coordination_system(coordinator, orchestrator, decision_maker)

        out = capsys.readouterr().out
        assert "Warning" in out or "warn" in out.lower() or "failed" in out.lower()


# ---------------------------------------------------------------------------
# _register_default_capabilities
# ---------------------------------------------------------------------------

class TestRegisterDefaultCapabilities:
    @pytest.mark.asyncio
    async def test_calls_register_for_each_capability(self):
        from src.coordination import _register_default_capabilities
        coordinator = AsyncMock()
        coordinator.register_agent_capability = AsyncMock()
        await _register_default_capabilities(coordinator)
        # Should register at least one capability (context-manager, task-scheduler, message-broker)
        assert coordinator.register_agent_capability.call_count >= 1

    @pytest.mark.asyncio
    async def test_single_failure_continues(self, capsys):
        """A failure on one capability must not abort registration of others."""
        from src.coordination import _register_default_capabilities
        coordinator = AsyncMock()
        call_count = 0

        async def _maybe_fail(capability):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("first cap failed")

        coordinator.register_agent_capability = _maybe_fail
        await _register_default_capabilities(coordinator)
        # At least the 2nd and 3rd capabilities should have been attempted
        assert call_count >= 2
        out = capsys.readouterr().out
        assert "Warning" in out or "warn" in out.lower() or "Failed" in out


# ---------------------------------------------------------------------------
# initialize_coordination_system (integration of above)
# ---------------------------------------------------------------------------

class TestInitializeCoordinationSystem:
    @pytest.mark.asyncio
    async def test_returns_dict_with_required_keys(self):
        from src.coordination import initialize_coordination_system

        mock_memory = MagicMock()

        # Patch the three heavy constructors and the warm-up call
        with (
            patch("src.coordination.SubAgentCoordinator") as MockCoord,
            patch("src.coordination.TaskOrchestrationEngine") as MockOrch,
            patch("src.coordination.DistributedDecisionMaker") as MockDM,
            patch("src.coordination._warm_up_coordination_system", new=AsyncMock()),
        ):
            mock_coord_inst = MagicMock()
            mock_orch_inst = MagicMock()
            mock_dm_inst = MagicMock()
            MockCoord.return_value = mock_coord_inst
            MockOrch.return_value = mock_orch_inst
            MockDM.return_value = mock_dm_inst

            result = await initialize_coordination_system(mock_memory)

        assert "coordinator" in result
        assert "orchestrator" in result
        assert "decision_maker" in result

    @pytest.mark.asyncio
    async def test_components_wired_correctly(self):
        from src.coordination import initialize_coordination_system

        mock_memory = MagicMock()
        coord_inst = MagicMock()
        orch_inst = MagicMock()
        dm_inst = MagicMock()

        # The function does local imports inside its body, so patch those sub-modules
        with (
            patch("src.coordination.sub_agent_coordinator.SubAgentCoordinator", return_value=coord_inst) as MockCoord,
            patch("src.coordination.task_orchestration.TaskOrchestrationEngine", return_value=orch_inst) as MockOrch,
            patch("src.coordination.distributed_decision.DistributedDecisionMaker", return_value=dm_inst) as MockDM,
            patch("src.coordination._warm_up_coordination_system", new=AsyncMock()),
        ):
            result = await initialize_coordination_system(mock_memory)

        assert result["coordinator"] is coord_inst
        assert result["orchestrator"] is orch_inst
        assert result["decision_maker"] is dm_inst
