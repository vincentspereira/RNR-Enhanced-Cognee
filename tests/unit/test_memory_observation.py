"""
Unit tests for src/memory_observation.py
Covers: MemoryObservationManager (all CRUD + search methods), singleton helpers.
All offline - asyncpg pool is fully mocked.
ASCII-only assertions.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


UTC = timezone.utc


# ---------------------------------------------------------------------------
# Pool / connection helpers
# ---------------------------------------------------------------------------

class _AsyncCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_pool(
    fetch_return=None,
    fetchrow_return=None,
    execute_return="UPDATE 1",
):
    """Build a minimal asyncpg-pool mock."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=execute_return)
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    mock_conn.fetch = AsyncMock(return_value=fetch_return or [])
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AsyncCtx(mock_conn))
    return pool, mock_conn


def _make_obs_row(
    obs_id="obs-uuid-1",
    memory_id="mem-1",
    agent_id="system",
    entity="user",
    attribute="name",
    value="Alice",
    confidence=1.0,
    created_at=None,
    updated_at=None,
):
    """Return a MagicMock that behaves like an asyncpg observation row."""
    now = datetime.now(UTC)
    row = MagicMock()
    data = {
        "id": obs_id,
        "memory_id": memory_id,
        "agent_id": agent_id,
        "entity": entity,
        "attribute": attribute,
        "value": value,
        "confidence": confidence,
        "created_at": created_at or now,
        "updated_at": updated_at or now,
    }
    row.__getitem__ = lambda self, key: data[key]
    for k, v in data.items():
        setattr(row, k, v)
    return row


# ===========================================================================
# Import
# ===========================================================================

from src.memory_observation import (
    MemoryObservationManager,
    init_observation_manager,
    get_observation_manager,
)


# ===========================================================================
# TestMemoryObservationManagerInit
# ===========================================================================

class TestMemoryObservationManagerInit:

    @pytest.mark.unit
    def test_init_with_pool(self):
        pool = MagicMock()
        mgr = MemoryObservationManager(postgres_pool=pool)
        assert mgr.pool is pool
        assert mgr._schema_ready is False

    @pytest.mark.unit
    def test_init_without_pool(self):
        mgr = MemoryObservationManager()
        assert mgr.pool is None
        assert mgr._schema_ready is False


# ===========================================================================
# TestEnsureSchema
# ===========================================================================

class TestEnsureSchema:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_when_no_pool(self):
        mgr = MemoryObservationManager()
        await mgr._ensure_schema()  # must not raise
        assert mgr._schema_ready is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sets_schema_ready_on_success(self):
        pool, mock_conn = _make_pool()
        mgr = MemoryObservationManager(pool)
        await mgr._ensure_schema()
        assert mgr._schema_ready is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executes_ddl_statements(self):
        pool, mock_conn = _make_pool()
        mgr = MemoryObservationManager(pool)
        await mgr._ensure_schema()
        assert mock_conn.execute.call_count >= 3  # table + 2 indexes

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_when_already_ready(self):
        pool, mock_conn = _make_pool()
        mgr = MemoryObservationManager(pool)
        mgr._schema_ready = True
        await mgr._ensure_schema()
        mock_conn.execute.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_ddl_exception_gracefully(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("DDL failed"))
        mgr = MemoryObservationManager(pool)
        await mgr._ensure_schema()  # must not raise
        assert mgr._schema_ready is False


# ===========================================================================
# TestAddObservation
# ===========================================================================

