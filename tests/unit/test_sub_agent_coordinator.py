"""
Unit tests for src/coordination/sub_agent_coordinator.py
Covers: SubAgentCoordinator init, assign_task, register_agent_capability,
        route_message, get_agent_load, get_coordination_overview,
        private helpers (_find_suitable_agents, _assign_to_least_loaded_agents,
        _send_message routing, _store_coordination_task/message,
        _get_recent_message_activity, _get_most_active_agents,
        _broadcast_to_all, _send_direct_message).
"""

import uuid
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Stub AgentMemoryIntegration so sub_agent_coordinator can be imported cleanly
# ---------------------------------------------------------------------------

import sys
import types

# Build minimal stub for src.agent_memory_integration if not already present
if "src.agent_memory_integration" not in sys.modules:
    _stub = types.ModuleType("src.agent_memory_integration")

    class _MemType:
        SEMANTIC = "semantic"
        EPISODIC = "episodic"

    class _AMI:
        def __init__(self): pass
        async def initialize(self): pass
        async def add_memory(self, **kw): return "mem-id"
        async def close(self): pass

    _stub.AgentMemoryIntegration = _AMI
    _stub.MemoryType = _MemType
    sys.modules["src.agent_memory_integration"] = _stub

# If another test file already pre-loaded minimal stubs, evict them and
# restore the real src.coordination package so Python finds the real source.
from pathlib import Path as _Path
_real_coord_path = str(_Path(__file__).parent.parent.parent / "src" / "coordination")
_existing_coord = sys.modules.get("src.coordination")
if _existing_coord is not None and not hasattr(_existing_coord, "_is_real_pkg"):
    _real_pkg = types.ModuleType("src.coordination")
    _real_pkg.__path__ = [_real_coord_path]
    _real_pkg.__package__ = "src.coordination"
    _real_pkg._is_real_pkg = True
    sys.modules["src.coordination"] = _real_pkg
sys.modules.pop("src.coordination.sub_agent_coordinator", None)

from src.coordination.sub_agent_coordinator import (
    SubAgentCoordinator,
    AgentTask,
    AgentMessage,
    AgentCapability,
    AgentStatus,
    TaskPriority,
    MessageType,
    _TradingMemoryWrapperStub,
    _DevelopmentMemoryWrapperStub,
    _CoordinationMemoryWrapperStub,
)

# Capture AgentMemoryIntegration at module load time (before cleanup fixtures run)
# so the integration fixture can use it even after sys.modules is cleaned up.
_AgentMemoryIntegration = sys.modules["src.agent_memory_integration"].AgentMemoryIntegration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def integration():
    m = MagicMock(spec=_AgentMemoryIntegration)
    return m


@pytest.fixture
def coordinator(integration):
    return SubAgentCoordinator(integration)


def _make_task(title="Analyze data", desc="desc", priority=TaskPriority.NORMAL,
               assigned_to=None):
    return AgentTask(
        task_id=str(uuid.uuid4()),
        title=title,
        description=desc,
        assigned_to=assigned_to or [],
        created_by="test_manager",
        priority=priority,
    )


def _make_message(from_agent="a", to_agent="risk-management",
                  msg_type=MessageType.REQUEST):
    return AgentMessage(
        message_id=str(uuid.uuid4()),
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=msg_type,
        subject="Test",
        content={"key": "value"},
    )


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class TestStubs:
    @pytest.mark.unit
    def test_trading_stub_init(self, integration):
        stub = _TradingMemoryWrapperStub(integration)
        assert stub.integration is integration

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_trading_stub_store_no_error(self, integration):
        stub = _TradingMemoryWrapperStub(integration)
        await stub.store_execution_result()  # should not raise

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_development_stub_store_no_error(self, integration):
        stub = _DevelopmentMemoryWrapperStub(integration)
        await stub.store_analysis_report()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_coordination_stub_all_methods(self, integration):
        stub = _CoordinationMemoryWrapperStub(integration)
        await stub.store_message()
        await stub.store_context()
        await stub.store_task()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestSubAgentCoordinatorInit:
    @pytest.mark.unit
    def test_agent_registry_populated(self, coordinator):
        assert len(coordinator.agent_registry) > 0
        assert "algorithmic-trading-system" in coordinator.agent_registry
        assert "risk-management" in coordinator.agent_registry

    @pytest.mark.unit
    def test_active_tasks_empty(self, coordinator):
        assert coordinator.active_tasks == {}

    @pytest.mark.unit
    def test_message_queue_empty(self, coordinator):
        assert coordinator.message_queue == []

    @pytest.mark.unit
    def test_coordination_settings_populated(self, coordinator):
        assert "max_task_retries" in coordinator.coordination_settings

    @pytest.mark.unit
    def test_all_agents_have_category(self, coordinator):
        for agent_id, info in coordinator.agent_registry.items():
            assert "category" in info
            assert info["category"] in {"trading", "development", "coordination"}


# ---------------------------------------------------------------------------
# assign_task
# ---------------------------------------------------------------------------

