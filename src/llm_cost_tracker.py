"""
LLM Cost Tracker for RNR Enhanced Cognee
=====================================
Tracks LLM token usage and estimated API cost per agent and tool.

Architecture
------------
- Registers a LiteLLM success_callback to capture every completion call
  transparently, regardless of which tool triggered it.
- Stores records in PostgreSQL table shared_memory.llm_usage.
- Falls back to an in-memory ring buffer (10,000 entries) when PostgreSQL
  is unavailable.
- Supports per-agent monthly budget limits with WARN-level alerts.
- Context variables (agent_id, tool_name) allow attribution of each LLM
  call to the originating MCP tool and agent.

Usage
-----
    from src.llm_cost_tracker import init_cost_tracker, set_llm_context

    # At server startup:
    tracker = init_cost_tracker(postgres_pool=pool)
    await tracker.initialize()

    # Inside an MCP tool (optional, improves attribution):
    set_llm_context(agent_id="my-agent", tool_name="recall")

Author: RNR Enhanced Cognee
Version: 1.0.0
"""

import asyncio
import logging
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Context variables for per-call attribution (thread-safe / async-safe)
# ---------------------------------------------------------------------------
_current_agent_id: ContextVar[str] = ContextVar("current_agent_id", default="system")
_current_tool_name: ContextVar[str] = ContextVar("current_tool_name", default="unknown")


def set_llm_context(agent_id: str, tool_name: str) -> None:
    """
    Set the agent and tool name for attribution of the next LLM call.

    Call this at the start of any MCP tool that invokes an LLM so that
    cost records are attributed correctly.

    Args:
        agent_id:  Agent identifier (e.g. 'claude-code').
        tool_name: MCP tool name (e.g. 'recall', 'improve').
    """
    _current_agent_id.set(agent_id)
    _current_tool_name.set(tool_name)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class UsageRecord:
    """Single LLM call usage snapshot."""
    agent_id: str
    tool_name: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    timestamp: str  # ISO-8601 UTC


# ---------------------------------------------------------------------------
# Main tracker class
# ---------------------------------------------------------------------------

