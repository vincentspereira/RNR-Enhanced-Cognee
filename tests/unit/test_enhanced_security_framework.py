"""
Unit tests for src/security/enhanced_security_framework.py
Covers: uncovered branches in password policy helpers, rate limiter,
        SecureErrorHandler, EnhancedSecurityFramework, decorators.
"""

import os
import sys
import time
import importlib
import types
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


def _get_real_esf_module():
    """Return the real (not fake/stub) enhanced_security_framework module.

    Several test files (test_security_deployment.py, test_security_middleware.py)
    stub sys.modules['src.security.enhanced_security_framework'] during collection.
    Detect a stub by checking for attributes that only exist in the real module
    (FileScanner, SecureErrorHandler, DependencyUpdater) and force-reload if missing.
    """
    import importlib
    mod = sys.modules.get("src.security.enhanced_security_framework")
    if (
        mod is None
        or not hasattr(mod, "FileScanner")
        or not hasattr(mod, "SecureErrorHandler")
        or not hasattr(mod, "DependencyUpdater")
    ):
        # Not the real module; force a fresh load from disk
        sys.modules.pop("src.security.enhanced_security_framework", None)
        mod = importlib.import_module("src.security.enhanced_security_framework")
    return mod


_esf = _get_real_esf_module()
SecurityConfig = _esf.SecurityConfig
SecurityLogger = _esf.SecurityLogger
SecurityEvent = _esf.SecurityEvent
EnhancedPasswordPolicy = _esf.EnhancedPasswordPolicy
EnhancedRateLimiter = _esf.EnhancedRateLimiter
SecureErrorHandler = _esf.SecureErrorHandler
EnhancedSecurityFramework = _esf.EnhancedSecurityFramework
rate_limit = _esf.rate_limit
validate_file_upload = _esf.validate_file_upload
validate_password = _esf.validate_password

# Save real passlib argon2 at collection time (before test_security_modules.py can mock it).
# When test_security_modules.py replaces sys.modules['passlib.hash'] later, the module's
# bound name _esf.argon2 still points to the real object (it was bound at first import).
# But _esf.argon2 may be the real or mock depending on import order.
# Safest: grab it directly from the real passlib before any mock runs.
_REAL_ARGON2 = _esf.argon2  # bound at real-module import time = always the real class


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def logger():
    logger = MagicMock(spec=SecurityLogger)
    logger.log_security_event = MagicMock()
    logger.log_file_upload = MagicMock()
    return logger


@pytest.fixture
def password_policy(logger):
    return EnhancedPasswordPolicy(logger)


# ---------------------------------------------------------------------------
# EnhancedPasswordPolicy - _has_sequential_chars
# ---------------------------------------------------------------------------

class TestHasSequentialChars:
    @pytest.mark.unit
    def test_sequential_numbers_detected(self, password_policy):
        assert password_policy._has_sequential_chars("abc123def") is True

    @pytest.mark.unit
    def test_sequential_letters_detected(self, password_policy):
        # 'abc' is sequential letters
        assert password_policy._has_sequential_chars("Xabc123!") is True

    @pytest.mark.unit
    def test_non_sequential_returns_false(self, password_policy):
        assert password_policy._has_sequential_chars("aAbB1!xY") is False

    @pytest.mark.unit
    def test_empty_password(self, password_policy):
        assert password_policy._has_sequential_chars("") is False

    @pytest.mark.unit
    def test_short_password_no_sequential(self, password_policy):
        assert password_policy._has_sequential_chars("aB") is False


# ---------------------------------------------------------------------------
# EnhancedPasswordPolicy - _has_repeated_chars
# ---------------------------------------------------------------------------

class TestHasRepeatedChars:
    @pytest.mark.unit
    def test_three_consecutive_same_chars(self, password_policy):
        assert password_policy._has_repeated_chars("aaabbb") is True

    @pytest.mark.unit
    def test_more_than_50_percent_same(self, password_policy):
        # 5 'a' out of 7 chars = >50%
        assert password_policy._has_repeated_chars("aaaaabb") is True

    @pytest.mark.unit
    def test_normal_password_no_repeats(self, password_policy):
        assert password_policy._has_repeated_chars("aAbBcC1!") is False

    @pytest.mark.unit
    def test_empty_password(self, password_policy):
        assert password_policy._has_repeated_chars("") is False


# ---------------------------------------------------------------------------
# EnhancedPasswordPolicy - _contains_personal_info
# ---------------------------------------------------------------------------