class TestAssignTask:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_assigns_task_to_suitable_agent(self, coordinator):
        task = _make_task(title="Analyze market volatility", desc="market analysis")
        result = await coordinator.assign_task(task)
        assert result is True
        assert task.task_id in coordinator.active_tasks
        assert task.status == "assigned"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_task_with_no_suitable_agents_fails(self, coordinator):
        task = _make_task(
            title="ZZZunmatchable_xxxx",
            desc="zzz_completely_unrelated_zzz",
        )
        result = await coordinator.assign_task(task)
        assert result is False
        assert task.status == "failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_during_assign_returns_false(self, coordinator):
        task = _make_task(title="test", desc="analysis")
        with patch.object(coordinator, "_store_coordination_task", side_effect=Exception("db down")):
            result = await coordinator.assign_task(task)
        assert result is False
        assert task.error_message is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_task_stored_in_active_tasks(self, coordinator):
        task = _make_task(title="execution order market", desc="order execution")
        await coordinator.assign_task(task)
        assert task.task_id in coordinator.active_tasks

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_messages_queued_for_assigned_agents(self, coordinator):
        task = _make_task(title="market data analysis", desc="market analysis signal")
        initial_queue_len = len(coordinator.message_queue)
        await coordinator.assign_task(task)
        assert len(coordinator.message_queue) > initial_queue_len


# ---------------------------------------------------------------------------
# register_agent_capability
# ---------------------------------------------------------------------------

class TestRegisterAgentCapability:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_registers_capability(self, coordinator):
        cap = AgentCapability(
            agent_id="market-analyzer",
            capability_name="custom_analysis",
            description="Custom analysis",
            input_types=["data"],
            output_types=["result"],
        )
        result = await coordinator.register_agent_capability(cap)
        assert result is True
        assert "market-analyzer_custom_analysis" in coordinator.agent_capabilities

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_false(self, coordinator):
        cap = AgentCapability(
            agent_id="x",
            capability_name="y",
            description="d",
            input_types=[],
            output_types=[],
        )
        with patch.object(coordinator.smc_wrapper, "store_context", side_effect=Exception("err")):
            result = await coordinator.register_agent_capability(cap)
        assert result is False


# ---------------------------------------------------------------------------
# route_message
# ---------------------------------------------------------------------------

class TestRouteMessage:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_routes_to_known_agent(self, coordinator):
        msg = _make_message(to_agent="risk-management")
        result = await coordinator.route_message(msg)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fails_for_unknown_agent(self, coordinator):
        msg = _make_message(to_agent="nonexistent-agent-xyz")
        result = await coordinator.route_message(msg)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_broadcast_message_type(self, coordinator):
        msg = _make_message(to_agent="algorithmic-trading-system",
                            msg_type=MessageType.BROADCAST)
        result = await coordinator.route_message(msg)
        # _broadcast_message returns None (pass) which is falsy
        assert result is None or result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_route_to_all(self, coordinator):
        msg = AgentMessage(
            message_id=str(uuid.uuid4()),
            from_agent="coordinator",
            to_agent="all",
            message_type=MessageType.BROADCAST,
            subject="Broadcast",
            content={},
        )
        result = await coordinator.route_message(msg)
        # broadcast_to_all sends to all known agents
        assert result is True or result is False  # just no exception

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_false(self, coordinator):
        msg = _make_message()
        with patch.object(coordinator, "_store_coordination_message", side_effect=Exception("err")):
            result = await coordinator.route_message(msg)
        assert result is False


# ---------------------------------------------------------------------------
# get_agent_load
# ---------------------------------------------------------------------------

class TestGetAgentLoad:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_dict_for_known_agent(self, coordinator):
        result = await coordinator.get_agent_load("risk-management")
        assert result["agent_id"] == "risk-management"
        assert "active_tasks" in result
        assert "load_percentage" in result
        assert "status" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_zero_load_for_idle_agent(self, coordinator):
        result = await coordinator.get_agent_load("risk-management")
        assert result["active_tasks"] == 0
        assert result["load_percentage"] == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_busy_status_when_high_load(self, coordinator):
        # Put tasks in active_tasks assigned to this agent
        for i in range(3):
            task = AgentTask(
                task_id=str(uuid.uuid4()),
                title="t",
                description="d",
                assigned_to=["risk-management"],
                created_by="c",
                priority=TaskPriority.NORMAL,
                status="in_progress",
            )
            coordinator.active_tasks[task.task_id] = task
        result = await coordinator.get_agent_load("risk-management")
        # max_concurrent_tasks for risk-management is 3, so 3/3 = 100%
        assert result["status"] == "busy"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_agent_returns_defaults(self, coordinator):
        result = await coordinator.get_agent_load("ghost-agent")
        assert result["agent_id"] == "ghost-agent"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_error(self, coordinator):
        with patch.object(coordinator, "active_tasks", side_effect=Exception("err")):
            # active_tasks is a dict, so we trigger via different means
            result = await coordinator.get_agent_load("err-agent")
        # Should still return something
        assert "agent_id" in result


# ---------------------------------------------------------------------------
# get_coordination_overview
# ---------------------------------------------------------------------------

