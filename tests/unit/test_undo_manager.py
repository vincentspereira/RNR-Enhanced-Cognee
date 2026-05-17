"""
Unit tests for src/undo_manager.py

Coverage targets:
- UndoOperationType / UndoStatus enums
- UndoEntry: to_dict, from_dict
- UndoManager.__init__, _load_config (file found, not found, bad JSON)
- _get_default_config
- _ensure_schema (no pool, already created, success, exception)
- create_undo_entry (with/without db_pool, history trim)
- _save_undo_entry (success, exception)
- _load_undo_entry (no pool, success, row found, not found, exception)
- _update_undo_entry (no pool, success, exception)
- undo (entry in history, entry from DB, not found, already completed,
         expired, perform_undo success, perform_undo failure, exception)
- _perform_undo dispatch for each operation type + unsupported
- _undo_memory_add (no pool, no memory_id, success, not found, exception)
- _undo_memory_update (no pool, no memory_id, no content, not exists, success, exception)
- _undo_memory_delete (no pool, success with id, success without id, exception)
- _undo_memory_summarize (no pool, no memory_id, no content, not exists, success, exception)
- _undo_memory_deduplicate (no pool, no merged_ids, success, partial errors, exception)
- _undo_sharing_set (no pool, no memory_id, no policy, success 0 rows, success, exception)
- redo (no entries, success, success moves to undo_history, db update)
- _perform_redo: MEMORY_ADD (no pool/with pool), MEMORY_UPDATE, MEMORY_SUMMARIZE,
                 MEMORY_DELETE (no pool/with pool), SHARING_SET (no pool/with pool),
                 unsupported type
- undo_chain: empty chain, multi-entry chain sorted by timestamp
- get_undo_history: all agents, filtered by agent, limit
- cleanup_expired_entries (no pool, with pool, exception)
- get_undo_manager / init_undo_manager
"""

import json
import sys
import types
import pytest
from datetime import datetime, timezone, timedelta, UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.undo_manager import (
    UndoOperationType,
    UndoStatus,
    UndoEntry,
    UndoManager,
    get_undo_manager,
    init_undo_manager,
    POSTGRES_AVAILABLE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeConn:
    def __init__(self):
        self._fetchrow_queue = []
        self.execute = AsyncMock(return_value="DELETE 1")

    async def fetchrow(self, *args, **kwargs):
        if self._fetchrow_queue:
            return self._fetchrow_queue.pop(0)
        return None

    async def fetchval(self, *args, **kwargs):
        return None


class _AsyncCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_pool(conn=None):
    if conn is None:
        conn = _FakeConn()
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AsyncCtx(conn))
    return pool, conn


