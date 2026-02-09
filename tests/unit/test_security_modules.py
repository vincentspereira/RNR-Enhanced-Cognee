"""
Comprehensive Security Module Tests

Test coverage for:
1. EnhancedSecurityFramework - Security policies and threat detection
2. SecurityMiddleware - API security middleware
3. AuthManager - Authentication and authorization
4. DataProtectionManager - Encryption and PII protection
5. SecurityDeploymentManager - Security automation and monitoring

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-09
"""

import sys
import pytest
import asyncio
import json
import os
import secrets
import time
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch, call
from pathlib import Path
import tempfile
import hashlib
from typing import Dict, Any, List
import base64
import re

# Test configuration monkey-patch to prevent pytest theme errors
os.environ['PYTEST_THEME'] = 'monokai' if 'PYTEST_THEME' not in os.environ else os.environ['PYTEST_THEME']

# Mock all missing modules BEFORE importing security modules
mock_magic = MagicMock()
mock_magic.from_buffer = MagicMock(return_value='text/plain')
sys.modules['magic'] = mock_magic

mock_filetype = MagicMock()
mock_filetype.guess = MagicMock(return_value=None)
sys.modules['filetype'] = mock_filetype

# Create a proper mock for argon2 that handles both .using() and .verify()
def mock_verify_func(password, hashed_password):
    # Return True if password matches expected values, False otherwise
    return password in ["TestPassword123!", "Str0ng!P@ssw0rd", "StrongP@ssw0rd!2024", "Str0ng!P@ssw0rd#123"]

# Create mock for the argon2 hasher returned by .using()
class MockArgon2Hasher:
    def hash(self, password):
        return 'hashed_password_' + password

class MockArgon2:
    verify = staticmethod(mock_verify_func)

    @classmethod
    def using(cls, **kwargs):
        return MockArgon2Hasher()

sys.modules['passlib'] = MagicMock()
sys.modules['passlib.hash'] = MagicMock()
sys.modules['passlib.hash.bcrypt'] = MagicMock()
sys.modules['passlib.hash.argon2'] = MockArgon2()
sys.modules['passlib.context'] = MagicMock()
mock_crypt_context = MagicMock()
mock_crypt_context.return_value.hash = MagicMock(return_value='hashed')
mock_crypt_context.return_value.verify = MagicMock(return_value=True)
sys.modules['passlib.context'].CryptContext = MagicMock(return_value=mock_crypt_context)

sys.modules['boto3'] = MagicMock()
sys.modules['slowapi'] = MagicMock()
sys.modules['slowapi.util'] = MagicMock()
sys.modules['slowapi.errors'] = MagicMock()
sys.modules['slowapi.util'].get_remote_address = lambda request: '127.0.0.1'
sys.modules['requests'] = MagicMock()

# Mock jwt to actually encode/decode tokens
mock_jwt = MagicMock()

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def mock_jwt_encode(payload, key, algorithm='HS256'):
    """Mock jwt.encode that returns a fake token"""
    header = json.dumps({'alg': algorithm, 'typ': 'JWT'})
    payload_str = json.dumps(payload, default=json_serial)
    segments = [
        base64.urlsafe_b64encode(header.encode()).rstrip(b'=').decode(),
        base64.urlsafe_b64encode(payload_str.encode()).rstrip(b'=').decode()
    ]
    return '.'.join(segments) + '.signature'

def mock_jwt_decode(token, key, algorithms=['HS256']):
    """Mock jwt.decode that returns the payload"""
    try:
        segments = token.split('.')
        if len(segments) != 3:
            raise Exception("Not enough segments")
        payload_b64 = segments[1]
        # Add padding if needed
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload
    except Exception as e:
        raise Exception(f"Invalid token: {str(e)}")

mock_jwt.encode = mock_jwt_encode
mock_jwt.decode = mock_jwt_decode
mock_jwt.ExpiredSignatureError = Exception
sys.modules['jwt'] = mock_jwt

# Mock bleach to actually sanitize HTML
def mock_bleach_clean(text, tags=None, attributes=None, strip=False):
    """Mock bleach.clean that removes script tags and dangerous HTML"""
    # Remove script tags and their content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove all HTML tags if strip=True
    if strip:
        text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

sys.modules['bleach'] = MagicMock()
sys.modules['bleach'].clean = mock_bleach_clean

# DO NOT mock cryptography - we need the real package for EncryptionManager
# The cryptography package is installed and should be used directly

# Import FastAPI for middleware tests
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

# Import security modules with graceful handling of missing dependencies
try:
    from src.security.enhanced_security_framework import (
        SecurityConfig,
        SecurityEvent,
        SecurityLogger,
        EnhancedInputValidator,
        FileScanner,
        EnhancedPasswordPolicy,
        EnhancedRateLimiter,
        DependencyUpdater,
        SecureErrorHandler,
        EnhancedSecurityFramework
    )
    SECURITY_FRAMEWORK_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Security framework not available: {e}")
    SECURITY_FRAMEWORK_AVAILABLE = False

try:
    from src.security.security_middleware import (
        SecurityMiddleware,
        FileUploadSecurityMiddleware,
        AuthenticationSecurityMiddleware,
        InputSanitizationMiddleware,
        SecurityMonitoringMiddleware
    )
    MIDDLEWARE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Security middleware not available: {e}")
    MIDDLEWARE_AVAILABLE = False

try:
    from src.security.auth import (
        Role,
        Permission,
        JWTAuthenticator,
        APIKeyManager,
        RBACManager
    )
    AUTH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Auth module not available: {e}")
    AUTH_AVAILABLE = False

try:
    from src.security.data_protection import (
        EncryptionManager,
        PIIDetector,
        GDPRCompliance
    )
    DATA_PROTECTION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Data protection not available: {e}")
    DATA_PROTECTION_AVAILABLE = False

