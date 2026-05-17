"""
Unit tests for src/maintenance_scheduler.py

Covers MaintenanceScheduler with mocked APScheduler.
ASCII-only assertions.
"""

import asyncio
import json
import pytest
import sys
import types
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Stub APScheduler
# ---------------------------------------------------------------------------

def _install_aps_stubs():
    """Install fake APScheduler stubs into sys.modules.

    Uses direct assignment (not setdefault) so that even when the real
    apscheduler package is already registered in sys.modules (e.g. because
    an integration test file imported it earlier in the session), the stubs
    take precedence.  This prevents the real AsyncIOScheduler.start() from
    being called in sync tests, which would fail with "no running event loop".
    """
    aps_pkg = types.ModuleType("apscheduler")
    aps_pkg.__path__ = []
    sys.modules["apscheduler"] = aps_pkg

    class FakeCronTrigger:
        def __init__(self, **kwargs):
            self._kw = kwargs
        def __str__(self):
            return f"cron({self._kw})"

    triggers_mod = types.ModuleType("apscheduler.triggers")
    triggers_mod.__path__ = []
    cron_mod = types.ModuleType("apscheduler.triggers.cron")
    cron_mod.CronTrigger = FakeCronTrigger
    sys.modules["apscheduler.triggers"] = triggers_mod
    sys.modules["apscheduler.triggers.cron"] = cron_mod

    EVENT_JOB_EXECUTED = 1
    EVENT_JOB_ERROR = 2

    events_mod = types.ModuleType("apscheduler.events")
    events_mod.EVENT_JOB_EXECUTED = EVENT_JOB_EXECUTED
    events_mod.EVENT_JOB_ERROR = EVENT_JOB_ERROR
    sys.modules["apscheduler.events"] = events_mod

    class FakeJob:
        def __init__(self, job_id, name, trigger=None):
            self.id = job_id
            self.name = name
            self.next_run_time = None
            self.trigger = trigger or FakeCronTrigger()

        def modify(self, **kwargs):
            pass

    class FakeScheduler:
        def __init__(self):
            self.running = False
            self._listeners = []
            self._jobs = {}

        def add_job(self, func, trigger, id, name, replace_existing=True, kwargs=None):
            job = FakeJob(id, name, trigger)
            self._jobs[id] = job
            return job

        def add_listener(self, callback, mask):
            self._listeners.append((callback, mask))

        def start(self):
            self.running = True

        def shutdown(self, wait=True):
            self.running = False

        def remove_job(self, job):
            # job is the FakeJob object
            self._jobs.pop(job.id, None)

    schedulers_mod = types.ModuleType("apscheduler.schedulers")
    schedulers_mod.__path__ = []
    asyncio_mod = types.ModuleType("apscheduler.schedulers.asyncio")
    asyncio_mod.AsyncIOScheduler = FakeScheduler
    sys.modules["apscheduler.schedulers"] = schedulers_mod
    sys.modules["apscheduler.schedulers.asyncio"] = asyncio_mod

    return FakeScheduler, FakeCronTrigger


FakeScheduler, FakeCronTrigger = _install_aps_stubs()

# Force fresh import
if "src.maintenance_scheduler" in sys.modules:
    del sys.modules["src.maintenance_scheduler"]

from src.maintenance_scheduler import MaintenanceScheduler  # noqa: E402


# ---------------------------------------------------------------------------
# Mock MCP client
# ---------------------------------------------------------------------------

class _MockMCP:
    async def call_tool(self, tool_name, params):
        return json.dumps({"status": "success", "result": "mock"})


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_ms(mcp=None, config_path="nonexistent.json"):
    if mcp is None:
        mcp = _MockMCP()
    return MaintenanceScheduler(mcp_client=mcp, config_path=config_path)


