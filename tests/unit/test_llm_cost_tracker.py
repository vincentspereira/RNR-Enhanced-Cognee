"""
Unit tests for src/llm_cost_tracker.py
Covers: LLMCostTracker - initialize, record_usage, _persist, _buffer_record,
        _check_budget, _get_monthly_spend, get_cost_report, set_budget,
        _register_litellm_callback, _report_from_buffer, _format_report,
        context vars, singletons.
Target: >= 85% line coverage.
"""

import sys
import types
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn():
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=None)
    conn.fetchrow = AsyncMock(return_value=None)
    return conn


class _AcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_pool(conn=None):
    if conn is None:
        conn = _make_conn()
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AcquireCtx(conn))
    return pool, conn


# ---------------------------------------------------------------------------
# Import the module under test AFTER helpers are defined
# ---------------------------------------------------------------------------

from src.llm_cost_tracker import (
    LLMCostTracker,
    UsageRecord,
    set_llm_context,
    get_cost_tracker,
    init_cost_tracker,
    _current_agent_id,
    _current_tool_name,
)


# ---------------------------------------------------------------------------
# Context variable helpers
# ---------------------------------------------------------------------------

class TestContextVars:
    def test_set_llm_context_updates_vars(self):
        set_llm_context("agent-x", "tool-y")
        assert _current_agent_id.get() == "agent-x"
        assert _current_tool_name.get() == "tool-y"

    def test_default_context_values(self):
        # Defaults defined in ContextVar constructors
        from src.llm_cost_tracker import _current_agent_id as av, _current_tool_name as tv
        assert av.get() in ("system", "agent-x")  # may carry over from prior test
        assert tv.get() in ("unknown", "tool-y")


# ---------------------------------------------------------------------------
# UsageRecord dataclass
# ---------------------------------------------------------------------------

class TestUsageRecord:
    def test_create(self):
        r = UsageRecord(
            agent_id="a",
            tool_name="t",
            model="gpt-4",
            input_tokens=10,
            output_tokens=20,
            estimated_cost_usd=0.001,
            timestamp="2024-01-01T00:00:00+00:00",
        )
        assert r.agent_id == "a"
        assert r.output_tokens == 20


# ---------------------------------------------------------------------------
# LLMCostTracker.__init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_init_no_pool(self):
        tracker = LLMCostTracker()
        assert tracker.postgres_pool is None
        assert tracker._buffer == []
        assert tracker._budgets == {}
        assert tracker._registered is False

    def test_init_with_pool(self):
        pool, _ = _make_pool()
        tracker = LLMCostTracker(postgres_pool=pool)
        assert tracker.postgres_pool is pool


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------

class TestInitialize:
    @pytest.mark.asyncio
    async def test_initialize_with_pool(self):
        conn = _make_conn()
        row = MagicMock()
        row.__getitem__ = lambda self, k: {"agent_id": "a1", "monthly_usd": "5.00"}[k]
        conn.fetch = AsyncMock(return_value=[row])
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        with patch.object(tracker, "_register_litellm_callback") as mock_reg:
            await tracker.initialize()
            mock_reg.assert_called_once()
        assert tracker._budgets["a1"] == 5.0

    @pytest.mark.asyncio
    async def test_initialize_db_error(self):
        conn = _make_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError("db gone"))
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        with patch.object(tracker, "_register_litellm_callback"):
            await tracker.initialize()  # should not raise

    @pytest.mark.asyncio
    async def test_initialize_no_pool(self):
        tracker = LLMCostTracker()
        with patch.object(tracker, "_register_litellm_callback") as mock_reg:
            await tracker.initialize()
            mock_reg.assert_called_once()


# ---------------------------------------------------------------------------
# _register_litellm_callback
# ---------------------------------------------------------------------------

