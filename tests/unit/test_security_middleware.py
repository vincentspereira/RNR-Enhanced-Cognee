"""
Unit tests for src/security/security_middleware.py
Covers: SecurityMiddleware, FileUploadSecurityMiddleware,
        AuthenticationSecurityMiddleware, InputSanitizationMiddleware,
        SecurityMonitoringMiddleware, apply_security_middleware,
        and all helper methods.
Target: >= 85% line coverage.

Import isolation:
  The enhanced_security_framework has heavy deps (boto3, magic, etc.).
  We stub them at module level before any import, matching the pattern
  used by the existing test_security_modules.py that the test suite
  already relies on.
"""

import sys
import types
import asyncio
import pytest
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Snapshot BEFORE any manipulation for restore in fixture
# ---------------------------------------------------------------------------

_MODS_TO_RESTORE = [
    "src.security.security_middleware",
]
_SYS_MODULES_SNAPSHOT = {k: sys.modules.get(k) for k in _MODS_TO_RESTORE}


# ---------------------------------------------------------------------------
# Stub classes matching what security_middleware imports from
# enhanced_security_framework (already loaded by test_security_modules.py
# or we define minimal stubs here for the mock framework we'll inject).
# ---------------------------------------------------------------------------

class _SecurityConfig:
    ALLOWED_FILE_TYPES = {"image/jpeg", "image/png", "application/pdf", "text/plain"}
    MAX_FILE_SIZE = 50 * 1024 * 1024
    MAX_FILENAME_LENGTH = 255
    FORBIDDEN_FILE_EXTENSIONS = {".exe", ".bat", ".cmd"}
    MIN_PASSWORD_LENGTH = 12
    MAX_PASSWORD_LENGTH = 128
    PASSWORD_COMPLEXITY: Dict[str, bool] = {
        "uppercase": True, "lowercase": True, "digits": True,
        "special_chars": True, "no_common_patterns": True, "no_personal_info": True
    }
    RATE_LIMITS = {
        "auth_endpoints": "10/5m",
        "api_endpoints": "100/1m",
        "file_upload": "5/10m",
        "admin_endpoints": "20/5m",
    }
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
    }


@dataclass
class _SecurityEvent:
    event_type: str
    severity: str
    source_ip: str
    user_agent: str
    timestamp: datetime
    details: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class _SecurityLogger:
    def __init__(self, log_file="security_events.log"):
        pass
    def log_security_event(self, event):
        pass
    def log_file_upload(self, *a, **kw):
        pass
    def log_authentication_attempt(self, *a, **kw):
        pass
    def log_rate_limit_exceeded(self, endpoint, source_ip):
        pass


class _EnhancedInputValidator:
    def __init__(self, security_logger):
        self.security_logger = security_logger
    def validate_file_upload(self, content, filename, ctype, source_ip):
        return True, "OK"
    def sanitize_input(self, s, max_length=1000):
        return s


class _EnhancedPasswordPolicy:
    def validate_password(self, password, user_info=None):
        if not password or len(str(password)) < 12:
            return False, ["Password too short"]
        return True, []


class _EnhancedRateLimiter:
    def get_rate_limit_key(self, request, endpoint_type):
        return f"{endpoint_type}:key"
    def is_rate_limited(self, key, limit, window):
        return False, {}


class _EnhancedSecurityFramework:
    def __init__(self):
        self.security_logger = _SecurityLogger()
        self.rate_limiter = _EnhancedRateLimiter()
        self.input_validator = _EnhancedInputValidator(self.security_logger)
        self.password_policy = _EnhancedPasswordPolicy()


# ---------------------------------------------------------------------------
# Build the esf stub and inject it as the module imported by security_middleware
# ---------------------------------------------------------------------------