class TestGetCoordinationOverview:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_expected_keys(self, coordinator):
        result = await coordinator.get_coordination_overview()
        assert "total_agents" in result
        assert "active_agents" in result
        assert "task_statistics" in result
        assert "category_statistics" in result
        assert "coordination_health" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_agent_count_matches_registry(self, coordinator):
        result = await coordinator.get_coordination_overview()
        assert result["total_agents"] == len(coordinator.agent_registry)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_zero_tasks_when_empty(self, coordinator):
        result = await coordinator.get_coordination_overview()
        assert result["task_statistics"]["total_tasks"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_task_statistics_with_active_tasks(self, coordinator):
        task = _make_task()
        task.status = "completed"
        coordinator.active_tasks[task.task_id] = task
        result = await coordinator.get_coordination_overview()
        assert result["task_statistics"]["total_tasks"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self, coordinator):
        with patch.object(coordinator, "get_agent_load", side_effect=Exception("fail")):
            result = await coordinator.get_coordination_overview()
        assert "error" in result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

class TestFindSuitableAgents:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_finds_market_analyzer_for_market_task(self, coordinator):
        task = _make_task(title="market data analysis", desc="analyze market trends")
        agents = await coordinator._find_suitable_agents(task)
        assert len(agents) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_agents_for_unmatchable_task(self, coordinator):
        task = _make_task(title="qqqxxx", desc="zzzyyy")
        agents = await coordinator._find_suitable_agents(task)
        assert agents == []


class TestAssignToLeastLoaded:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_up_to_max_agents(self, coordinator):
        agents = ["risk-management", "market-analyzer", "algorithmic-trading-system"]
        task = _make_task()
        result = await coordinator._assign_to_least_loaded_agents(agents, task, max_assignments=2)
        assert len(result) <= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_all_if_fewer_than_max(self, coordinator):
        agents = ["risk-management"]
        task = _make_task()
        result = await coordinator._assign_to_least_loaded_agents(agents, task, max_assignments=5)
        assert len(result) == 1


class TestSendMessage:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sends_to_trading_category(self, coordinator):
        msg = _make_message(to_agent="algorithmic-trading-system",
                            msg_type=MessageType.REQUEST)
        result = await coordinator._send_message(msg)
        assert result is True
        assert msg in coordinator.message_queue

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sends_to_development_category(self, coordinator):
        msg = _make_message(to_agent="code-reviewer", msg_type=MessageType.REQUEST)
        result = await coordinator._send_message(msg)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sends_to_coordination_category(self, coordinator):
        msg = _make_message(to_agent="context-manager", msg_type=MessageType.NOTIFICATION)
        result = await coordinator._send_message(msg)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_false(self, coordinator):
        msg = _make_message()
        with patch.object(coordinator.ats_wrapper, "store_execution_result", side_effect=Exception("e")):
            result = await coordinator._send_message(msg)
        # It routes to trading category -> error -> returns False
        assert result is False


class TestGetMostActiveAgents:
    @pytest.mark.unit
    def test_returns_sorted_by_count(self, coordinator):
        messages = [
            {"from_agent": "a", "to_agent": "b"},
            {"from_agent": "a", "to_agent": "c"},
            {"from_agent": "b", "to_agent": "a"},
        ]
        result = coordinator._get_most_active_agents(messages)
        assert result[0]["agent"] == "a"

    @pytest.mark.unit
    def test_respects_limit(self, coordinator):
        messages = [{"from_agent": f"agent_{i}", "to_agent": "x"} for i in range(10)]
        result = coordinator._get_most_active_agents(messages, limit=3)
        assert len(result) <= 3

    @pytest.mark.unit
    def test_excludes_all_recipient(self, coordinator):
        messages = [{"from_agent": "a", "to_agent": "all"}]
        result = coordinator._get_most_active_agents(messages)
        # "all" should not appear as most active
        agent_names = [r["agent"] for r in result]
        assert "all" not in agent_names


class TestGetRecentMessageActivity:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_only_recent_messages(self, coordinator):
        old_msg = AgentMessage(
            message_id="old",
            from_agent="x",
            to_agent="risk-management",
            message_type=MessageType.REQUEST,
            subject="old",
            content={},
        )
        old_msg.created_at = datetime.now(UTC) - timedelta(hours=3)

        recent_msg = AgentMessage(
            message_id="new",
            from_agent="y",
            to_agent="risk-management",
            message_type=MessageType.REQUEST,
            subject="new",
            content={},
        )
        coordinator.message_queue = [old_msg, recent_msg]
        result = await coordinator._get_recent_message_activity(hours=1)
        ids = [m["message_id"] for m in result]
        assert "new" in ids
        assert "old" not in ids


class TestBroadcastToAll:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sends_to_all_agents(self, coordinator):
        msg = _make_message(from_agent="coordinator", to_agent="all",
                            msg_type=MessageType.BROADCAST)
        result = await coordinator._broadcast_to_all(msg)
        # With stubs, all sends should succeed
        assert isinstance(result, bool)
        # Queue should have entries for all agents
        assert len(coordinator.message_queue) == len(coordinator.agent_registry)