class LLMCostTracker:
    """
    Track LLM token usage and estimated cost per agent / tool.

    Features
    --------
    - LiteLLM callback registration (automatic, transparent interception)
    - PostgreSQL persistence (shared_memory.llm_usage)
    - In-memory ring buffer fallback
    - Monthly budget tracking with WARN alerts
    - ASCII-only output (Windows cp1252 compatible)
    """

    _TABLE_DDL = """
        CREATE TABLE IF NOT EXISTS shared_memory.llm_usage (
            id                  BIGSERIAL PRIMARY KEY,
            agent_id            TEXT        NOT NULL DEFAULT 'system',
            tool_name           TEXT        NOT NULL DEFAULT 'unknown',
            model               TEXT        NOT NULL,
            input_tokens        INT         NOT NULL DEFAULT 0,
            output_tokens       INT         NOT NULL DEFAULT 0,
            estimated_cost_usd  NUMERIC(12, 8) NOT NULL DEFAULT 0,
            recorded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_llm_usage_agent_id
            ON shared_memory.llm_usage (agent_id);
        CREATE INDEX IF NOT EXISTS idx_llm_usage_recorded_at
            ON shared_memory.llm_usage (recorded_at DESC);
    """

    _BUDGETS_DDL = """
        CREATE TABLE IF NOT EXISTS shared_memory.llm_budgets (
            agent_id    TEXT        PRIMARY KEY,
            monthly_usd NUMERIC(10, 2) NOT NULL,
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """

    _MAX_BUFFER = 10_000

    def __init__(self, postgres_pool=None) -> None:
        self.postgres_pool = postgres_pool
        self._buffer: List[UsageRecord] = []
        self._budgets: Dict[str, float] = {}
        self._registered = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create DB tables if needed and register the LiteLLM callback."""
        if self.postgres_pool:
            try:
                async with self.postgres_pool.acquire() as conn:
                    await conn.execute(self._TABLE_DDL)
                    await conn.execute(self._BUDGETS_DDL)
                    rows = await conn.fetch(
                        "SELECT agent_id, monthly_usd FROM shared_memory.llm_budgets"
                    )
                    for row in rows:
                        self._budgets[row["agent_id"]] = float(row["monthly_usd"])
                logger.info("OK LLM Cost Tracker tables ready")
            except Exception as exc:
                logger.warning(f"LLM Cost Tracker DB init failed: {exc}")

        self._register_litellm_callback()

    # ------------------------------------------------------------------
    # LiteLLM callback
    # ------------------------------------------------------------------

    def _register_litellm_callback(self) -> None:
        """Register a LiteLLM success_callback to intercept every completion."""
        if self._registered:
            return

        try:
            import litellm
        except ImportError:
            logger.info(
                "INFO LLM Cost Tracker: litellm not installed, "
                "manual tracking only (record_usage())"
            )
            return

        tracker_ref = self  # strong ref inside closure

        def _on_success(kwargs, completion_response, start_time, end_time):
            """
            LiteLLM fires this sync callback after every successful completion.
            We read context vars for attribution and schedule an async persist.
            """
            try:
                agent_id = _current_agent_id.get()
                tool_name = _current_tool_name.get()
                model = kwargs.get("model", "unknown")

                usage = getattr(completion_response, "usage", None)
                input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

                # Prefer LiteLLM's own cost calculator; fall back to rough estimate
                try:
                    cost = float(
                        litellm.completion_cost(completion_response=completion_response)
                    )
                except Exception:
                    cost = (input_tokens + output_tokens) * 1e-6  # ~$0.001/1K tokens

                record = UsageRecord(
                    agent_id=agent_id,
                    tool_name=tool_name,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=cost,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

                # Persist asynchronously if a running event loop is available
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(tracker_ref._persist(record))
                    loop.create_task(tracker_ref._check_budget(agent_id, cost))
                except RuntimeError:
                    # No running loop (e.g. sync context) - buffer only
                    tracker_ref._buffer_record(record)

            except Exception as exc:
                # Never raise from a callback - just log at DEBUG
                logger.debug(f"LLM cost callback error (non-fatal): {exc}")

        # Append to existing callbacks list (don't overwrite other hooks)
        if not hasattr(litellm, "success_callback"):
            litellm.success_callback = []
        if not isinstance(litellm.success_callback, list):
            litellm.success_callback = [litellm.success_callback]
        litellm.success_callback.append(_on_success)

        self._registered = True
        logger.info("OK LLM Cost Tracker callback registered with LiteLLM")

    # ------------------------------------------------------------------
    # Manual tracking (for tools that do not go through LiteLLM)
    # ------------------------------------------------------------------

    async def record_usage(
        self,
        agent_id: str,
        tool_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Optional[float] = None,
    ) -> None:
        """
        Manually record an LLM usage event.

        Use this for LLM calls that bypass LiteLLM (e.g. direct OpenAI client).

        Args:
            agent_id:     Agent that triggered the call.
            tool_name:    MCP tool name.
            model:        Model identifier (e.g. 'gpt-4o').
            input_tokens: Prompt token count.
            output_tokens: Completion token count.
            cost_usd:     Estimated cost. If None, a rough estimate is used.
        """
        if cost_usd is None:
            cost_usd = (input_tokens + output_tokens) * 1e-6

        record = UsageRecord(
            agent_id=agent_id,
            tool_name=tool_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost_usd,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        await self._persist(record)
        await self._check_budget(agent_id, cost_usd)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _buffer_record(self, record: UsageRecord) -> None:
        """Append to ring buffer, evicting oldest entries when full."""
        self._buffer.append(record)
        if len(self._buffer) > self._MAX_BUFFER:
            self._buffer = self._buffer[-self._MAX_BUFFER:]

    async def _persist(self, record: UsageRecord) -> None:
        """Write a usage record to PostgreSQL; fall back to buffer on error."""
        if self.postgres_pool:
            try:
                async with self.postgres_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO shared_memory.llm_usage
                            (agent_id, tool_name, model, input_tokens, output_tokens,
                             estimated_cost_usd, recorded_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        record.agent_id,
                        record.tool_name,
                        record.model,
                        record.input_tokens,
                        record.output_tokens,
                        record.estimated_cost_usd,
                        datetime.fromisoformat(record.timestamp),
                    )
                return
            except Exception as exc:
                logger.debug(f"LLM usage persist failed, buffering locally: {exc}")
        self._buffer_record(record)

    async def _check_budget(self, agent_id: str, new_cost: float) -> None:
        """
        Check if this agent (or global '*') has exceeded its monthly budget.
        Logs a WARN if the limit is breached.  Does NOT hard-stop by default.
        """
        budget = self._budgets.get(agent_id) or self._budgets.get("*")
        if not budget:
            return

        current_spend = await self._get_monthly_spend(agent_id)
        if current_spend >= budget:
            logger.warning(
                f"WARN LLM budget exceeded for agent '{agent_id}': "
                f"${current_spend:.4f} >= monthly limit ${budget:.2f}"
            )

    async def _get_monthly_spend(self, agent_id: str) -> float:
        """Return total LLM spend (USD) for agent in the current calendar month."""
        month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        if self.postgres_pool:
            try:
                async with self.postgres_pool.acquire() as conn:
                    value = await conn.fetchval(
                        """
                        SELECT COALESCE(SUM(estimated_cost_usd), 0)
                        FROM shared_memory.llm_usage
                        WHERE agent_id = $1 AND recorded_at >= $2
                        """,
                        agent_id,
                        month_start,
                    )
                    return float(value or 0)
            except Exception:
                pass

        # Buffer fallback
        return sum(
            r.estimated_cost_usd
            for r in self._buffer
            if r.agent_id == agent_id
            and datetime.fromisoformat(r.timestamp).replace(tzinfo=timezone.utc)
            >= month_start
        )

    # ------------------------------------------------------------------
    # Public API: cost report
    # ------------------------------------------------------------------

    async def get_cost_report(
        self,
        agent_id: Optional[str] = None,
        days_back: int = 30,
        group_by: str = "agent",
    ) -> str:
        """
        Generate an ASCII cost report for the specified period.

        Args:
            agent_id:  Filter to a single agent (None = all agents).
            days_back: Number of calendar days to look back (default: 30).
            group_by:  Grouping dimension: 'agent', 'tool', or 'model'.

        Returns:
            Formatted ASCII report string.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days_back)

        if self.postgres_pool:
            return await self._report_from_db(agent_id, since, days_back, group_by)
        return self._report_from_buffer(agent_id, since, days_back, group_by)

    async def _report_from_db(
        self, agent_id, since, days_back, group_by
    ) -> str:
        """Build cost report from PostgreSQL."""
        group_col = {
            "agent": "agent_id",
            "tool":  "tool_name",
            "model": "model",
        }.get(group_by, "agent_id")

        try:
            async with self.postgres_pool.acquire() as conn:
                # Per-group breakdown
                if agent_id:
                    rows = await conn.fetch(
                        f"""
                        SELECT {group_col} AS group_key,
                               SUM(input_tokens)          AS total_input,
                               SUM(output_tokens)         AS total_output,
                               SUM(estimated_cost_usd)    AS total_cost,
                               COUNT(*)                   AS calls
                        FROM shared_memory.llm_usage
                        WHERE recorded_at >= $1 AND agent_id = $2
                        GROUP BY {group_col}
                        ORDER BY total_cost DESC
                        LIMIT 50
                        """,
                        since, agent_id,
                    )
                    total_row = await conn.fetchrow(
                        """
                        SELECT SUM(input_tokens) AS total_input,
                               SUM(output_tokens) AS total_output,
                               SUM(estimated_cost_usd) AS total_cost,
                               COUNT(*) AS calls
                        FROM shared_memory.llm_usage
                        WHERE recorded_at >= $1 AND agent_id = $2
                        """,
                        since, agent_id,
                    )
                else:
                    rows = await conn.fetch(
                        f"""
                        SELECT {group_col} AS group_key,
                               SUM(input_tokens)          AS total_input,
                               SUM(output_tokens)         AS total_output,
                               SUM(estimated_cost_usd)    AS total_cost,
                               COUNT(*)                   AS calls
                        FROM shared_memory.llm_usage
                        WHERE recorded_at >= $1
                        GROUP BY {group_col}
                        ORDER BY total_cost DESC
                        LIMIT 50
                        """,
                        since,
                    )
                    total_row = await conn.fetchrow(
                        """
                        SELECT SUM(input_tokens) AS total_input,
                               SUM(output_tokens) AS total_output,
                               SUM(estimated_cost_usd) AS total_cost,
                               COUNT(*) AS calls
                        FROM shared_memory.llm_usage
                        WHERE recorded_at >= $1
                        """,
                        since,
                    )
        except Exception as exc:
            return f"ERR Cost report DB query failed: {exc}"

        return self._format_report(rows, total_row, agent_id, days_back, group_by)

    def _report_from_buffer(
        self, agent_id, since, days_back, group_by
    ) -> str:
        """Build cost report from in-memory buffer (PostgreSQL not available)."""
        records = [
            r for r in self._buffer
            if datetime.fromisoformat(r.timestamp).replace(tzinfo=timezone.utc) >= since
            and (not agent_id or r.agent_id == agent_id)
        ]

        groups: Dict[str, Dict] = defaultdict(
            lambda: {"total_input": 0, "total_output": 0, "total_cost": 0.0, "calls": 0}
        )
        for r in records:
            key = {
                "agent": r.agent_id,
                "tool":  r.tool_name,
                "model": r.model,
            }.get(group_by, r.agent_id)
            g = groups[key]
            g["total_input"] += r.input_tokens
            g["total_output"] += r.output_tokens
            g["total_cost"] += r.estimated_cost_usd
            g["calls"] += 1

        sorted_groups = sorted(
            groups.items(), key=lambda x: x[1]["total_cost"], reverse=True
        )

        # Fake row objects matching the DB row interface
        class _Row:
            def __init__(self, key, d):
                self.group_key   = key
                self.total_input = d["total_input"]
                self.total_output = d["total_output"]
                self.total_cost  = d["total_cost"]
                self.calls       = d["calls"]

        class _Total:
            total_input  = sum(r.input_tokens for r in records)
            total_output = sum(r.output_tokens for r in records)
            total_cost   = sum(r.estimated_cost_usd for r in records)
            calls        = len(records)

        rows = [_Row(k, v) for k, v in sorted_groups[:50]]
        return self._format_report(rows, _Total(), agent_id, days_back, group_by)

    @staticmethod
    def _format_report(rows, total_row, agent_id, days_back, group_by) -> str:
        """Render report rows as a fixed-width ASCII table."""
        header = (
            f"OK LLM Cost Report -- last {days_back} day(s)"
            + (f", agent: {agent_id}" if agent_id else ", all agents")
            + f", grouped by: {group_by}"
        )

        sep = "-" * 72
        col_hdr = (
            f"{'Group':<30} {'Calls':>6} {'In-Tok':>9} {'Out-Tok':>9} {'USD':>10}"
        )
        lines = [header, "", col_hdr, sep]

        for row in rows:
            key  = str(getattr(row, "group_key", "?") or "?")
            if len(key) > 30:
                key = key[:27] + "..."
            lines.append(
                f"{key:<30} "
                f"{int(getattr(row, 'calls', 0)):>6} "
                f"{int(getattr(row, 'total_input', 0)):>9,} "
                f"{int(getattr(row, 'total_output', 0)):>9,} "
                f"{float(getattr(row, 'total_cost', 0)):>10.6f}"
            )

        lines.append(sep)
        if total_row:
            lines.append(
                f"{'TOTAL':<30} "
                f"{int(getattr(total_row, 'calls', 0)):>6} "
                f"{int(getattr(total_row, 'total_input', 0)):>9,} "
                f"{int(getattr(total_row, 'total_output', 0)):>9,} "
                f"{float(getattr(total_row, 'total_cost', 0)):>10.6f}"
            )

        if not rows:
            lines += [
                "",
                "  (No LLM usage recorded in this period)",
                "",
                "INFO Usage is recorded automatically when tools that invoke an LLM",
                "     are called (cognify, recall, improve, intelligent_summarize, etc.).",
                "INFO If PostgreSQL is unavailable, usage is stored in an in-memory",
                "     ring buffer and will be lost on server restart.",
            ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Public API: budget management
    # ------------------------------------------------------------------

    async def set_budget(self, agent_id: str, monthly_usd: float) -> str:
        """
        Set the monthly LLM cost budget for an agent.

        Use '*' as agent_id to set a global default that applies to any
        agent without a specific budget.

        Args:
            agent_id:    Agent identifier or '*' for global default.
            monthly_usd: Monthly spending ceiling in USD.

        Returns:
            ASCII confirmation string.
        """
        self._budgets[agent_id] = monthly_usd

        if self.postgres_pool:
            try:
                async with self.postgres_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO shared_memory.llm_budgets
                            (agent_id, monthly_usd, updated_at)
                        VALUES ($1, $2, NOW())
                        ON CONFLICT (agent_id) DO UPDATE
                            SET monthly_usd = EXCLUDED.monthly_usd,
                                updated_at  = NOW()
                        """,
                        agent_id,
                        monthly_usd,
                    )
                return (
                    f"OK Budget set: agent='{agent_id}' "
                    f"monthly_usd={monthly_usd:.2f} (persisted to DB)"
                )
            except Exception as exc:
                return (
                    f"WARN Budget set in memory only "
                    f"(DB persist failed: {exc})"
                )

        return (
            f"OK Budget set: agent='{agent_id}' "
            f"monthly_usd={monthly_usd:.2f} (in-memory only -- no DB)"
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_cost_tracker: Optional[LLMCostTracker] = None


def get_cost_tracker() -> Optional[LLMCostTracker]:
    """Return the global LLMCostTracker instance (None if not initialized)."""
    return _cost_tracker


def init_cost_tracker(postgres_pool=None) -> LLMCostTracker:
    """
    Create and register the global LLMCostTracker.

    Call this once at server startup, before registering the LiteLLM
    callback (which happens inside tracker.initialize()).

    Args:
        postgres_pool: asyncpg connection pool (None = in-memory only).

    Returns:
        The newly created LLMCostTracker instance.
    """
    global _cost_tracker
    _cost_tracker = LLMCostTracker(postgres_pool=postgres_pool)
    return _cost_tracker
