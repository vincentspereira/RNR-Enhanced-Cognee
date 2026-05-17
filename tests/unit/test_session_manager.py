"""
Unit tests for src.session_manager
=====================================
Tests SessionManager and ContextInjector.
All database calls are mocked via asyncpg pool mocks.
No real DB connections. No Unicode characters.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool():
    """Build a minimal asyncpg pool mock."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])

    class MockAcquireCtx:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=MockAcquireCtx())
    return mock_pool, mock_conn


def _make_session_row(session_id="sess-1", user_id="default", agent_id="claude-code",
                      end_time=None, summary=None, metadata="{}"):
    """Create a mock session row dict."""
    now = datetime.now(timezone.utc)
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "id": session_id,
        "user_id": user_id,
        "agent_id": agent_id,
        "start_time": now,
        "end_time": end_time,
        "summary": summary,
        "metadata": metadata,
        "created_at": now,
        "updated_at": now,
    }[key]
    return row


def _make_stat_row(total_sessions=5, active_sessions=1, completed_sessions=4,
                   avg_duration_minutes=30.0, last_session_start=None):
    now = datetime.now(timezone.utc)
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "completed_sessions": completed_sessions,
        "avg_duration_minutes": avg_duration_minutes,
        "last_session_start": last_session_start or now,
    }[key]
    return row


# ---------------------------------------------------------------------------
# SessionManager.start_session
# ---------------------------------------------------------------------------

