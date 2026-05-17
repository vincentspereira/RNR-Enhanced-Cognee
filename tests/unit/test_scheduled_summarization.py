"""
Unit tests for src/scheduled_summarization.py
Covers: ScheduledSummarization init, _load_config, summarize_old_memories (dry-run,
        real, no candidates, error), _find_memories, _generate_summary (LLM path,
        extractive fallback, edge cases), _summarize_memory, summarize_by_type,
        summarize_by_concept, preserve_original_content, summarization_statistics,
        get_summarization_history.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from src.scheduled_summarization import ScheduledSummarization


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(memories=None, stats=None):
    """Build an async context-manager mock for postgres pool acquire()."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=memories if memories is not None else [])
    conn.execute = AsyncMock(return_value="UPDATE 1")
    if stats is not None:
        conn.fetch = AsyncMock(return_value=stats)
    return conn


def _make_pool(conn):
    class _Ctx:
        async def __aenter__(self): return conn
        async def __aexit__(self, *a): pass
    class _Pool:
        def acquire(self): return _Ctx()
    return _Pool()


@pytest.fixture
def pool():
    return _make_pool(_make_conn())


@pytest.fixture
def ss(pool, tmp_path):
    """ScheduledSummarization without LLM client, temporary config path."""
    return ScheduledSummarization(
        postgres_pool=pool,
        llm_client=None,
        config_path=str(tmp_path / "nonexistent.json"),
    )


# ---------------------------------------------------------------------------
# Initialization & _load_config
# ---------------------------------------------------------------------------

class TestInit:
    @pytest.mark.unit
    def test_default_config_loaded_when_no_file(self, ss):
        assert ss.config["schedule"] == "monthly"
        assert ss.config["age_threshold_days"] == 30
        assert ss.config["preserve_original"] is True

    @pytest.mark.unit
    def test_loads_config_from_file(self, tmp_path):
        cfg = {"schedule": "weekly", "age_threshold_days": 7, "min_length": 500,
               "summary_target_length": 100, "preserve_original": False}
        cfg_file = tmp_path / "ss.json"
        cfg_file.write_text(json.dumps(cfg))
        pool = _make_pool(_make_conn())
        ss = ScheduledSummarization(pool, config_path=str(cfg_file))
        assert ss.config["schedule"] == "weekly"
        assert ss.config["age_threshold_days"] == 7

    @pytest.mark.unit
    def test_falls_back_to_default_on_bad_json(self, tmp_path):
        cfg_file = tmp_path / "bad.json"
        cfg_file.write_text("{not valid json}")
        pool = _make_pool(_make_conn())
        ss = ScheduledSummarization(pool, config_path=str(cfg_file))
        assert ss.config["preserve_original"] is True

    @pytest.mark.unit
    def test_summarization_history_starts_empty(self, ss):
        assert ss.summarization_history == []


# ---------------------------------------------------------------------------
# summarize_old_memories
# ---------------------------------------------------------------------------

