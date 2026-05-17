"""
Unit tests for src/scheduler.py

Covers TaskScheduler and DryRunManager.
APScheduler is mocked so tests run without it installed.
ASCII-only assertions.
"""

import asyncio
import json
import pytest
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Stub APScheduler so tests work whether or not it's installed
# ---------------------------------------------------------------------------

def _install_apscheduler_stubs():
    """Install minimal APScheduler stubs into sys.modules.

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
            self._kwargs = kwargs

        def __str__(self):
            return f"cron({self._kwargs})"

    triggers_mod = types.ModuleType("apscheduler.triggers")
    triggers_mod.__path__ = []
    cron_mod = types.ModuleType("apscheduler.triggers.cron")
    cron_mod.CronTrigger = FakeCronTrigger
    sys.modules["apscheduler.triggers"] = triggers_mod
    sys.modules["apscheduler.triggers.cron"] = cron_mod

    class FakeJob:
        def __init__(self, job_id, name):
            self.id = job_id
            self.name = name
            self.next_run_time = None
            self.trigger = FakeCronTrigger()

        def modify(self, **kwargs):
            pass

    class FakeScheduler:
        def __init__(self):
            self._jobs = []
            self.running = False

        def add_job(self, func, trigger, id, name, replace_existing=True, kwargs=None):
            job = FakeJob(id, name)
            self._jobs.append(job)
            return job

        def start(self):
            self.running = True

        def shutdown(self, wait=True):
            self.running = False

        def remove_job(self, job):
            if job in self._jobs:
                self._jobs.remove(job)

        def add_listener(self, callback, mask):
            pass

    schedulers_mod = types.ModuleType("apscheduler.schedulers")
    schedulers_mod.__path__ = []
    asyncio_mod = types.ModuleType("apscheduler.schedulers.asyncio")
    asyncio_mod.AsyncIOScheduler = FakeScheduler
    sys.modules["apscheduler.schedulers"] = schedulers_mod
    sys.modules["apscheduler.schedulers.asyncio"] = asyncio_mod

    return FakeScheduler, FakeCronTrigger


FakeScheduler, FakeCronTrigger = _install_apscheduler_stubs()


# Force reload of scheduler module with stubs in place
if "src.scheduler" in sys.modules:
    del sys.modules["src.scheduler"]

from src.scheduler import TaskScheduler, DryRunManager  # noqa: E402


# ---------------------------------------------------------------------------
# Mock MCP client
# ---------------------------------------------------------------------------

class _MockMCPClient:
    async def call_tool(self, tool_name, params):
        return json.dumps({
            "duplicates_found": 3,
            "memories_summarized": 5,
            "status": "success"
        })


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _base_config(dedup_enabled=False, summary_enabled=False,
                 dedup_schedule="weekly", summary_schedule="monthly",
                 require_approval=True, dry_run_first=True):
    return {
        "auto_deduplication": {
            "enabled": dedup_enabled,
            "schedule": dedup_schedule,
            "dry_run_first": dry_run_first,
            "require_approval": require_approval,
        },
        "auto_summarization": {
            "enabled": summary_enabled,
            "schedule": summary_schedule,
            "age_threshold_days": 30,
            "min_length": 500,
        }
    }


# ---------------------------------------------------------------------------
# Tests: TaskScheduler init and start/stop
# ---------------------------------------------------------------------------

class TestTaskSchedulerLifecycle:
    def test_init_creates_scheduler(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        assert ts.scheduler is not None

    def test_start_sets_running(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.start()
        assert ts.scheduler.running is True

    def test_start_already_running_does_not_crash(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.start()
        ts.start()  # second start should log warning, not raise
        assert ts.scheduler.running is True

    def test_stop_sets_not_running(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.start()
        ts.stop()
        assert ts.scheduler.running is False

    def test_stop_without_start_does_nothing(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.stop()  # should not raise


# ---------------------------------------------------------------------------
# Tests: _schedule_jobs
# ---------------------------------------------------------------------------

class TestScheduleJobs:
    def test_no_jobs_when_all_disabled(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts._schedule_jobs()
        assert len(ts.jobs) == 0

    def test_dedup_job_scheduled_when_enabled(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(dedup_enabled=True))
        ts._schedule_jobs()
        assert "deduplication" in ts.jobs

    def test_summary_job_scheduled_when_enabled(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(summary_enabled=True))
        ts._schedule_jobs()
        assert "summarization" in ts.jobs
        assert "category_summarization" in ts.jobs

    def test_both_jobs_when_both_enabled(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(
            dedup_enabled=True, summary_enabled=True))
        ts._schedule_jobs()
        assert "deduplication" in ts.jobs
        assert "summarization" in ts.jobs

    def test_dedup_daily_schedule(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(
            dedup_enabled=True, dedup_schedule="daily"))
        ts._schedule_jobs()
        assert "deduplication" in ts.jobs

    def test_dedup_monthly_schedule(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(
            dedup_enabled=True, dedup_schedule="monthly"))
        ts._schedule_jobs()
        assert "deduplication" in ts.jobs

    def test_dedup_unknown_schedule_logs_warning(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(
            dedup_enabled=True, dedup_schedule="quarterly"))
        ts._schedule_jobs()
        # Unknown schedule -> job should NOT be added
        assert "deduplication" not in ts.jobs

    def test_summary_weekly_schedule(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(
            summary_enabled=True, summary_schedule="weekly"))
        ts._schedule_jobs()
        assert "summarization" in ts.jobs

    def test_summary_unknown_schedule_no_job(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(
            summary_enabled=True, summary_schedule="yearly"))
        ts._schedule_jobs()
        assert "summarization" not in ts.jobs


# ---------------------------------------------------------------------------
# Tests: get_scheduled_jobs / get_statistics
# ---------------------------------------------------------------------------

class TestGetScheduledJobsAndStats:
    def test_get_jobs_empty_when_none_scheduled(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        jobs = ts.get_scheduled_jobs()
        assert isinstance(jobs, dict)
        assert len(jobs) == 0

    def test_get_jobs_after_schedule(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(dedup_enabled=True))
        ts.start()
        jobs = ts.get_scheduled_jobs()
        assert "deduplication" in jobs

    def test_get_statistics_returns_dict(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        stats = ts.get_statistics()
        assert "jobs_scheduled" in stats
        assert "running" in stats

    def test_statistics_running_flag(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.start()
        stats = ts.get_statistics()
        assert stats["running"] is True

    def test_get_jobs_no_scheduler(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.scheduler = None
        jobs = ts.get_scheduled_jobs()
        assert jobs == {}

    def test_statistics_no_scheduler(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.scheduler = None
        stats = ts.get_statistics()
        assert stats["running"] is False


# ---------------------------------------------------------------------------
# Tests: trigger_job
# ---------------------------------------------------------------------------

class TestTriggerJob:
    def test_trigger_existing_job(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config(dedup_enabled=True))
        ts.start()
        result = ts.trigger_job("deduplication")
        assert result is True

    def test_trigger_nonexistent_job_returns_false(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.start()
        result = ts.trigger_job("nonexistent")
        assert result is False

    def test_trigger_without_scheduler_returns_false(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        ts.scheduler = None
        result = ts.trigger_job("anything")
        assert result is False


# ---------------------------------------------------------------------------
# Tests: _run_deduplication (async task runner)
# ---------------------------------------------------------------------------

class TestRunDeduplication:
    @pytest.mark.asyncio
    async def test_run_deduplication_no_duplicates(self):
        mcp = _MockMCPClient()
        mcp.call_tool = AsyncMock(return_value=json.dumps({"duplicates_found": 0}))
        ts = TaskScheduler(mcp, _base_config(dedup_enabled=True))
        await ts._run_deduplication()
        assert ts.stats["jobs_completed"] == 1

    @pytest.mark.asyncio
    async def test_run_deduplication_with_duplicates_requires_approval(self):
        mcp = _MockMCPClient()
        mcp.call_tool = AsyncMock(return_value=json.dumps({"duplicates_found": 5}))
        ts = TaskScheduler(mcp, _base_config(
            dedup_enabled=True, dry_run_first=True, require_approval=True))
        await ts._run_deduplication()
        assert ts.stats["jobs_completed"] == 1

    @pytest.mark.asyncio
    async def test_run_deduplication_auto_approve(self):
        call_log = []

        async def mock_call(tool, params):
            call_log.append((tool, params))
            return json.dumps({"duplicates_found": 3})

        mcp = _MockMCPClient()
        mcp.call_tool = mock_call
        ts = TaskScheduler(mcp, _base_config(
            dedup_enabled=True, dry_run_first=True, require_approval=False))
        await ts._run_deduplication()
        # Should have called auto_deduplicate twice (dry run + final)
        tools_called = [t for t, _ in call_log]
        assert tools_called.count("auto_deduplicate") == 2

    @pytest.mark.asyncio
    async def test_run_deduplication_exception_increments_failed(self):
        mcp = _MockMCPClient()
        mcp.call_tool = AsyncMock(side_effect=RuntimeError("MCP exploded"))
        ts = TaskScheduler(mcp, _base_config(dedup_enabled=True))
        await ts._run_deduplication()
        assert ts.stats["jobs_failed"] == 1


# ---------------------------------------------------------------------------
# Tests: _run_summarization
# ---------------------------------------------------------------------------

class TestRunSummarization:
    @pytest.mark.asyncio
    async def test_run_summarization_success(self):
        mcp = _MockMCPClient()
        mcp.call_tool = AsyncMock(return_value=json.dumps({"memories_summarized": 10}))
        ts = TaskScheduler(mcp, _base_config(summary_enabled=True))
        await ts._run_summarization()
        assert ts.stats["jobs_completed"] == 1
        assert "summarization" in ts.stats["last_run"]

    @pytest.mark.asyncio
    async def test_run_summarization_exception_increments_failed(self):
        mcp = _MockMCPClient()
        mcp.call_tool = AsyncMock(side_effect=RuntimeError("error"))
        ts = TaskScheduler(mcp, _base_config(summary_enabled=True))
        await ts._run_summarization()
        assert ts.stats["jobs_failed"] == 1


# ---------------------------------------------------------------------------
# Tests: _run_category_summarization
# ---------------------------------------------------------------------------

class TestRunCategorySummarization:
    @pytest.mark.asyncio
    async def test_run_category_summarization_success(self):
        mcp = _MockMCPClient()
        mcp.call_tool = AsyncMock(return_value=json.dumps({"status": "ok"}))
        ts = TaskScheduler(mcp, _base_config())
        await ts._run_category_summarization()
        # Should not raise

    @pytest.mark.asyncio
    async def test_run_category_summarization_exception(self):
        mcp = _MockMCPClient()
        mcp.call_tool = AsyncMock(side_effect=RuntimeError("fail"))
        ts = TaskScheduler(mcp, _base_config())
        await ts._run_category_summarization()
        # Should not raise


# ---------------------------------------------------------------------------
# Tests: _request_approval
# ---------------------------------------------------------------------------

class TestRequestApproval:
    @pytest.mark.asyncio
    async def test_request_approval_logs_and_returns(self):
        ts = TaskScheduler(_MockMCPClient(), _base_config())
        # Should not raise
        await ts._request_approval("auto_deduplicate", {"duplicates_found": 5})


# ---------------------------------------------------------------------------
# Tests: DryRunManager
# ---------------------------------------------------------------------------

class TestDryRunManager:
    def test_init(self):
        drm = DryRunManager()
        assert drm.pending_approvals == {}
        assert drm.dry_run_history == []

    @pytest.mark.asyncio
    async def test_execute_dry_run_mode(self):
        drm = DryRunManager()

        async def mock_op(dry_run=True, **kwargs):
            return {"status": "dry_run_ok", "dry_run": dry_run}

        result = await drm.execute_with_dry_run(mock_op, "test_op", dry_run=True)
        assert result["success"] is True
        assert result["dry_run"] is True
        assert "test_op" in drm.pending_approvals

    @pytest.mark.asyncio
    async def test_execute_actual_mode(self):
        drm = DryRunManager()

        async def mock_op(dry_run=False, **kwargs):
            return {"status": "done", "dry_run": dry_run}

        result = await drm.execute_with_dry_run(mock_op, "real_op", dry_run=False)
        assert result["success"] is True
        assert result["dry_run"] is False
        assert len(drm.dry_run_history) == 1

    @pytest.mark.asyncio
    async def test_execute_exception_sets_error(self):
        drm = DryRunManager()

        async def failing_op(dry_run=True, **kwargs):
            raise ValueError("Something went wrong")

        result = await drm.execute_with_dry_run(failing_op, "fail_op", dry_run=True)
        assert result["success"] is False
        assert result["error"] is not None

    def test_get_pending_approvals(self):
        drm = DryRunManager()
        drm.pending_approvals["op1"] = {"data": "x"}
        approvals = drm.get_pending_approvals()
        assert "op1" in approvals

    @pytest.mark.asyncio
    async def test_approve_operation_existing(self):
        drm = DryRunManager()
        drm.pending_approvals["op-approve"] = {"kwargs": {}, "data": "x"}
        result = await drm.approve_operation("op-approve")
        assert result is True
        assert "op-approve" not in drm.pending_approvals

    @pytest.mark.asyncio
    async def test_approve_operation_missing(self):
        drm = DryRunManager()
        result = await drm.approve_operation("no-such-op")
        assert result is False

    def test_reject_operation(self):
        drm = DryRunManager()
        drm.pending_approvals["op-reject"] = {"data": "y"}
        drm.reject_operation("op-reject")
        assert "op-reject" not in drm.pending_approvals

    def test_reject_nonexistent_does_nothing(self):
        drm = DryRunManager()
        drm.reject_operation("never-there")
        # Should not raise


# ---------------------------------------------------------------------------
# Tests: APSCHEDULER_AVAILABLE=False paths (lines 63-64)
# ---------------------------------------------------------------------------

class TestStartWithoutApscheduler:
    def test_start_returns_early_when_apscheduler_unavailable(self):
        import src.scheduler as _sched_mod
        ts = TaskScheduler(_MockMCPClient(), _base_config(dedup_enabled=True))
        # Set scheduler to None to simulate unavailability
        ts.scheduler = None
        with patch.object(_sched_mod, "APSCHEDULER_AVAILABLE", False):
            ts.start()
        # Should return without scheduling or raising
        assert len(ts.jobs) == 0


# ---------------------------------------------------------------------------
# Tests: main() function (lines 488-525)
# ---------------------------------------------------------------------------

class TestMainFunction:
    @pytest.mark.asyncio
    async def test_main_runs_without_raising(self):
        """Exercising the module-level main() function."""
        import src.scheduler as _sched_mod
        # main() creates a scheduler, starts it, sleeps, then stops
        # We mock asyncio.sleep to avoid actual delay
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await _sched_mod.main()