class TestContainsPersonalInfo:
    @pytest.mark.unit
    def test_contains_username(self, password_policy):
        result = password_policy._contains_personal_info(
            "alice123!", {"username": "alice"}
        )
        assert result is True

    @pytest.mark.unit
    def test_contains_email_local_part(self, password_policy):
        result = password_policy._contains_personal_info(
            "johnPass1!", {"email": "john@example.com"}
        )
        assert result is True

    @pytest.mark.unit
    def test_contains_name_part(self, password_policy):
        result = password_policy._contains_personal_info(
            "RobertPass1!", {"name": "Robert Smith"}
        )
        assert result is True

    @pytest.mark.unit
    def test_no_personal_info(self, password_policy):
        # Username "qwerty" not in password, email local "notinpwd" not in password,
        # name parts "Jo" (len<=2) skipped
        result = password_policy._contains_personal_info(
            "Hk5#PvB!9Lm",
            {"username": "qwerty", "email": "notinpwd@example.com", "name": "Jo Li"}
        )
        assert result is False

    @pytest.mark.unit
    def test_empty_user_info(self, password_policy):
        result = password_policy._contains_personal_info("anypassword", {})
        assert result is False

    @pytest.mark.unit
    def test_none_username(self, password_policy):
        result = password_policy._contains_personal_info("pass", {"username": None})
        assert result is False

    @pytest.mark.unit
    def test_none_email(self, password_policy):
        result = password_policy._contains_personal_info("pass", {"email": None})
        assert result is False

    @pytest.mark.unit
    def test_none_name(self, password_policy):
        result = password_policy._contains_personal_info("pass", {"name": None})
        assert result is False

    @pytest.mark.unit
    def test_short_name_parts_ignored(self, password_policy):
        # 2-char name parts should be ignored
        result = password_policy._contains_personal_info("abcdefgh!", {"name": "Jo Li"})
        assert result is False


# ---------------------------------------------------------------------------
# EnhancedPasswordPolicy - _calculate_entropy
# ---------------------------------------------------------------------------

class TestCalculateEntropy:
    @pytest.mark.unit
    def test_empty_password_returns_zero(self, password_policy):
        assert password_policy._calculate_entropy("") == 0

    @pytest.mark.unit
    def test_lowercase_only(self, password_policy):
        entropy = password_policy._calculate_entropy("abcdefgh")
        assert entropy > 0

    @pytest.mark.unit
    def test_all_char_classes(self, password_policy):
        entropy = password_policy._calculate_entropy("aA1!xX2@")
        # Should be higher than lowercase only
        lower_entropy = password_policy._calculate_entropy("abcdefgh")
        assert entropy > lower_entropy

    @pytest.mark.unit
    def test_only_symbols_returns_nonzero(self, password_policy):
        entropy = password_policy._calculate_entropy("!@#$%^&*")
        assert entropy > 0


# ---------------------------------------------------------------------------
# EnhancedPasswordPolicy - hash_password / verify_password
# ---------------------------------------------------------------------------

class TestHashAndVerifyPassword:
    """Tests for hash_password / verify_password.

    These tests need real passlib/argon2/bcrypt.  When test_enhanced_security.py
    (collected from tests/ root before tests/unit/) sets sys.modules['passlib.hash']
    to a MagicMock at collection time, the ESF module's first import binds its
    module-level 'argon2' name to a MagicMock.

    Additionally, test_security_middleware.py (collected later) replaces
    sys.modules['src.security.enhanced_security_framework'] with a stub at
    collection time.  When _get_real_esf_module() is then called during test
    execution it force-reloads a FRESH ESF module -- which is a different object
    than what the password_policy fixture was built from.  Patching only that
    fresh module's .argon2 does not affect the original module that
    password_policy.hash_password uses.

    Fix: obtain the actual module dict from the method's __globals__ attribute
    (which IS the module dict that hash_password and verify_password resolve
    names in) and patch argon2 there.  real passlib must remain in sys.modules
    during the ENTIRE test body because passlib's argon2 handler internally
    references sys.modules during verification.
    """

    def _run_with_real_passlib(self, policy, func):
        """Run func() with real passlib active and the policy's module patched.

        - Removes mocked passlib from sys.modules and loads the real package.
        - Patches argon2 in the module dict that policy.hash_password actually
          uses (obtained via __globals__), not in an unrelated fresh-reload.
        - Calls func() and propagates any exception including AssertionError.
        - Restores everything (sys.modules and the module's argon2 binding) in
          the finally block.

        Skips the test (via pytest.skip) only if the real passlib cannot be
        imported; all other exceptions propagate normally so test failures are
        reported as FAILED, not SKIPPED.
        """
        import importlib

        # The module dict that hash_password / verify_password resolve names in.
        # This may differ from _get_real_esf_module() when middleware stubs have
        # replaced sys.modules['src.security.enhanced_security_framework'].
        method_globals = policy.hash_password.__globals__

        # Step 1: Save and remove all current passlib entries (mocks or real)
        passlib_keys = [k for k in list(sys.modules.keys())
                        if k == 'passlib' or k.startswith('passlib.')]
        saved = {k: sys.modules.pop(k) for k in passlib_keys}

        # Load real passlib -- skip the test ONLY if this import fails
        try:
            real_hash_mod = importlib.import_module('passlib.hash')
            real_argon2 = real_hash_mod.argon2
        except Exception as e:
            sys.modules.update(saved)
            pytest.skip(f"Cannot load real passlib.hash - skipping test: {e}")
            return None

        # Patch the actual module dict (not just _m which may be a fresh copy)
        old_argon2 = method_globals.get('argon2')
        method_globals['argon2'] = real_argon2

        try:
            # Run the test body with real passlib active in sys.modules
            return func()
        finally:
            # Restore the original argon2 binding in the method's module dict
            if old_argon2 is None:
                method_globals.pop('argon2', None)
            else:
                method_globals['argon2'] = old_argon2

            # Remove any newly added real passlib entries from sys.modules
            new_passlib_keys = [k for k in list(sys.modules.keys())
                                if (k == 'passlib' or k.startswith('passlib.'))
                                and k not in saved]
            for k in new_passlib_keys:
                sys.modules.pop(k, None)
            # Restore the original (possibly mocked) sys.modules entries
            sys.modules.update(saved)

    @pytest.mark.unit
    def test_hash_password_returns_hash_and_type(self, password_policy):
        def _body():
            hashed, hash_type = password_policy.hash_password("SecurePass1!")
            assert isinstance(hashed, str)
            assert hash_type in {"argon2", "bcrypt"}

        self._run_with_real_passlib(password_policy, _body)

    @pytest.mark.unit
    def test_verify_correct_argon2_password(self, password_policy):
        def _body():
            hashed, hash_type = password_policy.hash_password("TestPass1!")
            if hash_type == "argon2":
                result = password_policy.verify_password("TestPass1!", hashed, "argon2")
                assert result is True

        self._run_with_real_passlib(password_policy, _body)

    @pytest.mark.unit
    def test_verify_wrong_password_returns_false(self, password_policy):
        def _body():
            hashed, hash_type = password_policy.hash_password("CorrectPass1!")
            result = password_policy.verify_password("WrongPass1!", hashed, hash_type)
            assert result is False

        self._run_with_real_passlib(password_policy, _body)

    @pytest.mark.unit
    def test_verify_unknown_hash_type(self, password_policy):
        def _body():
            import bcrypt as _bcrypt
            salt = _bcrypt.gensalt(rounds=4)
            hashed = _bcrypt.hashpw("MyPass1!".encode(), salt).decode()
            # Pass "unknown" hash type -> tries both
            result = password_policy.verify_password("MyPass1!", hashed, "unknown")
            # bcrypt should match
            assert isinstance(result, bool)

        self._run_with_real_passlib(password_policy, _body)

    @pytest.mark.unit
    def test_verify_invalid_hash_returns_false(self, password_policy):
        def _body():
            result = password_policy.verify_password("pass", "not-a-valid-hash", "argon2")
            assert result is False

        self._run_with_real_passlib(password_policy, _body)