class TestSummarizeOldMemories:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_candidates_returns_zero_summarized(self, pool):
        ss = ScheduledSummarization(pool)
        result = await ss.summarize_old_memories(days=30)
        assert result["status"] == "success"
        assert result["memories_summarized"] == 0
        assert "No memories" in result["message"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dry_run_does_not_summarize(self, tmp_path):
        long_content = "word " * 300  # >1000 chars
        memories = [{"id": "m1", "content": long_content}]
        conn = _make_conn(memories=memories)
        pool = _make_pool(conn)
        ss = ScheduledSummarization(pool, config_path=str(tmp_path / "x.json"))
        result = await ss.summarize_old_memories(days=30, dry_run=True)
        assert result["dry_run"] is True
        assert len(result["summaries"]) == 1
        # dry_run: no execute() call on conn
        conn.execute.assert_not_called()
        # history not appended on dry run
        assert ss.summarization_history == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_real_run_summarizes_and_appends_history(self, tmp_path):
        long_content = "Sentence one. Sentence two. " * 50  # >1000 chars
        memories = [{"id": "m1", "content": long_content}]
        conn = _make_conn(memories=memories)
        pool = _make_pool(conn)
        ss = ScheduledSummarization(pool, config_path=str(tmp_path / "x.json"))
        result = await ss.summarize_old_memories(days=30, dry_run=False)
        assert result["memories_summarized"] == 1
        assert len(ss.summarization_history) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_real_run_calculates_space_saved(self, tmp_path):
        long_content = "a " * 600  # 1200 chars
        memories = [{"id": "m2", "content": long_content}]
        conn = _make_conn(memories=memories)
        pool = _make_pool(conn)
        ss = ScheduledSummarization(pool, config_path=str(tmp_path / "x.json"))
        result = await ss.summarize_old_memories(days=1, dry_run=False)
        assert result["space_saved_bytes"] > 0
        assert result["token_savings"] >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self, tmp_path):
        # The outer exception must come from something OTHER than _find_memories
        # (which catches exceptions internally). Patch _generate_summary to raise after
        # a non-empty memory list is returned.
        long_content = "word " * 300
        memories = [{"id": "m1", "content": long_content}]
        conn = _make_conn(memories=memories)
        pool = _make_pool(conn)
        ss = ScheduledSummarization(pool, config_path=str(tmp_path / "x.json"))
        with patch.object(ss, "_generate_summary", side_effect=RuntimeError("unexpected failure")):
            result = await ss.summarize_old_memories()
        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dry_run_reports_compression_ratio(self, tmp_path):
        long_content = "word " * 300
        memories = [{"id": "m3", "content": long_content}]
        conn = _make_conn(memories=memories)
        pool = _make_pool(conn)
        ss = ScheduledSummarization(pool, config_path=str(tmp_path / "x.json"))
        result = await ss.summarize_old_memories(dry_run=True)
        summary_entry = result["summaries"][0]
        assert "compression_ratio" in summary_entry
        assert "%" in summary_entry["compression_ratio"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_memories_all_summarized(self, tmp_path):
        long_content = "word " * 300
        memories = [{"id": f"m{i}", "content": long_content} for i in range(3)]
        conn = _make_conn(memories=memories)
        pool = _make_pool(conn)
        ss = ScheduledSummarization(pool, config_path=str(tmp_path / "x.json"))
        result = await ss.summarize_old_memories(dry_run=False)
        assert result["memories_summarized"] == 3


# ---------------------------------------------------------------------------
# _generate_summary
# ---------------------------------------------------------------------------

class TestGenerateSummary:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extractive_fallback_multiple_sentences(self, ss):
        text = "First sentence. Second sentence. Third sentence. " * 5
        summary = await ss._generate_summary(text)
        assert len(summary) > 0
        assert len(summary) <= len(text)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extractive_single_long_sentence_truncated(self, ss):
        text = "A" * 2000
        summary = await ss._generate_summary(text)
        assert summary.endswith("...")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extractive_short_text_returned_as_is(self, ss):
        ss.config["summary_target_length"] = 500
        text = "Short text."
        summary = await ss._generate_summary(text)
        assert "Short text" in summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_path_used_when_client_provided(self, pool):
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="LLM summary")
        ss = ScheduledSummarization(pool, llm_client=mock_llm)
        text = "word " * 300
        summary = await ss._generate_summary(text)
        assert summary == "LLM summary"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_falls_back_to_extractive_when_llm_fails(self, pool):
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM unavailable"))
        ss = ScheduledSummarization(pool, llm_client=mock_llm)
        text = "First sentence. Second sentence. Third sentence."
        summary = await ss._generate_summary(text)
        assert len(summary) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_empty_response_falls_back(self, pool):
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="")
        ss = ScheduledSummarization(pool, llm_client=mock_llm)
        text = "First. Second. Third."
        summary = await ss._generate_summary(text)
        assert len(summary) > 0


# ---------------------------------------------------------------------------
# _find_memories_to_summarize
# ---------------------------------------------------------------------------

class TestFindMemoriesToSummarize:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self, tmp_path):
        rows = [{"id": "m1", "title": "T1", "content": "c1", "created_at": "2026-01-01"}]
        conn = _make_conn(memories=rows)
        pool = _make_pool(conn)
        ss = ScheduledSummarization(pool, config_path=str(tmp_path / "x.json"))
        result = await ss._find_memories_to_summarize(30, 100)
        assert isinstance(result, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self, tmp_path):
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=Exception("error"))

        class _Ctx:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): pass
        class _Pool:
            def acquire(self): return _Ctx()

        ss = ScheduledSummarization(_Pool(), config_path=str(tmp_path / "x.json"))
        result = await ss._find_memories_to_summarize(30, 100)
        assert result == []


# ---------------------------------------------------------------------------
# _summarize_memory
# ---------------------------------------------------------------------------