class TestRegisterLitellmCallback:
    def test_already_registered_skips(self):
        tracker = LLMCostTracker()
        tracker._registered = True
        tracker._register_litellm_callback()
        # If already registered, function returns immediately - no error

    def test_litellm_not_installed(self):
        tracker = LLMCostTracker()
        with patch.dict(sys.modules, {"litellm": None}):
            tracker._register_litellm_callback()
        assert not tracker._registered

    def test_litellm_installed_registers(self):
        tracker = LLMCostTracker()
        litellm_mock = MagicMock()
        litellm_mock.success_callback = []
        litellm_mock.completion_cost = MagicMock(return_value=0.001)
        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()
        assert tracker._registered
        assert len(litellm_mock.success_callback) == 1

    def test_litellm_callback_not_list(self):
        tracker = LLMCostTracker()
        litellm_mock = MagicMock()
        litellm_mock.success_callback = lambda *a: None  # not a list
        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()
        assert isinstance(litellm_mock.success_callback, list)

    def test_litellm_callback_appends_when_list(self):
        tracker = LLMCostTracker()
        existing = MagicMock()
        litellm_mock = MagicMock()
        litellm_mock.success_callback = [existing]
        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()
        assert existing in litellm_mock.success_callback
        assert len(litellm_mock.success_callback) == 2

    def test_litellm_callback_no_attribute(self):
        tracker = LLMCostTracker()
        litellm_mock = MagicMock(spec=[])  # no success_callback attr
        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()
        assert hasattr(litellm_mock, "success_callback")


# ---------------------------------------------------------------------------
# _on_success callback invocation (via registered callback)
# ---------------------------------------------------------------------------

class TestOnSuccessCallback:
    @pytest.mark.asyncio
    async def test_callback_runs_with_running_loop(self):
        tracker = LLMCostTracker()
        litellm_mock = MagicMock()
        litellm_mock.success_callback = []
        litellm_mock.completion_cost = MagicMock(return_value=0.0005)

        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()

        callback = litellm_mock.success_callback[-1]

        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 50
        completion_response = MagicMock()
        completion_response.usage = usage

        with patch.object(tracker, "_persist", new=AsyncMock()), \
             patch.object(tracker, "_check_budget", new=AsyncMock()):
            # running inside an async test so get_running_loop() will succeed
            callback({"model": "gpt-4"}, completion_response, None, None)

    def test_callback_no_running_loop(self):
        tracker = LLMCostTracker()
        litellm_mock = MagicMock()
        litellm_mock.success_callback = []
        litellm_mock.completion_cost = MagicMock(return_value=0.001)
        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()
        callback = litellm_mock.success_callback[-1]

        usage = MagicMock()
        usage.prompt_tokens = 10
        usage.completion_tokens = 5
        completion_response = MagicMock()
        completion_response.usage = usage

        with patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")):
            callback({"model": "gpt-3.5"}, completion_response, None, None)
        assert len(tracker._buffer) == 1

    def test_callback_cost_calculation_fallback(self):
        tracker = LLMCostTracker()
        litellm_mock = MagicMock()
        litellm_mock.success_callback = []
        litellm_mock.completion_cost = MagicMock(side_effect=Exception("cost calc failed"))
        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()
        callback = litellm_mock.success_callback[-1]

        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 100
        completion_response = MagicMock()
        completion_response.usage = usage

        with patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")):
            callback({"model": "gpt-4"}, completion_response, None, None)
        assert len(tracker._buffer) == 1
        assert tracker._buffer[0].estimated_cost_usd == pytest.approx(200 * 1e-6)

    def test_callback_exception_silenced(self):
        tracker = LLMCostTracker()
        litellm_mock = MagicMock()
        litellm_mock.success_callback = []
        litellm_mock.completion_cost = MagicMock(return_value=0.0)
        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()
        callback = litellm_mock.success_callback[-1]

        # Pass bad kwargs to trigger exception inside callback body
        callback({}, MagicMock(), None, None)  # should not raise

    def test_callback_outer_exception_silenced(self):
        """Cover lines 213-215: outer except that silences all callback errors."""
        tracker = LLMCostTracker()
        litellm_mock = MagicMock()
        litellm_mock.success_callback = []
        # Make _current_agent_id.get raise to trigger outer exception
        litellm_mock.completion_cost = MagicMock(return_value=0.001)
        with patch.dict(sys.modules, {"litellm": litellm_mock}):
            tracker._register_litellm_callback()
        callback = litellm_mock.success_callback[-1]

        # Patch _current_agent_id so calling .get() raises (covers the outer except)
        with patch("src.llm_cost_tracker._current_agent_id") as mock_var:
            mock_var.get = MagicMock(side_effect=RuntimeError("var error"))
            callback({"model": "m"}, MagicMock(), None, None)  # should not raise


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------

