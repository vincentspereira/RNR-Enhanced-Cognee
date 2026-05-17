"""
Unit tests for src.memory_provenance
======================================
Covers MemoryProvenanceTracker, init_provenance_tracker, get_provenance_tracker.
All tests use mocked PostgreSQL pools. No live connections required.
No Unicode characters in assertions or messages.
asyncio_mode = auto (from pytest.ini).
"""

import json
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock

import src.memory_provenance as prov_module
from src.memory_provenance import (
    MemoryProvenanceTracker,
    init_provenance_tracker,
    get_provenance_tracker,
)


# ---------------------------------------------------------------------------
# Pool / connection factory helpers
# ---------------------------------------------------------------------------

def _make_pool(conn: AsyncMock) -> MagicMock:
    """Return a mock pool whose acquire() is an async context manager."""
    class _Ctx:
        async def __aenter__(self):
            return conn
        async def __aexit__(self, *args):
            pass

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_Ctx())
    return pool


def _tracker_with_conn(conn: AsyncMock) -> MemoryProvenanceTracker:
    pool = _make_pool(conn)
    return MemoryProvenanceTracker(pool)


# ---------------------------------------------------------------------------
# _sha256 helper
# ---------------------------------------------------------------------------

class TestSha256:
    def test_known_value(self):
        text = "hello"
        expected = hashlib.sha256(b"hello").hexdigest()
        assert MemoryProvenanceTracker._sha256(text) == expected

    def test_empty_string(self):
        result = MemoryProvenanceTracker._sha256("")
        assert len(result) == 64  # sha256 hex is always 64 chars

    def test_different_inputs_different_hashes(self):
        h1 = MemoryProvenanceTracker._sha256("abc")
        h2 = MemoryProvenanceTracker._sha256("abd")
        assert h1 != h2


# ---------------------------------------------------------------------------
# set_provenance
# ---------------------------------------------------------------------------