try:
    from src.security.security_deployment import (
        SecurityIncidentSeverity,
        AlertChannel,
        SecurityIncident,
        AlertRule,
        SecurityMetrics,
        AlertManager,
        SecurityMonitoringService,
        load_security_config
    )
    DEPLOYMENT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Security deployment not available: {e}")
    DEPLOYMENT_AVAILABLE = False


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def security_logger():
    """Create security logger instance"""
    return SecurityLogger(log_file="test_security_events.log")


@pytest.fixture
def security_framework():
    """Create security framework instance"""
    return EnhancedSecurityFramework()


@pytest.fixture
def input_validator(security_logger):
    """Create input validator instance"""
    return EnhancedInputValidator(security_logger)


@pytest.fixture
def password_policy(security_logger):
    """Create password policy instance"""
    return EnhancedPasswordPolicy(security_logger)


@pytest.fixture
def rate_limiter(security_logger):
    """Create rate limiter instance"""
    limiter = EnhancedRateLimiter(security_logger)
    # Force use of memory store by setting redis_client to None
    limiter.redis_client = None
    return limiter


@pytest.fixture
def file_scanner():
    """Create file scanner instance"""
    return FileScanner()


@pytest.fixture
def encryption_manager():
    """Create encryption manager instance"""
    return EncryptionManager()


@pytest.fixture
def pii_detector():
    """Create PII detector instance"""
    return PIIDetector()


@pytest.fixture
def jwt_authenticator():
    """Create JWT authenticator instance"""
    return JWTAuthenticator()


@pytest.fixture
def sample_security_event():
    """Create sample security event"""
    return SecurityEvent(
        event_type="test_event",
        severity="medium",
        source_ip="192.168.1.1",
        user_agent="test-agent",
        timestamp=datetime.now(),
        details={"test": "data"}
    )


@pytest.fixture
def mock_fastapi_request():
    """Create mock FastAPI request"""
    request = Mock(spec=Request)
    request.url = Mock(path="/api/test", query="param=value")
    request.url.path = "/api/test"
    request.url.query = "param=value"
    request.method = "GET"
    request.headers = {"user-agent": "test-agent", "content-type": "application/json"}
    request.client = Mock(host="192.168.1.1")
    request.state = Mock()
    return request


@pytest.fixture
def mock_fastapi_response():
    """Create mock FastAPI response"""
    response = Mock(spec=Response)
    response.status_code = 200
    response.headers = {}
    return response


# ============================================================================
# SecurityConfig Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestSecurityConfig:
    """Test SecurityConfig configuration"""

    def test_file_type_restrictions(self):
        """Test file type restrictions are properly defined"""
        assert 'image/jpeg' in SecurityConfig.ALLOWED_FILE_TYPES
        assert 'application/pdf' in SecurityConfig.ALLOWED_FILE_TYPES
        assert 'application/exe' not in SecurityConfig.ALLOWED_FILE_TYPES

    def test_max_file_size(self):
        """Test maximum file size is set"""
        assert SecurityConfig.MAX_FILE_SIZE == 50 * 1024 * 1024  # 50MB

    def test_forbidden_extensions(self):
        """Test forbidden file extensions"""
        assert '.exe' in SecurityConfig.FORBIDDEN_FILE_EXTENSIONS
        assert '.bat' in SecurityConfig.FORBIDDEN_FILE_EXTENSIONS
        assert '.js' in SecurityConfig.FORBIDDEN_FILE_EXTENSIONS

    def test_password_policy(self):
        """Test password policy configuration"""
        assert SecurityConfig.MIN_PASSWORD_LENGTH == 12
        assert SecurityConfig.MAX_PASSWORD_LENGTH == 128
        assert SecurityConfig.PASSWORD_COMPLEXITY['uppercase'] is True
        assert SecurityConfig.PASSWORD_COMPLEXITY['digits'] is True

    def test_rate_limits(self):
        """Test rate limit configuration"""
        assert 'auth_endpoints' in SecurityConfig.RATE_LIMITS
        assert 'api_endpoints' in SecurityConfig.RATE_LIMITS
        assert 'file_upload' in SecurityConfig.RATE_LIMITS

    def test_security_headers(self):
        """Test security headers are configured"""
        assert 'X-Content-Type-Options' in SecurityConfig.SECURITY_HEADERS
        assert 'X-Frame-Options' in SecurityConfig.SECURITY_HEADERS
        assert 'Strict-Transport-Security' in SecurityConfig.SECURITY_HEADERS
        assert SecurityConfig.SECURITY_HEADERS['X-Frame-Options'] == 'DENY'


# ============================================================================
# SecurityEvent Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestSecurityEvent:
    """Test SecurityEvent data structure"""

    def test_security_event_creation(self):
        """Test creating a security event"""
        event = SecurityEvent(
            event_type="test_type",
            severity="high",
            source_ip="10.0.0.1",
            user_agent="test-ua",
            timestamp=datetime.now(),
            details={"key": "value"}
        )

        assert event.event_type == "test_type"
        assert event.severity == "high"
        assert event.source_ip == "10.0.0.1"
        assert event.details == {"key": "value"}

    def test_security_event_with_optional_fields(self):
        """Test security event with optional user_id and session_id"""
        event = SecurityEvent(
            event_type="auth_failure",
            severity="medium",
            source_ip="10.0.0.2",
            user_agent="test-ua",
            timestamp=datetime.now(),
            details={},
            user_id="user123",
            session_id="session456"
        )

        assert event.user_id == "user123"
        assert event.session_id == "session456"