class TestRecordUsage:
    @pytest.mark.asyncio
    async def test_record_usage_with_cost(self):
        tracker = LLMCostTracker()
        with patch.object(tracker, "_persist", new=AsyncMock()) as mock_p, \
             patch.object(tracker, "_check_budget", new=AsyncMock()) as mock_b:
            await tracker.record_usage("ag", "tool", "gpt-4", 100, 50, 0.002)
            mock_p.assert_called_once()
            mock_b.assert_called_once_with("ag", 0.002)

    @pytest.mark.asyncio
    async def test_record_usage_auto_cost(self):
        tracker = LLMCostTracker()
        with patch.object(tracker, "_persist", new=AsyncMock()) as mock_p, \
             patch.object(tracker, "_check_budget", new=AsyncMock()):
            await tracker.record_usage("ag", "tool", "gpt-4", 500, 200)
            record = mock_p.call_args[0][0]
            expected = (500 + 200) * 1e-6
            assert record.estimated_cost_usd == pytest.approx(expected)


# ---------------------------------------------------------------------------
# _buffer_record
# ---------------------------------------------------------------------------

class TestBufferRecord:
    def test_buffer_appends(self):
        tracker = LLMCostTracker()
        r = UsageRecord("a", "t", "m", 1, 1, 0.0, "2024-01-01T00:00:00+00:00")
        tracker._buffer_record(r)
        assert len(tracker._buffer) == 1

    def test_buffer_evicts_oldest(self):
        tracker = LLMCostTracker()
        tracker._MAX_BUFFER = 3
        for i in range(5):
            r = UsageRecord("a", "t", "m", i, i, 0.0, "2024-01-01T00:00:00+00:00")
            tracker._buffer_record(r)
        assert len(tracker._buffer) == 3
        # Newest should remain
        assert tracker._buffer[-1].input_tokens == 4


# ---------------------------------------------------------------------------
# _persist
# ---------------------------------------------------------------------------

class TestPersist:
    @pytest.mark.asyncio
    async def test_persist_to_db_success(self):
        conn = _make_conn()
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        r = UsageRecord("a", "t", "gpt-4", 10, 5, 0.001, datetime.now(UTC).isoformat())
        await tracker._persist(r)
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_db_failure_falls_back_to_buffer(self):
        conn = _make_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError("pg fail"))
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        r = UsageRecord("a", "t", "gpt-4", 10, 5, 0.001, datetime.now(UTC).isoformat())
        await tracker._persist(r)
        assert len(tracker._buffer) == 1

    @pytest.mark.asyncio
    async def test_persist_no_pool_uses_buffer(self):
        tracker = LLMCostTracker()
        r = UsageRecord("a", "t", "m", 1, 1, 0.0, datetime.now(UTC).isoformat())
        await tracker._persist(r)
        assert len(tracker._buffer) == 1


# ---------------------------------------------------------------------------
# _check_budget
# ---------------------------------------------------------------------------

class TestCheckBudget:
    @pytest.mark.asyncio
    async def test_no_budget_set(self):
        tracker = LLMCostTracker()
        # Should return without error when no budget is set
        await tracker._check_budget("agent_x", 5.0)

    @pytest.mark.asyncio
    async def test_budget_not_exceeded(self):
        tracker = LLMCostTracker()
        tracker._budgets["agent_y"] = 100.0
        with patch.object(tracker, "_get_monthly_spend", new=AsyncMock(return_value=50.0)):
            await tracker._check_budget("agent_y", 1.0)  # no warning

    @pytest.mark.asyncio
    async def test_budget_exceeded_logs_warning(self):
        tracker = LLMCostTracker()
        tracker._budgets["agent_z"] = 10.0
        with patch.object(tracker, "_get_monthly_spend", new=AsyncMock(return_value=15.0)):
            with patch("src.llm_cost_tracker.logger") as mock_log:
                await tracker._check_budget("agent_z", 1.0)
                mock_log.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_global_budget_used_when_no_agent_budget(self):
        tracker = LLMCostTracker()
        tracker._budgets["*"] = 5.0
        with patch.object(tracker, "_get_monthly_spend", new=AsyncMock(return_value=6.0)):
            with patch("src.llm_cost_tracker.logger") as mock_log:
                await tracker._check_budget("agent_new", 0.1)
                mock_log.warning.assert_called_once()


# ---------------------------------------------------------------------------
# _get_monthly_spend
# ---------------------------------------------------------------------------