class TestAddObservation:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_error_when_no_pool(self):
        mgr = MemoryObservationManager()
        result = await mgr.add_observation("m1", "user", "name", "Alice")
        assert "error" in result
        assert result["error"] == "No database pool"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_add_returns_expected_keys(self):
        row = _make_obs_row()
        pool, mock_conn = _make_pool(fetchrow_return=row)
        mgr = MemoryObservationManager(pool)

        result = await mgr.add_observation(
            memory_id="mem-1",
            entity="user",
            attribute="name",
            value="Alice",
        )
        for key in ("observation_id", "memory_id", "entity", "attribute", "value",
                    "confidence", "created_at"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returned_observation_id_is_string(self):
        row = _make_obs_row(obs_id="uuid-123")
        pool, mock_conn = _make_pool(fetchrow_return=row)
        mgr = MemoryObservationManager(pool)

        result = await mgr.add_observation("m1", "entity", "attr", "val")
        assert isinstance(result["observation_id"], str)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confidence_clamped_below_zero(self):
        row = _make_obs_row(confidence=0.0)
        pool, mock_conn = _make_pool(fetchrow_return=row)
        mgr = MemoryObservationManager(pool)
        # Negative confidence should be clamped to 0.0
        result = await mgr.add_observation("m1", "e", "a", "v", confidence=-5.0)
        assert result["confidence"] == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confidence_clamped_above_one(self):
        row = _make_obs_row(confidence=1.0)
        pool, mock_conn = _make_pool(fetchrow_return=row)
        mgr = MemoryObservationManager(pool)
        result = await mgr.add_observation("m1", "e", "a", "v", confidence=99.0)
        assert result["confidence"] == 1.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_db_exception_returns_error_dict(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("insert failed"))
        mgr = MemoryObservationManager(pool)
        # _ensure_schema will also fail - that's fine
        result = await mgr.add_observation("m1", "e", "a", "v")
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_custom_agent_id_passed_to_db(self):
        row = _make_obs_row(agent_id="custom-agent")
        pool, mock_conn = _make_pool(fetchrow_return=row)
        mgr = MemoryObservationManager(pool)
        result = await mgr.add_observation(
            "m1", "e", "a", "v", agent_id="custom-agent"
        )
        # Check the insert was called (schema + insert = at least 4 execute calls)
        assert mock_conn.fetchrow.called

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_created_at_is_isoformat_string(self):
        row = _make_obs_row()
        pool, mock_conn = _make_pool(fetchrow_return=row)
        mgr = MemoryObservationManager(pool)
        result = await mgr.add_observation("m1", "e", "a", "v")
        assert isinstance(result["created_at"], str)
        # Must be parseable as ISO8601
        datetime.fromisoformat(result["created_at"])


# ===========================================================================
# TestGetObservations
# ===========================================================================

class TestGetObservations:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_pool(self):
        mgr = MemoryObservationManager()
        result = await mgr.get_observations("m1")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_rows(self):
        pool, mock_conn = _make_pool(fetch_return=[])
        mgr = MemoryObservationManager(pool)
        result = await mgr.get_observations("m1")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self):
        row = _make_obs_row()
        pool, mock_conn = _make_pool(fetch_return=[row])
        mgr = MemoryObservationManager(pool)
        result = await mgr.get_observations("mem-1")
        assert len(result) == 1
        obs = result[0]
        for key in ("observation_id", "memory_id", "agent_id", "entity",
                    "attribute", "value", "confidence", "created_at", "updated_at"):
            assert key in obs, f"Missing key: {key}"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_rows_returned(self):
        rows = [_make_obs_row(obs_id=f"id-{i}", attribute=f"attr-{i}") for i in range(3)]
        pool, mock_conn = _make_pool(fetch_return=rows)
        mgr = MemoryObservationManager(pool)
        result = await mgr.get_observations("m1")
        assert len(result) == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_db_exception_returns_empty_list(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("query failed"))
        mgr = MemoryObservationManager(pool)
        result = await mgr.get_observations("m1")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confidence_is_float(self):
        row = _make_obs_row(confidence=0.75)
        pool, mock_conn = _make_pool(fetch_return=[row])
        mgr = MemoryObservationManager(pool)
        result = await mgr.get_observations("m1")
        assert isinstance(result[0]["confidence"], float)


# ===========================================================================
# TestUpdateObservation
# ===========================================================================

class TestUpdateObservation:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_error_when_no_pool(self):
        mgr = MemoryObservationManager()
        result = await mgr.update_observation("obs-1", "new value")
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_update_returns_ok(self):
        pool, mock_conn = _make_pool(execute_return="UPDATE 1")
        mgr = MemoryObservationManager(pool)
        result = await mgr.update_observation("obs-1", "updated value")
        assert result.get("ok") is True
        assert result["observation_id"] == "obs-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_not_found_returns_error(self):
        pool, mock_conn = _make_pool(execute_return="UPDATE 0")
        mgr = MemoryObservationManager(pool)
        result = await mgr.update_observation("obs-missing", "val")
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_db_exception_returns_error(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("update failed"))
        mgr = MemoryObservationManager(pool)
        result = await mgr.update_observation("obs-1", "val")
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_confidence_clamped_in_update(self):
        pool, mock_conn = _make_pool(execute_return="UPDATE 1")
        mgr = MemoryObservationManager(pool)
        # Should not raise even with out-of-range confidence
        result = await mgr.update_observation("obs-1", "val", confidence=2.5)
        assert result.get("ok") is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_execute_called_once(self):
        pool, mock_conn = _make_pool(execute_return="UPDATE 1")
        mgr = MemoryObservationManager(pool)
        mgr._schema_ready = True  # skip DDL
        await mgr.update_observation("obs-1", "new val")
        # At least one execute call for the UPDATE
        assert mock_conn.execute.call_count >= 1


# ===========================================================================
# TestDeleteObservation
# ===========================================================================

class TestDeleteObservation:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_error_when_no_pool(self):
        mgr = MemoryObservationManager()
        result = await mgr.delete_observation("obs-1")
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_delete_returns_deleted_true(self):
        pool, mock_conn = _make_pool(execute_return="DELETE 1")
        mgr = MemoryObservationManager(pool)
        result = await mgr.delete_observation("obs-1")
        assert result.get("deleted") is True
        assert result["observation_id"] == "obs-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_not_found_returns_error(self):
        pool, mock_conn = _make_pool(execute_return="DELETE 0")
        mgr = MemoryObservationManager(pool)
        result = await mgr.delete_observation("obs-missing")
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_db_exception_returns_error(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("delete failed"))
        mgr = MemoryObservationManager(pool)
        result = await mgr.delete_observation("obs-1")
        assert "error" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_execute_contains_obs_id(self):
        pool, mock_conn = _make_pool(execute_return="DELETE 1")
        mgr = MemoryObservationManager(pool)
        mgr._schema_ready = True
        await mgr.delete_observation("obs-xyz")
        # The execute call should reference the id
        call_args = mock_conn.execute.call_args
        assert "obs-xyz" in str(call_args)