# ---------------------------------------------------------------------------
# Tests: init and _load_config
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_config_when_file_missing(self):
        ms = _make_ms()
        assert "tasks" in ms.config
        assert "cleanup_expired_memories" in ms.config["tasks"]

    def test_loads_config_from_file(self, tmp_path):
        cfg = {"tasks": {"my_task": {"enabled": True, "schedule": "0 1 * * *"}}}
        cfg_file = tmp_path / "maint.json"
        cfg_file.write_text(json.dumps(cfg))
        ms = _make_ms(config_path=str(cfg_file))
        assert "my_task" in ms.config["tasks"]

    def test_fallback_on_bad_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{broken")
        ms = _make_ms(config_path=str(bad))
        assert "tasks" in ms.config

    def test_scheduler_created(self):
        ms = _make_ms()
        assert ms.scheduler is not None

    def test_event_listeners_added(self):
        ms = _make_ms()
        # Listeners are added in _add_event_listeners
        assert len(ms.scheduler._listeners) == 2


# ---------------------------------------------------------------------------
# Tests: start / stop
# ---------------------------------------------------------------------------

class TestStartStop:
    def test_start_schedules_tasks_and_runs(self):
        ms = _make_ms()
        ms.start()
        assert ms.scheduler.running is True

    def test_start_already_running(self):
        ms = _make_ms()
        ms.start()
        ms.start()  # Should warn but not raise
        assert ms.scheduler.running is True

    def test_stop_scheduler(self):
        ms = _make_ms()
        ms.start()
        ms.stop()
        assert ms.scheduler.running is False

    def test_stop_without_scheduler(self):
        ms = _make_ms()
        ms.scheduler = None
        ms.stop()  # Should not raise

    def test_start_without_apscheduler(self):
        import src.maintenance_scheduler as _ms_mod
        from unittest.mock import patch
        ms = _make_ms()
        ms.scheduler = None
        with patch.object(_ms_mod, "APSCHEDULER_AVAILABLE", False):
            ms.start()  # Should log warning but not raise


# ---------------------------------------------------------------------------
# Tests: _schedule_tasks
# ---------------------------------------------------------------------------

class TestScheduleTasks:
    def test_schedules_enabled_tasks(self):
        ms = _make_ms()
        ms.start()
        # Default config has 5 tasks all enabled
        assert len(ms.jobs) >= 1

    def test_skips_disabled_tasks(self):
        ms = _make_ms()
        # Disable all tasks
        for task in ms.config["tasks"].values():
            task["enabled"] = False
        ms._schedule_tasks()
        assert len(ms.jobs) == 0

    def test_invalid_cron_expression_skipped(self):
        ms = _make_ms()
        ms.config["tasks"]["bad_task"] = {
            "enabled": True,
            "schedule": "invalid"  # not 5 parts
        }
        ms._schedule_tasks()
        assert "bad_task" not in ms.jobs


# ---------------------------------------------------------------------------
# Tests: _schedule_task
# ---------------------------------------------------------------------------

class TestScheduleTask:
    def test_adds_job_to_jobs_dict(self):
        ms = _make_ms()
        ms._schedule_task("cleanup_expired_memories", {
            "enabled": True, "schedule": "0 2 * * *", "age_days": 90
        })
        assert "cleanup_expired_memories" in ms.jobs


# ---------------------------------------------------------------------------
# Tests: _execute_task
# ---------------------------------------------------------------------------

class TestExecuteTask:
    @pytest.mark.asyncio
    async def test_execute_cleanup(self):
        mcp = _MockMCP()
        mcp.call_tool = AsyncMock(return_value=json.dumps({"status": "success"}))
        ms = _make_ms(mcp=mcp)
        await ms._execute_task("cleanup_expired_memories", {"age_days": 90})
        assert len(ms.task_history) == 1
        assert ms.task_history[0]["task_name"] == "cleanup_expired_memories"

    @pytest.mark.asyncio
    async def test_execute_archive(self):
        mcp = _MockMCP()
        mcp.call_tool = AsyncMock(return_value=json.dumps({"status": "success"}))
        ms = _make_ms(mcp=mcp)
        await ms._execute_task("archive_old_sessions", {"age_days": 365})
        assert ms.task_history[0]["task_name"] == "archive_old_sessions"

    @pytest.mark.asyncio
    async def test_execute_optimize(self):
        ms = _make_ms()
        await ms._execute_task("optimize_indexes", {})
        assert ms.task_history[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_clear_cache(self):
        mcp = _MockMCP()
        mcp.call_tool = AsyncMock(return_value=json.dumps({"status": "success"}))
        ms = _make_ms(mcp=mcp)
        await ms._execute_task("clear_cache", {})
        assert len(ms.task_history) == 1

    @pytest.mark.asyncio
    async def test_execute_backup_verification(self):
        mcp = _MockMCP()
        mcp.call_tool = AsyncMock(return_value=json.dumps({"status": "success"}))
        ms = _make_ms(mcp=mcp)
        await ms._execute_task("backup_verification", {})
        assert len(ms.task_history) == 1

    @pytest.mark.asyncio
    async def test_execute_unknown_task(self):
        ms = _make_ms()
        await ms._execute_task("unknown_task_xyz", {})
        assert ms.task_history[0]["result"]["status"] == "unknown_task"

    @pytest.mark.asyncio
    async def test_execute_exception_recorded(self):
        mcp = _MockMCP()
        mcp.call_tool = AsyncMock(side_effect=RuntimeError("crash"))
        ms = _make_ms(mcp=mcp)
        await ms._execute_task("cleanup_expired_memories", {"age_days": 90})
        assert ms.task_history[0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_task_history_capped_at_100(self):
        ms = _make_ms()
        # Pre-fill with 100 entries
        ms.task_history = [{"task_name": f"t{i}", "status": "completed"}
                           for i in range(100)]
        await ms._execute_task("optimize_indexes", {})
        assert len(ms.task_history) <= 100


# ---------------------------------------------------------------------------
# Tests: task sub-methods with no mcp client
# ---------------------------------------------------------------------------

class TestTasksNoMCP:
    @pytest.mark.asyncio
    async def test_cleanup_no_mcp(self):
        ms = _make_ms()
        ms.mcp_client = None
        result = await ms._cleanup_expired_memories({"age_days": 30})
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_archive_no_mcp(self):
        ms = _make_ms()
        ms.mcp_client = None
        result = await ms._archive_old_sessions({"age_days": 365})
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_optimize_indexes(self):
        ms = _make_ms()
        result = await ms._optimize_indexes({})
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_clear_cache_no_mcp(self):
        ms = _make_ms()
        ms.mcp_client = None
        result = await ms._clear_cache({})
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_verify_backups_no_mcp(self):
        ms = _make_ms()
        ms.mcp_client = None
        result = await ms._verify_backups({})
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_cleanup_exception(self):
        mcp = _MockMCP()
        mcp.call_tool = AsyncMock(side_effect=RuntimeError("db error"))
        ms = _make_ms(mcp=mcp)
        result = await ms._cleanup_expired_memories({"age_days": 30})
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Tests: schedule_* convenience methods
# ---------------------------------------------------------------------------

class TestScheduleConvenienceMethods:
    def test_schedule_cleanup(self):
        ms = _make_ms()
        ms.schedule_cleanup(days=60, schedule="0 3 * * *")
        assert ms.config["tasks"]["cleanup_expired_memories"]["age_days"] == 60

    def test_schedule_archival(self):
        ms = _make_ms()
        ms.schedule_archival(days=180)
        assert ms.config["tasks"]["archive_old_sessions"]["age_days"] == 180

    def test_schedule_optimization(self):
        ms = _make_ms()
        ms.schedule_optimization(schedule="0 5 * * *")
        assert ms.config["tasks"]["optimize_indexes"]["enabled"] is True

    def test_schedule_cache_clearing(self):
        ms = _make_ms()
        ms.schedule_cache_clearing()
        assert ms.config["tasks"]["clear_cache"]["enabled"] is True

    def test_schedule_backup_verification(self):
        ms = _make_ms()
        ms.schedule_backup_verification()
        assert ms.config["tasks"]["backup_verification"]["enabled"] is True


# ---------------------------------------------------------------------------
# Tests: get_scheduled_tasks / cancel_task / get_task_history / get_statistics
# ---------------------------------------------------------------------------

class TestManagement:
    def test_get_scheduled_tasks_after_start(self):
        ms = _make_ms()
        ms.start()
        tasks = ms.get_scheduled_tasks()
        assert isinstance(tasks, dict)

    def test_get_scheduled_tasks_no_scheduler(self):
        ms = _make_ms()
        ms.scheduler = None
        tasks = ms.get_scheduled_tasks()
        assert tasks == {}

    def test_cancel_task_success(self):
        ms = _make_ms()
        ms.start()
        # Add a job manually
        ms._schedule_task("cleanup_expired_memories", {
            "enabled": True, "schedule": "0 2 * * *", "age_days": 90
        })
        result = ms.cancel_task("cleanup_expired_memories")
        assert result is True
        assert "cleanup_expired_memories" not in ms.jobs

    def test_cancel_nonexistent_task(self):
        ms = _make_ms()
        ms.start()
        result = ms.cancel_task("nonexistent")
        assert result is False

    def test_cancel_task_no_scheduler(self):
        ms = _make_ms()
        ms.scheduler = None
        result = ms.cancel_task("anything")
        assert result is False

    def test_get_task_history(self):
        ms = _make_ms()
        ms.task_history = [{"task_name": "t1"}, {"task_name": "t2"}]
        history = ms.get_task_history(limit=1)
        assert len(history) == 1

    def test_get_statistics(self):
        ms = _make_ms()
        stats = ms.get_statistics()
        assert "total_executions" in stats
        assert "tasks_scheduled" in stats

    def test_statistics_avg_times_calculated(self):
        ms = _make_ms()
        ms.execution_stats["execution_times"]["cleanup"] = [1.0, 2.0, 3.0]
        stats = ms.get_statistics()
        assert "average_execution_times" in stats
        assert stats["average_execution_times"]["cleanup"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Tests: save_config
# ---------------------------------------------------------------------------

class TestSaveConfig:
    def test_save_config_to_file(self, tmp_path):
        cfg_file = tmp_path / "maint_save.json"
        ms = MaintenanceScheduler(mcp_client=None, config_path=str(cfg_file))
        ms.save_config()
        assert cfg_file.exists()
        saved = json.loads(cfg_file.read_text())
        assert "tasks" in saved

    def test_save_config_exception_does_not_raise(self, tmp_path):
        ms = _make_ms()
        ms.config_path = Path("/no/permission/file.json")
        ms.save_config()  # Should log error but not raise


# ---------------------------------------------------------------------------
# Tests: event listener callbacks
# ---------------------------------------------------------------------------

class TestEventListeners:
    def test_on_job_executed_increments_stats(self):
        ms = _make_ms()
        # Get the listeners
        listeners = ms.scheduler._listeners
        # First listener is on_job_executed
        executed_cb, _ = listeners[0]

        class FakeEvent:
            job_id = "cleanup_expired_memories"

        executed_cb(FakeEvent())
        assert ms.execution_stats["successful_executions"] == 1
        assert ms.execution_stats["total_executions"] == 1

    def test_on_job_error_increments_failed(self):
        ms = _make_ms()
        listeners = ms.scheduler._listeners
        # Second listener is on_job_error
        error_cb, _ = listeners[1]

        class FakeErrEvent:
            job_id = "bad_task"
            exception = RuntimeError("boom")

        error_cb(FakeErrEvent())
        assert ms.execution_stats["failed_executions"] == 1
        assert ms.execution_stats["total_executions"] == 1
