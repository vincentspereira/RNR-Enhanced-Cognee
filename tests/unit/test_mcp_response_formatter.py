"""
Unit tests for src/mcp_response_formatter.py
Target: >= 85% line coverage.
"""

import json
import pytest
from datetime import timezone
from dateutil import parser as dateutil_parser


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_ts(ts: str):
    """Return a timezone-aware datetime from an ISO 8601 string."""
    return dateutil_parser.isoparse(ts)


# ---------------------------------------------------------------------------
# success_response
# ---------------------------------------------------------------------------

class TestSuccessResponse:
    def test_status_is_success(self):
        from src.mcp_response_formatter import success_response
        r = success_response("hello")
        assert r["status"] == "success"

    def test_data_passthrough(self):
        from src.mcp_response_formatter import success_response
        payload = {"key": "value", "num": 42}
        r = success_response(payload)
        assert r["data"] == payload

    def test_error_is_none(self):
        from src.mcp_response_formatter import success_response
        r = success_response(None)
        assert r["error"] is None

    def test_default_operation(self):
        from src.mcp_response_formatter import success_response
        r = success_response("x")
        assert r["operation"] == "operation"

    def test_custom_operation(self):
        from src.mcp_response_formatter import success_response
        r = success_response("x", operation="add_memory")
        assert r["operation"] == "add_memory"

    def test_timestamp_is_utc_iso(self):
        from src.mcp_response_formatter import success_response
        r = success_response("x")
        ts = _parse_ts(r["timestamp"])
        assert ts.tzinfo is not None

    def test_data_can_be_list(self):
        from src.mcp_response_formatter import success_response
        r = success_response([1, 2, 3])
        assert r["data"] == [1, 2, 3]

    def test_data_can_be_none(self):
        from src.mcp_response_formatter import success_response
        r = success_response(None, operation="noop")
        assert r["status"] == "success"
        assert r["data"] is None


# ---------------------------------------------------------------------------
# error_response
# ---------------------------------------------------------------------------

class TestErrorResponse:
    def test_status_is_error(self):
        from src.mcp_response_formatter import error_response
        r = error_response("something broke")
        assert r["status"] == "error"

    def test_error_message_preserved(self):
        from src.mcp_response_formatter import error_response
        msg = "DB connection failed"
        r = error_response(msg)
        assert r["error"] == msg

    def test_data_is_none(self):
        from src.mcp_response_formatter import error_response
        r = error_response("boom")
        assert r["data"] is None

    def test_default_operation(self):
        from src.mcp_response_formatter import error_response
        r = error_response("boom")
        assert r["operation"] == "operation"

    def test_custom_operation(self):
        from src.mcp_response_formatter import error_response
        r = error_response("boom", operation="search_memories")
        assert r["operation"] == "search_memories"

    def test_timestamp_present(self):
        from src.mcp_response_formatter import error_response
        r = error_response("boom")
        assert "timestamp" in r
        _parse_ts(r["timestamp"])  # must not raise


# ---------------------------------------------------------------------------
# validation_error_response
# ---------------------------------------------------------------------------

class TestValidationErrorResponse:
    def test_status(self):
        from src.mcp_response_formatter import validation_error_response
        r = validation_error_response("bad uuid")
        assert r["status"] == "validation_error"

    def test_error_contains_prefix(self):
        from src.mcp_response_formatter import validation_error_response
        r = validation_error_response("bad uuid")
        assert r["error"].startswith("Validation failed:")

    def test_error_contains_detail(self):
        from src.mcp_response_formatter import validation_error_response
        detail = "UUID must be version 4"
        r = validation_error_response(detail)
        assert detail in r["error"]

    def test_data_is_none(self):
        from src.mcp_response_formatter import validation_error_response
        r = validation_error_response("oops")
        assert r["data"] is None

    def test_custom_operation(self):
        from src.mcp_response_formatter import validation_error_response
        r = validation_error_response("oops", operation="delete_memory")
        assert r["operation"] == "delete_memory"


# ---------------------------------------------------------------------------
# authorization_error_response
# ---------------------------------------------------------------------------

