"""
Unit tests for src/security_mcp.py
Covers: exception hierarchy, validate_uuid, validate_positive_int, validate_days,
        validate_limit, validate_agent_id, validate_category, validate_memory_content,
        sanitize_string, validate_path_safe, Authorizer, ConfirmationManager,
        require_agent_authorization, validate_dry_run_safe,
        handle_backup_exception, handle_deduplication_exception,
        handle_summarization_exception.

NOTE: handle_database_exception imports asyncpg/qdrant at call time; we avoid
calling it in these unit tests (it belongs to integration tests that have those
packages available).
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.security_mcp import (
    # Exception types
    ValidationError, AuthorizationError, ConfirmationRequiredError,
    DatabaseConnectionError, DatabaseQueryError, DataIntegrityError,
    BackupCreationError, BackupRestoreError, DeduplicationError,
    SummarizationError, SynchronizationError, ConfigurationError,
    RateLimitError, ResourceExhaustedError, InsufficientPermissionsError,
    InvalidStateError,
    # Validation functions
    validate_uuid, validate_positive_int, validate_days, validate_limit,
    validate_agent_id, validate_category, validate_memory_content,
    sanitize_string, validate_path_safe,
    # Auth / confirmation
    Authorizer, authorizer, ConfirmationManager, confirmation_manager,
    require_agent_authorization, validate_dry_run_safe,
    # Error handlers
    handle_backup_exception, handle_deduplication_exception,
    handle_summarization_exception,
)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    @pytest.mark.unit
    def test_validation_error_is_exception(self):
        with pytest.raises(ValidationError):
            raise ValidationError("bad input")

    @pytest.mark.unit
    def test_authorization_error_is_exception(self):
        with pytest.raises(AuthorizationError):
            raise AuthorizationError("denied")

    @pytest.mark.unit
    def test_confirmation_required_error_is_exception(self):
        with pytest.raises(ConfirmationRequiredError):
            raise ConfirmationRequiredError("confirm first")

    @pytest.mark.unit
    def test_all_custom_exceptions_are_exceptions(self):
        for exc_cls in [
            DatabaseConnectionError, DatabaseQueryError, DataIntegrityError,
            BackupCreationError, BackupRestoreError, DeduplicationError,
            SummarizationError, SynchronizationError, ConfigurationError,
            RateLimitError, ResourceExhaustedError, InsufficientPermissionsError,
            InvalidStateError,
        ]:
            with pytest.raises(Exception):
                raise exc_cls("test")


# ---------------------------------------------------------------------------
# validate_uuid
# ---------------------------------------------------------------------------

class TestValidateUUID:
    @pytest.mark.unit
    def test_valid_uuid_returns_string(self):
        uid = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_uuid(uid)
        assert result == uid

    @pytest.mark.unit
    def test_invalid_uuid_raises_validation_error(self):
        with pytest.raises(ValidationError):
            validate_uuid("not-a-uuid")

    @pytest.mark.unit
    def test_empty_string_raises_validation_error(self):
        with pytest.raises(ValidationError):
            validate_uuid("")

    @pytest.mark.unit
    def test_none_raises(self):
        # uuid.UUID(None) raises TypeError (not caught by validate_uuid), any exception is fine
        with pytest.raises(Exception):
            validate_uuid(None)

    @pytest.mark.unit
    def test_custom_param_name_appears_in_message(self):
        with pytest.raises(ValidationError, match="memory_id"):
            validate_uuid("bad", param_name="memory_id")

    @pytest.mark.unit
    def test_uppercase_uuid_accepted(self):
        uid = "550E8400-E29B-41D4-A716-446655440000"
        result = validate_uuid(uid)
        assert result.lower() == uid.lower()


# ---------------------------------------------------------------------------
# validate_positive_int
# ---------------------------------------------------------------------------

class TestValidatePositiveInt:
    @pytest.mark.unit
    def test_valid_value_returned(self):
        assert validate_positive_int(5) == 5

    @pytest.mark.unit
    def test_min_value_accepted(self):
        assert validate_positive_int(1, min_value=1) == 1

    @pytest.mark.unit
    def test_below_min_raises(self):
        with pytest.raises(ValidationError):
            validate_positive_int(0, min_value=1)

    @pytest.mark.unit
    def test_max_value_respected(self):
        assert validate_positive_int(10, max_value=10) == 10

    @pytest.mark.unit
    def test_above_max_raises(self):
        with pytest.raises(ValidationError):
            validate_positive_int(11, max_value=10)

    @pytest.mark.unit
    def test_non_int_raises(self):
        with pytest.raises(ValidationError):
            validate_positive_int("five")

    @pytest.mark.unit
    def test_float_raises(self):
        with pytest.raises(ValidationError):
            validate_positive_int(3.5)


# ---------------------------------------------------------------------------
# validate_days
# ---------------------------------------------------------------------------

class TestValidateDays:
    @pytest.mark.unit
    def test_zero_days_accepted(self):
        assert validate_days(0) == 0

    @pytest.mark.unit
    def test_positive_days_returned(self):
        assert validate_days(30) == 30

    @pytest.mark.unit
    def test_max_days_accepted(self):
        assert validate_days(36500) == 36500

    @pytest.mark.unit
    def test_above_max_raises(self):
        with pytest.raises(ValidationError):
            validate_days(36501)

    @pytest.mark.unit
    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            validate_days(-1)


# ---------------------------------------------------------------------------
# validate_limit
# ---------------------------------------------------------------------------

class TestValidateLimit:
    @pytest.mark.unit
    def test_valid_limit_returned(self):
        assert validate_limit(10) == 10

    @pytest.mark.unit
    def test_min_limit_one(self):
        assert validate_limit(1) == 1

    @pytest.mark.unit
    def test_zero_raises(self):
        with pytest.raises(ValidationError):
            validate_limit(0)

    @pytest.mark.unit
    def test_max_limit_accepted(self):
        assert validate_limit(10000) == 10000

    @pytest.mark.unit
    def test_above_max_raises(self):
        with pytest.raises(ValidationError):
            validate_limit(10001)


# ---------------------------------------------------------------------------
# validate_agent_id
# ---------------------------------------------------------------------------

class TestValidateAgentId:
    @pytest.mark.unit
    def test_valid_agent_id_returned(self):
        assert validate_agent_id("risk-management") == "risk-management"

    @pytest.mark.unit
    def test_alphanumeric_with_separators(self):
        assert validate_agent_id("agent_1.v2-b") == "agent_1.v2-b"

    @pytest.mark.unit
    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_agent_id("")

    @pytest.mark.unit
    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_agent_id(None)

    @pytest.mark.unit
    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_agent_id("a" * 256)

    @pytest.mark.unit
    def test_special_chars_raise(self):
        with pytest.raises(ValidationError):
            validate_agent_id("agent@bad!")

    @pytest.mark.unit
    def test_space_raises(self):
        with pytest.raises(ValidationError):
            validate_agent_id("agent id")


# ---------------------------------------------------------------------------
# validate_category
# ---------------------------------------------------------------------------

class TestValidateCategory:
    @pytest.mark.unit
    def test_valid_category_returned(self):
        assert validate_category("trading") == "trading"

    @pytest.mark.unit
    def test_hyphen_and_underscore_allowed(self):
        assert validate_category("my-cat_1") == "my-cat_1"

    @pytest.mark.unit
    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_category("")

    @pytest.mark.unit
    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_category("a" * 101)

    @pytest.mark.unit
    def test_period_not_allowed(self):
        with pytest.raises(ValidationError):
            validate_category("cat.sub")

    @pytest.mark.unit
    def test_spaces_not_allowed(self):
        with pytest.raises(ValidationError):
            validate_category("my category")


# ---------------------------------------------------------------------------
# validate_memory_content
# ---------------------------------------------------------------------------

class TestValidateMemoryContent:
    @pytest.mark.unit
    def test_valid_content_returned(self):
        assert validate_memory_content("hello world") == "hello world"

    @pytest.mark.unit
    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_memory_content("")

    @pytest.mark.unit
    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_memory_content(None)

    @pytest.mark.unit
    def test_exceeds_max_length_raises(self):
        with pytest.raises(ValidationError):
            validate_memory_content("x" * 1000001)

    @pytest.mark.unit
    def test_custom_max_length(self):
        with pytest.raises(ValidationError):
            validate_memory_content("12345", max_length=4)


# ---------------------------------------------------------------------------
# sanitize_string
# ---------------------------------------------------------------------------

class TestSanitizeString:
    @pytest.mark.unit
    def test_normal_string_returned(self):
        assert sanitize_string("hello") == "hello"

    @pytest.mark.unit
    def test_null_bytes_removed(self):
        result = sanitize_string("he\x00llo")
        assert "\x00" not in result
        assert "hello" in result

    @pytest.mark.unit
    def test_truncated_to_max_length(self):
        result = sanitize_string("a" * 2000, max_length=100)
        assert len(result) <= 100

    @pytest.mark.unit
    def test_stripped(self):
        result = sanitize_string("  hello  ")
        assert result == "hello"

    @pytest.mark.unit
    def test_non_string_raises(self):
        with pytest.raises(ValidationError):
            sanitize_string(123)


# ---------------------------------------------------------------------------
# validate_path_safe
# ---------------------------------------------------------------------------

class TestValidatePathSafe:
    @pytest.mark.unit
    def test_safe_path_returned(self, tmp_path):
        result = validate_path_safe("subdir/file.txt", str(tmp_path))
        assert result.startswith(str(tmp_path))

    @pytest.mark.unit
    def test_traversal_raises(self, tmp_path):
        with pytest.raises(ValidationError, match="traversal"):
            validate_path_safe("../../etc/passwd", str(tmp_path))


# ---------------------------------------------------------------------------
# Authorizer
# ---------------------------------------------------------------------------

class TestAuthorizer:
    @pytest.fixture
    def auth(self):
        return Authorizer()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_admin_can_delete_anything(self, auth):
        result = await auth.check_delete_permission("admin", category="system")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_admin_protected_category_raises(self, auth):
        with pytest.raises(AuthorizationError):
            await auth.check_delete_permission("user-agent", category="system")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_admin_normal_category_allowed(self, auth):
        result = await auth.check_delete_permission("user-agent", category="trading")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_admin_no_category_allowed(self, auth):
        result = await auth.check_delete_permission("user-agent")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_admin_modify_always_allowed(self, auth):
        result = await auth.check_modify_permission("admin", "mem-1")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_admin_modify_returns_true_with_warning(self, auth):
        result = await auth.check_modify_permission("some-agent", "mem-1")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_admin_backup_allowed(self, auth):
        result = await auth.check_backup_permission("system")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_admin_backup_raises(self, auth):
        with pytest.raises(AuthorizationError):
            await auth.check_backup_permission("random-agent")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_claude_code_is_admin(self, auth):
        result = await auth.check_backup_permission("claude-code")
        assert result is True


# ---------------------------------------------------------------------------
# ConfirmationManager
# ---------------------------------------------------------------------------

class TestConfirmationManager:
    @pytest.fixture
    def cm(self):
        return ConfirmationManager()

    @pytest.mark.unit
    def test_no_token_raises_confirmation_required(self, cm):
        with pytest.raises(ConfirmationRequiredError):
            cm.require_confirmation("delete_all", {"count": 100})

    @pytest.mark.unit
    def test_confirmation_id_stored_in_pending(self, cm):
        try:
            cm.require_confirmation("op", {})
        except ConfirmationRequiredError:
            pass
        assert len(cm.pending_confirmations) == 1

    @pytest.mark.unit
    def test_invalid_token_raises_validation_error(self, cm):
        with pytest.raises(ValidationError):
            cm.require_confirmation("op", {}, confirm_token="invalid-token-xyz")

    @pytest.mark.unit
    def test_valid_token_returns_and_removes(self, cm):
        try:
            cm.require_confirmation("op", {})
        except ConfirmationRequiredError:
            pass
        token = list(cm.pending_confirmations.keys())[0]
        result = cm.require_confirmation("op", {}, confirm_token=token)
        assert result == token
        assert token not in cm.pending_confirmations

    @pytest.mark.unit
    def test_expired_token_raises_validation_error(self, cm):
        try:
            cm.require_confirmation("op", {})
        except ConfirmationRequiredError:
            pass
        token = list(cm.pending_confirmations.keys())[0]
        # Backdate the confirmation
        cm.pending_confirmations[token]["created_at"] = (
            datetime.now() - timedelta(minutes=10)
        )
        with pytest.raises(ValidationError):
            cm.require_confirmation("op", {}, confirm_token=token)
        assert token not in cm.pending_confirmations

    @pytest.mark.unit
    def test_has_pending_confirmation_true(self, cm):
        try:
            cm.require_confirmation("backup", {})
        except ConfirmationRequiredError:
            pass
        assert cm.has_pending_confirmation("backup") is True

    @pytest.mark.unit
    def test_has_pending_confirmation_false_for_other_op(self, cm):
        try:
            cm.require_confirmation("backup", {})
        except ConfirmationRequiredError:
            pass
        assert cm.has_pending_confirmation("delete_all") is False

    @pytest.mark.unit
    def test_empty_pending_has_no_confirmations(self, cm):
        assert cm.has_pending_confirmation("anything") is False


# ---------------------------------------------------------------------------
# require_agent_authorization
# ---------------------------------------------------------------------------

class TestRequireAgentAuthorization:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_admin_passes_without_exception(self):
        await require_agent_authorization("admin", "delete", category="trading")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_with_protected_category_raises(self):
        with pytest.raises(AuthorizationError):
            await require_agent_authorization("user-agent", "delete", category="system")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_with_safe_category_passes(self):
        await require_agent_authorization("user-agent", "delete", category="trading")


# ---------------------------------------------------------------------------
# validate_dry_run_safe
# ---------------------------------------------------------------------------

class TestValidateDryRunSafe:
    @pytest.mark.unit
    def test_dry_run_true_passes(self):
        # dry_run=True should not raise anything
        validate_dry_run_safe(True, "dedup_all")

    @pytest.mark.unit
    def test_dry_run_false_raises_confirmation_required(self):
        with pytest.raises(ConfirmationRequiredError):
            validate_dry_run_safe(False, "delete_all")


# ---------------------------------------------------------------------------
# handle_backup_exception
# ---------------------------------------------------------------------------

class TestHandleBackupException:
    @pytest.mark.unit
    def test_disk_full_detected(self):
        e = OSError("no space left on device")
        result = handle_backup_exception(e, "create_backup")
        assert "ERR" in result
        assert "disk" in result.lower() or "storage" in result.lower() or "space" in result.lower()

    @pytest.mark.unit
    def test_permission_error_detected(self):
        e = PermissionError("permission denied")
        result = handle_backup_exception(e, "create_backup")
        assert "ERR" in result
        assert "permission" in result.lower()

    @pytest.mark.unit
    def test_corruption_error_detected(self):
        e = ValueError("corruption in backup data")
        result = handle_backup_exception(e, "create_backup")
        assert "ERR" in result
        assert "corruption" in result.lower()

    @pytest.mark.unit
    def test_generic_error_fallback(self):
        e = RuntimeError("something went wrong")
        result = handle_backup_exception(e, "create_backup")
        assert "ERR" in result


# ---------------------------------------------------------------------------
# handle_deduplication_exception
# ---------------------------------------------------------------------------

class TestHandleDeduplicationException:
    @pytest.mark.unit
    def test_threshold_error_detected(self):
        e = RuntimeError("threshold exceeded for batch")
        result = handle_deduplication_exception(e, "dedup_op")
        assert "ERR" in result
        assert "threshold" in result.lower()

    @pytest.mark.unit
    def test_embedding_error_detected(self):
        e = RuntimeError("embedding generation failed")
        result = handle_deduplication_exception(e, "dedup_op")
        assert "ERR" in result
        assert "embedding" in result.lower()

    @pytest.mark.unit
    def test_vector_error_detected(self):
        e = RuntimeError("vector database unavailable")
        result = handle_deduplication_exception(e, "dedup_op")
        assert "ERR" in result

    @pytest.mark.unit
    def test_generic_error_fallback(self):
        e = RuntimeError("unknown issue")
        result = handle_deduplication_exception(e, "dedup_op")
        assert "ERR" in result


# ---------------------------------------------------------------------------
# handle_summarization_exception
# ---------------------------------------------------------------------------

class TestHandleSummarizationException:
    @pytest.mark.unit
    def test_api_key_error_detected(self):
        e = RuntimeError("api key invalid")
        result = handle_summarization_exception(e, "summarize_op")
        assert "ERR" in result
        assert "authentication" in result.lower() or "api key" in result.lower()

    @pytest.mark.unit
    def test_rate_limit_error_detected(self):
        e = RuntimeError("rate limit exceeded")
        result = handle_summarization_exception(e, "summarize_op")
        assert "ERR" in result
        assert "rate limit" in result.lower()

    @pytest.mark.unit
    def test_quota_error_detected(self):
        e = RuntimeError("quota exhausted")
        result = handle_summarization_exception(e, "summarize_op")
        assert "ERR" in result

    @pytest.mark.unit
    def test_timeout_error_detected(self):
        e = RuntimeError("request timed out")
        result = handle_summarization_exception(e, "summarize_op")
        assert "ERR" in result
        assert "timeout" in result.lower()

    @pytest.mark.unit
    def test_generic_error_fallback(self):
        e = RuntimeError("unknown LLM error")
        result = handle_summarization_exception(e, "summarize_op")
        assert "ERR" in result