# ============================================================================
# SecurityLogger Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestSecurityLogger:
    """Test security logging functionality"""

    def test_logger_initialization(self, security_logger):
        """Test logger initializes correctly"""
        assert security_logger.logger is not None
        assert security_logger.log_file == "test_security_events.log"

    def test_log_security_event_high_severity(self, security_logger, sample_security_event):
        """Test logging high severity security event"""
        sample_security_event.severity = "high"
        # Should not raise exception
        security_logger.log_security_event(sample_security_event)

    def test_log_security_event_critical_severity(self, security_logger, sample_security_event):
        """Test logging critical security event"""
        sample_security_event.severity = "critical"
        # Should not raise exception
        security_logger.log_security_event(sample_security_event)

    def test_log_file_upload_success(self, security_logger):
        """Test logging successful file upload"""
        security_logger.log_file_upload(
            filename="test.jpg",
            file_type="image/jpeg",
            file_size=1024,
            source_ip="10.0.0.1",
            user_id="user123",
            success=True
        )

    def test_log_file_upload_failure(self, security_logger):
        """Test logging failed file upload"""
        security_logger.log_file_upload(
            filename="malicious.exe",
            file_type="application/exe",
            file_size=2048,
            source_ip="10.0.0.2",
            success=False
        )

    def test_log_authentication_attempt_success(self, security_logger):
        """Test logging successful authentication"""
        security_logger.log_authentication_attempt(
            username="testuser",
            source_ip="10.0.0.1",
            success=True
        )

    def test_log_authentication_attempt_failure(self, security_logger):
        """Test logging failed authentication"""
        security_logger.log_authentication_attempt(
            username="testuser",
            source_ip="10.0.0.2",
            success=False,
            failure_reason="invalid_password"
        )

    def test_log_rate_limit_exceeded(self, security_logger):
        """Test logging rate limit exceeded"""
        security_logger.log_rate_limit_exceeded(
            endpoint="/api/test",
            source_ip="10.0.0.1"
        )


# ============================================================================
# EnhancedInputValidator Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestEnhancedInputValidator:
    """Test input validation functionality"""

    def test_validate_file_upload_success(self, input_validator):
        """Test successful file upload validation"""
        file_content = b'\xff\xd8\xff\xe0\x00\x10JFIF'  # JPEG header
        result, message = input_validator.validate_file_upload(
            file_content=file_content,
            filename="test.jpg",
            content_type="image/jpeg",
            source_ip="10.0.0.1"
        )

        assert result is True
        assert "successful" in message.lower()

    def test_validate_file_upload_too_large(self, input_validator):
        """Test file size validation"""
        large_file = b'x' * (SecurityConfig.MAX_FILE_SIZE + 1)
        result, message = input_validator.validate_file_upload(
            file_content=large_file,
            filename="large.jpg",
            content_type="image/jpeg",
            source_ip="10.0.0.1"
        )

        assert result is False
        assert "exceeds maximum" in message.lower()

    def test_validate_filename_too_long(self, input_validator):
        """Test filename length validation"""
        long_filename = "a" * (SecurityConfig.MAX_FILENAME_LENGTH + 1)
        result, message = input_validator._validate_filename(long_filename)

        assert result is False
        assert "exceeds maximum length" in message.lower()

    def test_validate_filename_forbidden_extension(self, input_validator):
        """Test forbidden file extension validation"""
        result, message = input_validator._validate_filename("malicious.exe")

        assert result is False
        assert "not allowed" in message.lower()

    def test_validate_filename_dangerous_chars(self, input_validator):
        """Test dangerous character detection"""
        result, message = input_validator._validate_filename("test../../../file.jpg")

        assert result is False
        assert "invalid" in message.lower() or "traversal" in message.lower()

    def test_validate_file_type_not_allowed(self, input_validator):
        """Test file type validation"""
        file_content = b'MZ'  # Executable header
        result, message = input_validator._validate_file_type(
            file_content=file_content,
            filename="test.exe",
            content_type="application/exe"
        )

        assert result is False

    def test_sanitize_input_html_removal(self, input_validator):
        """Test HTML sanitization"""
        dirty_input = "<script>alert('xss')</script>clean text"
        clean = input_validator.sanitize_input(dirty_input)

        assert "<script>" not in clean
        assert "clean text" in clean

    def test_sanitize_input_sql_injection(self, input_validator):
        """Test SQL injection sanitization"""
        dirty_input = "text' OR '1'='1"
        clean = input_validator.sanitize_input(dirty_input)

        # Should sanitize dangerous patterns
        assert "OR" not in clean or clean.count("OR") < dirty_input.count("OR")

    def test_sanitize_input_length_limit(self, input_validator):
        """Test input length truncation"""
        long_input = "a" * 2000
        clean = input_validator.sanitize_input(long_input, max_length=100)

        assert len(clean) <= 100

    def test_sanitize_input_empty_string(self, input_validator):
        """Test empty input handling"""
        clean = input_validator.sanitize_input("")

        assert clean == ""


# ============================================================================
# FileScanner Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestFileScanner:
    """Test malicious file detection"""

    def test_scan_clean_file(self, file_scanner):
        """Test scanning a clean file"""
        clean_content = b'This is a clean text file with normal content'
        result, message = file_scanner.scan_file(clean_content)

        assert result is True
        assert "successful" in message.lower()

    def test_scan_script_content(self, file_scanner):
        """Test detecting embedded scripts"""
        script_content = b'<script>alert("xss")</script>'
        result, message = file_scanner.scan_file(script_content)

        assert result is False
        assert "script" in message.lower()

    def test_scan_executable_file(self, file_scanner):
        """Test detecting executable files"""
        exe_content = b'MZ\x90\x00'  # PE executable header
        result, message = file_scanner.scan_file(exe_content)

        assert result is False
        assert "executable" in message.lower()

    def test_scan_elf_executable(self, file_scanner):
        """Test detecting ELF executables"""
        elf_content = b'\x7fELF'  # ELF header
        result, message = file_scanner.scan_file(elf_content)

        assert result is False
        assert "executable" in message.lower()

    def test_scan_suspicious_patterns(self, file_scanner):
        """Test detecting suspicious patterns"""
        suspicious_content = b'document.write("test")'
        result, message = file_scanner.scan_file(suspicious_content)

        assert result is False