class TestStartSession:
    async def test_start_returns_uuid_string(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()
        assert isinstance(session_id, str)
        # Should look like a UUID
        assert len(session_id) == 36

    async def test_start_inserts_into_db(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        await mgr.start_session(user_id="user-1", agent_id="agent-1")
        conn.execute.assert_called_once()
        args = conn.execute.call_args[0]
        assert "user-1" in args
        assert "agent-1" in args

    async def test_start_caches_session(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()
        assert session_id in mgr.active_sessions

    async def test_start_with_metadata(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        metadata = {"project": "test", "version": 1}
        session_id = await mgr.start_session(metadata=metadata)
        cached = mgr.active_sessions[session_id]
        assert cached["metadata"] == metadata

    async def test_start_stores_user_and_agent(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session(user_id="test-user", agent_id="test-agent")
        cached = mgr.active_sessions[session_id]
        assert cached["user_id"] == "test-user"
        assert cached["agent_id"] == "test-agent"


# ---------------------------------------------------------------------------
# SessionManager.end_session
# ---------------------------------------------------------------------------

class TestEndSession:
    async def test_end_nonexistent_returns_error(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        # get_session will return None
        conn.fetchrow = AsyncMock(return_value=None)
        result = await mgr.end_session("no-such-session")
        assert "error" in result

    async def test_end_already_ended_returns_session(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)

        now = datetime.now(timezone.utc)
        row = _make_session_row(session_id="s-1", end_time=now)
        conn.fetchrow = AsyncMock(return_value=row)

        result = await mgr.end_session("s-1")
        # Should return the session (already ended)
        assert result.get("end_time") is not None

    async def test_end_active_session(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)

        # Set up a session in the cache
        session_id = await mgr.start_session()

        # When end_session calls get_session, it should check cache first,
        # then the DB update call
        row_no_end = _make_session_row(session_id=session_id)
        row_with_end = _make_session_row(session_id=session_id, end_time=datetime.now(timezone.utc))
        # First call returns no end_time (active), second call returns with end_time
        conn.fetchrow = AsyncMock(side_effect=[row_no_end, row_with_end])

        result = await mgr.end_session(session_id)
        # execute should have been called for start + end
        assert conn.execute.call_count >= 2
        # Session removed from cache
        assert session_id not in mgr.active_sessions

    async def test_end_with_summary_provided(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)

        row = _make_session_row(session_id="s-2")
        row_end = _make_session_row(session_id="s-2", end_time=datetime.now(timezone.utc))
        conn.fetchrow = AsyncMock(side_effect=[row, row_end])

        await mgr.end_session("s-2", summary="Session summary text")
        # Should call execute with the summary text
        execute_call = conn.execute.call_args_list[-1][0]
        assert "Session summary text" in execute_call

    async def test_end_generates_summary_when_llm_client_set(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()

        mock_llm = AsyncMock()
        mock_llm.summarize = AsyncMock(return_value="Generated summary")
        mgr = SessionManager(db_pool=pool, llm_client=mock_llm)

        session_id = await mgr.start_session()  # session now in cache

        row = _make_session_row(session_id=session_id)
        row_end = _make_session_row(session_id=session_id, end_time=datetime.now(timezone.utc))
        # First fetchrow for get_session (at end_time check) - returns active session
        # Second fetchrow for get_session (return after update) - returns ended session
        conn.fetchrow = AsyncMock(side_effect=[row, row_end])
        conn.fetch = AsyncMock(return_value=[])  # empty memories

        await mgr.end_session(session_id)
        # With empty memories, summary = "Empty session - no memories to summarize"
        # summarize() should NOT be called
        mock_llm.summarize.assert_not_called()


# ---------------------------------------------------------------------------
# SessionManager.get_session
# ---------------------------------------------------------------------------

class TestGetSession:
    async def test_get_session_from_cache(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()
        # Should return from cache without DB call
        result = await mgr.get_session(session_id)
        assert result is not None
        assert result["session_id"] == session_id

    async def test_get_session_from_db(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        row = _make_session_row(session_id="db-sess", user_id="u1")
        conn.fetchrow = AsyncMock(return_value=row)
        result = await mgr.get_session("db-sess")
        assert result is not None
        assert result["user_id"] == "u1"

    async def test_get_session_not_found_returns_none(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        conn.fetchrow = AsyncMock(return_value=None)
        result = await mgr.get_session("missing-sess")
        assert result is None

    async def test_get_session_parses_metadata(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        row = _make_session_row(metadata='{"key": "value"}')
        conn.fetchrow = AsyncMock(return_value=row)
        result = await mgr.get_session("s-meta")
        assert result["metadata"] == {"key": "value"}

    async def test_get_session_end_time_none(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        row = _make_session_row(end_time=None)
        conn.fetchrow = AsyncMock(return_value=row)
        result = await mgr.get_session("s-active")
        assert result["end_time"] is None


# ---------------------------------------------------------------------------
# SessionManager.get_session_context
# ---------------------------------------------------------------------------

class TestGetSessionContext:
    async def test_context_not_found_returns_error(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        conn.fetchrow = AsyncMock(return_value=None)
        result = await mgr.get_session_context("no-sess")
        assert "error" in result

    async def test_context_without_memories(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()
        conn.fetch = AsyncMock(return_value=[])
        result = await mgr.get_session_context(session_id, include_memories=False)
        assert "session" in result
        assert result["memories"] == []

    async def test_context_with_memories(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()

        now = datetime.now(timezone.utc)
        mem_row = MagicMock()
        mem_row.__getitem__ = lambda self, key: {
            "id": "mem-1",
            "data_text": "test memory content",
            "data_type": "text",
            "created_at": now,
            "metadata": "{}"
        }[key]
        conn.fetch = AsyncMock(return_value=[mem_row])

        result = await mgr.get_session_context(session_id, include_memories=True)
        assert len(result["memories"]) == 1
        assert result["memories"][0]["content"] == "test memory content"

    async def test_context_with_limit(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()
        conn.fetch = AsyncMock(return_value=[])

        await mgr.get_session_context(session_id, include_memories=True, limit=5)
        query_call = conn.fetch.call_args[0][0]
        assert "5" in query_call  # LIMIT 5 appended


# ---------------------------------------------------------------------------
# SessionManager.get_recent_sessions
# ---------------------------------------------------------------------------

class TestGetRecentSessions:
    async def test_returns_list_of_sessions(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        row = _make_session_row()
        conn.fetch = AsyncMock(return_value=[row])
        result = await mgr.get_recent_sessions()
        assert len(result) == 1

    async def test_active_only_filter(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        conn.fetch = AsyncMock(return_value=[])
        await mgr.get_recent_sessions(active_only=True)
        query = conn.fetch.call_args[0][0]
        assert "NULL" in query  # end_time IS NULL

    async def test_empty_result_returns_empty_list(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        conn.fetch = AsyncMock(return_value=[])
        result = await mgr.get_recent_sessions()
        assert result == []


# ---------------------------------------------------------------------------
# SessionManager.get_active_session
# ---------------------------------------------------------------------------

class TestGetActiveSession:
    async def test_returns_session_id_when_active(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        row = _make_session_row(session_id="active-1")
        conn.fetch = AsyncMock(return_value=[row])
        result = await mgr.get_active_session()
        assert result == "active-1"

    async def test_returns_none_when_no_active_sessions(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        conn.fetch = AsyncMock(return_value=[])
        result = await mgr.get_active_session()
        assert result is None


# ---------------------------------------------------------------------------
# SessionManager.add_memory_to_session
# ---------------------------------------------------------------------------

class TestAddMemoryToSession:
    async def test_add_memory_returns_true_on_success(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        result = await mgr.add_memory_to_session("sess-1", "mem-1")
        assert result is True
        conn.execute.assert_called_once()

    async def test_add_memory_returns_false_on_exception(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        conn.execute = AsyncMock(side_effect=Exception("DB error"))
        mgr = SessionManager(db_pool=pool)
        result = await mgr.add_memory_to_session("sess-1", "mem-1")
        assert result is False


# ---------------------------------------------------------------------------
# SessionManager.generate_session_summary
# ---------------------------------------------------------------------------

class TestGenerateSessionSummary:
    async def test_no_llm_client_returns_none(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        result = await mgr.generate_session_summary("sess-1")
        assert result is None

    async def test_empty_memories_returns_empty_message(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        mock_llm = AsyncMock()
        mgr = SessionManager(db_pool=pool, llm_client=mock_llm)

        session_id = await mgr.start_session()
        conn.fetch = AsyncMock(return_value=[])

        result = await mgr.generate_session_summary(session_id)
        assert "Empty session" in result

    async def test_with_memories_calls_llm(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()

        mock_llm = AsyncMock()
        mock_llm.summarize = AsyncMock(return_value="Summary text")
        mgr = SessionManager(db_pool=pool, llm_client=mock_llm)

        session_id = await mgr.start_session()

        now = datetime.now(timezone.utc)
        mem_row = MagicMock()
        mem_row.__getitem__ = lambda self, key: {
            "id": "m-1",
            "data_text": "important memory",
            "data_type": "text",
            "created_at": now,
            "metadata": "{}"
        }[key]
        conn.fetch = AsyncMock(return_value=[mem_row])

        result = await mgr.generate_session_summary(session_id)
        mock_llm.summarize.assert_called_once()
        assert result == "Summary text"

    async def test_llm_exception_returns_none(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()

        mock_llm = AsyncMock()
        mock_llm.summarize = AsyncMock(side_effect=Exception("LLM error"))
        mgr = SessionManager(db_pool=pool, llm_client=mock_llm)

        session_id = await mgr.start_session()

        now = datetime.now(timezone.utc)
        mem_row = MagicMock()
        mem_row.__getitem__ = lambda self, key: {
            "id": "m-1",
            "data_text": "content",
            "data_type": "text",
            "created_at": now,
            "metadata": "{}"
        }[key]
        conn.fetch = AsyncMock(return_value=[mem_row])

        result = await mgr.generate_session_summary(session_id)
        assert result is None


# ---------------------------------------------------------------------------
# SessionManager.cleanup_stale_sessions
# ---------------------------------------------------------------------------

class TestCleanupStaleSessions:
    async def test_cleanup_returns_count(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        conn.execute = AsyncMock(return_value="UPDATE 3")
        mgr = SessionManager(db_pool=pool)
        count = await mgr.cleanup_stale_sessions(max_age_hours=24)
        assert count == 3

    async def test_cleanup_returns_zero_when_no_match(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        conn.execute = AsyncMock(return_value="UPDATE 0")
        mgr = SessionManager(db_pool=pool)
        count = await mgr.cleanup_stale_sessions()
        assert count == 0

    async def test_cleanup_handles_non_numeric_result(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        conn.execute = AsyncMock(return_value="UPDATE")
        mgr = SessionManager(db_pool=pool)
        count = await mgr.cleanup_stale_sessions()
        assert count == 0  # ValueError caught -> 0


# ---------------------------------------------------------------------------
# SessionManager.get_session_stats
# ---------------------------------------------------------------------------

class TestGetSessionStats:
    async def test_stats_returns_dict(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        row = _make_stat_row()
        conn.fetchrow = AsyncMock(return_value=row)
        mgr = SessionManager(db_pool=pool)
        stats = await mgr.get_session_stats()
        assert "total_sessions" in stats
        assert "active_sessions" in stats
        assert "completed_sessions" in stats
        assert "avg_duration_minutes" in stats

    async def test_stats_null_avg_duration_defaults_to_zero(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        row = _make_stat_row(avg_duration_minutes=None)
        conn.fetchrow = AsyncMock(return_value=row)
        mgr = SessionManager(db_pool=pool)
        stats = await mgr.get_session_stats()
        assert stats["avg_duration_minutes"] == 0.0

    async def test_stats_null_last_session_start_is_none(self):
        from src.session_manager import SessionManager
        pool, conn = _make_pool()
        # Build row dict directly
        row = {
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
            "avg_duration_minutes": None,
            "last_session_start": None,
        }
        conn.fetchrow = AsyncMock(return_value=row)
        mgr = SessionManager(db_pool=pool)
        stats = await mgr.get_session_stats()
        assert stats["last_session_start"] is None


# ---------------------------------------------------------------------------
# ContextInjector
# ---------------------------------------------------------------------------

class TestContextInjector:
    async def test_inject_context_no_session_returns_empty(self):
        from src.session_manager import SessionManager, ContextInjector
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        conn.fetchrow = AsyncMock(return_value=None)
        injector = ContextInjector(mgr)
        result = await injector.inject_context("no-sess")
        assert result == ""

    async def test_inject_context_no_memories_returns_empty(self):
        from src.session_manager import SessionManager, ContextInjector
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()
        conn.fetch = AsyncMock(return_value=[])
        injector = ContextInjector(mgr)
        result = await injector.inject_context(session_id)
        assert result == ""

    async def test_inject_context_with_memories(self):
        from src.session_manager import SessionManager, ContextInjector
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()

        now = datetime.now(timezone.utc)
        mem_row = MagicMock()
        mem_row.__getitem__ = lambda self, key: {
            "id": "m-1",
            "data_text": "test content",
            "data_type": "text",
            "created_at": now,
            "metadata": "{}"
        }[key]
        conn.fetch = AsyncMock(return_value=[mem_row])

        injector = ContextInjector(mgr)
        result = await injector.inject_context(session_id)
        assert "<context>" in result
        assert session_id in result
        assert "test content" in result

    async def test_inject_context_token_limit_respected(self):
        from src.session_manager import SessionManager, ContextInjector
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        session_id = await mgr.start_session()

        now = datetime.now(timezone.utc)
        # Create a very large memory that would exceed token limit
        large_content = "x" * 500

        def make_row(idx):
            r = MagicMock()
            r.__getitem__ = lambda self, key: {
                "id": f"m-{idx}",
                "data_text": large_content,
                "data_type": "text",
                "created_at": now,
                "metadata": "{}"
            }[key]
            return r

        # 1000 memories, each with 500 chars
        conn.fetch = AsyncMock(return_value=[make_row(i) for i in range(1000)])

        injector = ContextInjector(mgr)
        # max_tokens=10 -> very small budget
        result = await injector.inject_context(session_id, max_tokens=10)
        # Should have stopped adding memories early
        assert "<context>" in result
        # Should have far fewer than 1000 memories
        memory_count = result.count("<memory")
        assert memory_count < 100

    async def test_inject_recent_context_no_sessions(self):
        from src.session_manager import SessionManager, ContextInjector
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)
        conn.fetch = AsyncMock(return_value=[])
        injector = ContextInjector(mgr)
        result = await injector.inject_recent_context()
        assert result == ""

    async def test_inject_recent_context_with_sessions(self):
        from src.session_manager import SessionManager, ContextInjector
        pool, conn = _make_pool()
        mgr = SessionManager(db_pool=pool)

        session_id = "old-sess-unique-1"
        session_row = _make_session_row(session_id=session_id)
        # Cache the session so get_session finds it from cache
        now = datetime.now(timezone.utc)
        mgr.active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": "default",
            "agent_id": "claude-code",
            "start_time": now.isoformat(),
            "metadata": {}
        }

        now = datetime.now(timezone.utc)
        mem_row = MagicMock()
        mem_row.__getitem__ = lambda self, key: {
            "id": "m-1",
            "data_text": "past memory content",
            "data_type": "text",
            "created_at": now,
            "metadata": "{}"
        }[key]

        # inject_recent_context:
        #   1. get_recent_sessions -> conn.fetch returns [session_row]
        #   2. get_session_context memories -> conn.fetch returns [mem_row]
        conn.fetch = AsyncMock(side_effect=[[session_row], [mem_row]])

        injector = ContextInjector(mgr)
        result = await injector.inject_recent_context()
        assert "<recent_sessions>" in result