class TestSetProvenance:
    async def test_no_pool_returns_false(self):
        tracker = MemoryProvenanceTracker(postgres_pool=None)
        result = await tracker.set_provenance("mem-1", source="user_input")
        assert result is False

    async def test_success_returns_true(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        tracker = _tracker_with_conn(conn)
        result = await tracker.set_provenance("mem-1", source="user_input")
        assert result is True

    async def test_zero_rows_updated_returns_false(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 0")
        tracker = _tracker_with_conn(conn)
        result = await tracker.set_provenance("mem-9", source="user_input")
        assert result is False

    async def test_source_url_included_in_provenance(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        tracker = _tracker_with_conn(conn)
        await tracker.set_provenance(
            "mem-2", source="ingest_url", source_url="https://example.com"
        )
        # Verify the JSON passed to execute contains source_url
        call_args = conn.execute.call_args
        prov_json = call_args[0][1]  # second positional arg is the JSON string
        prov = json.loads(prov_json)
        assert prov.get("source_url") == "https://example.com"

    async def test_checksum_computed_when_content_given(self):
        content = "my important content"
        expected_checksum = hashlib.sha256(content.encode()).hexdigest()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        tracker = _tracker_with_conn(conn)
        await tracker.set_provenance(
            "mem-3", source="cognify", content_for_checksum=content
        )
        call_args = conn.execute.call_args
        prov = json.loads(call_args[0][1])
        assert prov.get("checksum") == expected_checksum

    async def test_no_checksum_when_content_not_given(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        tracker = _tracker_with_conn(conn)
        await tracker.set_provenance("mem-4", source="import")
        prov = json.loads(conn.execute.call_args[0][1])
        assert "checksum" not in prov

    async def test_extra_fields_merged(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        tracker = _tracker_with_conn(conn)
        await tracker.set_provenance(
            "mem-5", source="revert", extra={"custom_key": "custom_value"}
        )
        prov = json.loads(conn.execute.call_args[0][1])
        assert prov.get("custom_key") == "custom_value"

    async def test_agent_id_used_as_author(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        tracker = _tracker_with_conn(conn)
        await tracker.set_provenance("mem-6", source="user_input", agent_id="bot-1")
        prov = json.loads(conn.execute.call_args[0][1])
        assert prov.get("author") == "bot-1"

    async def test_no_agent_id_defaults_to_unknown(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        tracker = _tracker_with_conn(conn)
        await tracker.set_provenance("mem-7", source="cognify")
        prov = json.loads(conn.execute.call_args[0][1])
        assert prov.get("author") == "unknown"

    async def test_db_exception_returns_false(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("DB error"))
        tracker = _tracker_with_conn(conn)
        result = await tracker.set_provenance("mem-8", source="user_input")
        assert result is False

    async def test_verified_is_false_by_default(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        tracker = _tracker_with_conn(conn)
        await tracker.set_provenance("mem-10", source="user_input")
        prov = json.loads(conn.execute.call_args[0][1])
        assert prov["verified"] is False
        assert prov["verified_at"] is None
        assert prov["verified_by"] is None


# ---------------------------------------------------------------------------
# get_provenance
# ---------------------------------------------------------------------------

class TestGetProvenance:
    async def test_no_pool_returns_none(self):
        tracker = MemoryProvenanceTracker(postgres_pool=None)
        result = await tracker.get_provenance("mem-1")
        assert result is None

    async def test_memory_not_found_returns_none(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        result = await tracker.get_provenance("nonexistent")
        assert result is None

    async def test_provenance_is_none_returns_default(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"provenance": None})
        tracker = _tracker_with_conn(conn)
        result = await tracker.get_provenance("mem-no-prov")
        assert result == {"source": "unknown", "verified": False}

    async def test_provenance_is_string_json_parsed(self):
        prov_data = {"source": "ingest_url", "verified": True}
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"provenance": json.dumps(prov_data)})
        tracker = _tracker_with_conn(conn)
        result = await tracker.get_provenance("mem-str")
        assert result == prov_data

    async def test_provenance_is_dict_returned_directly(self):
        prov_data = {"source": "cognify", "verified": False}
        conn = AsyncMock()
        # asyncpg may return JSONB as a dict already
        conn.fetchrow = AsyncMock(return_value={"provenance": prov_data})
        tracker = _tracker_with_conn(conn)
        result = await tracker.get_provenance("mem-dict")
        assert result == prov_data

    async def test_db_exception_returns_none(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=RuntimeError("DB down"))
        tracker = _tracker_with_conn(conn)
        result = await tracker.get_provenance("mem-err")
        assert result is None


# ---------------------------------------------------------------------------
# add_transformation
# ---------------------------------------------------------------------------

class TestAddTransformation:
    async def test_no_pool_returns_false(self):
        tracker = MemoryProvenanceTracker(postgres_pool=None)
        result = await tracker.add_transformation("mem-1", "redact_pii")
        assert result is False

    async def test_success_returns_true(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        result = await tracker.add_transformation("mem-1", "redact_pii")
        assert result is True

    async def test_execute_called_once(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        await tracker.add_transformation("mem-2", "translate", {"from": "fr", "to": "en"})
        conn.execute.assert_awaited_once()

    async def test_details_merged_into_entry(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        await tracker.add_transformation("mem-3", "summarize", {"model": "gpt-4"})
        # The first positional arg to execute after the SQL is the JSON list
        call_args = conn.execute.call_args[0]
        entry_list = json.loads(call_args[1])
        assert len(entry_list) == 1
        entry = entry_list[0]
        assert entry["type"] == "summarize"
        assert entry["model"] == "gpt-4"
        assert "timestamp" in entry

    async def test_db_exception_returns_false(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=Exception("insert fail"))
        tracker = _tracker_with_conn(conn)
        result = await tracker.add_transformation("mem-4", "redact_pii")
        assert result is False

    async def test_no_details_still_succeeds(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        result = await tracker.add_transformation("mem-5", "redact_pii", details=None)
        assert result is True


# ---------------------------------------------------------------------------
# mark_verified
# ---------------------------------------------------------------------------

class TestMarkVerified:
    async def test_no_pool_returns_false(self):
        tracker = MemoryProvenanceTracker(postgres_pool=None)
        result = await tracker.mark_verified("mem-1")
        assert result is False

    async def test_success_returns_true(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        result = await tracker.mark_verified("mem-1")
        assert result is True

    async def test_verified_by_defaults_to_system(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        await tracker.mark_verified("mem-1", verified_by=None)
        # Second positional arg to execute is verified_by ("system")
        call_args = conn.execute.call_args[0]
        assert call_args[2] == "system"

    async def test_verified_by_custom_value(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        await tracker.mark_verified("mem-1", verified_by="admin-agent")
        call_args = conn.execute.call_args[0]
        assert call_args[2] == "admin-agent"

    async def test_db_exception_returns_false(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("boom"))
        tracker = _tracker_with_conn(conn)
        result = await tracker.mark_verified("mem-err")
        assert result is False


# ---------------------------------------------------------------------------
# verify_checksum
# ---------------------------------------------------------------------------

class TestVerifyChecksum:
    async def test_no_pool_returns_error_dict(self):
        tracker = MemoryProvenanceTracker(postgres_pool=None)
        result = await tracker.verify_checksum("mem-1")
        assert result["match"] is None
        assert "error" in result

    async def test_memory_not_found(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        tracker = _tracker_with_conn(conn)
        result = await tracker.verify_checksum("nonexistent")
        assert result["match"] is None
        assert "error" in result

    async def test_no_provenance_returns_error(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"content": "data", "provenance": None})
        tracker = _tracker_with_conn(conn)
        result = await tracker.verify_checksum("mem-no-prov")
        assert result["match"] is None
        assert "error" in result

    async def test_no_checksum_in_provenance(self):
        prov = json.dumps({"source": "user_input"})
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"content": "data", "provenance": prov})
        tracker = _tracker_with_conn(conn)
        result = await tracker.verify_checksum("mem-no-cs")
        assert result["match"] is None
        assert "error" in result

    async def test_matching_checksum(self):
        content = "original content"
        checksum = hashlib.sha256(content.encode()).hexdigest()
        prov = json.dumps({"checksum": checksum})
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(
            return_value={"content": content, "provenance": prov}
        )
        tracker = _tracker_with_conn(conn)
        result = await tracker.verify_checksum("mem-match")
        assert result["match"] is True
        assert result["stored_checksum"] == checksum
        assert result["actual_checksum"] == checksum
        assert result["memory_id"] == "mem-match"

    async def test_mismatched_checksum(self):
        content = "modified content"
        original = "original content"
        checksum = hashlib.sha256(original.encode()).hexdigest()
        prov = json.dumps({"checksum": checksum})
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(
            return_value={"content": content, "provenance": prov}
        )
        tracker = _tracker_with_conn(conn)
        result = await tracker.verify_checksum("mem-mismatch")
        assert result["match"] is False
        assert result["stored_checksum"] != result["actual_checksum"]

    async def test_dict_provenance_also_works(self):
        """provenance returned as dict (not str) is also handled."""
        content = "dict prov content"
        checksum = hashlib.sha256(content.encode()).hexdigest()
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(
            return_value={
                "content": content,
                "provenance": {"checksum": checksum},
            }
        )
        tracker = _tracker_with_conn(conn)
        result = await tracker.verify_checksum("mem-dict-prov")
        assert result["match"] is True

    async def test_db_exception_returns_error_dict(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=RuntimeError("network error"))
        tracker = _tracker_with_conn(conn)
        result = await tracker.verify_checksum("mem-exc")
        assert result["match"] is None
        assert "error" in result


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------

class TestSingletonHelpers:
    def test_init_returns_tracker(self):
        pool = MagicMock()
        tracker = init_provenance_tracker(pool)
        assert isinstance(tracker, MemoryProvenanceTracker)

    def test_init_sets_singleton(self):
        pool = MagicMock()
        tracker = init_provenance_tracker(pool)
        assert get_provenance_tracker() is tracker

    def test_get_before_init_returns_none_or_instance(self):
        result = get_provenance_tracker()
        assert result is None or isinstance(result, MemoryProvenanceTracker)

    def test_init_twice_replaces_singleton(self):
        pool1 = MagicMock()
        pool2 = MagicMock()
        init_provenance_tracker(pool1)
        tracker2 = init_provenance_tracker(pool2)
        assert get_provenance_tracker() is tracker2