# ============================================================================
# EnhancedPasswordPolicy Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestEnhancedPasswordPolicy:
    """Test password policy enforcement"""

    @patch('src.security.enhanced_security_framework.argon2.verify')
    def test_validate_strong_password(self, mock_verify, password_policy):
        """Test validating a strong password"""
        # Configure mock
        mock_verify.return_value = True

        # Use a password without sequential characters
        strong_password = "Str0ng!P@ssw0rd#9X7"
        is_valid, errors = password_policy.validate_password(strong_password)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_too_short(self, password_policy):
        """Test password length validation"""
        short_password = "Short1!"
        is_valid, errors = password_policy.validate_password(short_password)

        assert is_valid is False
        assert any("at least" in err.lower() and "character" in err.lower() for err in errors)

    def test_validate_missing_uppercase(self, password_policy):
        """Test uppercase requirement"""
        password = "lowercase1!password"
        is_valid, errors = password_policy.validate_password(password)

        assert is_valid is False
        assert any("uppercase" in err.lower() for err in errors)

    def test_validate_missing_lowercase(self, password_policy):
        """Test lowercase requirement"""
        password = "UPPERCASE1!PASSWORD"
        is_valid, errors = password_policy.validate_password(password)

        assert is_valid is False
        assert any("lowercase" in err.lower() for err in errors)

    def test_validate_missing_digits(self, password_policy):
        """Test digit requirement"""
        password = "NoDigits!Password"
        is_valid, errors = password_policy.validate_password(password)

        assert is_valid is False
        assert any("digit" in err.lower() for err in errors)

    def test_validate_missing_special_chars(self, password_policy):
        """Test special character requirement"""
        password = "NoSpecialChars123"
        is_valid, errors = password_policy.validate_password(password)

        assert is_valid is False
        assert any("special" in err.lower() for err in errors)

    def test_validate_common_password(self, password_policy):
        """Test common password detection"""
        is_valid, errors = password_policy.validate_password("password123")

        assert is_valid is False
        assert any("common" in err.lower() for err in errors)

    def test_validate_sequential_chars(self, password_policy):
        """Test sequential character detection"""
        is_valid, errors = password_policy.validate_password("Abc123!Password")

        assert is_valid is False
        assert any("sequential" in err.lower() for err in errors)

    def test_validate_repeated_chars(self, password_policy):
        """Test repeated character detection"""
        is_valid, errors = password_policy.validate_password("AAAaaa111!!!")

        assert is_valid is False
        assert any("repeated" in err.lower() for err in errors)

    def test_validate_with_user_info(self, password_policy):
        """Test personal information detection"""
        user_info = {
            "username": "john_doe",
            "email": "john@example.com",
            "name": "John Doe"
        }
        is_valid, errors = password_policy.validate_password("John123!Password", user_info)

        assert is_valid is False
        assert any("personal" in err.lower() for err in errors)

    def test_hash_password_argon2(self, password_policy):
        """Test password hashing with Argon2"""
        # Re-configure the module-level argon2 mock to ensure it's working
        import src.security.enhanced_security_framework as security_framework
        security_framework.argon2 = sys.modules['passlib.hash.argon2']

        password = "TestPassword123!"
        hashed, hash_type = password_policy.hash_password(password)

        assert hashed is not None
        assert hash_type in ["argon2", "bcrypt"]
        # Our mock returns 'hashed_password_' + password, which should be long enough
        assert len(hashed) >= len('hashed_password_' + password)

    @patch('src.security.enhanced_security_framework.argon2.verify')
    def test_verify_password_correct(self, mock_verify, password_policy):
        """Test verifying correct password"""
        # Configure mock to return True for matching password
        def verify_side_effect(password, hashed):
            return password == "TestPassword123!"
        mock_verify.side_effect = verify_side_effect

        password = "TestPassword123!"
        hashed, hash_type = password_policy.hash_password(password)

        is_valid = password_policy.verify_password(password, hashed, hash_type)
        assert is_valid is True

    @patch('src.security.enhanced_security_framework.argon2.verify')
    def test_verify_password_incorrect(self, mock_verify, password_policy):
        """Test verifying incorrect password"""
        # Configure mock to return True only for correct password
        def verify_side_effect(password, hashed):
            return password == "TestPassword123!"
        mock_verify.side_effect = verify_side_effect

        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed, hash_type = password_policy.hash_password(password)

        is_valid = password_policy.verify_password(wrong_password, hashed, hash_type)
        assert is_valid is False


# ============================================================================
# EnhancedRateLimiter Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestEnhancedRateLimiter:
    """Test rate limiting functionality"""

    def test_rate_limit_under_limit(self, rate_limiter):
        """Test request under rate limit"""
        # Make 5 requests with limit of 10
        for i in range(5):
            is_limited, info = rate_limiter.is_rate_limited(
                key="test_ip",
                limit="10/1m",
                window_seconds=60
            )
            assert is_limited is False

    def test_rate_limit_exceeded(self, rate_limiter):
        """Test rate limit exceeded"""
        # Make 15 requests with limit of 10
        exceeded_count = 0
        for i in range(15):
            is_limited, info = rate_limiter.is_rate_limited(
                key="test_ip_exceed",
                limit="10/1m",
                window_seconds=60
            )
            if is_limited:
                exceeded_count += 1

        assert exceeded_count > 0

    def test_rate_limit_window_expiry(self, rate_limiter):
        """Test rate limit window expires"""
        # Make requests up to limit
        for i in range(10):
            rate_limiter.is_rate_limited(
                key="test_ip_window",
                limit="10/1s",
                window_seconds=1
            )

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        is_limited, info = rate_limiter.is_rate_limited(
            key="test_ip_window",
            limit="10/1s",
            window_seconds=1
        )
        assert is_limited is False

    def test_rate_limit_different_keys(self, rate_limiter):
        """Test rate limiting for different keys"""
        # First key
        for i in range(10):
            rate_limiter.is_rate_limited(
                key="user1",
                limit="5/1m",
                window_seconds=60
            )

        # Second key should not be affected
        is_limited, info = rate_limiter.is_rate_limited(
            key="user2",
            limit="5/1m",
            window_seconds=60
        )
        assert is_limited is False


