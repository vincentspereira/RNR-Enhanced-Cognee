"""
Unit tests for src/coordination/task_orchestration.py
Covers: TaskOrchestrationEngine - create_workflow, execute_workflow,
        get_workflow_status, pause_workflow, resume_workflow, cancel_workflow,
        _validate_workflow, _has_circular_dependencies, _schedule_ready_tasks,
        _are_dependencies_satisfied, _execute_task, _handle_task_failure,
        _handle_task_timeout, _retry_task, _should_fail_workflow,
        _pause_task_execution, _cancel_task_execution,
        _send_task_control_message, dataclasses, enums.
Target: >= 85% line coverage.

Import isolation:
  task_orchestration imports sub_agent_coordinator which pulls in
  agent_memory_integration (qdrant/numpy C-extensions). We stub that
  chain at module level before importing the real task_orchestration.

  Strategy (mirrors test_security_middleware.py):
  - Do NOT stub the real src.coordination package itself; let Python
    resolve it normally so its __path__ stays intact.
  - Pre-stub only the problematic sub-modules so their imports succeed.
  - Import src.coordination.task_orchestration with importlib after stubs.
"""

import sys
import types
import uuid
import asyncio
import importlib as _importlib
import pytest
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Snapshot BEFORE stub injection
# ---------------------------------------------------------------------------

_MODULES_TO_PROTECT = [
    "src.coordination",
    "src.coordination.sub_agent_coordinator",
    "src.coordination.distributed_decision",
    "src.coordination.coordination_api",
    "src.coordination.task_orchestration",
    "src.agent_memory_integration",
    "src.agents",
    "src.agents.smc_memory_wrapper",
]
_SYS_MODULES_SNAPSHOT = {k: sys.modules.get(k) for k in _MODULES_TO_PROTECT}


# ---------------------------------------------------------------------------
# Module-level stub injection (happens at import/collection time)
# ---------------------------------------------------------------------------

# ---- agent_memory_integration stub ----
_ami_mod = types.ModuleType("src.agent_memory_integration")