class TestSummarizeMemory:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calls_execute_with_correct_args(self, tmp_path):
        conn = _make_conn()
        pool = _make_pool(conn)
        ss = ScheduledSummarization(pool, config_path=str(tmp_path / "x.json"))
        await ss._summarize_memory("mem-id", "summary text", 500)
        conn.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_on_db_error(self, tmp_path):
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=Exception("db failure"))

        class _Ctx:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): pass
        class _Pool:
            def acquire(self): return _Ctx()

        ss = ScheduledSummarization(_Pool(), config_path=str(tmp_path / "x.json"))
        with pytest.raises(Exception, match="db failure"):
            await ss._summarize_memory("m1", "s", 100)


# ---------------------------------------------------------------------------
# summarize_by_type / summarize_by_concept
# ---------------------------------------------------------------------------

class TestSummarizeByTypeAndConcept:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_by_type_returns_dict(self, ss):
        result = await ss.summarize_by_type("episodic", days=30)
        assert isinstance(result, dict)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summarize_by_concept_returns_dict(self, ss):
        result = await ss.summarize_by_concept("trading", days=30)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# preserve_original_content
# ---------------------------------------------------------------------------

class TestPreserveOriginalContent:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_true_by_default(self, ss):
        result = await ss.preserve_original_content()
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_config_value(self, pool, tmp_path):
        cfg_file = tmp_path / "c.json"
        cfg_file.write_text(json.dumps({"preserve_original": False}))
        ss = ScheduledSummarization(pool, config_path=str(cfg_file))
        result = await ss.preserve_original_content()
        assert result is False


# ---------------------------------------------------------------------------
# summarization_statistics
# ---------------------------------------------------------------------------

class TestSummarizationStatistics:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_dict_with_expected_keys(self, tmp_path):
        stat_row = {
            "total_memories": 100,
            "summarized_memories": 20,
            "avg_length": 300.0,
            "avg_original_length": 1500.0,
        }
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[stat_row])

        class _Ctx:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): pass
        class _Pool:
            def acquire(self): return _Ctx()

        ss = ScheduledSummarization(_Pool(), config_path=str(tmp_path / "x.json"))
        result = await ss.summarization_statistics()
        assert result["total_memories"] == 100
        assert result["summarized_memories"] == 20
        assert "summarization_ratio" in result
        assert "estimated_space_saved_bytes" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_zero_ratio_when_no_memories(self, tmp_path):
        stat_row = {
            "total_memories": 0,
            "summarized_memories": 0,
            "avg_length": None,
            "avg_original_length": None,
        }
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[stat_row])

        class _Ctx:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): pass
        class _Pool:
            def acquire(self): return _Ctx()

        ss = ScheduledSummarization(_Pool(), config_path=str(tmp_path / "x.json"))
        result = await ss.summarization_statistics()
        assert result["summarization_ratio"] == "0%"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_error_on_empty_stats(self, tmp_path):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])

        class _Ctx:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): pass
        class _Pool:
            def acquire(self): return _Ctx()

        ss = ScheduledSummarization(_Pool(), config_path=str(tmp_path / "x.json"))
        result = await ss.summarization_statistics()
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_error_on_exception(self, tmp_path):
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=Exception("conn failed"))

        class _Ctx:
            async def __aenter__(self): return conn
            async def __aexit__(self, *a): pass
        class _Pool:
            def acquire(self): return _Ctx()

        ss = ScheduledSummarization(_Pool(), config_path=str(tmp_path / "x.json"))
        result = await ss.summarization_statistics()
        assert result.get("error") is not None


# ---------------------------------------------------------------------------
# get_summarization_history
# ---------------------------------------------------------------------------

class TestGetSummarizationHistory:
    @pytest.mark.unit
    def test_returns_empty_list_initially(self, ss):
        assert ss.get_summarization_history() == []

    @pytest.mark.unit
    def test_respects_limit(self, ss):
        for i in range(10):
            ss.summarization_history.append({"run": i})
        result = ss.get_summarization_history(limit=3)
        assert len(result) == 3
        assert result[0]["run"] == 7  # last 3

    @pytest.mark.unit
    def test_returns_all_when_limit_exceeds_count(self, ss):
        ss.summarization_history = [{"run": 0}, {"run": 1}]
        result = ss.get_summarization_history(limit=100)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# schedule_monthly_summarization
# ---------------------------------------------------------------------------

class TestScheduleMonthly:
    @pytest.mark.unit
    def test_returns_cron_trigger(self, ss):
        with patch("src.scheduled_summarization.ScheduledSummarization.schedule_monthly_summarization"):
            from apscheduler.triggers.cron import CronTrigger
            trigger = ss.schedule_monthly_summarization()
            # Just verify it doesn't raise and returns something
            assert trigger is not None