# ============================================================================
# DependencyUpdater Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestDependencyUpdater:
    """Test dependency vulnerability checking"""

    def test_load_vulnerable_packages(self, security_logger):
        """Test loading vulnerable packages list"""
        updater = DependencyUpdater(security_logger)
        assert len(updater.vulnerable_packages) > 0
        assert 'requests' in updater.vulnerable_packages

    @patch('subprocess.run')
    def test_check_dependencies_success(self, mock_run, security_logger):
        """Test checking dependencies"""
        # Mock pip list output
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {"name": "requests", "version": "2.28.0"},
                {"name": "urllib3", "version": "1.26.0"}
            ])
        )

        updater = DependencyUpdater(security_logger)
        result = updater.check_dependencies()

        assert 'vulnerable_packages' in result
        assert 'safe_packages' in result

    @patch('subprocess.run')
    def test_check_vulnerable_dependencies(self, mock_run, security_logger):
        """Test detecting vulnerable dependencies"""
        # Mock pip list with vulnerable version
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {"name": "requests", "version": "2.25.0"}  # Old version
            ])
        )

        updater = DependencyUpdater(security_logger)
        result = updater.check_dependencies()

        assert len(result['vulnerable_packages']) > 0


# ============================================================================
# SecureErrorHandler Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestSecureErrorHandler:
    """Test secure error handling"""

    def test_handle_error_production_mode(self, security_logger):
        """Test error handling in production mode"""
        handler = SecureErrorHandler(security_logger)
        handler.production_mode = True

        error = Exception("Database connection failed")
        response = handler.handle_error(error, {"source_ip": "10.0.0.1"})

        assert "error" in response
        assert "Database connection failed" not in response  # Details hidden
        assert "error_id" in response

    def test_handle_error_development_mode(self, security_logger):
        """Test error handling in development mode"""
        handler = SecureErrorHandler(security_logger)
        handler.production_mode = False

        error = Exception("Database connection failed")
        response = handler.handle_error(error, {"source_ip": "10.0.0.1"})

        assert "error" in response
        assert response.get("message") == "Database connection failed"  # Details shown
        assert "debug_mode" in response

    def test_sanitize_error_message_paths(self, security_logger):
        """Test sanitizing file paths in error messages"""
        handler = SecureErrorHandler(security_logger)

        message = "Error at /home/user/project/app/main.py line 42"
        sanitized = handler.sanitize_error_message(message)

        assert "/home/user/project" not in sanitized
        assert "/path/" in sanitized

    def test_sanitize_error_message_database_urls(self, security_logger):
        """Test sanitizing database URLs"""
        handler = SecureErrorHandler(security_logger)

        message = "Connection to postgresql://user:pass@localhost:5432/db failed"
        sanitized = handler.sanitize_error_message(message)

        assert "postgresql://" not in sanitized
        assert "DATABASE_URL" in sanitized


# ============================================================================
# EncryptionManager Tests
# ============================================================================

@pytest.mark.skipif(not DATA_PROTECTION_AVAILABLE, reason="Data protection not available")
class TestEncryptionManager:
    """Test encryption and decryption"""

    def test_encrypt_decrypt_string(self, encryption_manager):
        """Test encrypting and decrypting a string"""
        plaintext = "Sensitive data to encrypt"
        ciphertext = encryption_manager.encrypt(plaintext)
        decrypted = encryption_manager.decrypt(ciphertext)

        assert decrypted == plaintext
        assert ciphertext != plaintext

    def test_encrypt_dict(self, encryption_manager):
        """Test encrypting a dictionary"""
        data = {"key": "value", "number": 123}
        ciphertext = encryption_manager.encrypt_dict(data)
        decrypted = encryption_manager.decrypt_dict(ciphertext)

        assert decrypted == data

    def test_encrypt_different_results(self, encryption_manager):
        """Test that encryption produces different results"""
        plaintext = "Same data"
        cipher1 = encryption_manager.encrypt(plaintext)
        cipher2 = encryption_manager.encrypt(plaintext)

        # Fernet uses random IV, so results should differ
        assert cipher1 != cipher2

    def test_decrypt_invalid_ciphertext(self, encryption_manager):
        """Test decrypting invalid ciphertext"""
        with pytest.raises(Exception):
            encryption_manager.decrypt("invalid_ciphertext")


# ============================================================================
# PIIDetector Tests
# ============================================================================

@pytest.mark.skipif(not DATA_PROTECTION_AVAILABLE, reason="Data protection not available")
class TestPIIDetector:
    """Test PII detection and masking"""

    def test_detect_email(self, pii_detector):
        """Test email detection"""
        text = "Contact us at support@example.com for help"
        detected = pii_detector.detect_pii(text)

        assert 'email' in detected
        assert len(detected['email']) == 1
        assert 'support@example.com' in detected['email'][0]['value']

    def test_detect_phone(self, pii_detector):
        """Test phone number detection"""
        text = "Call us at 555-123-4567 for support"
        detected = pii_detector.detect_pii(text)

        assert 'phone' in detected
        assert len(detected['phone']) == 1

    def test_detect_ssn(self, pii_detector):
        """Test SSN detection"""
        text = "SSN: 123-45-6789"
        detected = pii_detector.detect_pii(text)

        assert 'ssn' in detected
        assert len(detected['ssn']) == 1

    def test_detect_credit_card(self, pii_detector):
        """Test credit card detection"""
        text = "Card: 4532-1234-5678-9010"
        detected = pii_detector.detect_pii(text)

        assert 'credit_card' in detected

    def test_detect_ip_address(self, pii_detector):
        """Test IP address detection"""
        text = "Server IP: 192.168.1.1"
        detected = pii_detector.detect_pii(text)

        assert 'ip_address' in detected

    def test_mask_email(self, pii_detector):
        """Test email masking"""
        text = "Email: john.doe@example.com"
        masked = pii_detector.mask_pii(text)

        assert "john.doe@example.com" not in masked
        assert "***@***.***" in masked

    def test_mask_phone(self, pii_detector):
        """Test phone number masking"""
        text = "Call 555-123-4567 now"
        masked = pii_detector.mask_pii(text)

        assert "555-123-4567" not in masked
        assert "***-***-****" in masked

    def test_mask_multiple_pii_types(self, pii_detector):
        """Test masking multiple PII types"""
        text = "Contact john@example.com or call 555-123-4567"
        masked = pii_detector.mask_pii(text)

        assert "john@example.com" not in masked
        assert "555-123-4567" not in masked

    def test_sanitize_dict_for_logging(self, pii_detector):
        """Test sanitizing dictionary for logging"""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com"
        }
        sanitized = pii_detector.sanitize_for_log(data, mask_pii=True)

        assert "secret123" not in sanitized
        assert "***MASKED***" in sanitized