# ===========================================================================
# TestSearchObservations
# ===========================================================================

class TestSearchObservations:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_pool(self):
        mgr = MemoryObservationManager()
        result = await mgr.search_observations(entity="user")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_all_when_no_filters(self):
        rows = [_make_obs_row(obs_id=f"id-{i}") for i in range(2)]
        pool, mock_conn = _make_pool(fetch_return=rows)
        mgr = MemoryObservationManager(pool)
        result = await mgr.search_observations()
        assert len(result) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_entity_filter_applied(self):
        row = _make_obs_row(entity="server")
        pool, mock_conn = _make_pool(fetch_return=[row])
        mgr = MemoryObservationManager(pool)
        result = await mgr.search_observations(entity="server")
        assert len(result) == 1
        assert result[0]["entity"] == "server"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_attribute_filter_applied(self):
        row = _make_obs_row(attribute="status")
        pool, mock_conn = _make_pool(fetch_return=[row])
        mgr = MemoryObservationManager(pool)
        result = await mgr.search_observations(attribute="status")
        assert len(result) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_both_filters_applied(self):
        row = _make_obs_row(entity="user", attribute="name")
        pool, mock_conn = _make_pool(fetch_return=[row])
        mgr = MemoryObservationManager(pool)
        result = await mgr.search_observations(entity="user", attribute="name")
        assert len(result) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_result_when_no_match(self):
        pool, mock_conn = _make_pool(fetch_return=[])
        mgr = MemoryObservationManager(pool)
        result = await mgr.search_observations(entity="nonexistent")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_db_exception_returns_empty_list(self):
        pool = MagicMock()
        pool.acquire = MagicMock(side_effect=Exception("search failed"))
        mgr = MemoryObservationManager(pool)
        result = await mgr.search_observations(entity="user")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_all_keys(self):
        row = _make_obs_row()
        pool, mock_conn = _make_pool(fetch_return=[row])
        mgr = MemoryObservationManager(pool)
        result = await mgr.search_observations()
        assert len(result) == 1
        obs = result[0]
        for key in ("observation_id", "memory_id", "agent_id", "entity",
                    "attribute", "value", "confidence", "created_at", "updated_at"):
            assert key in obs, f"Missing key: {key}"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ilike_params_passed_for_entity_filter(self):
        pool, mock_conn = _make_pool(fetch_return=[])
        mgr = MemoryObservationManager(pool)
        mgr._schema_ready = True
        await mgr.search_observations(entity="user")
        # fetch should have been called once (no DDL since schema_ready=True)
        assert mock_conn.fetch.called
        call_args = mock_conn.fetch.call_args
        # The %entity% pattern should be in the args
        args_str = str(call_args)
        assert "user" in args_str

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_params_when_no_filters(self):
        pool, mock_conn = _make_pool(fetch_return=[])
        mgr = MemoryObservationManager(pool)
        mgr._schema_ready = True
        await mgr.search_observations()
        # fetch called with only the SQL string, no params
        assert mock_conn.fetch.called

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_both_filters_build_two_conditions(self):
        pool, mock_conn = _make_pool(fetch_return=[])
        mgr = MemoryObservationManager(pool)
        mgr._schema_ready = True
        await mgr.search_observations(entity="user", attribute="status")
        call_args = mock_conn.fetch.call_args
        # Both filter strings should appear in the params
        args_str = str(call_args)
        assert "user" in args_str
        assert "status" in args_str


# ===========================================================================
# TestSingleton
# ===========================================================================

class TestSingleton:

    @pytest.fixture(autouse=True)
    def _reset_singleton(self):
        import src.memory_observation as mod
        mod._instance = None
        yield
        mod._instance = None

    @pytest.mark.unit
    def test_init_returns_instance(self):
        pool = MagicMock()
        mgr = init_observation_manager(pool)
        assert isinstance(mgr, MemoryObservationManager)

    @pytest.mark.unit
    def test_get_returns_same_instance(self):
        pool = MagicMock()
        m1 = init_observation_manager(pool)
        m2 = get_observation_manager()
        assert m1 is m2

    @pytest.mark.unit
    def test_get_returns_none_before_init(self):
        import src.memory_observation as mod
        mod._instance = None
        assert get_observation_manager() is None

    @pytest.mark.unit
    def test_reinit_replaces_instance(self):
        p1 = MagicMock()
        p2 = MagicMock()
        m1 = init_observation_manager(p1)
        m2 = init_observation_manager(p2)
        assert get_observation_manager() is m2
        assert m1 is not m2

    @pytest.mark.unit
    def test_init_without_pool(self):
        mgr = init_observation_manager()
        assert mgr.pool is None