class _MemoryType(Enum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    WORKING = "working"


class _AgentMemoryIntegration:
    def __init__(self): pass
    async def initialize(self): pass
    async def close(self): pass


_ami_mod.AgentMemoryIntegration = _AgentMemoryIntegration
_ami_mod.MemoryType = _MemoryType
sys.modules["src.agent_memory_integration"] = _ami_mod

# ---- sub_agent_coordinator stub ----
_sac_mod = types.ModuleType("src.coordination.sub_agent_coordinator")


class _AgentStatus(Enum):
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    SUSPENDED = "suspended"
    ERROR = "error"


class _TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class _MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    TASK_ASSIGNMENT = "task_assignment"
    TASK_COMPLETION = "task_completion"
    ERROR_REPORT = "error_report"
    HEARTBEAT = "heartbeat"


@dataclass
class _AgentTask:
    task_id: str
    title: str
    description: str
    assigned_to: List[str]
    created_by: str
    priority: "_TaskPriority"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class _AgentMessage:
    message_id: str
    from_agent: str
    to_agent: str
    message_type: "_MessageType"
    subject: str
    content: Dict[str, Any]
    priority: "_TaskPriority" = field(default=None)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reply_to: Optional[str] = None
    requires_response: bool = False
    responded_at: Optional[datetime] = None


class _SubAgentCoordinator:
    def __init__(self, integration=None):
        self.integration = integration
        self.active_tasks = {}
        self.message_queue = []
    async def assign_task(self, task): return True
    async def route_message(self, message): pass


_sac_mod.AgentStatus = _AgentStatus
_sac_mod.TaskPriority = _TaskPriority
_sac_mod.MessageType = _MessageType
_sac_mod.AgentTask = _AgentTask
_sac_mod.AgentMessage = _AgentMessage
_sac_mod.SubAgentCoordinator = _SubAgentCoordinator
# Also stub AgentCapability for __init__.py imports
_sac_mod.AgentCapability = MagicMock()
sys.modules["src.coordination.sub_agent_coordinator"] = _sac_mod

# ---- distributed_decision stub (imported by __init__.py) ----
_dd_mod = types.ModuleType("src.coordination.distributed_decision")
_dd_mod.DistributedDecisionMaker = MagicMock()
sys.modules["src.coordination.distributed_decision"] = _dd_mod

# ---- coordination_api stub (imported by __init__.py) ----
_api_mod = types.ModuleType("src.coordination.coordination_api")
_api_mod.app = MagicMock()
sys.modules["src.coordination.coordination_api"] = _api_mod

# ---- smc_memory_wrapper stub ----
_agents_mod = types.ModuleType("src.agents")
_agents_mod.__path__ = []
sys.modules["src.agents"] = _agents_mod
_smc_mod = types.ModuleType("src.agents.smc_memory_wrapper")


class _SMCMemoryWrapper:
    def __init__(self, integration=None): pass
    async def store_task(self, agent_id, task_data): pass


_smc_mod.SMCMemoryWrapper = _SMCMemoryWrapper
sys.modules["src.agents.smc_memory_wrapper"] = _smc_mod

# ---- import real module (do NOT stub src.coordination itself) ----
# Only pop task_orchestration so it re-imports cleanly with our stubs in place.
# We do NOT pop src.coordination itself to avoid re-running __init__.py which
# could trigger reimport chains and numpy "cannot load module more than once"
# errors in parallel test processes.
sys.modules.pop("src.coordination.task_orchestration", None)
_orch_mod = _importlib.import_module("src.coordination.task_orchestration")

# Immediately restore ALL stubbed modules so other test files are unaffected.
# The task_orchestration module is already imported and its top-level namespace
# is fully bound to our stub objects.  Deferred imports inside methods (e.g.
# _store_workflow_definition uses `from ..agents.smc_memory_wrapper import ...`)
# will be patched contextually in the tests that call those methods.
_RESTORE_NOW = list(_SYS_MODULES_SNAPSHOT.keys())
for _k in _RESTORE_NOW:
    _orig = _SYS_MODULES_SNAPSHOT.get(_k)
    if _orig is None:
        sys.modules.pop(_k, None)
    else:
        sys.modules[_k] = _orig

# ---- bind public symbols ----
TaskOrchestrationEngine = _orch_mod.TaskOrchestrationEngine
TaskStatus = _orch_mod.TaskStatus
WorkflowStatus = _orch_mod.WorkflowStatus
TaskDependency = _orch_mod.TaskDependency
WorkflowDefinition = _orch_mod.WorkflowDefinition
TaskExecution = _orch_mod.TaskExecution
WorkflowExecution = _orch_mod.WorkflowExecution

# from stub
SubAgentCoordinator = _SubAgentCoordinator
AgentTask = _AgentTask
AgentMessage = _AgentMessage
TaskPriority = _TaskPriority


# ---------------------------------------------------------------------------
# Autouse fixture (no-op -- all stubs are restored immediately after import)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _restore_modules():
    """All stubs were restored at import time; this is a no-op placeholder."""
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_coordinator():
    coord = MagicMock(spec=SubAgentCoordinator)
    coord.integration = MagicMock()
    coord.assign_task = AsyncMock(return_value=True)
    coord.route_message = AsyncMock()
    return coord


def _make_engine():
    coord = _make_coordinator()
    engine = TaskOrchestrationEngine(coord)
    return engine, coord


def _make_task(task_id="t1", priority=None, assigned_to=None):
    if priority is None:
        priority = TaskPriority.NORMAL
    return AgentTask(
        task_id=task_id,
        title=f"Task {task_id}",
        description="Test task",
        assigned_to=assigned_to or [],
        created_by="test",
        priority=priority,
    )


def _make_workflow(workflow_id="wf1", tasks=None, deps=None):
    if tasks is None:
        tasks = [_make_task("t1")]
    return WorkflowDefinition(
        workflow_id=workflow_id,
        name="Test Workflow",
        description="Test",
        created_by="tester",
        tasks=tasks,
        dependencies=deps or [],
    )


# ---------------------------------------------------------------------------
# Enums and dataclasses
# ---------------------------------------------------------------------------

class TestEnums:
    def test_task_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.TIMEOUT.value == "timeout"
        assert TaskStatus.RETRY.value == "retry"
        assert TaskStatus.SCHEDULED.value == "scheduled"
        assert TaskStatus.WAITING_DEPENDENCIES.value == "waiting_dependencies"

    def test_workflow_status_values(self):
        assert WorkflowStatus.DRAFT.value == "draft"
        assert WorkflowStatus.ACTIVE.value == "active"
        assert WorkflowStatus.PAUSED.value == "paused"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"


class TestDataclasses:
    def test_task_dependency(self):
        dep = TaskDependency("t1", "t0", "completion")
        assert dep.task_id == "t1"
        assert dep.depends_on == "t0"
        assert dep.dependency_type == "completion"
        assert dep.condition is None

    def test_task_dependency_with_condition(self):
        dep = TaskDependency("t2", "t1", "success", "result.ok == true")
        assert dep.condition == "result.ok == true"

    def test_workflow_definition_defaults(self):
        wf = WorkflowDefinition(
            workflow_id="wf_test",
            name="Test",
            description="Desc",
            created_by="user"
        )
        assert wf.tasks == []
        assert wf.dependencies == []
        assert wf.status == WorkflowStatus.DRAFT

    def test_task_execution_defaults(self):
        te = TaskExecution(
            execution_id="ex1",
            task_id="t1",
            workflow_id="wf1",
            assigned_agents=[]
        )
        assert te.status == TaskStatus.PENDING
        assert te.retry_count == 0
        assert te.max_retries == 3
        assert te.timeout_minutes == 60

    def test_workflow_execution_defaults(self):
        we = WorkflowExecution(
            execution_id="ex1",
            workflow_id="wf1"
        )
        assert we.status == WorkflowStatus.DRAFT
        assert we.task_executions == {}
        assert we.current_step == 0


# ---------------------------------------------------------------------------
# TaskOrchestrationEngine.__init__
# ---------------------------------------------------------------------------

class TestEngineInit:
    def test_init_defaults(self):
        engine, coord = _make_engine()
        assert engine.coordinator is coord
        assert engine.workflows == {}
        assert engine.workflow_executions == {}
        assert engine.task_executions == {}
        assert engine.pending_tasks == []
        assert engine.running_tasks == []
        assert engine.completed_tasks == []

    def test_orchestration_settings(self):
        engine, _ = _make_engine()
        assert engine.orchestration_settings["max_concurrent_workflows"] == 10
        assert engine.orchestration_settings["auto_retry_on_failure"] is True


# ---------------------------------------------------------------------------
# create_workflow
# ---------------------------------------------------------------------------

class TestCreateWorkflow:
    @pytest.mark.asyncio
    async def test_create_simple_workflow(self):
        engine, _ = _make_engine()
        wf = _make_workflow()
        with patch.object(engine, "_store_workflow_definition", new=AsyncMock()):
            wf_id = await engine.create_workflow(wf)
        assert wf_id == "wf1"
        assert "wf1" in engine.workflows

    @pytest.mark.asyncio
    async def test_create_workflow_with_dependencies(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        dep = TaskDependency("t2", "t1", "completion")
        wf = _make_workflow(tasks=[t1, t2], deps=[dep])
        with patch.object(engine, "_store_workflow_definition", new=AsyncMock()):
            wf_id = await engine.create_workflow(wf)
        assert wf_id == "wf1"

    @pytest.mark.asyncio
    async def test_create_invalid_workflow_raises(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t1_dup = _make_task("t1")  # duplicate ID
        wf = _make_workflow(tasks=[t1, t1_dup])
        with pytest.raises(ValueError, match="Invalid workflow definition"):
            await engine.create_workflow(wf)

    @pytest.mark.asyncio
    async def test_create_workflow_invalid_dep_raises(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        dep = TaskDependency("t1", "t_nonexistent", "completion")
        wf = _make_workflow(tasks=[t1], deps=[dep])
        with pytest.raises(ValueError):
            await engine.create_workflow(wf)

    @pytest.mark.asyncio
    async def test_create_workflow_circular_dep_raises(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        deps = [
            TaskDependency("t1", "t2", "completion"),
            TaskDependency("t2", "t1", "completion"),
        ]
        wf = _make_workflow(tasks=[t1, t2], deps=deps)
        with pytest.raises(ValueError):
            await engine.create_workflow(wf)

    @pytest.mark.asyncio
    async def test_store_workflow_definition_called(self):
        engine, _ = _make_engine()
        wf = _make_workflow()
        with patch.object(engine, "_store_workflow_definition", new=AsyncMock()) as mock_store:
            await engine.create_workflow(wf)
            mock_store.assert_called_once_with(wf)


# ---------------------------------------------------------------------------
# _validate_workflow
# ---------------------------------------------------------------------------

class TestValidateWorkflow:
    @pytest.mark.asyncio
    async def test_valid_workflow(self):
        engine, _ = _make_engine()
        wf = _make_workflow()
        assert await engine._validate_workflow(wf) is True

    @pytest.mark.asyncio
    async def test_duplicate_task_ids_invalid(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t1b = _make_task("t1")
        wf = _make_workflow(tasks=[t1, t1b])
        assert await engine._validate_workflow(wf) is False

    @pytest.mark.asyncio
    async def test_invalid_dep_task_id(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        dep = TaskDependency("ghost", "t1", "completion")
        wf = _make_workflow(tasks=[t1], deps=[dep])
        assert await engine._validate_workflow(wf) is False

    @pytest.mark.asyncio
    async def test_invalid_dep_depends_on(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        dep = TaskDependency("t1", "ghost", "completion")
        wf = _make_workflow(tasks=[t1], deps=[dep])
        assert await engine._validate_workflow(wf) is False


# ---------------------------------------------------------------------------
# _has_circular_dependencies
# ---------------------------------------------------------------------------

class TestHasCircularDependencies:
    @pytest.mark.asyncio
    async def test_no_cycle(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        t3 = _make_task("t3")
        deps = [
            TaskDependency("t2", "t1", "completion"),
            TaskDependency("t3", "t2", "completion"),
        ]
        wf = _make_workflow(tasks=[t1, t2, t3], deps=deps)
        assert await engine._has_circular_dependencies(wf) is False

    @pytest.mark.asyncio
    async def test_cycle_detected(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        deps = [
            TaskDependency("t1", "t2", "completion"),
            TaskDependency("t2", "t1", "completion"),
        ]
        wf = _make_workflow(tasks=[t1, t2], deps=deps)
        assert await engine._has_circular_dependencies(wf) is True

    @pytest.mark.asyncio
    async def test_no_deps_no_cycle(self):
        engine, _ = _make_engine()
        wf = _make_workflow()
        assert await engine._has_circular_dependencies(wf) is False


# ---------------------------------------------------------------------------
# execute_workflow
# ---------------------------------------------------------------------------

class TestExecuteWorkflow:
    @pytest.mark.asyncio
    async def test_execute_unknown_workflow_raises(self):
        engine, _ = _make_engine()
        with pytest.raises(ValueError, match="not found"):
            await engine.execute_workflow("nonexistent")

    @pytest.mark.asyncio
    async def test_execute_creates_execution(self):
        engine, _ = _make_engine()
        # The production code references "max_retries_on_failure" which is not
        # in the default orchestration_settings dict -- add it for the test.
        engine.orchestration_settings["max_retries_on_failure"] = 3
        wf = _make_workflow()
        engine.workflows["wf1"] = wf
        with patch.object(engine, "_schedule_ready_tasks", new=AsyncMock()), \
             patch.object(engine, "_store_workflow_execution", new=AsyncMock()):
            exec_id = await engine.execute_workflow("wf1")
        assert exec_id in engine.workflow_executions
        ex = engine.workflow_executions[exec_id]
        assert ex.status == WorkflowStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_execute_workflow_with_context(self):
        engine, _ = _make_engine()
        engine.orchestration_settings["max_retries_on_failure"] = 3
        wf = _make_workflow()
        engine.workflows["wf1"] = wf
        ctx = {"env": "test"}
        with patch.object(engine, "_schedule_ready_tasks", new=AsyncMock()), \
             patch.object(engine, "_store_workflow_execution", new=AsyncMock()):
            exec_id = await engine.execute_workflow("wf1", execution_context=ctx)
        ex = engine.workflow_executions[exec_id]
        assert ex.global_context == ctx


# ---------------------------------------------------------------------------
# get_workflow_status
# ---------------------------------------------------------------------------

class TestGetWorkflowStatus:
    @pytest.mark.asyncio
    async def test_unknown_execution_returns_error(self):
        engine, _ = _make_engine()
        result = await engine.get_workflow_status("nonexistent_exec")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_status_with_progress(self):
        engine, _ = _make_engine()
        wf = _make_workflow(tasks=[_make_task("t1"), _make_task("t2")])
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution(
            execution_id="ex1",
            workflow_id="wf1",
            status=WorkflowStatus.ACTIVE,
            started_at=datetime.now(UTC) - timedelta(minutes=5),
            total_steps=2,
        )
        te1 = TaskExecution("te1", "t1", "wf1", [])
        te1.status = TaskStatus.COMPLETED
        te2 = TaskExecution("te2", "t2", "wf1", [])
        te2.status = TaskStatus.RUNNING
        ex.task_executions = {"t1": te1, "t2": te2}
        engine.workflow_executions["ex1"] = ex

        status = await engine.get_workflow_status("ex1")
        assert status["execution_id"] == "ex1"
        assert status["progress_percentage"] == 50.0
        assert status["task_statistics"]["completed"] == 1
        assert status["task_statistics"]["running"] == 1

    @pytest.mark.asyncio
    async def test_status_zero_progress_eta_unknown(self):
        engine, _ = _make_engine()
        wf = _make_workflow()
        engine.workflows["wf1"] = wf
        ex = WorkflowExecution(
            execution_id="ex2",
            workflow_id="wf1",
            status=WorkflowStatus.ACTIVE,
            started_at=None,
            total_steps=1,
        )
        te = TaskExecution("te1", "t1", "wf1", [])
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex2"] = ex

        status = await engine.get_workflow_status("ex2")
        assert status["estimated_completion"] == "Unknown"

    @pytest.mark.asyncio
    async def test_status_no_tasks(self):
        engine, _ = _make_engine()
        wf = _make_workflow(tasks=[])
        engine.workflows["wf1"] = wf
        ex = WorkflowExecution(
            execution_id="ex3",
            workflow_id="wf1",
            status=WorkflowStatus.ACTIVE,
            total_steps=0,
        )
        engine.workflow_executions["ex3"] = ex
        status = await engine.get_workflow_status("ex3")
        assert status["progress_percentage"] == 0

    @pytest.mark.asyncio
    async def test_status_missing_workflow_def(self):
        engine, _ = _make_engine()
        # execution exists but workflow def doesn't
        ex = WorkflowExecution("ex4", "wf_ghost", status=WorkflowStatus.ACTIVE)
        engine.workflow_executions["ex4"] = ex
        result = await engine.get_workflow_status("ex4")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_status_completed_at_included(self):
        engine, _ = _make_engine()
        wf = _make_workflow(tasks=[_make_task("t1")])
        engine.workflows["wf1"] = wf
        ex = WorkflowExecution(
            execution_id="ex5",
            workflow_id="wf1",
            status=WorkflowStatus.COMPLETED,
            started_at=datetime.now(UTC) - timedelta(minutes=10),
            completed_at=datetime.now(UTC),
            total_steps=1,
        )
        te = TaskExecution("te1", "t1", "wf1", [])
        te.status = TaskStatus.COMPLETED
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex5"] = ex
        status = await engine.get_workflow_status("ex5")
        assert status["completed_at"] is not None


# ---------------------------------------------------------------------------
# pause_workflow
# ---------------------------------------------------------------------------

class TestPauseWorkflow:
    @pytest.mark.asyncio
    async def test_pause_active_workflow(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        te = TaskExecution("te1", "t1", "wf1", [])
        te.status = TaskStatus.RUNNING
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex
        with patch.object(engine, "_store_workflow_execution", new=AsyncMock()):
            result = await engine.pause_workflow("ex1")
        assert result is True
        assert ex.status == WorkflowStatus.PAUSED

    @pytest.mark.asyncio
    async def test_pause_non_active_returns_false(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.PAUSED)
        engine.workflow_executions["ex1"] = ex
        result = await engine.pause_workflow("ex1")
        assert result is False

    @pytest.mark.asyncio
    async def test_pause_unknown_returns_false(self):
        engine, _ = _make_engine()
        result = await engine.pause_workflow("unknown")
        assert result is False

    @pytest.mark.asyncio
    async def test_pause_non_running_tasks_not_paused(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        te = TaskExecution("te1", "t1", "wf1", [])
        te.status = TaskStatus.PENDING  # Not running
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex
        with patch.object(engine, "_store_workflow_execution", new=AsyncMock()):
            result = await engine.pause_workflow("ex1")
        assert result is True
        assert te.status == TaskStatus.PENDING  # Unchanged


# ---------------------------------------------------------------------------
# resume_workflow
# ---------------------------------------------------------------------------

class TestResumeWorkflow:
    @pytest.mark.asyncio
    async def test_resume_paused_workflow(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.PAUSED)
        engine.workflow_executions["ex1"] = ex
        engine.workflows["wf1"] = _make_workflow()
        with patch.object(engine, "_schedule_ready_tasks", new=AsyncMock()) as mock_sched, \
             patch.object(engine, "_store_workflow_execution", new=AsyncMock()):
            result = await engine.resume_workflow("ex1")
        assert result is True
        assert ex.status == WorkflowStatus.ACTIVE
        mock_sched.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_non_paused_returns_false(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        engine.workflow_executions["ex1"] = ex
        result = await engine.resume_workflow("ex1")
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_unknown_returns_false(self):
        engine, _ = _make_engine()
        result = await engine.resume_workflow("ghost")
        assert result is False


# ---------------------------------------------------------------------------
# cancel_workflow
# ---------------------------------------------------------------------------

class TestCancelWorkflow:
    @pytest.mark.asyncio
    async def test_cancel_active_workflow(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        te = TaskExecution("te1", "t1", "wf1", [])
        te.status = TaskStatus.RUNNING
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex
        with patch.object(engine, "_store_workflow_execution", new=AsyncMock()):
            result = await engine.cancel_workflow("ex1")
        assert result is True
        assert ex.status == WorkflowStatus.CANCELLED
        assert te.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_scheduled_task(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        te = TaskExecution("te1", "t1", "wf1", [])
        te.status = TaskStatus.SCHEDULED
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex
        with patch.object(engine, "_store_workflow_execution", new=AsyncMock()):
            result = await engine.cancel_workflow("ex1")
        assert result is True
        assert te.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_already_completed_returns_false(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.COMPLETED)
        engine.workflow_executions["ex1"] = ex
        result = await engine.cancel_workflow("ex1")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_already_failed_returns_false(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.FAILED)
        engine.workflow_executions["ex1"] = ex
        result = await engine.cancel_workflow("ex1")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_returns_false(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.CANCELLED)
        engine.workflow_executions["ex1"] = ex
        result = await engine.cancel_workflow("ex1")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_unknown_returns_false(self):
        engine, _ = _make_engine()
        result = await engine.cancel_workflow("ghost")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_skips_pending_tasks(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        te = TaskExecution("te1", "t1", "wf1", [])
        te.status = TaskStatus.PENDING  # Not running/scheduled
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex
        with patch.object(engine, "_store_workflow_execution", new=AsyncMock()):
            result = await engine.cancel_workflow("ex1")
        assert result is True
        assert te.status == TaskStatus.PENDING  # Unchanged


# ---------------------------------------------------------------------------
# _are_dependencies_satisfied
# ---------------------------------------------------------------------------

class TestAreDependenciesSatisfied:
    @pytest.mark.asyncio
    async def test_no_deps_satisfied(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        wf = _make_workflow(tasks=[t1])
        engine.workflows["wf1"] = wf
        ex = WorkflowExecution("ex1", "wf1")
        result = await engine._are_dependencies_satisfied(t1, ex)
        assert result is True

    @pytest.mark.asyncio
    async def test_completion_dep_satisfied(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        dep = TaskDependency("t2", "t1", "completion")
        wf = _make_workflow(tasks=[t1, t2], deps=[dep])
        engine.workflows["wf1"] = wf
        te1 = TaskExecution("e1", "t1", "wf1", [])
        te1.status = TaskStatus.COMPLETED
        ex = WorkflowExecution("ex1", "wf1")
        ex.task_executions = {"t1": te1}
        result = await engine._are_dependencies_satisfied(t2, ex)
        assert result is True

    @pytest.mark.asyncio
    async def test_completion_dep_not_satisfied(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        dep = TaskDependency("t2", "t1", "completion")
        wf = _make_workflow(tasks=[t1, t2], deps=[dep])
        engine.workflows["wf1"] = wf
        te1 = TaskExecution("e1", "t1", "wf1", [])
        te1.status = TaskStatus.RUNNING
        ex = WorkflowExecution("ex1", "wf1")
        ex.task_executions = {"t1": te1}
        result = await engine._are_dependencies_satisfied(t2, ex)
        assert result is False

    @pytest.mark.asyncio
    async def test_success_dep_satisfied(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        dep = TaskDependency("t2", "t1", "success")
        wf = _make_workflow(tasks=[t1, t2], deps=[dep])
        engine.workflows["wf1"] = wf
        te1 = TaskExecution("e1", "t1", "wf1", [])
        te1.status = TaskStatus.COMPLETED
        te1.error_message = None
        ex = WorkflowExecution("ex1", "wf1")
        ex.task_executions = {"t1": te1}
        result = await engine._are_dependencies_satisfied(t2, ex)
        assert result is True

    @pytest.mark.asyncio
    async def test_success_dep_failed_not_satisfied(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        dep = TaskDependency("t2", "t1", "success")
        wf = _make_workflow(tasks=[t1, t2], deps=[dep])
        engine.workflows["wf1"] = wf
        te1 = TaskExecution("e1", "t1", "wf1", [])
        te1.status = TaskStatus.COMPLETED
        te1.error_message = "had error"
        ex = WorkflowExecution("ex1", "wf1")
        ex.task_executions = {"t1": te1}
        result = await engine._are_dependencies_satisfied(t2, ex)
        assert result is False

    @pytest.mark.asyncio
    async def test_data_dep_satisfied(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        dep = TaskDependency("t2", "t1", "data")
        wf = _make_workflow(tasks=[t1, t2], deps=[dep])
        engine.workflows["wf1"] = wf
        te1 = TaskExecution("e1", "t1", "wf1", [])
        te1.result_data = {"output": 42}
        ex = WorkflowExecution("ex1", "wf1")
        ex.task_executions = {"t1": te1}
        result = await engine._are_dependencies_satisfied(t2, ex)
        assert result is True

    @pytest.mark.asyncio
    async def test_data_dep_no_data(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        dep = TaskDependency("t2", "t1", "data")
        wf = _make_workflow(tasks=[t1, t2], deps=[dep])
        engine.workflows["wf1"] = wf
        te1 = TaskExecution("e1", "t1", "wf1", [])
        te1.result_data = None
        ex = WorkflowExecution("ex1", "wf1")
        ex.task_executions = {"t1": te1}
        result = await engine._are_dependencies_satisfied(t2, ex)
        assert result is False

    @pytest.mark.asyncio
    async def test_dep_exec_not_found(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        dep = TaskDependency("t2", "t1", "completion")
        wf = _make_workflow(tasks=[t1, t2], deps=[dep])
        engine.workflows["wf1"] = wf
        ex = WorkflowExecution("ex1", "wf1")
        ex.task_executions = {}  # t1 execution missing
        result = await engine._are_dependencies_satisfied(t2, ex)
        assert result is False

    @pytest.mark.asyncio
    async def test_workflow_not_found(self):
        engine, _ = _make_engine()
        t1 = _make_task("t1")
        ex = WorkflowExecution("ex1", "wf_ghost")
        result = await engine._are_dependencies_satisfied(t1, ex)
        assert result is False


# ---------------------------------------------------------------------------
# _schedule_ready_tasks
# ---------------------------------------------------------------------------

class TestScheduleReadyTasks:
    @pytest.mark.asyncio
    async def test_schedule_ready_tasks_no_execution(self):
        engine, _ = _make_engine()
        # Should not raise
        await engine._schedule_ready_tasks("ghost_exec")

    @pytest.mark.asyncio
    async def test_schedule_ready_tasks_assigns(self):
        engine, coord = _make_engine()
        t1 = _make_task("t1")
        t1.assigned_to = ["agent1"]
        wf = _make_workflow(tasks=[t1])
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        te = TaskExecution("te1", "t1", "ex1", [])
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex

        with patch.object(engine, "_execute_task", new=AsyncMock()) as mock_exec:
            await engine._schedule_ready_tasks("ex1")
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_respects_concurrency_limit(self):
        engine, coord = _make_engine()
        tasks = [_make_task(f"t{i}") for i in range(10)]
        wf = _make_workflow(tasks=tasks)
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        for t in tasks:
            te = TaskExecution(str(uuid.uuid4()), t.task_id, "ex1", [])
            ex.task_executions[t.task_id] = te
        engine.workflow_executions["ex1"] = ex

        with patch.object(engine, "_execute_task", new=AsyncMock()) as mock_exec:
            await engine._schedule_ready_tasks("ex1")
            max_concurrent = engine.orchestration_settings["max_concurrent_tasks_per_workflow"]
            assert mock_exec.call_count <= max_concurrent

    @pytest.mark.asyncio
    async def test_schedule_skips_non_pending_tasks(self):
        engine, coord = _make_engine()
        t1 = _make_task("t1")
        wf = _make_workflow(tasks=[t1])
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1")
        te = TaskExecution("te1", "t1", "ex1", [])
        te.status = TaskStatus.RUNNING  # Already running
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex

        with patch.object(engine, "_execute_task", new=AsyncMock()) as mock_exec:
            await engine._schedule_ready_tasks("ex1")
            mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_coordinator_assign_fails(self):
        engine, coord = _make_engine()
        coord.assign_task = AsyncMock(return_value=False)
        t1 = _make_task("t1")
        wf = _make_workflow(tasks=[t1])
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1")
        te = TaskExecution("te1", "t1", "ex1", [])
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex

        with patch.object(engine, "_execute_task", new=AsyncMock()) as mock_exec:
            await engine._schedule_ready_tasks("ex1")
            mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_no_workflow_in_execution(self):
        engine, coord = _make_engine()
        # execution exists but no matching workflow
        ex = WorkflowExecution("ex1", "wf_ghost")
        engine.workflow_executions["ex1"] = ex
        await engine._schedule_ready_tasks("ex1")  # Should not raise

    @pytest.mark.asyncio
    async def test_schedule_exception_silenced(self):
        engine, coord = _make_engine()
        t1 = _make_task("t1")
        wf = _make_workflow(tasks=[t1])
        engine.workflows["wf1"] = wf
        ex = WorkflowExecution("ex1", "wf1")
        te = TaskExecution("te1", "t1", "ex1", [])
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex

        coord.assign_task = AsyncMock(side_effect=RuntimeError("assign failed"))
        await engine._schedule_ready_tasks("ex1")  # Should not raise


# ---------------------------------------------------------------------------
# _execute_task
# ---------------------------------------------------------------------------

class TestExecuteTask:
    @pytest.mark.asyncio
    async def test_execute_task_sets_running(self):
        engine, coord = _make_engine()
        t1 = _make_task("t1")
        t1.assigned_to = ["agent1"]
        te = TaskExecution("te1", "t1", "ex1", [])

        with patch("asyncio.create_task"):
            await engine._execute_task(t1, te)
        assert te.status == TaskStatus.RUNNING
        coord.route_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_no_assigned_agent(self):
        engine, coord = _make_engine()
        t1 = _make_task("t1")
        t1.assigned_to = []  # No agents
        te = TaskExecution("te1", "t1", "ex1", [])

        with patch("asyncio.create_task"):
            await engine._execute_task(t1, te)
        assert te.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_execute_task_exception_calls_failure(self):
        engine, coord = _make_engine()
        coord.route_message = AsyncMock(side_effect=RuntimeError("route fail"))
        t1 = _make_task("t1")
        t1.assigned_to = ["a1"]
        te = TaskExecution("te1", "t1", "ex1", [])

        with patch.object(engine, "_handle_task_failure", new=AsyncMock()) as mock_fail:
            await engine._execute_task(t1, te)
            mock_fail.assert_called_once()


# ---------------------------------------------------------------------------
# _handle_task_failure
# ---------------------------------------------------------------------------

class TestHandleTaskFailure:
    @pytest.mark.asyncio
    async def test_handle_failure_sets_status(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex

        wf = _make_workflow(tasks=[_make_task("t1")])
        engine.workflows["wf1"] = wf

        with patch.object(engine, "_should_fail_workflow", new=AsyncMock(return_value=False)):
            await engine._handle_task_failure(te, "Something went wrong")
        assert te.status == TaskStatus.FAILED
        assert te.error_message == "Something went wrong"

    @pytest.mark.asyncio
    async def test_handle_failure_fails_workflow_when_critical(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.task_id = "t1"
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex

        t1 = _make_task("t1", priority=TaskPriority.CRITICAL)
        wf = _make_workflow(tasks=[t1])
        engine.workflows["wf1"] = wf

        with patch.object(engine, "_should_fail_workflow", new=AsyncMock(return_value=True)):
            await engine._handle_task_failure(te, "critical fail")
        assert ex.status == WorkflowStatus.FAILED

    @pytest.mark.asyncio
    async def test_handle_failure_no_execution(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ghost_exec", [])
        # Should not raise
        await engine._handle_task_failure(te, "error")
        assert te.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_handle_failure_increments_step(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        ex = WorkflowExecution("ex1", "wf1", status=WorkflowStatus.ACTIVE)
        ex.current_step = 0
        ex.task_executions = {"t1": te}
        engine.workflow_executions["ex1"] = ex
        engine.workflows["wf1"] = _make_workflow()
        with patch.object(engine, "_should_fail_workflow", new=AsyncMock(return_value=False)):
            await engine._handle_task_failure(te, "err")
        assert ex.current_step == 1


# ---------------------------------------------------------------------------
# _should_fail_workflow
# ---------------------------------------------------------------------------

class TestShouldFailWorkflow:
    @pytest.mark.asyncio
    async def test_no_workflow_returns_true(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "ghost_wf")
        assert await engine._should_fail_workflow(ex) is True

    @pytest.mark.asyncio
    async def test_critical_task_fails_workflow(self):
        engine, _ = _make_engine()
        t_critical = _make_task("t_crit", priority=TaskPriority.CRITICAL)
        wf = _make_workflow(tasks=[t_critical])
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1")
        te = TaskExecution("te1", "t_crit", "ex1", [])
        te.status = TaskStatus.FAILED
        te.task_id = "t_crit"
        ex.task_executions = {"t_crit": te}

        assert await engine._should_fail_workflow(ex) is True

    @pytest.mark.asyncio
    async def test_majority_failed_fails_workflow(self):
        engine, _ = _make_engine()
        tasks = [_make_task(f"t{i}", priority=TaskPriority.NORMAL) for i in range(4)]
        wf = _make_workflow(tasks=tasks)
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1")
        for i, t in enumerate(tasks):
            te = TaskExecution(f"te{i}", t.task_id, "ex1", [])
            te.status = TaskStatus.FAILED if i < 3 else TaskStatus.COMPLETED
            te.task_id = t.task_id
            ex.task_executions[t.task_id] = te

        assert await engine._should_fail_workflow(ex) is True

    @pytest.mark.asyncio
    async def test_no_critical_few_failures(self):
        engine, _ = _make_engine()
        tasks = [_make_task(f"t{i}", priority=TaskPriority.NORMAL) for i in range(4)]
        wf = _make_workflow(tasks=tasks)
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1")
        for i, t in enumerate(tasks):
            te = TaskExecution(f"te{i}", t.task_id, "ex1", [])
            te.status = TaskStatus.FAILED if i == 0 else TaskStatus.COMPLETED
            te.task_id = t.task_id
            ex.task_executions[t.task_id] = te

        assert await engine._should_fail_workflow(ex) is False

    @pytest.mark.asyncio
    async def test_no_failures_returns_false(self):
        engine, _ = _make_engine()
        tasks = [_make_task("t1")]
        wf = _make_workflow(tasks=tasks)
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1")
        te = TaskExecution("te1", "t1", "ex1", [])
        te.status = TaskStatus.COMPLETED
        te.task_id = "t1"
        ex.task_executions = {"t1": te}

        assert await engine._should_fail_workflow(ex) is False

    @pytest.mark.asyncio
    async def test_critical_task_not_in_tasks_list(self):
        """Task id in execution not matching any workflow task -> not critical."""
        engine, _ = _make_engine()
        t1 = _make_task("t1", priority=TaskPriority.NORMAL)
        wf = _make_workflow(tasks=[t1])
        engine.workflows["wf1"] = wf

        ex = WorkflowExecution("ex1", "wf1")
        te = TaskExecution("te1", "ghost_task", "ex1", [])
        te.status = TaskStatus.FAILED
        te.task_id = "ghost_task"
        ex.task_executions = {"ghost_task": te}

        # Only 1/1 tasks failed, which is > 50%, so it should fail
        assert await engine._should_fail_workflow(ex) is True


# ---------------------------------------------------------------------------
# _handle_task_timeout
# ---------------------------------------------------------------------------

class TestHandleTaskTimeout:
    @pytest.mark.asyncio
    async def test_timeout_retries_if_retries_remain(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.retry_count = 0
        te.max_retries = 3
        with patch.object(engine, "_retry_task", new=AsyncMock()) as mock_retry:
            await engine._handle_task_timeout(te)
        assert te.status == TaskStatus.TIMEOUT
        mock_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_fails_when_max_retries_exhausted(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.retry_count = 3
        te.max_retries = 3
        with patch.object(engine, "_handle_task_failure", new=AsyncMock()) as mock_fail:
            await engine._handle_task_timeout(te)
        mock_fail.assert_called_once_with(te, "Maximum retries exceeded")


# ---------------------------------------------------------------------------
# _retry_task
# ---------------------------------------------------------------------------

class TestRetryTask:
    @pytest.mark.asyncio
    async def test_retry_increments_count(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.retry_count = 0
        te.max_retries = 3
        te.error_message = "prev error"

        with patch("asyncio.sleep", new=AsyncMock()), \
             patch.object(engine, "_schedule_ready_tasks", new=AsyncMock()):
            await engine._retry_task(te)
        assert te.retry_count == 1
        assert te.status == TaskStatus.PENDING
        assert te.error_message is None

    @pytest.mark.asyncio
    async def test_retry_exception_calls_failure(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.retry_count = 1

        with patch("asyncio.sleep", new=AsyncMock(side_effect=RuntimeError("sleep fail"))), \
             patch.object(engine, "_handle_task_failure", new=AsyncMock()) as mock_fail:
            await engine._retry_task(te)
        mock_fail.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_clears_started_at(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.retry_count = 0
        te.started_at = datetime.now(UTC)

        with patch("asyncio.sleep", new=AsyncMock()), \
             patch.object(engine, "_schedule_ready_tasks", new=AsyncMock()):
            await engine._retry_task(te)
        assert te.started_at is None


# ---------------------------------------------------------------------------
# _pause_task_execution
# ---------------------------------------------------------------------------

class TestPauseTaskExecution:
    @pytest.mark.asyncio
    async def test_pause_sets_scheduled(self):
        engine, coord = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.status = TaskStatus.RUNNING
        with patch.object(engine, "_send_task_control_message", new=AsyncMock()):
            await engine._pause_task_execution(te)
        assert te.status == TaskStatus.SCHEDULED


# ---------------------------------------------------------------------------
# _cancel_task_execution
# ---------------------------------------------------------------------------

class TestCancelTaskExecution:
    @pytest.mark.asyncio
    async def test_cancel_sets_cancelled(self):
        engine, coord = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        with patch.object(engine, "_send_task_control_message", new=AsyncMock()):
            await engine._cancel_task_execution(te)
        assert te.status == TaskStatus.CANCELLED
        assert te.completed_at is not None


# ---------------------------------------------------------------------------
# _send_task_control_message
# ---------------------------------------------------------------------------

class TestSendTaskControlMessage:
    @pytest.mark.asyncio
    async def test_send_pause_message(self):
        engine, coord = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        await engine._send_task_control_message(te, "pause")
        coord.route_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_cancel_message(self):
        engine, coord = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        await engine._send_task_control_message(te, "cancel")
        coord.route_message.assert_called_once()


# ---------------------------------------------------------------------------
# _store_workflow_definition and _store_workflow_execution
# ---------------------------------------------------------------------------

class TestStoreWorkflow:
    """Tests for _store_workflow_definition and _store_workflow_execution.

    Both methods use deferred imports (`from ..agents.smc_memory_wrapper import
    SMCMemoryWrapper`) so we patch sys.modules contextually for each test.
    """

    def _smc_sys_patch(self):
        """Return a patch.dict context that injects the SMC stub."""
        return patch.dict(sys.modules, {
            "src.agents.smc_memory_wrapper": _smc_mod,
            "src.agents": _agents_mod,
        })

    @pytest.mark.asyncio
    async def test_store_workflow_definition(self):
        engine, _ = _make_engine()
        wf = _make_workflow()
        with self._smc_sys_patch():
            await engine._store_workflow_definition(wf)

    @pytest.mark.asyncio
    async def test_store_workflow_execution(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1")
        ex.started_at = datetime.now(UTC)
        with self._smc_sys_patch():
            await engine._store_workflow_execution(ex)

    @pytest.mark.asyncio
    async def test_store_workflow_execution_no_started_at(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1")
        ex.started_at = None
        ex.completed_at = None
        with self._smc_sys_patch():
            await engine._store_workflow_execution(ex)

    @pytest.mark.asyncio
    async def test_store_workflow_execution_with_completed_at(self):
        engine, _ = _make_engine()
        ex = WorkflowExecution("ex1", "wf1")
        ex.started_at = datetime.now(UTC)
        ex.completed_at = datetime.now(UTC)
        with self._smc_sys_patch():
            await engine._store_workflow_execution(ex)


# ---------------------------------------------------------------------------
# _monitor_task_timeout
# ---------------------------------------------------------------------------

class TestMonitorTaskTimeout:
    @pytest.mark.asyncio
    async def test_monitor_task_completes_before_timeout(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.timeout_minutes = 0  # 0 seconds timeout
        te.status = TaskStatus.COMPLETED  # Already done
        with patch.object(engine, "_handle_task_timeout", new=AsyncMock()) as mock_timeout:
            await engine._monitor_task_timeout(te)
        mock_timeout.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_task_timeout_exception_silenced(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.timeout_minutes = 0

        with patch("asyncio.sleep", new=AsyncMock(side_effect=RuntimeError("sleep fail"))):
            await engine._monitor_task_timeout(te)  # Should not raise

    @pytest.mark.asyncio
    async def test_monitor_task_times_out(self):
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.timeout_minutes = 0  # 0 seconds = loop runs 0 times

        # Status remains RUNNING but loop never ran so timeout fires
        te.status = TaskStatus.RUNNING

        with patch.object(engine, "_handle_task_timeout", new=AsyncMock()) as mock_timeout:
            await engine._monitor_task_timeout(te)
        mock_timeout.assert_called_once_with(te)

    @pytest.mark.asyncio
    async def test_monitor_task_returns_early_in_loop(self):
        """Cover lines 497-499: loop body where task is no longer running."""
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.timeout_minutes = 1  # 60 seconds = loop would run 60 times
        te.status = TaskStatus.RUNNING

        call_count = 0

        async def _fake_sleep(n):
            nonlocal call_count
            call_count += 1
            # After first sleep, mark task completed so loop exits
            te.status = TaskStatus.COMPLETED

        with patch("asyncio.sleep", side_effect=_fake_sleep), \
             patch.object(engine, "_handle_task_timeout", new=AsyncMock()) as mock_timeout:
            await engine._monitor_task_timeout(te)
        # Loop ran once, then exited early - timeout never called
        mock_timeout.assert_not_called()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_monitor_task_exception_in_loop(self):
        """Cover lines 505-506: exception while sleeping in the monitor loop."""
        engine, _ = _make_engine()
        te = TaskExecution("te1", "t1", "ex1", [])
        te.timeout_minutes = 1  # non-zero so the loop is entered
        te.status = TaskStatus.RUNNING

        async def _raise_on_sleep(n):
            raise RuntimeError("sleep interrupted")

        with patch("asyncio.sleep", side_effect=_raise_on_sleep):
            # Should not propagate - caught by the outer except
            await engine._monitor_task_timeout(te)