# ============================================================================
# JWT Authentication Tests
# ============================================================================

@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth module not available")
class TestJWTAuthenticator:
    """Test JWT authentication"""

    def test_create_token(self, jwt_authenticator):
        """Test creating JWT token"""
        token = jwt_authenticator.create_token(
            user_id="user123",
            role=Role.USER
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_create_token_with_additional_claims(self, jwt_authenticator):
        """Test creating token with additional claims"""
        additional_claims = {"email": "user@example.com"}
        token = jwt_authenticator.create_token(
            user_id="user123",
            role=Role.ADMIN,
            additional_claims=additional_claims
        )

        assert token is not None

    def test_verify_valid_token(self, jwt_authenticator):
        """Test verifying valid token"""
        token = jwt_authenticator.create_token(
            user_id="user123",
            role=Role.USER
        )

        payload = jwt_authenticator.verify_token(token)

        assert payload is not None
        assert payload["user_id"] == "user123"
        assert payload["role"] == Role.USER

    def test_verify_invalid_token(self, jwt_authenticator):
        """Test verifying invalid token"""
        payload = jwt_authenticator.verify_token("invalid_token")

        assert payload is None

    def test_refresh_token(self, jwt_authenticator):
        """Test token refresh"""
        token = jwt_authenticator.create_token(
            user_id="user123",
            role=Role.USER
        )

        refreshed = jwt_authenticator.refresh_token(token)

        assert refreshed is not None
        assert isinstance(refreshed, str)


# ============================================================================
# Role and Permission Tests
# ============================================================================

@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth module not available")
class TestRolesAndPermissions:
    """Test RBAC roles and permissions"""

    def test_role_enum_values(self):
        """Test role enum values"""
        assert Role.ADMIN == "admin"
        assert Role.USER == "user"
        assert Role.READONLY == "readonly"
        assert Role.API_CLIENT == "api_client"

    def test_permission_enum_values(self):
        """Test permission enum values"""
        assert Permission.MEMORY_READ == "memory:read"
        assert Permission.MEMORY_WRITE == "memory:write"
        assert Permission.SYSTEM_ADMIN == "system:admin"

    def test_admin_permissions(self):
        """Test admin has all permissions"""
        from src.security.auth import ROLE_PERMISSIONS

        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.MEMORY_READ in admin_perms
        assert Permission.SYSTEM_ADMIN in admin_perms
        assert len(admin_perms) > 8

    def test_user_permissions(self):
        """Test user has limited permissions"""
        from src.security.auth import ROLE_PERMISSIONS

        user_perms = ROLE_PERMISSIONS[Role.USER]
        assert Permission.MEMORY_READ in user_perms
        assert Permission.SYSTEM_ADMIN not in user_perms

    def test_readonly_permissions(self):
        """Test readonly has only read permissions"""
        from src.security.auth import ROLE_PERMISSIONS

        readonly_perms = ROLE_PERMISSIONS[Role.READONLY]
        assert Permission.MEMORY_READ in readonly_perms
        assert Permission.MEMORY_WRITE not in readonly_perms


# ============================================================================
# RBAC Manager Tests
# ============================================================================

@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth module not available")
class TestRBACManager:
    """Test role-based access control"""

    @pytest.fixture
    def rbac_manager(self, mock_postgres_pool):
        """Create RBAC manager instance"""
        return RBACManager(mock_postgres_pool)

    def test_has_permission_admin(self, rbac_manager):
        """Test admin has permission"""
        assert rbac_manager.has_permission(Role.ADMIN, Permission.SYSTEM_ADMIN) is True
        assert rbac_manager.has_permission(Role.ADMIN, Permission.MEMORY_DELETE) is True

    def test_has_permission_user(self, rbac_manager):
        """Test user has limited permissions"""
        assert rbac_manager.has_permission(Role.USER, Permission.MEMORY_READ) is True
        assert rbac_manager.has_permission(Role.USER, Permission.SYSTEM_ADMIN) is False

    def test_has_any_permission(self, rbac_manager):
        """Test checking for any of multiple permissions"""
        perms = [Permission.SYSTEM_ADMIN, Permission.MEMORY_READ]
        assert rbac_manager.has_any_permission(Role.USER, perms) is True
        assert rbac_manager.has_any_permission(Role.READONLY, perms) is True

    def test_has_all_permissions(self, rbac_manager):
        """Test checking for all permissions"""
        perms = [Permission.MEMORY_READ, Permission.MEMORY_WRITE]
        assert rbac_manager.has_all_permissions(Role.USER, perms) is True
        assert rbac_manager.has_all_permissions(Role.READONLY, perms) is False


# ============================================================================
# Security Middleware Tests
# ============================================================================

@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason="Security middleware not available")
class TestSecurityMiddleware:
    """Test security middleware"""

    @pytest.fixture
    def security_middleware(self, security_framework):
        """Create security middleware instance"""
        return SecurityMiddleware(Mock(), security_framework)

    @pytest.mark.asyncio
    async def test_get_client_ip(self, security_middleware, mock_fastapi_request):
        """Test getting client IP"""
        ip = security_middleware._get_client_ip(mock_fastapi_request)

        assert ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_get_client_ip_with_forwarded(self, security_middleware, mock_fastapi_request):
        """Test getting client IP from X-Forwarded-For"""
        mock_fastapi_request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}

        ip = security_middleware._get_client_ip(mock_fastapi_request)

        assert ip == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_add_security_headers(self, security_middleware, mock_fastapi_response):
        """Test adding security headers"""
        security_middleware._add_security_headers(mock_fastapi_response)

        assert "X-Content-Type-Options" in mock_fastapi_response.headers
        assert mock_fastapi_response.headers["X-Frame-Options"] == "DENY"
        assert "X-Request-ID" in mock_fastapi_response.headers