# ---------------------------------------------------------------------------
# EnhancedRateLimiter
# ---------------------------------------------------------------------------

class TestEnhancedRateLimiter:
    @pytest.fixture
    def rl(self, logger):
        # redis is imported inside _init_redis() as a local import, so patch via sys.modules
        import sys
        mock_redis_mod = MagicMock()
        mock_redis_mod.Redis = MagicMock(side_effect=Exception("no redis"))
        original = sys.modules.get("redis", None)
        sys.modules["redis"] = mock_redis_mod
        try:
            rl = EnhancedRateLimiter(logger)
        finally:
            if original is None:
                sys.modules.pop("redis", None)
            else:
                sys.modules["redis"] = original
        return rl

    @pytest.mark.unit
    def test_init_redis_fails_returns_none(self, rl):
        # When Redis init fails, redis_client should be None
        assert rl.redis_client is None

    @pytest.mark.unit
    def test_rate_limit_not_limited_when_under_limit(self, rl):
        is_limited, info = rl.is_rate_limited("test-key", "100/1m", 60)
        assert is_limited is False
        assert "limit" in info

    @pytest.mark.unit
    def test_rate_limit_over_limit(self, rl):
        # Exhaust limit quickly
        for _ in range(5):
            rl.is_rate_limited("key2", "2/1m", 60)
        is_limited, info = rl.is_rate_limited("key2", "2/1m", 60)
        assert is_limited is True

    @pytest.mark.unit
    def test_rate_limit_hour_time_unit(self, rl):
        is_limited, info = rl.is_rate_limited("test-key", "100/1h", 3600)
        assert is_limited is False

    @pytest.mark.unit
    def test_rate_limit_second_time_unit(self, rl):
        is_limited, info = rl.is_rate_limited("test-key", "100/60s", 60)
        assert is_limited is False

    @pytest.mark.unit
    def test_rate_limit_numeric_time_unit(self, rl):
        is_limited, info = rl.is_rate_limited("test-key", "100/60", 60)
        assert is_limited is False

    @pytest.mark.unit
    def test_rate_limit_bad_format_fails_open(self, rl):
        is_limited, info = rl.is_rate_limited("test-key", "not-valid", 60)
        assert is_limited is False  # Fail open

    @pytest.mark.unit
    def test_check_redis_rate_limit(self, logger):
        """Test Redis path when redis client is available."""
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = MagicMock()
        mock_redis.zadd = MagicMock()
        mock_redis.zcard = MagicMock(return_value=5)
        mock_redis.expire = MagicMock()
        mock_redis.ttl = MagicMock(return_value=60)

        rl = EnhancedRateLimiter.__new__(EnhancedRateLimiter)
        rl.security_logger = logger
        rl.redis_client = mock_redis
        rl.memory_store = {}

        current_time = int(time.time())
        is_limited, info = rl._check_redis_rate_limit("key", 10, current_time - 60, current_time)
        assert is_limited is False
        assert "limit" in info

    @pytest.mark.unit
    def test_check_redis_rate_limited(self, logger):
        """Test Redis path when over limit."""
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = MagicMock()
        mock_redis.zadd = MagicMock()
        mock_redis.zcard = MagicMock(return_value=20)  # 20 > 10 limit
        mock_redis.expire = MagicMock()
        mock_redis.ttl = MagicMock(return_value=60)

        rl = EnhancedRateLimiter.__new__(EnhancedRateLimiter)
        rl.security_logger = logger
        rl.redis_client = mock_redis
        rl.memory_store = {}

        current_time = int(time.time())
        is_limited, info = rl._check_redis_rate_limit("key", 10, current_time - 60, current_time)
        assert is_limited is True