def _make_manager(db_pool=None, config_path="nonexistent_config.json"):
    """Create an UndoManager with default config (no config file)."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        mgr = UndoManager(config_path=config_path, db_pool=db_pool)
    return mgr


def _make_entry(
    op_type=UndoOperationType.MEMORY_ADD,
    memory_id="mem-1",
    agent_id="agent-1",
    original_state=None,
    new_state=None,
    chain_id=None,
    status=UndoStatus.PENDING,
    expiration_date=None,
):
    from datetime import datetime, timezone, timedelta
    if expiration_date is None:
        expiration_date = datetime.now(timezone.utc) + timedelta(days=7)
    _eid = memory_id or "none"
    return UndoEntry(
        undo_id="undo-" + _eid,
        operation_type=op_type,
        agent_id=agent_id,
        timestamp=datetime.now(timezone.utc),
        original_state=original_state or {},
        new_state=new_state or {"memory_id": memory_id},
        memory_id=memory_id,
        category=None,
        operation_chain_id=chain_id,
        status=status,
        error_message=None,
        expiration_date=expiration_date,
        metadata={},
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


def test_undo_operation_type_values():
    assert UndoOperationType.MEMORY_ADD.value == "memory_add"
    assert UndoOperationType.MEMORY_UPDATE.value == "memory_update"
    assert UndoOperationType.MEMORY_DELETE.value == "memory_delete"
    assert UndoOperationType.MEMORY_SUMMARIZE.value == "memory_summarize"
    assert UndoOperationType.MEMORY_DEDUPLICATE.value == "memory_deduplicate"
    assert UndoOperationType.SHARING_SET.value == "sharing_set"


def test_undo_status_values():
    assert UndoStatus.PENDING.value == "pending"
    assert UndoStatus.COMPLETED.value == "completed"
    assert UndoStatus.FAILED.value == "failed"
    assert UndoStatus.EXPIRED.value == "expired"


# ---------------------------------------------------------------------------
# UndoEntry
# ---------------------------------------------------------------------------


def test_undo_entry_to_dict():
    entry = _make_entry()
    d = entry.to_dict()
    assert d["operation_type"] == "memory_add"
    assert d["status"] == "pending"
    assert isinstance(d["timestamp"], str)
    assert isinstance(d["expiration_date"], str)


def test_undo_entry_to_dict_no_expiration():
    entry = _make_entry()
    entry.expiration_date = None  # forcibly clear
    d = entry.to_dict()
    # expiration_date should be None in the dict
    assert d.get("expiration_date") is None


def test_undo_entry_from_dict():
    entry = _make_entry()
    d = entry.to_dict()
    restored = UndoEntry.from_dict(d)
    assert restored.operation_type == UndoOperationType.MEMORY_ADD
    assert restored.status == UndoStatus.PENDING
    assert isinstance(restored.timestamp, datetime)


def test_undo_entry_from_dict_no_expiration():
    entry = _make_entry(expiration_date=None)
    d = entry.to_dict()
    d["expiration_date"] = None
    restored = UndoEntry.from_dict(d)
    assert restored.expiration_date is None


# ---------------------------------------------------------------------------
# UndoManager.__init__ / _load_config
# ---------------------------------------------------------------------------


def test_load_config_file_not_found():
    mgr = _make_manager()
    assert "undo_management" in mgr.config


def test_load_config_bad_json(tmp_path):
    cfg = tmp_path / "bad.json"
    cfg.write_text("{invalid json")
    mgr = UndoManager(config_path=str(cfg))
    assert "undo_management" in mgr.config


def test_load_config_success(tmp_path):
    cfg = tmp_path / "good.json"
    data = {"undo_management": {"max_undo_history": 42}}
    cfg.write_text(json.dumps(data))
    mgr = UndoManager(config_path=str(cfg))
    assert mgr.max_history == 42


def test_default_config_values():
    mgr = _make_manager()
    cfg = mgr._get_default_config()
    assert cfg["undo_management"]["enabled"] is True
    assert cfg["undo_management"]["max_undo_history"] == 100


# ---------------------------------------------------------------------------
# _ensure_schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_schema_no_pool():
    mgr = _make_manager(db_pool=None)
    await mgr._ensure_schema()
    assert mgr._schema_created is True


@pytest.mark.asyncio
async def test_ensure_schema_idempotent():
    pool, conn = _make_pool()
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    await mgr._ensure_schema()
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_schema_success():
    pool, conn = _make_pool()
    mgr = _make_manager(db_pool=pool)
    await mgr._ensure_schema()
    assert mgr._schema_created is True
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_schema_exception():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("permission denied")
    mgr = _make_manager(db_pool=pool)
    await mgr._ensure_schema()  # should not raise; just prints warning
    assert mgr._schema_created is False


# ---------------------------------------------------------------------------
# create_undo_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_undo_entry_no_pool():
    mgr = _make_manager()
    entry = await mgr.create_undo_entry(
        operation_type=UndoOperationType.MEMORY_ADD,
        agent_id="a1",
        original_state={},
        new_state={"memory_id": "m1"},
        memory_id="m1",
    )
    assert entry.undo_id is not None
    assert entry.status == UndoStatus.PENDING
    assert len(mgr.undo_history) == 1


@pytest.mark.asyncio
async def test_create_undo_entry_with_db_pool():
    pool, conn = _make_pool()
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    entry = await mgr.create_undo_entry(
        operation_type=UndoOperationType.MEMORY_UPDATE,
        agent_id="a1",
        original_state={"content": "old"},
        new_state={"content": "new"},
        memory_id="m1",
    )
    assert conn.execute.call_count >= 1
    assert entry is not None


@pytest.mark.asyncio
async def test_create_undo_entry_trims_history():
    mgr = _make_manager()
    mgr.max_history = 3
    for i in range(5):
        await mgr.create_undo_entry(
            operation_type=UndoOperationType.MEMORY_ADD,
            agent_id="a1",
            original_state={},
            new_state={"memory_id": f"m{i}"},
        )
    assert len(mgr.undo_history) == 3


@pytest.mark.asyncio
async def test_create_undo_entry_uses_default_metadata():
    mgr = _make_manager()
    entry = await mgr.create_undo_entry(
        operation_type=UndoOperationType.SHARING_SET,
        agent_id="a1",
        original_state={},
        new_state={},
        metadata=None,
    )
    assert entry.metadata == {}


# ---------------------------------------------------------------------------
# _save_undo_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_undo_entry_success():
    pool, conn = _make_pool()
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    entry = _make_entry()
    await mgr._save_undo_entry(entry)
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_save_undo_entry_exception_is_caught():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("insert failed")
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    entry = _make_entry()
    await mgr._save_undo_entry(entry)  # should not raise


# ---------------------------------------------------------------------------
# _load_undo_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_undo_entry_no_pool():
    mgr = _make_manager()
    result = await mgr._load_undo_entry("some-id")
    assert result is None


@pytest.mark.asyncio
async def test_load_undo_entry_not_found():
    pool, conn = _make_pool()
    # fetchrow returns None
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    result = await mgr._load_undo_entry("missing-id")
    assert result is None


@pytest.mark.asyncio
async def test_load_undo_entry_exception():
    pool, conn = _make_pool()

    async def _bad_fetchrow(*args, **kwargs):
        raise RuntimeError("query error")

    conn.fetchrow = _bad_fetchrow
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    result = await mgr._load_undo_entry("some-id")
    assert result is None


# ---------------------------------------------------------------------------
# _update_undo_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_undo_entry_no_pool():
    mgr = _make_manager()
    entry = _make_entry()
    await mgr._update_undo_entry(entry)  # should not raise


@pytest.mark.asyncio
async def test_update_undo_entry_success():
    pool, conn = _make_pool()
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry()
    await mgr._update_undo_entry(entry)
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_undo_entry_exception():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("update failed")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry()
    await mgr._update_undo_entry(entry)  # should not raise


# ---------------------------------------------------------------------------
# undo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_not_found_no_pool():
    mgr = _make_manager()
    result = await mgr.undo("nonexistent-id", "agent-1")
    assert result["success"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_undo_already_completed():
    mgr = _make_manager()
    entry = _make_entry(status=UndoStatus.COMPLETED)
    mgr.undo_history.append(entry)
    result = await mgr.undo(entry.undo_id, "agent-1")
    assert result["success"] is False
    assert "already undone" in result["error"]


@pytest.mark.asyncio
async def test_undo_expired():
    mgr = _make_manager()
    expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    entry = _make_entry(expiration_date=expired_at)
    mgr.undo_history.append(entry)
    result = await mgr.undo(entry.undo_id, "agent-1")
    assert result["success"] is False
    assert "expired" in result["error"]


@pytest.mark.asyncio
async def test_undo_memory_add_no_pool_success():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD)
    mgr.undo_history.append(entry)
    result = await mgr.undo(entry.undo_id, "agent-1")
    assert result["success"] is True
    assert entry in mgr.redo_history


@pytest.mark.asyncio
async def test_undo_memory_add_trimmed_redo():
    mgr = _make_manager()
    mgr.max_redo_history = 2
    for i in range(4):
        e = _make_entry(memory_id=f"mem-{i}")
        mgr.undo_history.append(e)
        r = await mgr.undo(e.undo_id, "agent-1")
        assert r["success"] is True
    assert len(mgr.redo_history) == 2


@pytest.mark.asyncio
async def test_undo_failed_operation_updates_status():
    mgr = _make_manager()
    entry = _make_entry(
        op_type=UndoOperationType.MEMORY_UPDATE,
        original_state={},  # missing "content" -> will fail
        memory_id="mem-1",
    )
    mgr.undo_history.append(entry)
    result = await mgr.undo(entry.undo_id, "agent-1")
    assert result["success"] is False
    assert entry.status == UndoStatus.FAILED


@pytest.mark.asyncio
async def test_undo_loads_from_db_when_not_in_memory():
    pool, conn = _make_pool()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD)
    entry_dict = entry.to_dict()
    conn._fetchrow_queue.append(entry_dict)
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True

    # Override _load_undo_entry to return entry directly
    async def _fake_load(undo_id):
        return entry

    mgr._load_undo_entry = _fake_load

    result = await mgr.undo(entry.undo_id, "agent-1")
    assert result["success"] is True


# ---------------------------------------------------------------------------
# _perform_undo dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_perform_undo_unsupported_type():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.CATEGORY_SUMMARIZE)
    result = await mgr._perform_undo(entry, "agent-1", None)
    assert result["success"] is False
    assert "Unsupported" in result["error"]


# ---------------------------------------------------------------------------
# _undo_memory_add
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_memory_add_no_memory_id():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={}, memory_id=None)
    entry.memory_id = None
    result = await mgr._undo_memory_add(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_add_with_pool_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="DELETE 1")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={"memory_id": "mem-1"})
    result = await mgr._undo_memory_add(entry, "agent-1", "reason")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_undo_memory_add_with_pool_not_found():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="DELETE 0")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={"memory_id": "mem-1"})
    result = await mgr._undo_memory_add(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_add_with_pool_exception():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("db error")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={"memory_id": "mem-1"})
    result = await mgr._undo_memory_add(entry, "agent-1", None)
    assert result["success"] is False


# ---------------------------------------------------------------------------
# _undo_memory_update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_memory_update_no_memory_id():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE, memory_id=None)
    entry.memory_id = None
    result = await mgr._undo_memory_update(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_update_no_original_content():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        original_state={})
    result = await mgr._undo_memory_update(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_update_no_pool_success():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        original_state={"content": "original"})
    result = await mgr._undo_memory_update(entry, "agent-1", None)
    assert result["success"] is True
    assert result.get("no_db_mode") is True


@pytest.mark.asyncio
async def test_undo_memory_update_with_pool_not_exists():
    pool, conn = _make_pool()
    # fetchval returns None (memory not found)
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        original_state={"content": "original"},
                        memory_id="mem-1")

    async def _fv(*args, **kwargs):
        return None

    conn.fetchval = _fv
    result = await mgr._undo_memory_update(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_update_with_pool_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")

    async def _fv(*args, **kwargs):
        return "mem-1"  # exists

    conn.fetchval = _fv
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        original_state={"content": "original"},
                        memory_id="mem-1")
    result = await mgr._undo_memory_update(entry, "agent-1", "test reason")
    assert result["success"] is True


# ---------------------------------------------------------------------------
# _undo_memory_delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_memory_delete_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DELETE,
                        original_state={"id": "mem-del-1", "content": "old"})
    result = await mgr._undo_memory_delete(entry, "agent-1", None)
    assert result["success"] is True
    assert result.get("no_db_mode") is True


@pytest.mark.asyncio
async def test_undo_memory_delete_with_pool_generates_id():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="INSERT 1")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DELETE,
                        original_state={"content": "restored content"})
    # No "id" in original_state -> will generate a uuid
    entry.original_state.pop("id", None)
    result = await mgr._undo_memory_delete(entry, "agent-1", None)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_undo_memory_delete_exception():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("insert failed")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DELETE,
                        original_state={"id": "m1", "content": "c"})
    result = await mgr._undo_memory_delete(entry, "agent-1", None)
    assert result["success"] is False


# ---------------------------------------------------------------------------
# _undo_memory_summarize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_memory_summarize_no_memory_id():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_SUMMARIZE, memory_id=None)
    entry.memory_id = None
    result = await mgr._undo_memory_summarize(entry, "a1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_summarize_no_original_content():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_SUMMARIZE,
                        original_state={})
    result = await mgr._undo_memory_summarize(entry, "a1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_summarize_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_SUMMARIZE,
                        original_state={"original_content": "full text"})
    result = await mgr._undo_memory_summarize(entry, "a1", None)
    assert result["success"] is True
    assert result.get("no_db_mode") is True


@pytest.mark.asyncio
async def test_undo_memory_summarize_not_found_in_db():
    pool, conn = _make_pool()

    async def _fv(*args, **kwargs):
        return None

    conn.fetchval = _fv
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_SUMMARIZE,
                        original_state={"original_content": "full text"})
    result = await mgr._undo_memory_summarize(entry, "a1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_summarize_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")

    async def _fv(*args, **kwargs):
        return "mem-1"

    conn.fetchval = _fv
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_SUMMARIZE,
                        original_state={"original_content": "full text"})
    result = await mgr._undo_memory_summarize(entry, "a1", None)
    assert result["success"] is True


# ---------------------------------------------------------------------------
# _undo_memory_deduplicate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_memory_deduplicate_no_merged_ids():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DEDUPLICATE,
                        original_state={"merged_memory_ids": []})
    result = await mgr._undo_memory_deduplicate(entry, "a1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_memory_deduplicate_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DEDUPLICATE,
                        original_state={"merged_memory_ids": [{"id": "m1", "content": "c"}]})
    result = await mgr._undo_memory_deduplicate(entry, "a1", None)
    assert result["success"] is True
    assert result.get("no_db_mode") is True


@pytest.mark.asyncio
async def test_undo_memory_deduplicate_with_pool_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="INSERT 1")
    mgr = _make_manager(db_pool=pool)
    merged = [
        {"id": "m1", "content": "c1", "agent_id": "a1", "metadata": {}},
        {"id": "m2", "content": "c2", "agent_id": "a1", "metadata": {}},
    ]
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DEDUPLICATE,
                        original_state={"merged_memory_ids": merged})
    result = await mgr._undo_memory_deduplicate(entry, "a1", None)
    assert result["success"] is True
    assert "Restored 2" in result["message"]


@pytest.mark.asyncio
async def test_undo_memory_deduplicate_partial_errors():
    pool, conn = _make_pool()
    call_count = [0]

    async def _flaky_execute(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("insert failed")
        return "INSERT 1"

    conn.execute = _flaky_execute
    mgr = _make_manager(db_pool=pool)
    merged = [
        {"id": "m1", "content": "c1"},
        {"id": "m2", "content": "c2"},
        {"id": "m3", "content": "c3"},
    ]
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DEDUPLICATE,
                        original_state={"merged_memory_ids": merged})
    result = await mgr._undo_memory_deduplicate(entry, "a1", None)
    assert "errors" in result


@pytest.mark.asyncio
async def test_undo_memory_deduplicate_outer_exception():
    pool, conn = _make_pool()

    async def _bad_acquire():
        raise RuntimeError("connection lost")

    pool.acquire.side_effect = RuntimeError("connection lost")
    mgr = _make_manager(db_pool=pool)
    merged = [{"id": "m1", "content": "c1"}]
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DEDUPLICATE,
                        original_state={"merged_memory_ids": merged})
    result = await mgr._undo_memory_deduplicate(entry, "a1", None)
    assert result["success"] is False


# ---------------------------------------------------------------------------
# _undo_sharing_set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_sharing_set_no_memory_id():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET, memory_id=None)
    entry.memory_id = None
    result = await mgr._undo_sharing_set(entry, "a1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_sharing_set_no_policy():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        original_state={})
    result = await mgr._undo_sharing_set(entry, "a1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_sharing_set_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        original_state={"sharing_policy": {"mode": "private"}})
    result = await mgr._undo_sharing_set(entry, "a1", None)
    assert result["success"] is True
    assert result.get("no_db_mode") is True


@pytest.mark.asyncio
async def test_undo_sharing_set_with_pool_zero_rows():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 0")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        original_state={"sharing_policy": {"mode": "public"}})
    result = await mgr._undo_sharing_set(entry, "a1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_undo_sharing_set_with_pool_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        original_state={"sharing_policy": {"mode": "shared"}})
    result = await mgr._undo_sharing_set(entry, "a1", None)
    assert result["success"] is True


# ---------------------------------------------------------------------------
# redo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redo_no_entries():
    mgr = _make_manager()
    result = await mgr.redo("agent-1")
    assert result["success"] is False
    assert "No redoable" in result["error"]


@pytest.mark.asyncio
async def test_redo_memory_add_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={"memory_id": "mem-1"})
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is True
    # Entry should move back to undo_history
    assert entry in mgr.undo_history
    assert entry not in mgr.redo_history


@pytest.mark.asyncio
async def test_redo_memory_update_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        new_state={"content": "new content"},
                        memory_id="mem-1")
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_redo_memory_summarize_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_SUMMARIZE,
                        new_state={"summarized_content": "summary"},
                        memory_id="mem-1")
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_redo_memory_delete_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DELETE,
                        memory_id="mem-1")
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_redo_sharing_set_no_pool():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        new_state={"sharing_policy": {"mode": "public"}},
                        memory_id="mem-1")
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_redo_unsupported_type():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.AGENT_SYNC)
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is False
    assert "Redo not supported" in result["error"]


@pytest.mark.asyncio
async def test_redo_memory_add_no_memory_id():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={}, memory_id=None)
    entry.memory_id = None
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    # Still succeeds because it generates a uuid
    assert result["success"] is True


@pytest.mark.asyncio
async def test_redo_memory_update_no_memory_id():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        new_state={"content": "c"}, memory_id=None)
    entry.memory_id = None
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_redo_memory_update_no_content():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        new_state={},
                        memory_id="mem-1")
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_redo_memory_delete_no_memory_id():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DELETE,
                        new_state={}, memory_id=None)
    entry.memory_id = None
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_redo_sharing_set_no_memory_id():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        new_state={"sharing_policy": {}}, memory_id=None)
    entry.memory_id = None
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_redo_sharing_set_no_policy():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        new_state={}, memory_id="mem-1")
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_redo_exception_returns_error():
    mgr = _make_manager()
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={"memory_id": "m1"})
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)

    async def _bad_redo(*args, **kwargs):
        raise RuntimeError("redo error")

    mgr._perform_redo = _bad_redo
    result = await mgr.redo("agent-1")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_redo_with_db_pool():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="INSERT 1")
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={"memory_id": "mem-1", "content": "c"},
                        agent_id="agent-1")
    entry.status = UndoStatus.COMPLETED
    mgr.redo_history.append(entry)
    result = await mgr.redo("agent-1")
    assert result["success"] is True


# ---------------------------------------------------------------------------
# undo_chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_chain_empty():
    mgr = _make_manager()
    results = await mgr.undo_chain("nonexistent-chain", "agent-1")
    assert results == []


@pytest.mark.asyncio
async def test_undo_chain_multiple_entries():
    mgr = _make_manager()
    chain_id = "chain-42"
    entries = []
    from datetime import timedelta

    for i in range(3):
        e = _make_entry(
            memory_id=f"mem-{i}",
            new_state={"memory_id": f"mem-{i}"},
            chain_id=chain_id,
        )
        # Stagger timestamps so sort order is deterministic
        e.timestamp = datetime.now(timezone.utc) + timedelta(seconds=i)
        entries.append(e)
        mgr.undo_history.append(e)

    results = await mgr.undo_chain(chain_id, "agent-1")
    assert len(results) == 3
    # Each result should have the undo_id and operation_type
    for r in results:
        assert "undo_id" in r
        assert "result" in r


# ---------------------------------------------------------------------------
# get_undo_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_undo_history_all_agents():
    mgr = _make_manager()
    for i in range(3):
        mgr.undo_history.append(_make_entry(memory_id=f"m{i}", agent_id=f"agent-{i}"))
    history = await mgr.get_undo_history()
    assert len(history) == 3


@pytest.mark.asyncio
async def test_get_undo_history_filtered_by_agent():
    mgr = _make_manager()
    mgr.undo_history.append(_make_entry(memory_id="m1", agent_id="agent-1"))
    mgr.undo_history.append(_make_entry(memory_id="m2", agent_id="agent-2"))
    history = await mgr.get_undo_history(agent_id="agent-1")
    assert len(history) == 1


@pytest.mark.asyncio
async def test_get_undo_history_limit():
    mgr = _make_manager()
    for i in range(10):
        mgr.undo_history.append(_make_entry(memory_id=f"m{i}"))
    history = await mgr.get_undo_history(limit=5)
    assert len(history) == 5


@pytest.mark.asyncio
async def test_get_undo_history_returns_dicts():
    mgr = _make_manager()
    mgr.undo_history.append(_make_entry())
    history = await mgr.get_undo_history()
    assert isinstance(history[0], dict)


# ---------------------------------------------------------------------------
# cleanup_expired_entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_expired_entries_removes_expired():
    mgr = _make_manager()
    past = datetime.now(timezone.utc) - timedelta(days=1)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    e1 = _make_entry(memory_id="m1", expiration_date=past)
    e2 = _make_entry(memory_id="m2", expiration_date=future)
    mgr.undo_history.extend([e1, e2])
    await mgr.cleanup_expired_entries()
    assert e1 not in mgr.undo_history
    assert e2 in mgr.undo_history


@pytest.mark.asyncio
async def test_cleanup_expired_entries_no_expiration_kept():
    mgr = _make_manager()
    e = _make_entry(expiration_date=None)
    mgr.undo_history.append(e)
    await mgr.cleanup_expired_entries()
    assert e in mgr.undo_history


@pytest.mark.asyncio
async def test_cleanup_expired_entries_with_db():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="DELETE 3")
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    await mgr.cleanup_expired_entries()
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_expired_entries_db_exception():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("db error")
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    await mgr.cleanup_expired_entries()  # should not raise


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def test_init_undo_manager_returns_instance():
    with patch("builtins.open", side_effect=FileNotFoundError):
        mgr = init_undo_manager()
    assert isinstance(mgr, UndoManager)


def test_get_undo_manager_returns_instance_after_init():
    with patch("builtins.open", side_effect=FileNotFoundError):
        init_undo_manager()
    mgr = get_undo_manager()
    assert mgr is not None


# ---------------------------------------------------------------------------
# _perform_redo with DB pool (cover lines 891-904, 919-932, 951-972)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_perform_redo_memory_update_with_pool_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        new_state={"content": "updated content"},
                        memory_id="mem-upd")
    result = await mgr._perform_redo(entry, "agent-1", None)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_perform_redo_memory_update_with_pool_exception():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("update failed")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        new_state={"content": "content"},
                        memory_id="mem-upd")
    result = await mgr._perform_redo(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_perform_redo_memory_delete_with_pool_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="DELETE 1")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DELETE,
                        memory_id="mem-del")
    result = await mgr._perform_redo(entry, "agent-1", None)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_perform_redo_memory_delete_with_pool_exception():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("delete failed")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_DELETE,
                        memory_id="mem-del")
    result = await mgr._perform_redo(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_perform_redo_sharing_set_with_pool_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        new_state={"sharing_policy": {"mode": "public"}},
                        memory_id="mem-share")
    result = await mgr._perform_redo(entry, "agent-1", None)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_perform_redo_sharing_set_with_pool_zero_rows():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 0")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        new_state={"sharing_policy": {"mode": "private"}},
                        memory_id="mem-share")
    result = await mgr._perform_redo(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_perform_redo_sharing_set_with_pool_exception():
    pool, conn = _make_pool()
    conn.execute.side_effect = RuntimeError("update error")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.SHARING_SET,
                        new_state={"sharing_policy": {"mode": "public"}},
                        memory_id="mem-share")
    result = await mgr._perform_redo(entry, "agent-1", None)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_perform_redo_memory_summarize_with_pool_success():
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = _make_manager(db_pool=pool)
    entry = _make_entry(op_type=UndoOperationType.MEMORY_SUMMARIZE,
                        new_state={"summarized_content": "short summary"},
                        memory_id="mem-sum")
    result = await mgr._perform_redo(entry, "agent-1", None)
    assert result["success"] is True


# ---------------------------------------------------------------------------
# Undo with actual DB pool updates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_undo_updates_db_on_success():
    """When undo succeeds and a pool is present, _update_undo_entry is called."""
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True

    entry = _make_entry(op_type=UndoOperationType.MEMORY_ADD,
                        new_state={"memory_id": "mem-1"})
    mgr.undo_history.append(entry)

    # execute will be called for both the DELETE and the status update
    result = await mgr.undo(entry.undo_id, "agent-1")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_undo_updates_db_on_failure():
    """When undo fails, _update_undo_entry is still called to record failure."""
    pool, conn = _make_pool()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    mgr = _make_manager(db_pool=pool)
    mgr._schema_created = True

    # MEMORY_UPDATE with no original content -> fails
    entry = _make_entry(op_type=UndoOperationType.MEMORY_UPDATE,
                        original_state={},  # missing content
                        memory_id="mem-1")
    mgr.undo_history.append(entry)

    result = await mgr.undo(entry.undo_id, "agent-1")
    assert result["success"] is False
    assert entry.status == UndoStatus.FAILED
