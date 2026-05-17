"""
Unit tests for src/integration/sdlc_integration.py
Covers: SDLCProject, IntegrationConfig, SDLCIntegrationManager
        (create_project, integrate_existing_agent, get_agent_memory_client,
        get_agent_coordination_client, store_agent_memory, search_agent_memory,
        coordinate_task, get_integration_status, private helpers,
        _map_agent_type_to_category).

All external dependencies (memory integration, coordination system) are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.integration.sdlc_integration import (
    SDLCProject,
    IntegrationConfig,
    SDLCIntegrationManager,
    sdlc_integration,
)


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------

class TestSDLCProject:
    @pytest.mark.unit
    def test_defaults(self):
        proj = SDLCProject(
            project_id="p1",
            name="Test",
            description="Desc",
            agent_team=["a", "b"],
        )
        assert proj.memory_retention_days == 30
        assert proj.coordination_enabled is True
        assert proj.auto_discovery is True

    @pytest.mark.unit
    def test_custom_values(self):
        proj = SDLCProject(
            project_id="p2",
            name="N",
            description="D",
            agent_team=[],
            memory_retention_days=60,
            coordination_enabled=False,
            auto_discovery=False,
        )
        assert proj.memory_retention_days == 60
        assert proj.coordination_enabled is False


class TestIntegrationConfig:
    @pytest.mark.unit
    def test_defaults(self):
        cfg = IntegrationConfig()
        assert cfg.automatic_registration is True
        assert "sdlc" in cfg.memory_categories
        assert cfg.coordination_enabled is True

    @pytest.mark.unit
    def test_custom_values(self):
        cfg = IntegrationConfig(automatic_registration=False, coordination_enabled=False)
        assert cfg.automatic_registration is False
        assert cfg.coordination_enabled is False


# ---------------------------------------------------------------------------
# SDLCIntegrationManager
# ---------------------------------------------------------------------------

class TestSDLCIntegrationManagerInit:
    @pytest.mark.unit
    def test_default_config(self):
        mgr = SDLCIntegrationManager()
        assert isinstance(mgr.config, IntegrationConfig)

    @pytest.mark.unit
    def test_custom_config(self):
        cfg = IntegrationConfig(auto_backup=False)
        mgr = SDLCIntegrationManager(config=cfg)
        assert mgr.config is cfg

    @pytest.mark.unit
    def test_initial_state(self):
        mgr = SDLCIntegrationManager()
        assert mgr.projects == {}
        assert mgr.agent_mappings == {}
        assert mgr.integration_status == {}
        assert mgr.memory_integration is None
        assert mgr.coordination_system is None


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------

class TestCreateProject:
    @pytest.fixture
    def mgr(self):
        m = SDLCIntegrationManager(config=IntegrationConfig(automatic_registration=False))
        m.memory_integration = AsyncMock()
        m.memory_integration.add_memory = AsyncMock(return_value="mem-id")
        return m

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_project_with_provided_id(self, mgr):
        pid = await mgr.create_project({
            "project_id": "my-proj",
            "name": "Test Project",
            "description": "A test",
            "agent_team": [],
            "auto_discovery": False,
        })
        assert pid == "my-proj"
        assert "my-proj" in mgr.projects

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_project_with_auto_id(self, mgr):
        pid = await mgr.create_project({
            "name": "Auto ID",
            "description": "desc",
            "agent_team": [],
            "auto_discovery": False,
        })
        assert pid is not None
        assert pid in mgr.projects

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_project_stored_with_correct_name(self, mgr):
        await mgr.create_project({
            "project_id": "p1",
            "name": "Named Project",
            "description": "d",
            "agent_team": [],
            "auto_discovery": False,
        })
        assert mgr.projects["p1"].name == "Named Project"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auto_discovery_registers_agents(self, mgr):
        # auto_discovery=True should call integrate_existing_agent for each team member
        mgr.integration_status["frontend-dev"] = {
            "status": "integrated", "category": "development",
            "integration_time": "2026-01-01T00:00:00",
            "memory_enabled": True, "coordination_enabled": False
        }
        mgr.agent_mappings["frontend-dev"] = "development_frontend-dev"

        with patch.object(mgr, "integrate_existing_agent", AsyncMock(return_value=True)) as mock_int:
            await mgr.create_project({
                "project_id": "p2",
                "name": "P2",
                "description": "d",
                "agent_team": ["frontend-dev"],
                "auto_discovery": True,
            })
            mock_int.assert_called_once()


# ---------------------------------------------------------------------------
# integrate_existing_agent
# ---------------------------------------------------------------------------

class TestIntegrateExistingAgent:
    @pytest.fixture
    def mgr(self):
        m = SDLCIntegrationManager(config=IntegrationConfig(coordination_enabled=False))
        m.memory_integration = AsyncMock()
        return m

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_success_returns_true(self, mgr):
        result = await mgr.integrate_existing_agent({
            "agent_id": "code-reviewer",
            "agent_type": "development",
            "capabilities": ["review"],
        })
        assert result is True
        assert "code-reviewer" in mgr.agent_mappings
        assert mgr.integration_status["code-reviewer"]["status"] == "integrated"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_trading_agent_maps_to_trading_category(self, mgr):
        await mgr.integrate_existing_agent({
            "agent_id": "trade-bot",
            "agent_type": "trading",
            "capabilities": [],
        })
        assert mgr.integration_status["trade-bot"]["category"] == "trading"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sdlc_agent_maps_to_development_category(self, mgr):
        await mgr.integrate_existing_agent({
            "agent_id": "sdlc-bot",
            "agent_type": "sdlc",
            "capabilities": [],
        })
        assert mgr.integration_status["sdlc-bot"]["category"] == "development"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_type_maps_to_coordination(self, mgr):
        await mgr.integrate_existing_agent({
            "agent_id": "misc-bot",
            "agent_type": "misc",
            "capabilities": [],
        })
        assert mgr.integration_status["misc-bot"]["category"] == "coordination"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_false(self, mgr):
        with patch.object(mgr, "_map_agent_type_to_category", side_effect=RuntimeError("err")):
            result = await mgr.integrate_existing_agent({
                "agent_id": "bad-agent",
                "agent_type": "development",
            })
        assert result is False


# ---------------------------------------------------------------------------
# get_agent_memory_client
# ---------------------------------------------------------------------------

class TestGetAgentMemoryClient:
    @pytest.fixture
    def mgr(self):
        m = SDLCIntegrationManager()
        m.integration_status["my-agent"] = {"status": "integrated"}
        m.agent_mappings["my-agent"] = "development_my-agent"
        return m

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_not_integrated_returns_none(self, mgr):
        result = await mgr.get_agent_memory_client("unknown-agent")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_mapping_returns_none(self, mgr):
        mgr.integration_status["no-map"] = {"status": "integrated"}
        result = await mgr.get_agent_memory_client("no-map")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_integrated_agent_returns_none_no_wrapper(self, mgr):
        # Legacy wrappers were removed; returns None
        result = await mgr.get_agent_memory_client("my-agent")
        assert result is None


# ---------------------------------------------------------------------------
# get_agent_coordination_client
# ---------------------------------------------------------------------------

class TestGetAgentCoordinationClient:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coordination_disabled_returns_none(self):
        mgr = SDLCIntegrationManager(config=IntegrationConfig(coordination_enabled=False))
        result = await mgr.get_agent_coordination_client("any-agent")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_agent_not_integrated_returns_none(self):
        mgr = SDLCIntegrationManager()
        result = await mgr.get_agent_coordination_client("ghost-agent")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_coordination_system(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["my-agent"] = {"status": "integrated"}
        mock_coord = MagicMock()
        mgr.coordination_system = mock_coord
        result = await mgr.get_agent_coordination_client("my-agent")
        assert result is mock_coord


# ---------------------------------------------------------------------------
# store_agent_memory / search_agent_memory
# ---------------------------------------------------------------------------

class TestStoreAndSearchMemory:
    @pytest.fixture
    def mgr_with_client(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["my-agent"] = {"status": "integrated"}
        mgr.agent_mappings["my-agent"] = "development_my-agent"
        return mgr

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_memory_no_client_raises(self, mgr_with_client):
        with pytest.raises(ValueError, match="not available"):
            await mgr_with_client.store_agent_memory("my-agent", "content")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_memory_no_client_returns_empty(self, mgr_with_client):
        result = await mgr_with_client.search_agent_memory("my-agent", "query")
        assert result == []


# ---------------------------------------------------------------------------
# coordinate_task
# ---------------------------------------------------------------------------

class TestCoordinateTask:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coordination_disabled_returns_error(self):
        mgr = SDLCIntegrationManager(config=IntegrationConfig(coordination_enabled=False))
        result = await mgr.coordinate_task({"title": "t"})
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_coordination_client_returns_error(self):
        mgr = SDLCIntegrationManager()
        # coordination_enabled=True but client not found
        result = await mgr.coordinate_task({"title": "t", "description": "d"})
        assert "error" in result


# ---------------------------------------------------------------------------
# get_integration_status
# ---------------------------------------------------------------------------

class TestGetIntegrationStatus:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_status(self):
        mgr = SDLCIntegrationManager()
        status = await mgr.get_integration_status()
        assert status["total_agents"] == 0
        assert status["integrated_agents"] == []
        assert status["projects"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_status_with_agents(self):
        mgr = SDLCIntegrationManager()
        mgr.agent_mappings["agent1"] = "development_agent1"
        mgr.integration_status["agent1"] = {
            "status": "integrated",
            "integration_time": "2026-01-01T00:00:00",
        }
        status = await mgr.get_integration_status()
        assert status["total_agents"] == 1
        assert len(status["integrated_agents"]) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_status_with_project(self):
        mgr = SDLCIntegrationManager()
        mgr.projects["p1"] = SDLCProject(
            project_id="p1", name="Proj1", description="d", agent_team=["a"]
        )
        status = await mgr.get_integration_status()
        assert len(status["projects"]) == 1
        assert status["projects"][0]["project_id"] == "p1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_status_contains_configuration(self):
        mgr = SDLCIntegrationManager()
        status = await mgr.get_integration_status()
        assert "configuration" in status
        assert "automatic_registration" in status["configuration"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_status_enhanced_cognee_status(self):
        mgr = SDLCIntegrationManager()
        status = await mgr.get_integration_status()
        ec = status["enhanced_cognee_status"]
        assert ec["memory_system"] == "not_initialized"
        assert ec["coordination_system"] == "not_initialized"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_status_with_active_memory_integration(self):
        mgr = SDLCIntegrationManager()
        mgr.memory_integration = AsyncMock()
        mgr.coordination_system = MagicMock()
        status = await mgr.get_integration_status()
        ec = status["enhanced_cognee_status"]
        assert ec["memory_system"] == "operational"
        assert ec["coordination_system"] == "operational"


# ---------------------------------------------------------------------------
# _map_agent_type_to_category
# ---------------------------------------------------------------------------

class TestMapAgentTypeToCategory:
    @pytest.fixture
    def mgr(self):
        return SDLCIntegrationManager()

    @pytest.mark.unit
    def test_trading_maps_to_trading(self, mgr):
        assert mgr._map_agent_type_to_category("trading") == "trading"
        assert mgr._map_agent_type_to_category("TRADING_SYSTEM") == "trading"

    @pytest.mark.unit
    def test_development_maps_to_development(self, mgr):
        assert mgr._map_agent_type_to_category("development") == "development"
        assert mgr._map_agent_type_to_category("SDLC_agent") == "development"

    @pytest.mark.unit
    def test_unknown_maps_to_coordination(self, mgr):
        assert mgr._map_agent_type_to_category("analytics") == "coordination"
        assert mgr._map_agent_type_to_category("misc") == "coordination"


# ---------------------------------------------------------------------------
# initialize (patched heavy dependencies)
# ---------------------------------------------------------------------------

class TestInitialize:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_calls_components(self):
        """initialize() calls _initialize_enhanced_cognee and helpers."""
        mgr = SDLCIntegrationManager(config=IntegrationConfig(automatic_registration=True))

        with patch.object(mgr, "_initialize_enhanced_cognee", AsyncMock()) as mock_ec, \
             patch.object(mgr, "_register_sdlc_service", AsyncMock()) as mock_reg, \
             patch.object(mgr, "_setup_auto_discovery", AsyncMock()) as mock_disc:
            await mgr.initialize()
            mock_ec.assert_called_once()
            mock_reg.assert_called_once()
            mock_disc.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_without_auto_discovery(self):
        mgr = SDLCIntegrationManager(config=IntegrationConfig(automatic_registration=False))

        with patch.object(mgr, "_initialize_enhanced_cognee", AsyncMock()), \
             patch.object(mgr, "_register_sdlc_service", AsyncMock()), \
             patch.object(mgr, "_setup_auto_discovery", AsyncMock()) as mock_disc:
            await mgr.initialize()
            mock_disc.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_raises_on_enhanced_cognee_failure(self):
        mgr = SDLCIntegrationManager()
        with patch.object(mgr, "_initialize_enhanced_cognee", AsyncMock(side_effect=RuntimeError("fail"))):
            with pytest.raises(RuntimeError):
                await mgr.initialize()


# ---------------------------------------------------------------------------
# _initialize_project_memory / _register_project_agents / coordination paths
# ---------------------------------------------------------------------------

class TestPrivateHelpers:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_project_memory_success(self):
        mgr = SDLCIntegrationManager()
        mgr.memory_integration = AsyncMock()
        mgr.memory_integration.add_memory = AsyncMock(return_value="mem-id")
        proj = SDLCProject(project_id="p1", name="P1", description="d", agent_team=[])
        await mgr._initialize_project_memory(proj)  # should not raise

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_project_memory_error_logged(self):
        mgr = SDLCIntegrationManager()
        mgr.memory_integration = AsyncMock()
        mgr.memory_integration.add_memory = AsyncMock(side_effect=RuntimeError("fail"))
        proj = SDLCProject(project_id="p1", name="P1", description="d", agent_team=[])
        await mgr._initialize_project_memory(proj)  # should not raise

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_project_agents_calls_integrate(self):
        mgr = SDLCIntegrationManager()
        proj = SDLCProject(
            project_id="p1", name="P1", description="d",
            agent_team=["agent-a", "agent-b"]
        )
        with patch.object(mgr, "integrate_existing_agent", AsyncMock(return_value=True)) as mock_int:
            await mgr._register_project_agents(proj)
            assert mock_int.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_sdlc_service_is_noop(self):
        mgr = SDLCIntegrationManager()
        await mgr._register_sdlc_service()  # pass-through

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_setup_auto_discovery_is_noop(self):
        mgr = SDLCIntegrationManager()
        await mgr._setup_auto_discovery()  # pass-through

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_agent_memory_wrapper_is_noop(self):
        mgr = SDLCIntegrationManager()
        await mgr._create_agent_memory_wrapper("agent1", "trading")  # pass-through

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_with_coordination_is_noop(self):
        mgr = SDLCIntegrationManager()
        await mgr._register_with_coordination("agent1", ["cap1"])  # pass-through


# ---------------------------------------------------------------------------
# coordinate_task with mocked coordination client
# ---------------------------------------------------------------------------

class TestCoordinateTaskWithClient:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coordinate_task_success(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["sdlc_coordinator"] = {"status": "integrated"}

        mock_client = AsyncMock()
        mock_client.assign_task = AsyncMock(return_value=True)

        with patch.object(mgr, "get_agent_coordination_client", AsyncMock(return_value=mock_client)):
            result = await mgr.coordinate_task({
                "task_id": "t1",
                "title": "Build feature",
                "description": "Implement feature X",
                "priority": "normal",
            })
        assert "task_id" in result
        assert result["status"] == "assigned"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coordinate_task_failure_in_assign(self):
        mgr = SDLCIntegrationManager()

        mock_client = AsyncMock()
        mock_client.assign_task = AsyncMock(return_value=False)

        with patch.object(mgr, "get_agent_coordination_client", AsyncMock(return_value=mock_client)):
            result = await mgr.coordinate_task({
                "task_id": "t2",
                "title": "Task",
                "description": "desc",
                "priority": "high",
            })
        assert result["status"] == "failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coordinate_task_exception_returns_error(self):
        mgr = SDLCIntegrationManager()
        with patch.object(
            mgr, "get_agent_coordination_client",
            AsyncMock(side_effect=RuntimeError("coordination crashed"))
        ):
            result = await mgr.coordinate_task({"title": "t"})
        assert "error" in result


# ---------------------------------------------------------------------------
# create_project exception path (line 98-100)
# ---------------------------------------------------------------------------

class TestCreateProjectError:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_project_raises_on_memory_init_fail(self):
        mgr = SDLCIntegrationManager()
        mgr.memory_integration = AsyncMock()
        mgr.memory_integration.add_memory = AsyncMock(side_effect=RuntimeError("db"))
        # _initialize_project_memory catches its own error - need to fail in store
        with patch.object(mgr, "_initialize_project_memory", AsyncMock(side_effect=RuntimeError("fail"))):
            with pytest.raises(RuntimeError):
                await mgr.create_project({
                    "project_id": "bad",
                    "name": "N",
                    "description": "D",
                    "agent_team": [],
                    "auto_discovery": False,
                })


# ---------------------------------------------------------------------------
# store_agent_memory when client is available
# ---------------------------------------------------------------------------

class TestStoreMemoryWithClient:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_memory_via_client_returns_id(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["a1"] = {"status": "integrated"}
        mgr.agent_mappings["a1"] = "development_a1"

        mock_client = AsyncMock()
        mock_client.add_memory = AsyncMock(return_value="mem-999")

        with patch.object(mgr, "get_agent_memory_client", AsyncMock(return_value=mock_client)):
            mem_id = await mgr.store_agent_memory("a1", "content here")
        assert mem_id == "mem-999"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_memory_exception_re_raised(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["a1"] = {"status": "integrated"}
        mgr.agent_mappings["a1"] = "development_a1"

        mock_client = AsyncMock()
        mock_client.add_memory = AsyncMock(side_effect=RuntimeError("mem fail"))

        with patch.object(mgr, "get_agent_memory_client", AsyncMock(return_value=mock_client)):
            with pytest.raises(RuntimeError):
                await mgr.store_agent_memory("a1", "content")


# ---------------------------------------------------------------------------
# search_agent_memory when client is available
# ---------------------------------------------------------------------------

class TestSearchMemoryWithClient:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_memory_via_client_returns_results(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["a1"] = {"status": "integrated"}
        mgr.agent_mappings["a1"] = "development_a1"

        mock_client = AsyncMock()
        mock_client.search_memory = AsyncMock(return_value=[{"id": "m1"}])

        with patch.object(mgr, "get_agent_memory_client", AsyncMock(return_value=mock_client)):
            results = await mgr.search_agent_memory("a1", "query")
        assert len(results) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_memory_exception_returns_empty(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["a1"] = {"status": "integrated"}
        mgr.agent_mappings["a1"] = "development_a1"

        mock_client = AsyncMock()
        mock_client.search_memory = AsyncMock(side_effect=RuntimeError("fail"))

        with patch.object(mgr, "get_agent_memory_client", AsyncMock(return_value=mock_client)):
            results = await mgr.search_agent_memory("a1", "query")
        assert results == []


# ---------------------------------------------------------------------------
# get_agent_memory_client error path
# ---------------------------------------------------------------------------

class TestGetAgentMemoryClientError:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_none(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["a1"] = {"status": "integrated"}
        mgr.agent_mappings["a1"] = "development_a1"

        with patch.dict(mgr.agent_mappings, {}, clear=True):
            # agent_mappings is now empty so enhanced_agent_id will be None
            result = await mgr.get_agent_memory_client("a1")
        assert result is None


# ---------------------------------------------------------------------------
# get_agent_coordination_client exception path
# ---------------------------------------------------------------------------

class TestGetAgentCoordinationClientError:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_none(self):
        mgr = SDLCIntegrationManager()
        mgr.integration_status["a1"] = {"status": "integrated"}
        # Force exception inside the method by making config.coordination_enabled raise
        original = type(mgr.config).coordination_enabled
        try:
            type(mgr.config).coordination_enabled = property(
                fget=lambda self: (_ for _ in ()).throw(RuntimeError("oops"))
            )
            result = await mgr.get_agent_coordination_client("a1")
            assert result is None
        finally:
            type(mgr.config).coordination_enabled = original


# ---------------------------------------------------------------------------
# get_integration_status error path
# ---------------------------------------------------------------------------

class TestGetIntegrationStatusError:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self):
        mgr = SDLCIntegrationManager()
        # Corrupt agent_mappings to trigger exception
        mgr.agent_mappings = None  # will cause TypeError on len()
        status = await mgr.get_integration_status()
        assert "error" in status


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

class TestGlobalSingleton:
    @pytest.mark.unit
    def test_sdlc_integration_is_manager(self):
        assert isinstance(sdlc_integration, SDLCIntegrationManager)