class TestAuthorizationErrorResponse:
    def test_status(self):
        from src.mcp_response_formatter import authorization_error_response
        r = authorization_error_response("no perms")
        assert r["status"] == "authorization_error"

    def test_error_contains_prefix(self):
        from src.mcp_response_formatter import authorization_error_response
        r = authorization_error_response("no perms")
        assert r["error"].startswith("Authorization failed:")

    def test_error_contains_detail(self):
        from src.mcp_response_formatter import authorization_error_response
        detail = "Admin privileges required"
        r = authorization_error_response(detail)
        assert detail in r["error"]

    def test_data_is_none(self):
        from src.mcp_response_formatter import authorization_error_response
        r = authorization_error_response("no perms")
        assert r["data"] is None

    def test_custom_operation(self):
        from src.mcp_response_formatter import authorization_error_response
        r = authorization_error_response("no perms", operation="create_backup")
        assert r["operation"] == "create_backup"


# ---------------------------------------------------------------------------
# confirmation_required_response
# ---------------------------------------------------------------------------

class TestConfirmationRequiredResponse:
    def test_status(self):
        from src.mcp_response_formatter import confirmation_required_response
        r = confirmation_required_response(
            operation="delete_memory",
            confirmation_id="tok_abc",
            details={"memory_id": "m1"}
        )
        assert r["status"] == "confirmation_required"

    def test_data_contains_confirmation_id(self):
        from src.mcp_response_formatter import confirmation_required_response
        r = confirmation_required_response("op", "tok_123", {})
        assert r["data"]["confirmation_id"] == "tok_123"

    def test_data_contains_operation(self):
        from src.mcp_response_formatter import confirmation_required_response
        r = confirmation_required_response("delete_memory", "tok", {})
        assert r["data"]["operation"] == "delete_memory"

    def test_data_contains_details(self):
        from src.mcp_response_formatter import confirmation_required_response
        details = {"memory_id": "abc", "agent_id": "user1"}
        r = confirmation_required_response("delete_memory", "tok", details)
        assert r["data"]["details"] == details

    def test_error_contains_operation(self):
        from src.mcp_response_formatter import confirmation_required_response
        r = confirmation_required_response("delete_memory", "tok", {})
        assert "delete_memory" in r["error"]

    def test_operation_field(self):
        from src.mcp_response_formatter import confirmation_required_response
        r = confirmation_required_response("delete_memory", "tok", {})
        assert r["operation"] == "delete_memory"

    def test_timestamp_present(self):
        from src.mcp_response_formatter import confirmation_required_response
        r = confirmation_required_response("op", "tok", {})
        _parse_ts(r["timestamp"])


# ---------------------------------------------------------------------------
# format_response
# ---------------------------------------------------------------------------

class TestFormatResponse:
    def test_returns_valid_json(self):
        from src.mcp_response_formatter import success_response, format_response
        r = success_response({"k": "v"}, operation="test")
        s = format_response(r)
        parsed = json.loads(s)
        assert parsed["status"] == "success"

    def test_pretty_printed(self):
        from src.mcp_response_formatter import success_response, format_response
        r = success_response("hello")
        s = format_response(r)
        # indent=2 means newlines will be present
        assert "\n" in s

    def test_handles_non_serialisable_with_default_str(self):
        from src.mcp_response_formatter import format_response
        import datetime
        r = {"status": "ok", "data": datetime.datetime(2025, 1, 1)}
        s = format_response(r)
        parsed = json.loads(s)
        assert parsed["status"] == "ok"


# ---------------------------------------------------------------------------
# format_response_compact
# ---------------------------------------------------------------------------

class TestFormatResponseCompact:
    def test_returns_valid_json(self):
        from src.mcp_response_formatter import error_response, format_response_compact
        r = error_response("oops", operation="test")
        s = format_response_compact(r)
        parsed = json.loads(s)
        assert parsed["status"] == "error"

    def test_no_newlines(self):
        from src.mcp_response_formatter import success_response, format_response_compact
        r = success_response({"a": 1})
        s = format_response_compact(r)
        assert "\n" not in s

    def test_no_spaces_after_separators(self):
        from src.mcp_response_formatter import success_response, format_response_compact
        r = success_response({"a": 1})
        s = format_response_compact(r)
        assert ": " not in s  # compact separators strip trailing spaces