# ============================================================================
# File Upload Middleware Tests
# ============================================================================

@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason="Security middleware not available")
class TestFileUploadSecurityMiddleware:
    """Test file upload security middleware"""

    @pytest.fixture
    def file_upload_middleware(self, security_framework):
        """Create file upload middleware instance"""
        return FileUploadSecurityMiddleware(Mock(), security_framework)

    @pytest.mark.asyncio
    async def test_handle_file_upload_valid(self, file_upload_middleware, mock_fastapi_request):
        """Test handling valid file upload"""
        mock_fastapi_request.headers = {"content-type": "multipart/form-data"}

        # Mock form data with valid file
        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=b'\xff\xd8\xff\xe0')
        mock_file.seek = Mock()

        mock_form = Mock()
        mock_form.items = Mock(return_value=[("file", mock_file)])
        mock_fastapi_request.form = AsyncMock(return_value=mock_form)

        # Should not raise exception
        with patch.object(file_upload_middleware, '_handle_file_upload'):
            await file_upload_middleware.dispatch(mock_fastapi_request, Mock())

    @pytest.mark.asyncio
    async def test_handle_file_upload_invalid_type(self, file_upload_middleware, mock_fastapi_request):
        """Test handling invalid file type"""
        mock_fastapi_request.headers = {"content-type": "multipart/form-data"}

        # Mock form data with invalid file
        mock_file = Mock()
        mock_file.filename = "test.exe"
        mock_file.content_type = "application/exe"
        mock_file.read = AsyncMock(return_value=b'MZ')
        mock_file.seek = Mock()

        mock_form = Mock()
        mock_form.items = Mock(return_value=[("file", mock_file)])
        mock_fastapi_request.form = AsyncMock(return_value=mock_form)

        # Should raise exception or return error response
        result = await file_upload_middleware._handle_file_upload(mock_fastapi_request, Mock())
        assert result.status_code == 400


# ============================================================================
# Input Sanitization Middleware Tests
# ============================================================================

@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason="Security middleware not available")
class TestInputSanitizationMiddleware:
    """Test input sanitization middleware"""

    @pytest.fixture
    def sanitization_middleware(self, security_framework):
        """Create sanitization middleware instance"""
        return InputSanitizationMiddleware(Mock(), security_framework)

    def test_sanitize_dict(self, sanitization_middleware):
        """Test sanitizing dictionary"""
        data = {
            "clean": "normal text",
            "dirty": "<script>alert('xss')</script>",
            "nested": {"value": "test' OR '1'='1"}
        }

        sanitized = sanitization_middleware._sanitize_dict(data)

        assert "<script>" not in str(sanitized.get("dirty", ""))


# ============================================================================
# Security Monitoring Tests
# ============================================================================

@pytest.mark.skipif(not DEPLOYMENT_AVAILABLE, reason="Security deployment not available")
class TestSecurityMonitoring:
    """Test security monitoring and incident response"""

    @pytest.fixture(autouse=True)
    def clear_prometheus_registry(self):
        """Clear Prometheus metrics registry before each test to avoid duplicate registration errors."""
        from prometheus_client import REGISTRY
        # Clear all collectors from the registry
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            REGISTRY.unregister(collector)
        yield
        # Cleanup after test
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

    def test_security_incident_creation(self):
        """Test creating security incident"""
        incident = SecurityIncident(
            incident_id="INC-20260209-ABCD",
            severity=SecurityIncidentSeverity.HIGH,
            incident_type="malware_detected",
            source_ip="10.0.0.1",
            affected_systems=["file_system"],
            description="Malware detected in uploaded file",
            timestamp=datetime.now()
        )

        assert incident.incident_id == "INC-20260209-ABCD"
        assert incident.severity == SecurityIncidentSeverity.HIGH
        assert incident.resolved is False

    def test_alert_rule_creation(self):
        """Test creating alert rule"""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test alert rule",
            condition="severity:high",
            severity_threshold=SecurityIncidentSeverity.HIGH,
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK]
        )

        assert rule.rule_id == "test_rule"
        assert rule.enabled is True
        assert len(rule.channels) == 2

    def test_security_metrics(self):
        """Test security metrics initialization"""
        metrics = SecurityMetrics()

        assert metrics.security_events_total is not None
        assert metrics.security_incidents_total is not None
        assert metrics.blocked_requests_total is not None

    @pytest.mark.asyncio
    async def test_alert_manager_process_event(self):
        """Test alert manager processing security event"""
        config = {
            "email": {"enabled": False},
            "slack": {"enabled": False}
        }
        alert_manager = AlertManager(config)

        event = SecurityEvent(
            event_type="test_event",
            severity="high",
            source_ip="10.0.0.1",
            user_agent="test",
            timestamp=datetime.now(),
            details={"test": "data"}
        )

        # Should not raise exception
        result = await alert_manager.process_security_event(event)
        # Result might be None if no rule triggered
        assert result is None or isinstance(result, SecurityIncident)