_esf_stub = types.ModuleType("src.security.enhanced_security_framework")
_esf_stub.EnhancedSecurityFramework = _EnhancedSecurityFramework
_esf_stub.SecurityLogger = _SecurityLogger
_esf_stub.SecurityEvent = _SecurityEvent
_esf_stub.SecurityConfig = _SecurityConfig
_esf_stub.EnhancedInputValidator = _EnhancedInputValidator
_esf_stub.EnhancedPasswordPolicy = _EnhancedPasswordPolicy
_esf_stub.EnhancedRateLimiter = _EnhancedRateLimiter

# Only inject if the real module hasn't been loaded yet (or override it)
_orig_esf = sys.modules.get("src.security.enhanced_security_framework")
sys.modules["src.security.enhanced_security_framework"] = _esf_stub

# Force fresh load of the module under test (in case it's already cached)
sys.modules.pop("src.security.security_middleware", None)

import importlib
_mw_mod = importlib.import_module("src.security.security_middleware")
SecurityMiddleware = _mw_mod.SecurityMiddleware
FileUploadSecurityMiddleware = _mw_mod.FileUploadSecurityMiddleware
AuthenticationSecurityMiddleware = _mw_mod.AuthenticationSecurityMiddleware
InputSanitizationMiddleware = _mw_mod.InputSanitizationMiddleware
SecurityMonitoringMiddleware = _mw_mod.SecurityMonitoringMiddleware
apply_security_middleware = _mw_mod.apply_security_middleware


@pytest.fixture(scope="module", autouse=True)
def _restore_modules():
    """Restore original sys.modules entries after this module's tests."""
    yield
    # Restore esf if we replaced it
    if _orig_esf is None:
        sys.modules.pop("src.security.enhanced_security_framework", None)
    else:
        sys.modules["src.security.enhanced_security_framework"] = _orig_esf
    # Restore security_middleware entries
    for k, original in _SYS_MODULES_SNAPSHOT.items():
        if original is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = original


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_framework():
    return _EnhancedSecurityFramework()


def _make_request(
    path="/api/data",
    method="GET",
    headers=None,
    query="",
    client_host="127.0.0.1",
    body=None,
):
    request = MagicMock()
    request.url.path = path
    request.url.query = query
    request.method = method
    request.client = MagicMock()
    request.client.host = client_host
    _headers = headers or {}
    request.headers = MagicMock()
    request.headers.get = lambda k, default="": _headers.get(k, default)
    if body is not None:
        request.json = AsyncMock(return_value=body)
        request.body = AsyncMock(return_value=b"")
        request.form = AsyncMock(return_value={})
    else:
        request.json = AsyncMock(return_value={})
        request.body = AsyncMock(return_value=b"")
        request.form = AsyncMock(return_value={})
    return request