class TestGetMonthlySpend:
    @pytest.mark.asyncio
    async def test_spend_from_db(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(return_value="12.345")
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        result = await tracker._get_monthly_spend("agent_a")
        assert result == pytest.approx(12.345)

    @pytest.mark.asyncio
    async def test_spend_db_fallback_to_buffer(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(side_effect=RuntimeError("db err"))
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        ts = datetime.now(UTC).isoformat()
        tracker._buffer = [
            UsageRecord("agent_a", "t", "m", 10, 10, 0.5, ts),
            UsageRecord("agent_b", "t", "m", 10, 10, 1.0, ts),
        ]
        result = await tracker._get_monthly_spend("agent_a")
        assert result == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_spend_from_buffer_no_pool(self):
        tracker = LLMCostTracker()
        ts = datetime.now(UTC).isoformat()
        tracker._buffer = [
            UsageRecord("agent_a", "t", "m", 10, 5, 0.3, ts),
            UsageRecord("agent_a", "t", "m", 10, 5, 0.2, ts),
            UsageRecord("agent_b", "t", "m", 10, 5, 0.9, ts),
        ]
        result = await tracker._get_monthly_spend("agent_a")
        assert result == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_spend_filters_old_records(self):
        tracker = LLMCostTracker()
        old_ts = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        current_ts = datetime.now(UTC).isoformat()
        tracker._buffer = [
            UsageRecord("agent_a", "t", "m", 10, 5, 1.0, old_ts),
            UsageRecord("agent_a", "t", "m", 10, 5, 0.3, current_ts),
        ]
        result = await tracker._get_monthly_spend("agent_a")
        assert result == pytest.approx(0.3)

    @pytest.mark.asyncio
    async def test_spend_none_from_db(self):
        conn = _make_conn()
        conn.fetchval = AsyncMock(return_value=None)
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        result = await tracker._get_monthly_spend("agent_a")
        assert result == 0.0


# ---------------------------------------------------------------------------
# get_cost_report
# ---------------------------------------------------------------------------

class TestGetCostReport:
    @pytest.mark.asyncio
    async def test_report_from_buffer_no_records(self):
        tracker = LLMCostTracker()
        report = await tracker.get_cost_report()
        assert "No LLM usage" in report

    @pytest.mark.asyncio
    async def test_report_from_buffer_with_records(self):
        tracker = LLMCostTracker()
        ts = datetime.now(UTC).isoformat()
        tracker._buffer = [
            UsageRecord("agent_a", "recall", "gpt-4", 100, 50, 0.002, ts),
            UsageRecord("agent_b", "recall", "gpt-4", 200, 100, 0.004, ts),
        ]
        report = await tracker.get_cost_report()
        assert "OK LLM Cost Report" in report
        assert "TOTAL" in report

    @pytest.mark.asyncio
    async def test_report_from_buffer_grouped_by_tool(self):
        tracker = LLMCostTracker()
        ts = datetime.now(UTC).isoformat()
        tracker._buffer = [
            UsageRecord("agent_a", "recall", "gpt-4", 100, 50, 0.002, ts),
            UsageRecord("agent_a", "cognify", "gpt-4", 200, 100, 0.004, ts),
        ]
        report = await tracker.get_cost_report(group_by="tool")
        assert "recall" in report or "cognify" in report

    @pytest.mark.asyncio
    async def test_report_from_buffer_grouped_by_model(self):
        tracker = LLMCostTracker()
        ts = datetime.now(UTC).isoformat()
        tracker._buffer = [
            UsageRecord("agent_a", "t", "gpt-4", 10, 5, 0.001, ts),
            UsageRecord("agent_a", "t", "claude-3", 20, 10, 0.002, ts),
        ]
        report = await tracker.get_cost_report(group_by="model")
        assert "gpt-4" in report or "claude-3" in report

    @pytest.mark.asyncio
    async def test_report_from_buffer_filtered_by_agent(self):
        tracker = LLMCostTracker()
        ts = datetime.now(UTC).isoformat()
        tracker._buffer = [
            UsageRecord("agent_a", "t", "m", 10, 5, 0.001, ts),
            UsageRecord("agent_b", "t", "m", 20, 10, 0.002, ts),
        ]
        report = await tracker.get_cost_report(agent_id="agent_a")
        assert "agent_a" in report

    @pytest.mark.asyncio
    async def test_report_from_db_all_agents(self):
        conn = _make_conn()
        row = MagicMock()
        row.group_key = "agent_a"
        row.calls = 5
        row.total_input = 1000
        row.total_output = 500
        row.total_cost = 0.01
        total = MagicMock()
        total.calls = 5
        total.total_input = 1000
        total.total_output = 500
        total.total_cost = 0.01
        conn.fetch = AsyncMock(return_value=[row])
        conn.fetchrow = AsyncMock(return_value=total)
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        report = await tracker.get_cost_report()
        assert "OK LLM Cost Report" in report

    @pytest.mark.asyncio
    async def test_report_from_db_single_agent(self):
        conn = _make_conn()
        row = MagicMock()
        row.group_key = "tool_a"
        row.calls = 3
        row.total_input = 600
        row.total_output = 300
        row.total_cost = 0.005
        total = MagicMock()
        total.calls = 3
        total.total_input = 600
        total.total_output = 300
        total.total_cost = 0.005
        conn.fetch = AsyncMock(return_value=[row])
        conn.fetchrow = AsyncMock(return_value=total)
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        report = await tracker.get_cost_report(agent_id="agent_a", group_by="tool")
        assert "OK LLM Cost Report" in report

    @pytest.mark.asyncio
    async def test_report_from_db_exception(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("db fail"))
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        report = await tracker.get_cost_report()
        assert "ERR" in report

    @pytest.mark.asyncio
    async def test_report_from_db_no_rows(self):
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        total = MagicMock()
        total.calls = 0
        total.total_input = 0
        total.total_output = 0
        total.total_cost = 0.0
        conn.fetchrow = AsyncMock(return_value=total)
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        report = await tracker.get_cost_report()
        assert "No LLM usage" in report


# ---------------------------------------------------------------------------
# _format_report
# ---------------------------------------------------------------------------

class TestFormatReport:
    def test_empty_rows(self):
        report = LLMCostTracker._format_report([], None, None, 30, "agent")
        assert "No LLM usage" in report

    def test_rows_present(self):
        class _R:
            group_key = "ag1"
            calls = 10
            total_input = 1000
            total_output = 500
            total_cost = 0.005

        class _T:
            calls = 10
            total_input = 1000
            total_output = 500
            total_cost = 0.005

        report = LLMCostTracker._format_report([_R()], _T(), "ag1", 7, "agent")
        assert "ag1" in report
        assert "TOTAL" in report

    def test_long_group_key_truncated(self):
        class _R:
            group_key = "x" * 50
            calls = 1
            total_input = 1
            total_output = 1
            total_cost = 0.0

        class _T:
            calls = 1
            total_input = 1
            total_output = 1
            total_cost = 0.0

        report = LLMCostTracker._format_report([_R()], _T(), None, 30, "agent")
        assert "..." in report


# ---------------------------------------------------------------------------
# set_budget
# ---------------------------------------------------------------------------

class TestSetBudget:
    @pytest.mark.asyncio
    async def test_set_budget_in_memory_only(self):
        tracker = LLMCostTracker()
        msg = await tracker.set_budget("agent_a", 50.0)
        assert tracker._budgets["agent_a"] == 50.0
        assert "in-memory only" in msg

    @pytest.mark.asyncio
    async def test_set_budget_persists_to_db(self):
        conn = _make_conn()
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        msg = await tracker.set_budget("agent_b", 100.0)
        assert tracker._budgets["agent_b"] == 100.0
        assert "persisted to DB" in msg
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_budget_db_failure(self):
        conn = _make_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError("write fail"))
        pool, _ = _make_pool(conn)
        tracker = LLMCostTracker(postgres_pool=pool)
        msg = await tracker.set_budget("agent_c", 20.0)
        assert "WARN" in msg
        # In-memory should still be updated
        assert tracker._budgets["agent_c"] == 20.0

    @pytest.mark.asyncio
    async def test_set_global_budget(self):
        tracker = LLMCostTracker()
        await tracker.set_budget("*", 200.0)
        assert tracker._budgets["*"] == 200.0


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------

class TestSingletonHelpers:
    def test_init_cost_tracker(self):
        tracker = init_cost_tracker()
        assert isinstance(tracker, LLMCostTracker)
        assert get_cost_tracker() is tracker

    def test_init_cost_tracker_with_pool(self):
        pool, _ = _make_pool()
        tracker = init_cost_tracker(postgres_pool=pool)
        assert tracker.postgres_pool is pool

    def test_get_cost_tracker_none(self):
        import src.llm_cost_tracker as mod
        original = mod._cost_tracker
        mod._cost_tracker = None
        assert get_cost_tracker() is None
        mod._cost_tracker = original