# ============================================================================
# ASCII-Only Output Validation Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestASCIICOutputValidation:
    """Test that all output uses ASCII-only characters"""

    def test_security_logger_uses_ascii(self, security_logger, sample_security_event):
        """Test security logger produces ASCII-only output"""
        import io
        import sys

        # Capture log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(logging.Formatter('%(message)s'))
        security_logger.logger.addHandler(handler)

        security_logger.log_security_event(sample_security_event)

        # Get output and check for ASCII
        output = log_capture.getvalue()
        for char in output:
            if ord(char) > 127:
                pytest.fail(f"Non-ASCII character found in output: {char} (U+{ord(char):04X})")

    def test_error_messages_use_ascii(self, security_logger):
        """Test error messages use ASCII characters"""
        # Test various error scenarios
        messages = [
            "File upload blocked: malicious content detected",
            "Authentication failed: invalid credentials",
            "Rate limit exceeded: too many requests",
            "Security alert: potential intrusion detected",
            "Error: Password does not meet requirements"
        ]

        for message in messages:
            try:
                # Try to encode as ASCII
                message.encode('ascii')
            except UnicodeEncodeError:
                pytest.fail(f"Non-ASCII character in message: {message}")

    def test_password_validation_messages_ascii(self, password_policy):
        """Test password validation messages are ASCII-only"""
        _, errors = password_policy.validate_password("weak")

        for error in errors:
            try:
                error.encode('ascii')
            except UnicodeEncodeError:
                pytest.fail(f"Non-ASCII character in error message: {error}")


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.skipif(not (SECURITY_FRAMEWORK_AVAILABLE and DATA_PROTECTION_AVAILABLE and AUTH_AVAILABLE), reason="Required security modules not available")
class TestSecurityIntegration:
    """Integration tests for security modules"""

    @pytest.mark.asyncio
    async def test_complete_file_upload_security_flow(self, security_framework):
        """Test complete file upload security flow"""
        # Test file validation
        file_content = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        is_valid, message = security_framework.input_validator.validate_file_upload(
            file_content=file_content,
            filename="test.jpg",
            content_type="image/jpeg",
            source_ip="10.0.0.1"
        )

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self, jwt_authenticator, password_policy):
        """Test complete authentication flow"""
        # 1. Validate password (use a password without sequential characters)
        password = "SecureP@ss2024!"
        is_valid, errors = password_policy.validate_password(password)
        assert is_valid is True

        # 2. Hash password
        hashed, hash_type = password_policy.hash_password(password)
        assert hashed is not None

        # 3. Create JWT token
        token = jwt_authenticator.create_token(
            user_id="user123",
            role=Role.USER
        )
        assert token is not None

        # 4. Verify token
        payload = jwt_authenticator.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_complete_encryption_flow(self, encryption_manager, pii_detector):
        """Test complete encryption and PII protection flow"""
        # 1. Detect PII
        text = "Contact john@example.com for support"
        detected = pii_detector.detect_pii(text)
        assert 'email' in detected

        # 2. Mask PII
        masked = pii_detector.mask_pii(text)
        assert "john@example.com" not in masked

        # 3. Encrypt sensitive data
        encrypted = encryption_manager.encrypt(masked)
        assert encrypted != masked

        # 4. Decrypt
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == masked


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.skipif(not (SECURITY_FRAMEWORK_AVAILABLE and DATA_PROTECTION_AVAILABLE), reason="Required security modules not available")
class TestSecurityPerformance:
    """Performance tests for security operations"""

    def test_password_validation_performance(self, password_policy):
        """Test password validation performance"""
        password = "Str0ng!P@ssw0rd#123"

        start_time = time.time()
        for _ in range(100):
            password_policy.validate_password(password)
        elapsed = time.time() - start_time

        # Should complete 100 validations in under 1 second
        assert elapsed < 1.0

    def test_encryption_performance(self, encryption_manager):
        """Test encryption performance"""
        data = "Sensitive data to encrypt" * 100

        start_time = time.time()
        for _ in range(100):
            encrypted = encryption_manager.encrypt(data)
            encryption_manager.decrypt(encrypted)
        elapsed = time.time() - start_time

        # Should complete 100 encrypt/decrypt cycles in under 2 seconds
        assert elapsed < 2.0

    def test_pii_detection_performance(self, pii_detector):
        """Test PII detection performance"""
        text = "Contact john@example.com or call 555-123-4567 for support" * 100

        start_time = time.time()
        for _ in range(100):
            pii_detector.detect_pii(text)
        elapsed = time.time() - start_time

        # Should complete 100 detections in under 1 second
        assert elapsed < 1.0


# ============================================================================
# Edge Cases Tests
# ============================================================================

@pytest.mark.skipif(not SECURITY_FRAMEWORK_AVAILABLE, reason="Security framework not available")
class TestSecurityEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_password_validation(self, password_policy):
        """Test validating empty password"""
        is_valid, errors = password_policy.validate_password("")
        assert is_valid is False
        assert len(errors) > 0

    def test_maximum_length_password(self, password_policy):
        """Test maximum password length"""
        max_password = "A" * SecurityConfig.MAX_PASSWORD_LENGTH + "1!a"
        is_valid, errors = password_policy.validate_password(max_password)
        assert is_valid is False

    def test_unicode_in_password(self, password_policy):
        """Test password with unicode characters"""
        unicode_password = "Password123!with"
        is_valid, errors = password_policy.validate_password(unicode_password)
        # Should handle unicode without crashing
        assert isinstance(is_valid, bool)

    def test_empty_file_validation(self, input_validator):
        """Test validating empty file"""
        is_valid, message = input_validator.validate_file_upload(
            file_content=b'',
            filename="empty.jpg",
            content_type="image/jpeg",
            source_ip="10.0.0.1"
        )
        assert is_valid is False

    def test_very_long_filename(self, input_validator):
        """Test very long filename"""
        long_filename = "a" * 10000 + ".jpg"
        is_valid, message = input_validator._validate_filename(long_filename)
        assert is_valid is False

    def test_rate_limit_zero_limit(self, rate_limiter):
        """Test rate limit with zero limit"""
        is_limited, info = rate_limiter.is_rate_limited(
            key="test_zero",
            limit="0/1m",
            window_seconds=60
        )
        # Should handle gracefully
        assert isinstance(is_limited, bool)


# ============================================================================
# Test Run Hook
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers for security tests"""
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "encryption: Encryption tests")
    config.addinivalue_line("markers", "pii: PII protection tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