def _make_response(status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    return response


def _make_app():
    app = MagicMock()
    app.add_middleware = MagicMock()
    return app


# ---------------------------------------------------------------------------
# SecurityMiddleware
# ---------------------------------------------------------------------------

class TestSecurityMiddlewareInit:
    def test_init(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        assert sm.security_framework is fw
        assert sm.rate_limiter is fw.rate_limiter
        assert sm.input_validator is fw.input_validator


class TestSecurityMiddlewareDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_passes_through_not_limited(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request()
        response = _make_response(200)
        call_next = AsyncMock(return_value=response)
        result = await sm.dispatch(request, call_next)
        assert result is response
        assert "X-Request-ID" in result.headers

    @pytest.mark.asyncio
    async def test_dispatch_rate_limited(self):
        fw = _make_framework()
        fw.rate_limiter.is_rate_limited = MagicMock(return_value=(True, {"retry_after": 30}))
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request()
        call_next = AsyncMock()
        result = await sm.dispatch(request, call_next)
        assert result.status_code == 429
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_logs_auth_failure(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/auth/login")
        response = _make_response(401)
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await sm.dispatch(request, call_next)
        assert any(e.event_type == "authentication_failure" for e in logged)

    @pytest.mark.asyncio
    async def test_dispatch_login_path_401_logged(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/login/attempt")
        response = _make_response(401)
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await sm.dispatch(request, call_next)
        assert any(e.event_type == "authentication_failure" for e in logged)

    @pytest.mark.asyncio
    async def test_dispatch_logs_sensitive_admin_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/admin/settings")
        response = _make_response(200)
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await sm.dispatch(request, call_next)
        assert any(e.event_type == "sensitive_endpoint_access" for e in logged)

    @pytest.mark.asyncio
    async def test_dispatch_logs_sensitive_config_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/config/settings")
        response = _make_response(200)
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await sm.dispatch(request, call_next)
        assert any(e.event_type == "sensitive_endpoint_access" for e in logged)

    @pytest.mark.asyncio
    async def test_dispatch_logs_sensitive_security_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/security/audit")
        response = _make_response(200)
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await sm.dispatch(request, call_next)
        assert any(e.event_type == "sensitive_endpoint_access" for e in logged)

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_logs_event(self):
        fw = _make_framework()
        fw.rate_limiter.is_rate_limited = MagicMock(return_value=(True, {}))
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/api/data")
        call_next = AsyncMock()
        logged = []
        fw.security_logger.log_rate_limit_exceeded = lambda url, ip: logged.append(url)
        result = await sm.dispatch(request, call_next)
        assert result.status_code == 429
        assert len(logged) == 1


class TestGetClientIp:
    def test_forwarded_for(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2"})
        assert sm._get_client_ip(request) == "10.0.0.1"

    def test_real_ip(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"X-Real-IP": "192.168.1.100"})
        assert sm._get_client_ip(request) == "192.168.1.100"

    def test_client_host(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request()
        assert sm._get_client_ip(request) == "127.0.0.1"

    def test_no_client(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request()
        request.client = None
        assert sm._get_client_ip(request) == "unknown"


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_auth_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/auth/login")
        result = await sm._check_rate_limit(request, "127.0.0.1")
        assert result["endpoint_type"] == "auth_endpoints"

    @pytest.mark.asyncio
    async def test_admin_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/admin/users")
        result = await sm._check_rate_limit(request, "127.0.0.1")
        assert result["endpoint_type"] == "admin_endpoints"

    @pytest.mark.asyncio
    async def test_file_upload_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/upload/doc")
        result = await sm._check_rate_limit(request, "127.0.0.1")
        assert result["endpoint_type"] == "file_upload"

    @pytest.mark.asyncio
    async def test_file_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/file/download")
        result = await sm._check_rate_limit(request, "127.0.0.1")
        assert result["endpoint_type"] == "file_upload"

    @pytest.mark.asyncio
    async def test_login_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/login/submit")
        result = await sm._check_rate_limit(request, "127.0.0.1")
        assert result["endpoint_type"] == "auth_endpoints"

    @pytest.mark.asyncio
    async def test_register_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/register/new")
        result = await sm._check_rate_limit(request, "127.0.0.1")
        assert result["endpoint_type"] == "auth_endpoints"

    @pytest.mark.asyncio
    async def test_api_endpoint(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/api/memories")
        result = await sm._check_rate_limit(request, "127.0.0.1")
        assert result["endpoint_type"] == "api_endpoints"
        assert not result["limited"]


class TestAddSecurityHeaders:
    def test_adds_headers(self):
        fw = _make_framework()
        sm = SecurityMiddleware(MagicMock(), fw)
        response = _make_response()
        sm._add_security_headers(response)
        assert "X-Request-ID" in response.headers
        assert "X-API-Version" in response.headers
        assert "X-Content-Type-Options" in response.headers


# ---------------------------------------------------------------------------
# FileUploadSecurityMiddleware
# ---------------------------------------------------------------------------

class TestFileUploadMiddlewareInit:
    def test_init(self):
        fw = _make_framework()
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        assert fum.input_validator is fw.input_validator


class TestFileUploadMiddlewareDispatch:
    @pytest.mark.asyncio
    async def test_non_upload_passes_through(self):
        fw = _make_framework()
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"content-type": "application/json"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await fum.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_multipart_no_files_passes(self):
        fw = _make_framework()
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"content-type": "multipart/form-data"})
        request.form = AsyncMock(return_value={"field": "value"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await fum.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_valid_file_passes(self):
        fw = _make_framework()
        fw.input_validator.validate_file_upload = MagicMock(return_value=(True, "OK"))
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"content-type": "multipart/form-data"})

        file_mock = MagicMock()
        file_mock.filename = "test.pdf"
        file_mock.content_type = "application/pdf"
        file_mock.read = AsyncMock(return_value=b"%PDF content")
        file_mock.seek = MagicMock()

        request.form = AsyncMock(return_value={"upload": file_mock})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await fum.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_invalid_file_returns_400(self):
        fw = _make_framework()
        fw.input_validator.validate_file_upload = MagicMock(return_value=(False, "Bad file"))
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"content-type": "multipart/form-data"})

        file_mock = MagicMock()
        file_mock.filename = "malware.exe"
        file_mock.content_type = "application/octet-stream"
        file_mock.read = AsyncMock(return_value=b"MZ")
        file_mock.seek = MagicMock()

        request.form = AsyncMock(return_value={"upload": file_mock})
        call_next = AsyncMock()
        result = await fum.dispatch(request, call_next)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_form_exception_returns_500(self):
        fw = _make_framework()
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"content-type": "multipart/form-data"})
        request.form = AsyncMock(side_effect=RuntimeError("form parse error"))
        call_next = AsyncMock()
        result = await fum.dispatch(request, call_next)
        assert result.status_code == 500

    def test_get_client_ip_forwarded(self):
        fw = _make_framework()
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"X-Forwarded-For": "10.1.2.3"})
        assert fum._get_client_ip(request) == "10.1.2.3"

    def test_get_client_ip_no_forwarded(self):
        fw = _make_framework()
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        request = _make_request()
        assert fum._get_client_ip(request) == "127.0.0.1"

    def test_get_client_ip_no_client(self):
        fw = _make_framework()
        fum = FileUploadSecurityMiddleware(MagicMock(), fw)
        request = _make_request()
        request.client = None
        assert fum._get_client_ip(request) == "unknown"