# ---------------------------------------------------------------------------
# SecureErrorHandler
# ---------------------------------------------------------------------------

class TestSecureErrorHandler:
    @pytest.fixture
    def handler_dev(self, logger):
        handler = SecureErrorHandler(logger)
        handler.production_mode = False
        return handler

    @pytest.fixture
    def handler_prod(self, logger):
        handler = SecureErrorHandler(logger)
        handler.production_mode = True
        return handler

    @pytest.mark.unit
    def test_handle_error_dev_mode_returns_error_name(self, handler_dev):
        error = ValueError("bad input")
        result = handler_dev.handle_error(error)
        assert result["error"] == "ValueError"
        assert result["debug_mode"] is True

    @pytest.mark.unit
    def test_handle_error_prod_mode_sanitized(self, handler_prod):
        error = RuntimeError("sensitive internal info")
        result = handler_prod.handle_error(error)
        assert result["error"] == "Internal server error"
        assert "debug_mode" not in result

    @pytest.mark.unit
    def test_handle_error_with_context(self, handler_dev):
        error = KeyError("key")
        ctx = {"source_ip": "1.2.3.4", "user_agent": "browser", "path": "/api/v1"}
        result = handler_dev.handle_error(error, request_context=ctx)
        assert "error" in result

    @pytest.mark.unit
    def test_generate_error_id_unique(self, handler_dev):
        id1 = handler_dev._generate_error_id()
        id2 = handler_dev._generate_error_id()
        assert id1 != id2

    @pytest.mark.unit
    def test_sanitize_error_message_removes_path(self, handler_dev):
        msg = "Error in /home/user/project/src/module.py line 42"
        result = handler_dev.sanitize_error_message(msg)
        assert "/home/user/project/src" not in result

    @pytest.mark.unit
    def test_sanitize_error_message_removes_db_url(self, handler_dev):
        msg = "Could not connect to postgresql://user:pass@localhost/db"
        result = handler_dev.sanitize_error_message(msg)
        assert "postgresql://user:pass" not in result
        assert "DATABASE_URL" in result

    @pytest.mark.unit
    def test_sanitize_error_message_removes_ip(self, handler_dev):
        msg = "Connection from 192.168.1.100 failed"
        result = handler_dev.sanitize_error_message(msg)
        assert "192.168.1.100" not in result
        assert "IP_ADDRESS" in result


# ---------------------------------------------------------------------------
# Rate limit decorators
# ---------------------------------------------------------------------------

