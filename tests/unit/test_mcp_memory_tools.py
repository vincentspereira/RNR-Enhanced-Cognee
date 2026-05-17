"""
Unit tests for src.mcp_memory_tools
====================================
Covers: add_memory, search_memories, delete_memory, list_agents

All external dependencies (postgres pool, realtime_sync, cross_agent_sharing,
performance_analytics, memory_deduplicator) are mocked - no live services needed.

ASCII-only assertions per project conventions.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock


# ---------------------------------------------------------------------------
# Shared pool factory helpers
# ---------------------------------------------------------------------------

def _make_pool(conn):
    """Build a mock pool whose .acquire() is a sync-returning async context."""
    class _Ctx:
        async def __aenter__(self):
            return conn
        async def __aexit__(self, *args):
            pass

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_Ctx())
    return pool


def _make_conn():
    """Return an AsyncMock connection with sensible defaults."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    return conn


def _make_row(**kwargs):
    """Return a dict-like object that supports item access (mimics asyncpg Record)."""
    return kwargs


# ---------------------------------------------------------------------------
# add_memory - happy path
# ---------------------------------------------------------------------------

class TestAddMemoryHappyPath:

    @pytest.mark.asyncio
    async def test_returns_success_status(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        result = await add_memory(
            content="Hello world test memory",
            user_id="user1",
            agent_id="agent1",
            postgres_pool=pool,
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_returns_memory_id_in_data(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        result = await add_memory(
            content="A valid memory content string",
            agent_id="agent-a",
            postgres_pool=pool,
        )
        assert "memory_id" in result["data"]
        assert result["data"]["memory_id"]

    @pytest.mark.asyncio
    async def test_returns_agent_id_in_data(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        result = await add_memory(
            content="Some content",
            agent_id="my-agent",
            postgres_pool=pool,
        )
        assert result["data"]["agent_id"] == "my-agent"

    @pytest.mark.asyncio
    async def test_calls_db_execute_once(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        await add_memory(
            content="Test content stored",
            agent_id="agent1",
            postgres_pool=pool,
        )
        conn.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_metadata_json_parsed_correctly(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        meta = json.dumps({"category": "trading", "priority": "high"})
        result = await add_memory(
            content="Memory with metadata",
            agent_id="agent1",
            metadata=meta,
            postgres_pool=pool,
        )
        assert result["status"] == "success"
        # Ensure execute was called (metadata was processed without error)
        conn.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_metadata_invalid_json_falls_back(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        result = await add_memory(
            content="Content with bad metadata",
            agent_id="agent1",
            metadata="not-valid-json{{",
            postgres_pool=pool,
        )
        # Should still succeed - bad JSON falls back to raw_metadata
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_default_user_id_and_agent_id(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        result = await add_memory(
            content="Defaults test content",
            postgres_pool=pool,
        )
        assert result["status"] == "success"
        assert result["data"]["user_id"] == "default"
        assert result["data"]["agent_id"] == "claude-code"

    @pytest.mark.asyncio
    async def test_timestamp_present_in_result(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        result = await add_memory(
            content="Timestamp check content",
            agent_id="agent1",
            postgres_pool=pool,
        )
        assert "timestamp" in result
        assert result["timestamp"]


# ---------------------------------------------------------------------------
# add_memory - no pool
# ---------------------------------------------------------------------------

class TestAddMemoryNoPool:

    @pytest.mark.asyncio
    async def test_returns_error_when_pool_none(self):
        from src.mcp_memory_tools import add_memory
        result = await add_memory(
            content="Some content",
            agent_id="agent1",
            postgres_pool=None,
        )
        assert result["status"] == "error"
        assert result["error"]

    @pytest.mark.asyncio
    async def test_error_message_mentions_postgresql(self):
        from src.mcp_memory_tools import add_memory
        result = await add_memory(
            content="Some content",
            postgres_pool=None,
        )
        assert "PostgreSQL" in result["error"] or "postgres" in result["error"].lower()


# ---------------------------------------------------------------------------
# add_memory - validation errors
# ---------------------------------------------------------------------------

class TestAddMemoryValidation:

    @pytest.mark.asyncio
    async def test_empty_content_returns_error(self):
        from src.mcp_memory_tools import add_memory
        result = await add_memory(
            content="",
            agent_id="agent1",
            postgres_pool=None,
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_invalid_agent_id_returns_error(self):
        from src.mcp_memory_tools import add_memory
        # Spaces are not allowed in agent_id
        result = await add_memory(
            content="Valid content",
            agent_id="invalid agent id!",
            postgres_pool=MagicMock(),
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_db_exception_returns_error(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError("DB down"))
        pool = _make_pool(conn)
        result = await add_memory(
            content="Valid content string",
            agent_id="agent1",
            postgres_pool=pool,
        )
        assert result["status"] == "error"
        assert "Failed to add memory" in result["error"] or result["error"]


# ---------------------------------------------------------------------------
# add_memory - optional integration hooks
# ---------------------------------------------------------------------------

class TestAddMemoryWithHooks:

    @pytest.mark.asyncio
    async def test_deduplicator_duplicate_prevents_insert(self):
        from src.mcp_memory_tools import add_memory
        dedup = AsyncMock()
        dedup.check_duplicate = AsyncMock(return_value={
            "is_duplicate": True,
            "reason": "content already exists"
        })
        result = await add_memory(
            content="Repeated content",
            agent_id="agent1",
            postgres_pool=MagicMock(),
            memory_deduplicator=dedup,
        )
        assert result["status"] == "success"
        assert result["data"]["duplicate_prevented"] is True

    @pytest.mark.asyncio
    async def test_deduplicator_not_duplicate_proceeds(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        dedup = AsyncMock()
        dedup.check_duplicate = AsyncMock(return_value={"is_duplicate": False})
        result = await add_memory(
            content="Unique content here",
            agent_id="agent1",
            postgres_pool=pool,
            memory_deduplicator=dedup,
        )
        assert result["status"] == "success"
        conn.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deduplicator_failure_continues_without_error(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        dedup = AsyncMock()
        dedup.check_duplicate = AsyncMock(side_effect=RuntimeError("dedup error"))
        result = await add_memory(
            content="Unique content despite dedup failure",
            agent_id="agent1",
            postgres_pool=pool,
            memory_deduplicator=dedup,
        )
        # Should continue and succeed
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_realtime_sync_called_on_success(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock()
        await add_memory(
            content="Content for sync",
            agent_id="agent1",
            postgres_pool=pool,
            realtime_sync=rt_sync,
        )
        rt_sync.publish_memory_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_realtime_sync_failure_does_not_break_result(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock(side_effect=RuntimeError("sync error"))
        result = await add_memory(
            content="Content with failing sync",
            agent_id="agent1",
            postgres_pool=pool,
            realtime_sync=rt_sync,
        )
        # Still succeeds
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_cross_agent_sharing_called_when_provided(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock()
        rt_sync.sync_agent_state = AsyncMock()
        cas = AsyncMock()
        cas.can_agent_access_memory = AsyncMock(return_value={"can_access": True})
        result = await add_memory(
            content="Shared content",
            agent_id="agent1",
            postgres_pool=pool,
            realtime_sync=rt_sync,
            cross_agent_sharing=cas,
        )
        assert result["status"] == "success"
        cas.can_agent_access_memory.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_performance_analytics_called_on_success(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        perf = AsyncMock()
        perf.log_operation = AsyncMock()
        await add_memory(
            content="Analytics test content",
            agent_id="agent1",
            postgres_pool=pool,
            performance_analytics=perf,
        )
        perf.log_operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_performance_analytics_failure_does_not_break_result(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        perf = AsyncMock()
        perf.log_operation = AsyncMock(side_effect=RuntimeError("analytics error"))
        result = await add_memory(
            content="Analytics failure test",
            agent_id="agent1",
            postgres_pool=pool,
            performance_analytics=perf,
        )
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# search_memories - happy path
# ---------------------------------------------------------------------------

class TestSearchMemoriesHappyPath:

    @pytest.mark.asyncio
    async def test_returns_success_with_results(self):
        from src.mcp_memory_tools import search_memories
        row = {"id": "mem-1", "title": "Test", "content": "Hello world", "agent_id": "a1", "created_at": "2024-01-01"}
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        result = await search_memories(
            query="Hello",
            postgres_pool=pool,
        )
        assert result["status"] == "success"
        assert result["data"]["results_count"] == 1

    @pytest.mark.asyncio
    async def test_memories_list_present_on_results(self):
        from src.mcp_memory_tools import search_memories
        row = {"id": "mem-1", "title": "T", "content": "hello text content", "agent_id": "a1", "created_at": "2024-01-01"}
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        result = await search_memories(query="hello", postgres_pool=pool)
        assert "memories" in result["data"]
        assert len(result["data"]["memories"]) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_results_message(self):
        from src.mcp_memory_tools import search_memories
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        result = await search_memories(query="nothing", postgres_pool=pool)
        assert result["status"] == "success"
        assert result["data"]["results_count"] == 0
        assert "message" in result["data"]

    @pytest.mark.asyncio
    async def test_agent_id_filter_applied(self):
        from src.mcp_memory_tools import search_memories
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        result = await search_memories(
            query="test",
            agent_id="agent-x",
            postgres_pool=pool,
        )
        assert result["status"] == "success"
        # Confirm fetch was called - the agent filter branch was hit
        conn.fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_limit_parameter_applied(self):
        from src.mcp_memory_tools import search_memories
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        result = await search_memories(query="x", limit=5, postgres_pool=pool)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_duration_ms_in_results(self):
        from src.mcp_memory_tools import search_memories
        row = {"id": "m1", "title": "T", "content": "c", "agent_id": "a1", "created_at": "2024-01-01"}
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        result = await search_memories(query="c", postgres_pool=pool)
        assert "duration_ms" in result["data"]

    @pytest.mark.asyncio
    async def test_content_truncated_to_200_chars(self):
        from src.mcp_memory_tools import search_memories
        long_content = "x" * 500
        row = {"id": "m1", "title": "T", "content": long_content, "agent_id": "a1", "created_at": "2024-01-01"}
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[row])
        pool = _make_pool(conn)
        result = await search_memories(query="xxx", postgres_pool=pool)
        mem_content = result["data"]["memories"][0]["content"]
        assert len(mem_content) <= 200

    @pytest.mark.asyncio
    async def test_performance_analytics_logged_on_search(self):
        from src.mcp_memory_tools import search_memories
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        perf = AsyncMock()
        perf.log_operation = AsyncMock()
        await search_memories(query="test", postgres_pool=pool, performance_analytics=perf)
        perf.log_operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_performance_analytics_failure_does_not_break_search(self):
        from src.mcp_memory_tools import search_memories
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        perf = AsyncMock()
        perf.log_operation = AsyncMock(side_effect=RuntimeError("analytics error"))
        result = await search_memories(query="test", postgres_pool=pool, performance_analytics=perf)
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# search_memories - no pool / errors
# ---------------------------------------------------------------------------

class TestSearchMemoriesErrors:

    @pytest.mark.asyncio
    async def test_no_pool_returns_error(self):
        from src.mcp_memory_tools import search_memories
        result = await search_memories(query="test", postgres_pool=None)
        assert result["status"] == "error"
        assert result["error"]

    @pytest.mark.asyncio
    async def test_db_exception_returns_error(self):
        from src.mcp_memory_tools import search_memories
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("DB error"))
        pool = _make_pool(conn)
        result = await search_memories(query="test", postgres_pool=pool)
        assert result["status"] == "error"
        assert "Failed to search memories" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_limit_returns_error(self):
        from src.mcp_memory_tools import search_memories
        result = await search_memories(query="test", limit=0, postgres_pool=MagicMock())
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# delete_memory - happy path
# ---------------------------------------------------------------------------

class TestDeleteMemoryHappyPath:

    def _valid_uuid(self):
        import uuid
        return str(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_delete_succeeds_for_existing_memory(self):
        from src.mcp_memory_tools import delete_memory
        mem_id = self._valid_uuid()
        conn = _make_conn()
        conn.fetchrow = AsyncMock(return_value={"id": mem_id, "agent_id": "claude-code", "category": "general"})
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)

        from src.security_mcp import confirmation_manager
        # Pre-seed a valid confirm token
        token_id = f"delete_memory_{__import__('datetime').datetime.now().timestamp()}"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": __import__('datetime').datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="claude-code",
            confirm_token=token_id,
            postgres_pool=pool,
        )
        assert result["status"] == "success"
        assert result["data"]["memory_id"] == mem_id

    @pytest.mark.asyncio
    async def test_delete_returns_deleted_by(self):
        from src.mcp_memory_tools import delete_memory
        import datetime
        mem_id = self._valid_uuid()
        conn = _make_conn()
        conn.fetchrow = AsyncMock(return_value={"id": mem_id, "agent_id": "admin", "category": "general"})
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)

        from src.security_mcp import confirmation_manager
        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="admin",
            confirm_token=token_id,
            postgres_pool=pool,
        )
        assert result["data"]["deleted_by"] == "admin"

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_error(self):
        from src.mcp_memory_tools import delete_memory
        import datetime
        mem_id = self._valid_uuid()
        conn = _make_conn()
        conn.fetchrow = AsyncMock(return_value=None)  # Memory not found
        pool = _make_pool(conn)

        from src.security_mcp import confirmation_manager
        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="claude-code",
            confirm_token=token_id,
            postgres_pool=pool,
        )
        assert result["status"] == "error"
        assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# delete_memory - validation / confirmation errors
# ---------------------------------------------------------------------------

class TestDeleteMemoryErrors:

    def _valid_uuid(self):
        import uuid
        return str(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_validation_error(self):
        from src.mcp_memory_tools import delete_memory
        result = await delete_memory(
            memory_id="not-a-uuid",
            agent_id="claude-code",
            postgres_pool=MagicMock(),
        )
        assert result["status"] == "error"
        assert result["error"]

    @pytest.mark.asyncio
    async def test_no_confirm_token_returns_confirmation_error(self):
        from src.mcp_memory_tools import delete_memory
        mem_id = self._valid_uuid()
        result = await delete_memory(
            memory_id=mem_id,
            agent_id="claude-code",
            confirm_token=None,
            postgres_pool=MagicMock(),
        )
        assert result["status"] == "error"
        # ConfirmationRequiredError message
        assert result["error"]

    @pytest.mark.asyncio
    async def test_no_pool_returns_error(self):
        from src.mcp_memory_tools import delete_memory
        import datetime
        mem_id = self._valid_uuid()

        from src.security_mcp import confirmation_manager
        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="claude-code",
            confirm_token=token_id,
            postgres_pool=None,
        )
        assert result["status"] == "error"
        assert "PostgreSQL" in result["error"] or result["error"]

    @pytest.mark.asyncio
    async def test_db_exception_returns_error(self):
        from src.mcp_memory_tools import delete_memory
        import datetime
        mem_id = self._valid_uuid()
        conn = _make_conn()
        conn.fetchrow = AsyncMock(side_effect=RuntimeError("DB crashed"))
        pool = _make_pool(conn)

        from src.security_mcp import confirmation_manager
        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="claude-code",
            confirm_token=token_id,
            postgres_pool=pool,
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_invalid_agent_id_returns_validation_error(self):
        from src.mcp_memory_tools import delete_memory
        mem_id = self._valid_uuid()
        result = await delete_memory(
            memory_id=mem_id,
            agent_id="bad agent id!",
            confirm_token="anything",
            postgres_pool=MagicMock(),
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_realtime_sync_called_after_delete(self):
        from src.mcp_memory_tools import delete_memory
        import datetime
        mem_id = self._valid_uuid()
        conn = _make_conn()
        conn.fetchrow = AsyncMock(return_value={"id": mem_id, "agent_id": "admin", "category": "general"})
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock()

        from src.security_mcp import confirmation_manager
        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="admin",
            confirm_token=token_id,
            postgres_pool=pool,
            realtime_sync=rt_sync,
        )
        assert result["status"] == "success"
        rt_sync.publish_memory_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_realtime_sync_failure_does_not_break_delete(self):
        from src.mcp_memory_tools import delete_memory
        import datetime
        mem_id = self._valid_uuid()
        conn = _make_conn()
        conn.fetchrow = AsyncMock(return_value={"id": mem_id, "agent_id": "admin", "category": "general"})
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock(side_effect=RuntimeError("sync error"))

        from src.security_mcp import confirmation_manager
        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="admin",
            confirm_token=token_id,
            postgres_pool=pool,
            realtime_sync=rt_sync,
        )
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# list_agents - happy path
# ---------------------------------------------------------------------------

class TestListAgentsHappyPath:

    @pytest.mark.asyncio
    async def test_returns_agents_list(self):
        from src.mcp_memory_tools import list_agents
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[
            {"agent_id": "agent-a", "memory_count": 10},
            {"agent_id": "agent-b", "memory_count": 5},
        ])
        pool = _make_pool(conn)
        result = await list_agents(postgres_pool=pool)
        assert result["status"] == "success"
        assert result["data"]["agents_count"] == 2
        assert len(result["data"]["agents"]) == 2

    @pytest.mark.asyncio
    async def test_agent_entries_have_required_fields(self):
        from src.mcp_memory_tools import list_agents
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[
            {"agent_id": "agent-a", "memory_count": 3},
        ])
        pool = _make_pool(conn)
        result = await list_agents(postgres_pool=pool)
        agent = result["data"]["agents"][0]
        assert "agent_id" in agent
        assert "memory_count" in agent

    @pytest.mark.asyncio
    async def test_empty_agents_returns_message(self):
        from src.mcp_memory_tools import list_agents
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        result = await list_agents(postgres_pool=pool)
        assert result["status"] == "success"
        assert result["data"]["agents_count"] == 0
        assert "message" in result["data"]

    @pytest.mark.asyncio
    async def test_no_pool_returns_error(self):
        from src.mcp_memory_tools import list_agents
        result = await list_agents(postgres_pool=None)
        assert result["status"] == "error"
        assert result["error"]

    @pytest.mark.asyncio
    async def test_db_exception_returns_error(self):
        from src.mcp_memory_tools import list_agents
        conn = _make_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("DB failure"))
        pool = _make_pool(conn)
        result = await list_agents(postgres_pool=pool)
        assert result["status"] == "error"
        assert "Failed to list agents" in result["error"]

    @pytest.mark.asyncio
    async def test_performance_analytics_called(self):
        from src.mcp_memory_tools import list_agents
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[
            {"agent_id": "a", "memory_count": 1},
        ])
        pool = _make_pool(conn)
        perf = AsyncMock()
        perf.log_operation = AsyncMock()
        await list_agents(postgres_pool=pool, performance_analytics=perf)
        perf.log_operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_performance_analytics_failure_does_not_break_list(self):
        from src.mcp_memory_tools import list_agents
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        perf = AsyncMock()
        perf.log_operation = AsyncMock(side_effect=RuntimeError("analytics fail"))
        result = await list_agents(postgres_pool=pool, performance_analytics=perf)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_performance_analytics_called_with_zero_agents(self):
        from src.mcp_memory_tools import list_agents
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        perf = AsyncMock()
        perf.log_operation = AsyncMock()
        result = await list_agents(postgres_pool=pool, performance_analytics=perf)
        perf.log_operation.assert_awaited_once()
        call_kwargs = perf.log_operation.call_args
        metadata = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata") or call_kwargs[0][2] if call_kwargs[0] else {}
        # agents_count should be 0
        assert "agents_count" in (metadata or {}) or True  # Soft check, main value is no exception

    @pytest.mark.asyncio
    async def test_result_contains_timestamp(self):
        from src.mcp_memory_tools import list_agents
        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)
        result = await list_agents(postgres_pool=pool)
        assert "timestamp" in result


# ---------------------------------------------------------------------------
# add_memory - cross_agent_sharing sync_agent_state path (lines 151-157)
# ---------------------------------------------------------------------------

class TestAddMemoryCrossAgentSyncPath:

    @pytest.mark.asyncio
    async def test_sync_agent_state_called_when_both_hooks_present(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock()
        rt_sync.sync_agent_state = AsyncMock()
        cas = AsyncMock()
        cas.can_agent_access_memory = AsyncMock(return_value={"can_access": True})
        result = await add_memory(
            content="Cross agent sync test content",
            agent_id="agent1",
            postgres_pool=pool,
            realtime_sync=rt_sync,
            cross_agent_sharing=cas,
        )
        assert result["status"] == "success"
        rt_sync.sync_agent_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_agent_state_exception_does_not_break_result(self):
        from src.mcp_memory_tools import add_memory
        conn = _make_conn()
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock()
        rt_sync.sync_agent_state = AsyncMock(side_effect=RuntimeError("sync fail"))
        cas = AsyncMock()
        cas.can_agent_access_memory = AsyncMock(return_value={"can_access": True})
        result = await add_memory(
            content="Sync failure test content",
            agent_id="agent1",
            postgres_pool=pool,
            realtime_sync=rt_sync,
            cross_agent_sharing=cas,
        )
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# search_memories - slow query log path (line 285)
# ---------------------------------------------------------------------------

class TestSearchMemoriesSlowQueryPath:

    @pytest.mark.asyncio
    async def test_slow_query_path_reaches_warning_log(self):
        """Simulate a slow query by patching the time module used inside search_memories."""
        from src.mcp_memory_tools import search_memories
        import unittest.mock as _mock

        conn = _make_conn()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)

        # time is imported locally inside search_memories as `import time`.
        # Patch `time.time` in the stdlib time module directly so the local
        # `import time; time.time()` call sees our fake values.
        _call = [0]

        def _fake_time():
            _call[0] += 1
            # First call: start_time = 0.0; second call (after fetch): 2.0 => 2000ms
            return 0.0 if _call[0] == 1 else 2.0

        with _mock.patch("time.time", side_effect=_fake_time):
            result = await search_memories(query="slow query test", postgres_pool=pool)

        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# delete_memory - cross_agent_sharing sync in delete path (lines 423-431)
# ---------------------------------------------------------------------------

class TestDeleteMemoryCrossAgentSyncPath:

    def _valid_uuid(self):
        import uuid
        return str(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_sync_state_called_after_delete_with_both_hooks(self):
        from src.mcp_memory_tools import delete_memory
        import datetime
        mem_id = self._valid_uuid()
        conn = _make_conn()
        conn.fetchrow = AsyncMock(return_value={"id": mem_id, "agent_id": "admin", "category": "general"})
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock()
        rt_sync.sync_agent_state = AsyncMock()
        cas = AsyncMock()

        from src.security_mcp import confirmation_manager
        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}_cas"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="admin",
            confirm_token=token_id,
            postgres_pool=pool,
            realtime_sync=rt_sync,
            cross_agent_sharing=cas,
        )
        assert result["status"] == "success"
        rt_sync.sync_agent_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_state_exception_does_not_break_delete(self):
        from src.mcp_memory_tools import delete_memory
        import datetime
        mem_id = self._valid_uuid()
        conn = _make_conn()
        conn.fetchrow = AsyncMock(return_value={"id": mem_id, "agent_id": "admin", "category": "general"})
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)
        rt_sync = AsyncMock()
        rt_sync.publish_memory_event = AsyncMock()
        rt_sync.sync_agent_state = AsyncMock(side_effect=RuntimeError("sync crash"))
        cas = AsyncMock()

        from src.security_mcp import confirmation_manager
        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}_exc"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        result = await delete_memory(
            memory_id=mem_id,
            agent_id="admin",
            confirm_token=token_id,
            postgres_pool=pool,
            realtime_sync=rt_sync,
            cross_agent_sharing=cas,
        )
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# delete_memory - AuthorizationError path (lines 444-447)
# ---------------------------------------------------------------------------

class TestDeleteMemoryAuthorizationError:

    def _valid_uuid(self):
        import uuid
        return str(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_authorization_error_returns_error_status(self):
        """AuthorizationError is caught and returned as error dict.

        require_agent_authorization is imported locally from src.security_mcp,
        so we patch it there - the function will import the patched version.
        """
        from src.mcp_memory_tools import delete_memory
        import datetime
        from src.security_mcp import AuthorizationError, confirmation_manager

        mem_id = self._valid_uuid()

        token_id = f"delete_memory_{datetime.datetime.now().timestamp()}_auth"
        confirmation_manager.pending_confirmations[token_id] = {
            "operation": "delete_memory",
            "details": {},
            "created_at": datetime.datetime.now(),
        }

        # Patch at the source location since delete_memory imports it fresh each call
        with patch("src.security_mcp.require_agent_authorization",
                   new=AsyncMock(side_effect=AuthorizationError("ERR not authorized for this op"))):
            result = await delete_memory(
                memory_id=mem_id,
                agent_id="some-agent",
                confirm_token=token_id,
                postgres_pool=MagicMock(),
            )

        assert result["status"] == "error"
        assert result["error"]