# ---------------------------------------------------------------------------
# AuthenticationSecurityMiddleware
# ---------------------------------------------------------------------------

class TestAuthMiddlewareInit:
    def test_init(self):
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        assert am.password_policy is fw.password_policy


class TestAuthMiddlewareDispatch:
    @pytest.mark.asyncio
    async def test_non_auth_path_passes_through(self):
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/api/data")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await am.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_auth_path_get_passes_through(self):
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/auth/status", method="GET")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await am.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_valid_password_passes(self):
        fw = _make_framework()
        fw.password_policy.validate_password = MagicMock(return_value=(True, []))
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/auth/login", method="POST",
                                body={"username": "user1", "password": "Str0ngP@ssw0rd!"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await am.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_weak_password_returns_400(self):
        fw = _make_framework()
        fw.password_policy.validate_password = MagicMock(
            return_value=(False, ["Password too short"])
        )
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/auth/login", method="POST",
                                body={"password": "weak"})
        call_next = AsyncMock()
        result = await am.dispatch(request, call_next)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_new_password_field_validated(self):
        fw = _make_framework()
        fw.password_policy.validate_password = MagicMock(
            return_value=(False, ["Too short"])
        )
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/change-password/", method="POST",
                                body={"new_password": "short"})
        call_next = AsyncMock()
        result = await am.dispatch(request, call_next)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_json_parse_failure_continues(self):
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/register/user", method="POST")
        request.json = AsyncMock(side_effect=Exception("bad json"))
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await am.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_no_password_in_body_passes(self):
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/auth/check", method="POST",
                                body={"username": "user1"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await am.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_reset_password_path(self):
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/reset-password/token", method="POST",
                                body={"password": "ValidP@ss1word!"})
        fw.password_policy.validate_password = MagicMock(return_value=(True, []))
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await am.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_put_with_password_validated(self):
        fw = _make_framework()
        fw.password_policy.validate_password = MagicMock(return_value=(True, []))
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/auth/update", method="PUT",
                                body={"password": "NewStr0ng!pass"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await am.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_patch_with_password_validated(self):
        fw = _make_framework()
        fw.password_policy.validate_password = MagicMock(return_value=(True, []))
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(path="/auth/patch", method="PATCH",
                                body={"password": "PatchStr0ng!pass"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await am.dispatch(request, call_next)
        assert result is response

    def test_get_client_ip(self):
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request(headers={"X-Forwarded-For": "5.6.7.8"})
        assert am._get_client_ip(request) == "5.6.7.8"

    def test_get_client_ip_no_client(self):
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        request = _make_request()
        request.client = None
        assert am._get_client_ip(request) == "unknown"

    @pytest.mark.asyncio
    async def test_outer_exception_returns_500(self):
        """Cover lines 348-361: outer except in _handle_auth_request."""
        fw = _make_framework()
        am = AuthenticationSecurityMiddleware(MagicMock(), fw)
        # call_next raising inside the outer try triggers lines 348-361
        request = _make_request(path="/auth/login", method="GET")  # GET skips inner try
        call_next = AsyncMock(side_effect=RuntimeError("unexpected error"))
        result = await am.dispatch(request, call_next)
        assert result.status_code == 500


# ---------------------------------------------------------------------------
# InputSanitizationMiddleware
# ---------------------------------------------------------------------------

class TestInputSanitizationMiddlewareDispatch:
    @pytest.mark.asyncio
    async def test_non_json_non_form_passes(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        request = _make_request(headers={"content-type": "text/plain"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await ism.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_json_request_passes(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        request = _make_request(headers={"content-type": "application/json"},
                                body={"key": "value"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await ism.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_json_parse_failure_continues(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        request = _make_request(headers={"content-type": "application/json"})
        request.json = AsyncMock(side_effect=Exception("bad json"))
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await ism.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_form_request_passes(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        request = _make_request(
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        request.form = AsyncMock(return_value={"name": "John", "age": "30"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await ism.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_form_parse_failure_continues(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        request = _make_request(
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        request.form = AsyncMock(side_effect=Exception("form err"))
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await ism.dispatch(request, call_next)
        assert result is response


class TestSanitizeDict:
    def test_string_values(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        data = {"key": "value", "num": 42}
        result = ism._sanitize_dict(data)
        assert result["key"] == "value"
        assert result["num"] == 42

    def test_nested_dict(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        data = {"outer": {"inner": "text"}}
        result = ism._sanitize_dict(data)
        assert result["outer"]["inner"] == "text"

    def test_list_of_strings(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        data = {"tags": ["a", "b", 3]}
        result = ism._sanitize_dict(data)
        assert result["tags"] == ["a", "b", 3]

    def test_list_of_dicts(self):
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        data = {"items": [{"name": "x"}, {"name": "y"}]}
        result = ism._sanitize_dict(data)
        assert result["items"][0]["name"] == "x"

    def test_list_with_non_string_non_dict(self):
        """Cover line 435: else branch for non-str, non-dict list items."""
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        data = {"values": [1, 2, 3, None]}
        result = ism._sanitize_dict(data)
        assert result["values"] == [1, 2, 3, None]

    @pytest.mark.asyncio
    async def test_form_with_non_string_value(self):
        """Cover line 435: form item that is not a string."""
        fw = _make_framework()
        ism = InputSanitizationMiddleware(MagicMock(), fw)
        request = _make_request(
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        file_like = MagicMock()
        file_like.__class__ = object  # not a str
        request.form = AsyncMock(return_value={"file": file_like, "name": "Bob"})
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await ism.dispatch(request, call_next)
        assert result is response


# ---------------------------------------------------------------------------
# SecurityMonitoringMiddleware
# ---------------------------------------------------------------------------

class TestSecurityMonitoringMiddlewareDispatch:
    @pytest.mark.asyncio
    async def test_normal_request_passes(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request()
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        result = await smm.dispatch(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_sql_injection_union_select_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="union select * from users")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_sql_injection" for e in logged)

    @pytest.mark.asyncio
    async def test_sql_injection_drop_table_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="drop table users")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_sql_injection" for e in logged)

    @pytest.mark.asyncio
    async def test_sql_injection_or_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="or 1=1")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_sql_injection" for e in logged)

    @pytest.mark.asyncio
    async def test_sql_injection_xp_cmdshell_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="xp_cmdshell cmd")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_sql_injection" for e in logged)

    @pytest.mark.asyncio
    async def test_xss_script_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="<script>alert(1)</script>")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_xss_attempt" for e in logged)

    @pytest.mark.asyncio
    async def test_xss_javascript_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="javascript:alert()")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_xss_attempt" for e in logged)

    @pytest.mark.asyncio
    async def test_xss_onerror_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="onerror=bad()")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_xss_attempt" for e in logged)

    @pytest.mark.asyncio
    async def test_xss_onload_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="onload=fn()")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_xss_attempt" for e in logged)

    @pytest.mark.asyncio
    async def test_xss_eval_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(query="eval(code)")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_xss_attempt" for e in logged)

    @pytest.mark.asyncio
    async def test_path_traversal_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(path="/../etc/passwd")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_path_traversal" for e in logged)

    @pytest.mark.asyncio
    async def test_encoded_path_traversal_logged(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(path="/app%2e%2e%2fetc/passwd")
        response = _make_response()
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "potential_path_traversal" for e in logged)

    @pytest.mark.asyncio
    async def test_auth_failure_tracked(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request()
        response = _make_response(401)
        call_next = AsyncMock(return_value=response)
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)
        await smm.dispatch(request, call_next)
        assert any(e.event_type == "authentication_failure_tracking" for e in logged)

    def test_get_client_ip(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request()
        assert smm._get_client_ip(request) == "127.0.0.1"

    def test_get_client_ip_forwarded(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request(headers={"X-Forwarded-For": "9.8.7.6"})
        assert smm._get_client_ip(request) == "9.8.7.6"

    def test_get_client_ip_no_client(self):
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request()
        request.client = None
        assert smm._get_client_ip(request) == "unknown"

    @pytest.mark.asyncio
    async def test_slow_request_logged(self):
        """Cover line 557: slow request detection (process_time > 30)."""
        fw = _make_framework()
        smm = SecurityMonitoringMiddleware(MagicMock(), fw)
        request = _make_request()
        response = _make_response()
        logged = []
        fw.security_logger.log_security_event = lambda e: logged.append(e)

        import time as _time
        _orig_time = _time.time
        # Make time jump so process_time > 30
        _call_count = [0]
        def _fake_time():
            _call_count[0] += 1
            if _call_count[0] == 1:
                return 0.0
            return 35.0  # 35 seconds elapsed

        with patch("src.security.security_middleware.time.time", side_effect=_fake_time):
            call_next = AsyncMock(return_value=response)
            await smm.dispatch(request, call_next)
        assert any(e.event_type == "slow_request_detected" for e in logged)


# ---------------------------------------------------------------------------
# apply_security_middleware
# ---------------------------------------------------------------------------

class TestApplySecurityMiddleware:
    def test_applies_all_middleware(self):
        fw = _make_framework()
        app = _make_app()
        result = apply_security_middleware(app, fw)
        assert result is app
        assert app.add_middleware.call_count == 5

    def test_middleware_types_applied(self):
        fw = _make_framework()
        app = _make_app()
        apply_security_middleware(app, fw)
        applied_types = [call.args[0] for call in app.add_middleware.call_args_list]
        assert SecurityMiddleware in applied_types
        assert FileUploadSecurityMiddleware in applied_types
        assert AuthenticationSecurityMiddleware in applied_types
        assert InputSanitizationMiddleware in applied_types
        assert SecurityMonitoringMiddleware in applied_types