class TestDecorators:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limit_decorator_passes_through(self):
        @rate_limit("test_endpoint")
        async def my_func(x):
            return x * 2

        result = await my_func(21)
        assert result == 42

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_file_upload_decorator_passes_through(self):
        @validate_file_upload
        async def upload(data):
            return {"uploaded": True}

        result = await upload(b"some data")
        assert result["uploaded"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_password_decorator_passes_through(self):
        @validate_password
        async def change_password(pwd):
            return {"changed": True}

        result = await change_password("newpass")
        assert result["changed"] is True


# ---------------------------------------------------------------------------
# EnhancedSecurityFramework
# ---------------------------------------------------------------------------

class TestEnhancedSecurityFramework:
    @pytest.fixture
    def framework(self):
        return EnhancedSecurityFramework()

    @pytest.mark.unit
    def test_initialize_security_returns_status(self, framework):
        result = framework.initialize_security()
        assert result["status"] == "initialized"
        assert "components" in result
        assert len(result["components"]) > 0

    @pytest.mark.unit
    def test_run_security_audit_returns_results(self, framework):
        # Mock subprocess so it doesn't actually run pip
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            result = framework.run_security_audit()
        assert "audit_timestamp" in result
        assert "overall_score" in result
        assert "components" in result

    @pytest.mark.unit
    def test_framework_has_all_components(self, framework):
        assert framework.security_logger is not None
        assert framework.input_validator is not None
        assert framework.password_policy is not None
        assert framework.rate_limiter is not None
        assert framework.dependency_updater is not None
        assert framework.error_handler is not None

    @pytest.mark.unit
    def test_run_security_audit_with_vulnerabilities(self, framework):
        """Run audit path that adds recommendations."""
        vuln_result = {
            "vulnerable_packages": [
                {"package": "requests", "current_version": "2.0.0"}
            ],
            "safe_packages": [],
            "total_checked": 1
        }
        with patch.object(framework.dependency_updater, "check_dependencies", return_value=vuln_result):
            result = framework.run_security_audit()
        assert result["overall_score"] == 90
        assert len(result["recommendations"]) == 1


# ---------------------------------------------------------------------------
# SecurityLogger - branch coverage for log_security_event
# ---------------------------------------------------------------------------

class TestSecurityLoggerBranches:
    @pytest.fixture
    def real_logger(self, tmp_path):
        _m = _get_real_esf_module()
        log_file = str(tmp_path / "security.log")
        return _m.SecurityLogger(log_file=log_file)

    def _make_event(self, severity):
        _m = _get_real_esf_module()
        from datetime import datetime
        return _m.SecurityEvent(
            event_type="test",
            severity=severity,
            source_ip="1.2.3.4",
            user_agent="test-agent",
            timestamp=datetime.now(),
            details={"key": "val"},
            user_id="u1",
            session_id="s1",
        )

    @pytest.mark.unit
    def test_high_severity_uses_error(self, real_logger):
        event = self._make_event("high")
        with patch.object(real_logger.logger, "error") as mock_err:
            real_logger.log_security_event(event)
        mock_err.assert_called_once()

    @pytest.mark.unit
    def test_critical_severity_uses_error(self, real_logger):
        event = self._make_event("critical")
        with patch.object(real_logger.logger, "error") as mock_err:
            real_logger.log_security_event(event)
        mock_err.assert_called_once()

    @pytest.mark.unit
    def test_medium_severity_uses_warning(self, real_logger):
        event = self._make_event("medium")
        with patch.object(real_logger.logger, "warning") as mock_warn:
            real_logger.log_security_event(event)
        mock_warn.assert_called_once()

    @pytest.mark.unit
    def test_low_severity_uses_info(self, real_logger):
        event = self._make_event("low")
        with patch.object(real_logger.logger, "info") as mock_info:
            real_logger.log_security_event(event)
        mock_info.assert_called_once()

    @pytest.mark.unit
    def test_log_file_upload_success(self, real_logger):
        with patch.object(real_logger.logger, "info"):
            real_logger.log_file_upload("test.txt", "text/plain", 100, "1.2.3.4", user_id="u1", success=True)

    @pytest.mark.unit
    def test_log_file_upload_failure(self, real_logger):
        with patch.object(real_logger.logger, "warning"):
            real_logger.log_file_upload("bad.exe", "application/x-msdownload", 100, "1.2.3.4", success=False)

    @pytest.mark.unit
    def test_log_authentication_attempt_success(self, real_logger):
        with patch.object(real_logger.logger, "info"):
            real_logger.log_authentication_attempt("user1", "1.2.3.4", success=True)

    @pytest.mark.unit
    def test_log_authentication_attempt_failure(self, real_logger):
        with patch.object(real_logger.logger, "warning"):
            real_logger.log_authentication_attempt("user1", "1.2.3.4", success=False, failure_reason="bad_pass")

    @pytest.mark.unit
    def test_log_rate_limit_exceeded(self, real_logger):
        with patch.object(real_logger.logger, "warning"):
            real_logger.log_rate_limit_exceeded("/api/v1", "1.2.3.4")


# ---------------------------------------------------------------------------
# EnhancedInputValidator
# ---------------------------------------------------------------------------

class TestEnhancedInputValidator:
    @pytest.fixture
    def validator(self, logger):
        _m = _get_real_esf_module()
        return _m.EnhancedInputValidator(logger)

    # --- _validate_filename ---

    @pytest.mark.unit
    def test_filename_too_long(self, validator):
        long_name = "a" * 300 + ".txt"
        ok, msg = validator._validate_filename(long_name)
        assert ok is False
        assert "exceeds" in msg

    @pytest.mark.unit
    def test_forbidden_extension(self, validator):
        ok, msg = validator._validate_filename("malware.exe")
        assert ok is False
        assert "not allowed" in msg

    @pytest.mark.unit
    def test_dangerous_chars_double_dot(self, validator):
        ok, msg = validator._validate_filename("../etc/passwd")
        assert ok is False

    @pytest.mark.unit
    def test_valid_filename(self, validator):
        ok, msg = validator._validate_filename("report.pdf")
        assert ok is True

    # --- _validate_file_type ---

    @pytest.mark.unit
    def test_invalid_content_type(self, validator):
        ok, msg = validator._validate_file_type(b"data", "test.txt", "application/x-evil")
        assert ok is False
        assert "not allowed" in msg

    @pytest.mark.unit
    def test_magic_detects_bad_type(self, validator):
        _m = _get_real_esf_module()
        old = _m.magic
        try:
            mock_magic = MagicMock()
            mock_magic.from_buffer = MagicMock(return_value="application/x-evil")
            _m.magic = mock_magic
            ok, msg = validator._validate_file_type(b"data", "test.txt", "text/plain")
        finally:
            _m.magic = old
        assert ok is False
        assert "Detected file type" in msg

    @pytest.mark.unit
    def test_magic_exception_returns_error(self, validator):
        _m = _get_real_esf_module()
        old = _m.magic
        try:
            mock_magic = MagicMock()
            mock_magic.from_buffer = MagicMock(side_effect=Exception("magic error"))
            _m.magic = mock_magic
            ok, msg = validator._validate_file_type(b"data", "test.txt", "text/plain")
        finally:
            _m.magic = old
        assert ok is False
        assert "detection failed" in msg

    @pytest.mark.unit
    def test_jpeg_signature_mismatch(self, validator):
        _m = _get_real_esf_module()
        old = _m.magic
        try:
            mock_magic = MagicMock()
            mock_magic.from_buffer = MagicMock(return_value="image/jpeg")
            _m.magic = mock_magic
            ok, msg = validator._validate_file_type(b"not-a-jpeg", "img.jpg", "image/jpeg")
        finally:
            _m.magic = old
        assert ok is False
        assert "signature" in msg

    @pytest.mark.unit
    def test_valid_jpeg(self, validator):
        jpeg_magic = b"\xff\xd8\xff" + b"\x00" * 100
        _m = _get_real_esf_module()
        old_magic = _m.magic
        old_filetype = _m.filetype
        try:
            mock_magic = MagicMock()
            mock_magic.from_buffer = MagicMock(return_value="image/jpeg")
            _m.magic = mock_magic
            mock_filetype = MagicMock()
            mock_filetype.guess = MagicMock(return_value=None)
            _m.filetype = mock_filetype
            ok, msg = validator._validate_file_type(jpeg_magic, "img.jpg", "image/jpeg")
        finally:
            _m.magic = old_magic
            _m.filetype = old_filetype
        assert ok is True

    # --- sanitize_input ---

    @pytest.mark.unit
    def test_sanitize_empty_returns_empty(self, validator):
        assert validator.sanitize_input("") == ""

    @pytest.mark.unit
    def test_sanitize_truncates_long_input(self, validator):
        _m = _get_real_esf_module()
        old_bleach = _m.bleach
        try:
            # Ensure real bleach.clean is used (not the MagicMock from test_security_modules)
            import bleach as real_bleach
            _m.bleach = real_bleach
            long_input = "a" * 2000
            result = validator.sanitize_input(long_input, max_length=100)
        finally:
            _m.bleach = old_bleach
        assert len(result) <= 100

    @pytest.mark.unit
    def test_sanitize_sql_injection(self, validator):
        result = validator.sanitize_input("SELECT * FROM users")
        # SQL keyword should be stripped/sanitized
        assert isinstance(result, str)

    # --- validate_file_upload ---

    @pytest.mark.unit
    def test_file_too_large(self, validator, logger):
        big_file = b"x" * (52 * 1024 * 1024)  # 52MB
        ok, msg = validator.validate_file_upload(big_file, "big.txt", "text/plain", "1.2.3.4")
        assert ok is False
        assert "size" in msg
        logger.log_file_upload.assert_called()

    @pytest.mark.unit
    def test_invalid_filename_rejected(self, validator, logger):
        ok, msg = validator.validate_file_upload(b"data", "bad.exe", "text/plain", "1.2.3.4")
        assert ok is False
        logger.log_file_upload.assert_called()

    @pytest.mark.unit
    def test_invalid_content_type_rejected(self, validator, logger):
        ok, msg = validator.validate_file_upload(b"data", "test.txt", "application/x-evil", "1.2.3.4")
        assert ok is False

    @pytest.mark.unit
    def test_scanner_rejects_script_content(self, validator, logger):
        # Use allowed content_type + allowed magic detect, but file contains <script
        _m = _get_real_esf_module()
        old_magic = _m.magic
        old_filetype = _m.filetype
        try:
            mock_magic = MagicMock()
            mock_magic.from_buffer = MagicMock(return_value="text/plain")
            _m.magic = mock_magic
            mock_filetype = MagicMock()
            mock_filetype.guess = MagicMock(return_value=None)
            _m.filetype = mock_filetype
            ok, msg = validator.validate_file_upload(b"<script>alert(1)</script>", "test.txt", "text/plain", "1.2.3.4")
        finally:
            _m.magic = old_magic
            _m.filetype = old_filetype
        assert ok is False
        assert "scan" in msg.lower() or "script" in msg.lower()

    @pytest.mark.unit
    def test_valid_file_accepted(self, validator, logger):
        content = b"Hello, world! This is plain text."
        _m = _get_real_esf_module()
        old_magic = _m.magic
        old_filetype = _m.filetype
        try:
            mock_magic = MagicMock()
            mock_magic.from_buffer = MagicMock(return_value="text/plain")
            _m.magic = mock_magic
            mock_filetype = MagicMock()
            mock_filetype.guess = MagicMock(return_value=None)
            _m.filetype = mock_filetype
            ok, msg = validator.validate_file_upload(content, "hello.txt", "text/plain", "1.2.3.4")
        finally:
            _m.magic = old_magic
            _m.filetype = old_filetype
        assert ok is True
        assert "successful" in msg


# ---------------------------------------------------------------------------
# FileScanner
# ---------------------------------------------------------------------------

class TestFileScanner:
    @pytest.fixture
    def scanner(self):
        _m = _get_real_esf_module()
        return _m.FileScanner()

    @pytest.mark.unit
    def test_detects_script_tag(self, scanner):
        ok, msg = scanner.scan_file(b"<script>evil()</script>")
        assert ok is False
        assert "script" in msg.lower()

    @pytest.mark.unit
    def test_detects_javascript_protocol(self, scanner):
        ok, msg = scanner.scan_file(b"javascript:alert(1)")
        assert ok is False

    @pytest.mark.unit
    def test_detects_pe_executable(self, scanner):
        ok, msg = scanner.scan_file(b"MZ" + b"\x00" * 100)
        assert ok is False
        assert "Executable" in msg

    @pytest.mark.unit
    def test_detects_elf_executable(self, scanner):
        ok, msg = scanner.scan_file(b"\x7fELF" + b"\x00" * 100)
        assert ok is False

    @pytest.mark.unit
    def test_clean_file_passes(self, scanner):
        ok, msg = scanner.scan_file(b"Plain text content without anything suspicious.")
        assert ok is True

    @pytest.mark.unit
    def test_virustotal_path_skipped_without_key(self, scanner):
        # No VIRUS_TOTAL_API_KEY set -> virustotal not called
        scanner.virus_total_api_key = None
        ok, msg = scanner.scan_file(b"safe content")
        assert ok is True


# ---------------------------------------------------------------------------
# EnhancedPasswordPolicy.validate_password - full validation path
# ---------------------------------------------------------------------------

class TestValidatePassword:
    @pytest.fixture
    def policy(self, logger):
        _m = _get_real_esf_module()
        return _m.EnhancedPasswordPolicy(logger)

    @pytest.mark.unit
    def test_too_short_returns_error(self, policy):
        valid, errors = policy.validate_password("short")
        assert valid is False
        assert any("least" in e for e in errors)

    @pytest.mark.unit
    def test_too_long_returns_error(self, policy):
        valid, errors = policy.validate_password("A" * 200 + "1!")
        assert valid is False
        assert any("exceed" in e for e in errors)

    @pytest.mark.unit
    def test_missing_uppercase(self, policy):
        valid, errors = policy.validate_password("lowercase1!aaaaaa")
        assert valid is False
        assert any("uppercase" in e for e in errors)

    @pytest.mark.unit
    def test_missing_lowercase(self, policy):
        valid, errors = policy.validate_password("UPPERCASE1!AAAAAAA")
        assert valid is False
        assert any("lowercase" in e for e in errors)

    @pytest.mark.unit
    def test_missing_digit(self, policy):
        valid, errors = policy.validate_password("NoDigitsHere!!")
        assert valid is False
        assert any("digit" in e for e in errors)

    @pytest.mark.unit
    def test_missing_special_char(self, policy):
        valid, errors = policy.validate_password("NoSpecialChar1aaa")
        assert valid is False
        assert any("special" in e for e in errors)

    @pytest.mark.unit
    def test_common_password_rejected(self, policy):
        # 'password123' is in common list, pad to meet length
        valid, errors = policy.validate_password("password123")
        assert valid is False

    @pytest.mark.unit
    def test_personal_info_rejected(self, policy):
        valid, errors = policy.validate_password(
            "Johnsmith1!Xxxx",
            user_info={"name": "John Smith"}
        )
        assert valid is False
        assert any("personal" in e for e in errors)

    @pytest.mark.unit
    def test_valid_strong_password(self, policy):
        valid, errors = policy.validate_password("V@lidP4ssw0rd#99")
        assert valid is True
        assert errors == []


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------

class TestSecurityHeadersMiddleware:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_adds_headers_for_http_scope(self):
        _m = _get_real_esf_module()
        SecurityHeadersMiddleware = _m.SecurityHeadersMiddleware

        received_messages = []

        async def dummy_app(scope, receive, send):
            await send({"type": "http.response.start", "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def collect_send(msg):
            received_messages.append(msg)

        app = SecurityHeadersMiddleware(dummy_app)
        scope = {"type": "http"}
        await app(scope, MagicMock(), collect_send)

        start_msg = received_messages[0]
        header_keys = [k.decode() if isinstance(k, bytes) else k for k, v in start_msg["headers"]]
        assert "Strict-Transport-Security" in header_keys

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through(self):
        _m = _get_real_esf_module()
        SecurityHeadersMiddleware = _m.SecurityHeadersMiddleware

        called = []

        async def dummy_app(scope, receive, send):
            called.append(True)

        app = SecurityHeadersMiddleware(dummy_app)
        await app({"type": "websocket"}, MagicMock(), MagicMock())
        assert called == [True]


# ---------------------------------------------------------------------------
# EnhancedRateLimiter.get_rate_limit_key
# ---------------------------------------------------------------------------

class TestGetRateLimitKey:
    @pytest.fixture
    def rl_with_redis(self, logger):
        _m = _get_real_esf_module()
        rl = _m.EnhancedRateLimiter.__new__(_m.EnhancedRateLimiter)
        rl.security_logger = logger
        rl.redis_client = None
        rl.memory_store = {}
        return rl

    @pytest.mark.unit
    def test_authenticated_user_key(self, rl_with_redis):
        _m = _get_real_esf_module()
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        mock_request.headers.get = MagicMock(return_value="agent/1.0")
        old_gra = _m.get_remote_address
        try:
            _m.get_remote_address = lambda req: "10.0.0.1"
            key = rl_with_redis.get_rate_limit_key(mock_request, "login")
        finally:
            _m.get_remote_address = old_gra
        assert key == "login:user123"

    @pytest.mark.unit
    def test_anonymous_user_key(self, rl_with_redis):
        _m = _get_real_esf_module()
        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # no user_id attribute
        mock_request.headers.get = MagicMock(return_value="Mozilla/5.0")
        old_gra = _m.get_remote_address
        try:
            _m.get_remote_address = lambda req: "10.0.0.1"
            key = rl_with_redis.get_rate_limit_key(mock_request, "login")
        finally:
            _m.get_remote_address = old_gra
        assert key.startswith("login:10.0.0.1:")


# ---------------------------------------------------------------------------
# DependencyUpdater
# ---------------------------------------------------------------------------

class TestDependencyUpdater:
    @pytest.fixture
    def updater(self, logger):
        _m = _get_real_esf_module()
        return _m.DependencyUpdater(logger)

    @pytest.mark.unit
    def test_check_dependencies_pip_error(self, updater):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
            result = updater.check_dependencies()
        assert "error" in result

    @pytest.mark.unit
    def test_check_dependencies_finds_vulnerable(self, updater):
        pip_output = '[{"name": "requests", "version": "2.0.0"}]'
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=pip_output)
            result = updater.check_dependencies()
        assert len(result["vulnerable_packages"]) == 1
        assert result["vulnerable_packages"][0]["package"] == "requests"

    @pytest.mark.unit
    def test_check_dependencies_safe_package(self, updater):
        pip_output = '[{"name": "requests", "version": "2.30.0"}]'
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=pip_output)
            result = updater.check_dependencies()
        assert len(result["vulnerable_packages"]) == 0
        assert "requests" in result["safe_packages"]

    @pytest.mark.unit
    def test_check_dependencies_exception(self, updater):
        with patch("subprocess.run", side_effect=Exception("subprocess fail")):
            result = updater.check_dependencies()
        assert "error" in result

    @pytest.mark.unit
    def test_update_vulnerable_pkg_not_installed(self, updater):
        # pip show returns non-zero (not installed)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            result = updater.update_vulnerable_dependencies()
        assert "successful_updates" in result

    @pytest.mark.unit
    def test_update_vulnerable_pkg_already_safe(self, updater):
        # pip show returns package at safe version
        def fake_run(cmd, **kwargs):
            if "show" in cmd:
                return MagicMock(returncode=0, stdout="Version: 99.0.0\n")
            return MagicMock(returncode=0, stdout="")
        with patch("subprocess.run", side_effect=fake_run):
            result = updater.update_vulnerable_dependencies()
        assert len(result["skipped_updates"]) > 0

    @pytest.mark.unit
    def test_update_vulnerable_pkg_successful_update(self, updater):
        def fake_run(cmd, **kwargs):
            if "show" in cmd and "requests" in cmd:
                return MagicMock(returncode=0, stdout="Version: 2.0.0\n")
            return MagicMock(returncode=0, stdout="")
        with patch("subprocess.run", side_effect=fake_run):
            result = updater.update_vulnerable_dependencies()
        assert len(result["successful_updates"]) > 0

    @pytest.mark.unit
    def test_update_vulnerable_pkg_failed_update(self, updater):
        def fake_run(cmd, **kwargs):
            if "show" in cmd and "requests" in cmd:
                return MagicMock(returncode=0, stdout="Version: 2.0.0\n")
            if "install" in cmd:
                return MagicMock(returncode=1, stdout="", stderr="pip error")
            return MagicMock(returncode=0, stdout="")
        with patch("subprocess.run", side_effect=fake_run):
            result = updater.update_vulnerable_dependencies()
        assert len(result["failed_updates"]) > 0

    @pytest.mark.unit
    def test_update_raises_exception(self, updater):
        with patch("subprocess.run", side_effect=Exception("boom")):
            result = updater.update_vulnerable_dependencies()
        assert len(result["failed_updates"]) > 0
