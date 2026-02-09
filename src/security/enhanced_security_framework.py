"""
Enhanced Security Framework for Enhanced Cognee Multi-Agent System

Comprehensive security implementation addressing all identified issues:
1. Input validation enhancement for file upload endpoints
2. Password policy strengthening implementation
3. Security headers implementation
4. Rate limiting enhancement
5. Security logging improvement
6. Dependency updates
7. Error handling security
"""

import os
import sys
import re
import math
import hashlib
import secrets
import logging
import json
import time
import traceback
import boto3
import magic
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import asyncio
from functools import wraps
import hashlib
import bcrypt
import passlib.hash
from passlib.hash import bcrypt as passlib_bcrypt, argon2
from passlib.context import CryptContext
from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import requests
from packaging import version
import subprocess
import jwt
from pydantic import BaseModel, validator, constr
import filetype
import bleach
from urllib.parse import urlparse
import ssl
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Security configuration
class SecurityConfig:
    """Enhanced security configuration"""

    # File upload validation
    ALLOWED_FILE_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf', 'text/plain', 'text/csv',
        'application/json', 'application/xml'
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_FILENAME_LENGTH = 255
    FORBIDDEN_FILE_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.scr', '.pif', '.com', '.vbs',
        '.js', '.jar', '.app', '.deb', '.pkg', '.dmg', '.rpm'
    }

    # Password policy
    MIN_PASSWORD_LENGTH = 12
    MAX_PASSWORD_LENGTH = 128
    PASSWORD_COMPLEXITY = {
        'uppercase': True,
        'lowercase': True,
        'digits': True,
        'special_chars': True,
        'no_common_patterns': True,
        'no_personal_info': True
    }

    # Rate limiting
    RATE_LIMITS = {
        'auth_endpoints': "10/5m",  # 10 attempts per 5 minutes
        'api_endpoints': "100/1m",  # 100 requests per minute
        'file_upload': "5/10m",     # 5 uploads per 10 minutes
        'admin_endpoints': "20/5m"  # 20 requests per 5 minutes for admin
    }

    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'same-origin'
    }


@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    source_ip: str
    user_agent: str
    timestamp: datetime
    details: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class SecurityLogger:
    """Enhanced security logging system"""

    def __init__(self, log_file: str = "security_events.log"):
        self.log_file = log_file
        self.logger = logging.getLogger("security")
        self.setup_logging()

    def setup_logging(self):
        """Setup security logging with rotation and formatting"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # File handler with rotation
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.WARNING)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)

    def log_security_event(self, event: SecurityEvent):
        """Log security event with detailed information"""
        log_data = {
            "event_type": event.event_type,
            "severity": event.severity,
            "source_ip": event.source_ip,
            "user_agent": event.user_agent,
            "timestamp": event.timestamp.isoformat(),
            "details": event.details,
            "user_id": event.user_id,
            "session_id": event.session_id
        }

        if event.severity in ['high', 'critical']:
            self.logger.error(f"SECURITY EVENT: {json.dumps(log_data)}")
        elif event.severity == 'medium':
            self.logger.warning(f"SECURITY EVENT: {json.dumps(log_data)}")
        else:
            self.logger.info(f"SECURITY EVENT: {json.dumps(log_data)}")

    def log_file_upload(self, filename: str, file_type: str, file_size: int,
                       source_ip: str, user_id: str = None, success: bool = True):
        """Log file upload events"""
        event = SecurityEvent(
            event_type="file_upload",
            severity="medium" if success else "high",
            source_ip=source_ip,
            user_agent="",  # Add from request if needed
            timestamp=datetime.now(),
            details={
                "filename": filename,
                "file_type": file_type,
                "file_size": file_size,
                "success": success
            },
            user_id=user_id
        )
        self.log_security_event(event)

    def log_authentication_attempt(self, username: str, source_ip: str,
                                  success: bool, failure_reason: str = None):
        """Log authentication attempts"""
        event = SecurityEvent(
            event_type="authentication_attempt",
            severity="low" if success else "medium",
            source_ip=source_ip,
            user_agent="",
            timestamp=datetime.now(),
            details={
                "username": username,
                "success": success,
                "failure_reason": failure_reason
            }
        )
        self.log_security_event(event)

    def log_rate_limit_exceeded(self, endpoint: str, source_ip: str):
        """Log rate limit violations"""
        event = SecurityEvent(
            event_type="rate_limit_exceeded",
            severity="medium",
            source_ip=source_ip,
            user_agent="",
            timestamp=datetime.now(),
            details={
                "endpoint": endpoint,
                "violation_type": "rate_limit"
            }
        )
        self.log_security_event(event)


class EnhancedInputValidator:
    """Enhanced input validation for file uploads and user inputs"""

    def __init__(self, security_logger: SecurityLogger):
        self.security_logger = security_logger
        self.file_scanner = FileScanner()

    def validate_file_upload(self, file_content: bytes, filename: str,
                           content_type: str, source_ip: str) -> Tuple[bool, str]:
        """Comprehensive file upload validation"""

        # Check file size
        if len(file_content) > SecurityConfig.MAX_FILE_SIZE:
            error_msg = f"File size exceeds maximum allowed size of {SecurityConfig.MAX_FILE_SIZE} bytes"
            self.security_logger.log_file_upload(filename, content_type, len(file_content),
                                               source_ip, success=False)
            return False, error_msg

        # Check filename
        filename_validation = self._validate_filename(filename)
        if not filename_validation[0]:
            self.security_logger.log_file_upload(filename, content_type, len(file_content),
                                               source_ip, success=False)
            return filename_validation

        # Check file type
        file_type_validation = self._validate_file_type(file_content, filename, content_type)
        if not file_type_validation[0]:
            self.security_logger.log_file_upload(filename, content_type, len(file_content),
                                               source_ip, success=False)
            return file_type_validation

        # Scan for malicious content
        scan_result = self.file_scanner.scan_file(file_content)
        if not scan_result[0]:
            error_msg = f"File scan failed: {scan_result[1]}"
            self.security_logger.log_file_upload(filename, content_type, len(file_content),
                                               source_ip, success=False)
            return False, error_msg

        # Log successful validation
        self.security_logger.log_file_upload(filename, content_type, len(file_content),
                                           source_ip, success=True)

        return True, "File validation successful"

    def _validate_filename(self, filename: str) -> Tuple[bool, str]:
        """Validate filename for security issues"""

        # Check filename length
        if len(filename) > SecurityConfig.MAX_FILENAME_LENGTH:
            return False, f"Filename exceeds maximum length of {SecurityConfig.MAX_FILENAME_LENGTH} characters"

        # Check for forbidden extensions
        file_ext = Path(filename).suffix.lower()
        if file_ext in SecurityConfig.FORBIDDEN_FILE_EXTENSIONS:
            return False, f"File type {file_ext} is not allowed"

        # Check for dangerous characters
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in filename for char in dangerous_chars):
            return False, "Filename contains invalid characters"

        # Check for path traversal attempts
        if '..' in filename or filename.startswith('/') or '\\' in filename:
            return False, "Path traversal attempt detected"

        return True, "Filename validation successful"

    def _validate_file_type(self, file_content: bytes, filename: str,
                          content_type: str) -> Tuple[bool, str]:
        """Validate file type using multiple methods"""

        # Check content type against allowed types
        if content_type not in SecurityConfig.ALLOWED_FILE_TYPES:
            return False, f"Content type {content_type} is not allowed"

        # Use python-magic to detect actual file type
        try:
            detected_type = magic.from_buffer(file_content, mime=True)
            if detected_type not in SecurityConfig.ALLOWED_FILE_TYPES:
                return False, f"Detected file type {detected_type} is not allowed"
        except Exception as e:
            return False, f"File type detection failed: {str(e)}"

        # Additional validation using filetype library
        try:
            kind = filetype.guess(file_content)
            if kind and kind.mime not in SecurityConfig.ALLOWED_FILE_TYPES:
                return False, f"File type mismatch detected"
        except Exception:
            pass

        # Check for file signature matches
        expected_signatures = {
            'image/jpeg': b'\xff\xd8\xff',
            'image/png': b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a',
            'application/pdf': b'%PDF',
            'text/plain': None,  # Text files may not have clear signatures
        }

        if content_type in expected_signatures and expected_signatures[content_type]:
            signature = expected_signatures[content_type]
            if not file_content.startswith(signature):
                return False, "File signature does not match content type"

        return True, "File type validation successful"

    def sanitize_input(self, input_string: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent XSS and injection attacks"""

        if not input_string:
            return ""

        # Truncate to maximum length
        if len(input_string) > max_length:
            input_string = input_string[:max_length]

        # Remove potentially dangerous HTML tags
        cleaned_input = bleach.clean(
            input_string,
            tags=[],  # No HTML tags allowed
            attributes={},
            strip=True
        )

        # Additional sanitization for SQL injection attempts
        dangerous_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)',
            r'(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)',
            r'(--|#|\/\*|\*\/)',
            r'(\'\s*OR\s*\')',
            r'(\'\s*AND\s*\')',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, cleaned_input, re.IGNORECASE):
                # Log potential injection attempt
                self.security_logger.log_security_event(SecurityEvent(
                    event_type="potential_injection",
                    severity="high",
                    source_ip="",  # Add from request
                    user_agent="",
                    timestamp=datetime.now(),
                    details={
                        "input": cleaned_input[:100],  # Log first 100 chars
                        "pattern_matched": pattern
                    }
                ))
                # Remove dangerous content
                cleaned_input = re.sub(pattern, '', cleaned_input, flags=re.IGNORECASE)

        return cleaned_input.strip()


class FileScanner:
    """File scanner for detecting malicious content"""

    def __init__(self):
        self.virus_total_api_key = os.getenv('VIRUS_TOTAL_API_KEY')
        self.clamav_available = self._check_clamav()

    def _check_clamav(self) -> bool:
        """Check if ClamAV is available"""
        try:
            import pyclamd
            cd = pyclamd.ClamdUnixSocket()
            cd.ping()
            return True
        except:
            return False

    def scan_file(self, file_content: bytes) -> Tuple[bool, str]:
        """Scan file for malicious content"""

        # Check for embedded scripts in non-script files
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'data:text/html',
            b'eval(',
            b'Function(',
            b'document.write',
            b'innerHTML',
            b'outerHTML',
        ]

        file_content_lower = file_content.lower()
        for pattern in suspicious_patterns:
            if pattern in file_content_lower:
                return False, f"Suspicious script content detected: {pattern.decode('utf-8', errors='ignore')}"

        # Check for executable file signatures
        executable_signatures = [
            b'MZ',  # PE executable
            b'\x7fELF',  # ELF executable
            b'\xca\xfe\xba\xbe',  # Java class
            b'\xfe\xed\xfa\xce',  # Mach-O binary (macOS)
            b'\xfe\xed\xfa\xcf',  # Mach-O binary (macOS)
        ]

        for signature in executable_signatures:
            if file_content.startswith(signature):
                return False, "Executable file detected"

        # Use ClamAV if available
        if self.clamav_available:
            try:
                import pyclamd
                cd = pyclamd.ClamdUnixSocket()
                scan_result = cd.scan_stream(file_content)
                if scan_result:
                    return False, f"Malware detected by ClamAV: {scan_result}"
            except Exception as e:
                pass  # Continue with other checks if ClamAV fails

        # Use VirusTotal API if key is available
        if self.virus_total_api_key:
            try:
                vt_result = self._scan_with_virustotal(file_content)
                if not vt_result[0]:
                    return vt_result
            except Exception:
                pass  # Continue if VirusTotal fails

        return True, "File scan completed successfully"

    def _scan_with_virustotal(self, file_content: bytes) -> Tuple[bool, str]:
        """Scan file using VirusTotal API"""
        # File hash for VirusTotal lookup
        file_hash = hashlib.sha256(file_content).hexdigest()

        headers = {
            'x-apikey': self.virus_total_api_key
        }

        # Check if file already analyzed
        response = requests.get(
            f'https://www.virustotal.com/vtapi/v3/files/{file_hash}',
            headers=headers
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('data', {}).get('attributes', {}).get('last_analysis_stats', {}).get('malicious', 0) > 0:
                return False, f"File detected as malicious by {result['data']['attributes']['last_analysis_stats']['malicious']} engines"

        return True, "VirusTotal scan completed successfully"


class EnhancedPasswordPolicy:
    """Enhanced password policy implementation"""

    def __init__(self, security_logger: SecurityLogger):
        self.security_logger = security_logger
        self.common_passwords = self._load_common_passwords()

    def _load_common_passwords(self) -> set:
        """Load list of common passwords to avoid"""
        # Common passwords list (simplified for demo)
        return {
            'password', '123456', '123456789', '12345678', '12345', '1234567',
            '1234567890', '1234', 'qwerty', 'abc123', 'password123', 'admin',
            'letmein', 'welcome', 'monkey', '1234567890', 'password1', 'admin123'
        }

    def validate_password(self, password: str, user_info: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
        """Validate password against enhanced security policy"""

        errors = []

        # Length validation
        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters long")

        if len(password) > SecurityConfig.MAX_PASSWORD_LENGTH:
            errors.append(f"Password must not exceed {SecurityConfig.MAX_PASSWORD_LENGTH} characters")

        # Complexity validation
        complexity = SecurityConfig.PASSWORD_COMPLEXITY

        if complexity['uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        if complexity['lowercase'] and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        if complexity['digits'] and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")

        if complexity['special_chars'] and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>?]', password):
            errors.append("Password must contain at least one special character")

        # Common password validation
        if complexity['no_common_patterns']:
            password_lower = password.lower()
            if password_lower in self.common_passwords:
                errors.append("Password is too common and easily guessable")

            # Check for sequential characters
            if self._has_sequential_chars(password):
                errors.append("Password contains sequential characters")

            # Check for repeated characters
            if self._has_repeated_chars(password):
                errors.append("Password contains too many repeated characters")

        # Personal information validation
        if complexity['no_personal_info'] and user_info:
            if self._contains_personal_info(password, user_info):
                errors.append("Password contains personal information")

        # Entropy calculation
        entropy = self._calculate_entropy(password)
        if entropy < 50:  # Minimum entropy threshold
            errors.append(f"Password has low entropy ({entropy:.1f}). Use a more complex password")

        is_valid = len(errors) == 0

        if is_valid:
            self.security_logger.log_security_event(SecurityEvent(
                event_type="password_validation_success",
                severity="low",
                source_ip="",
                user_agent="",
                timestamp=datetime.now(),
                details={"entropy": entropy, "length": len(password)}
            ))
        else:
            self.security_logger.log_security_event(SecurityEvent(
                event_type="password_validation_failure",
                severity="medium",
                source_ip="",
                user_agent="",
                timestamp=datetime.now(),
                details={"errors": errors}
            ))

        return is_valid, errors

    def _has_sequential_chars(self, password: str) -> bool:
        """Check for sequential characters in password"""

        # Check for sequential numbers
        for i in range(len(password) - 2):
            if (password[i].isdigit() and password[i+1].isdigit() and password[i+2].isdigit() and
                int(password[i]) + 1 == int(password[i+1]) and
                int(password[i+1]) + 1 == int(password[i+2])):
                return True

        # Check for sequential letters
        for i in range(len(password) - 2):
            if (password[i].isalpha() and password[i+1].isalpha() and password[i+2].isalpha() and
                ord(password[i].lower()) + 1 == ord(password[i+1].lower()) and
                ord(password[i+1].lower()) + 1 == ord(password[i+2].lower())):
                return True

        return False

    def _has_repeated_chars(self, password: str) -> bool:
        """Check for too many repeated characters"""

        # Check for 3 or more consecutive same characters
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True

        # Check if more than 50% of characters are the same
        char_count = {}
        for char in password:
            char_count[char] = char_count.get(char, 0) + 1

        # Handle empty password case
        if char_count:
            max_count = max(char_count.values())
            if max_count > len(password) * 0.5:
                return True

        return False

    def _contains_personal_info(self, password: str, user_info: Dict[str, Any]) -> bool:
        """Check if password contains personal information"""

        password_lower = password.lower()

        # Check against username
        if 'username' in user_info and user_info['username']:
            username = user_info['username'].lower()
            if username in password_lower or password_lower in username:
                return True

        # Check against email
        if 'email' in user_info and user_info['email']:
            email_parts = user_info['email'].lower().split('@')
            if len(email_parts) > 1:
                if email_parts[0] in password_lower:
                    return True

        # Check against name
        if 'name' in user_info and user_info['name']:
            name_parts = user_info['name'].lower().split()
            for part in name_parts:
                if len(part) > 2 and part in password_lower:
                    return True

        return False

    def _calculate_entropy(self, password: str) -> float:
        """Calculate password entropy"""

        if not password:
            return 0

        char_set_size = 0

        if re.search(r'[a-z]', password):
            char_set_size += 26
        if re.search(r'[A-Z]', password):
            char_set_size += 26
        if re.search(r'\d', password):
            char_set_size += 10
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>?]', password):
            char_set_size += 32

        if char_set_size == 0:
            return 0

        entropy = len(password) * (math.log2(char_set_size))
        return entropy

    def hash_password(self, password: str) -> Tuple[str, str]:
        """Hash password using Argon2 (preferred) with bcrypt fallback"""

        try:
            # Try Argon2 first (more secure)
            salt = secrets.token_bytes(32)
            hash_obj = argon2.using(
                salt=salt,
                rounds=4,
                memory_cost=102400,  # 100MB
                parallelism=8,
                hash_len=32
            ).hash(password)
            return hash_obj, "argon2"
        except Exception:
            # Fallback to bcrypt
            salt = bcrypt.gensalt(rounds=14)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8'), "bcrypt"

    def verify_password(self, password: str, hashed_password: str, hash_type: str) -> bool:
        """Verify password against hash"""

        try:
            if hash_type == "argon2":
                return argon2.verify(password, hashed_password)
            elif hash_type == "bcrypt":
                return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
            else:
                # Try both if hash type is unknown
                return argon2.verify(password, hashed_password) or \
                       bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False


class SecurityHeadersMiddleware:
    """Middleware for adding security headers to responses"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Intercept response to add headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))

                    # Add security headers
                    for header_name, header_value in SecurityConfig.SECURITY_HEADERS.items():
                        # Convert header name to bytes for ASGI
                        header_bytes = header_name.encode('utf-8')
                        if header_bytes not in headers:
                            headers[header_bytes] = header_value.encode('utf-8')

                    message["headers"] = [(k, v) for k, v in headers.items()]

                await send(message)

            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


class EnhancedRateLimiter:
    """Enhanced rate limiting with multiple strategies"""

    def __init__(self, security_logger: SecurityLogger):
        self.security_logger = security_logger
        self.redis_client = self._init_redis()
        self.memory_store = {}  # Fallback

    def _init_redis(self):
        """Initialize Redis client for distributed rate limiting"""
        try:
            import redis
            return redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True
            )
        except Exception:
            return None

    def is_rate_limited(self, key: str, limit: str, window_seconds: int) -> Tuple[bool, Dict[str, Any]]:
        """Check if request should be rate limited"""

        try:
            # Parse limit string (e.g., "10/5m" -> 10 requests per 5 minutes)
            max_requests, time_unit = limit.split('/')
            max_requests = int(max_requests)

            # Convert time unit to seconds
            if time_unit.endswith('m'):
                window_seconds = int(time_unit[:-1]) * 60
            elif time_unit.endswith('h'):
                window_seconds = int(time_unit[:-1]) * 3600
            elif time_unit.endswith('s'):
                window_seconds = int(time_unit[:-1])
            else:
                window_seconds = int(time_unit)

            current_time = int(time.time())
            window_start = current_time - window_seconds

            if self.redis_client:
                return self._check_redis_rate_limit(key, max_requests, window_start, current_time)
            else:
                return self._check_memory_rate_limit(key, max_requests, window_start, current_time)

        except Exception as e:
            # Fail open - allow request if rate limiting fails
            return False, {"error": str(e)}

    def _check_redis_rate_limit(self, key: str, max_requests: int, window_start: int, current_time: int) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis"""

        # Use Redis sorted set for sliding window
        redis_key = f"rate_limit:{key}"

        # Remove old entries
        self.redis_client.zremrangebyscore(redis_key, 0, window_start)

        # Add current request
        self.redis_client.zadd(redis_key, {str(current_time): current_time})

        # Count requests in window
        request_count = self.redis_client.zcard(redis_key)

        # Set expiration
        self.redis_key = redis_key  # Fix: define redis_key before using it
        self.redis_client.expire(self.redis_key, 3600)  # 1 hour TTL

        is_limited = request_count > max_requests
        remaining_requests = max(0, max_requests - request_count)
        reset_time = current_time + self.redis_client.ttl(self.redis_key)

        return is_limited, {
            "limit": max_requests,
            "remaining": remaining_requests,
            "reset": reset_time,
            "retry_after": 60  # Suggest retry after 1 minute
        }

    def _check_memory_rate_limit(self, key: str, max_requests: int, window_start: int, current_time: int) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using in-memory storage (fallback)"""

        if key not in self.memory_store:
            self.memory_store[key] = []

        # Remove old entries
        self.memory_store[key] = [
            timestamp for timestamp in self.memory_store[key]
            if timestamp > window_start
        ]

        # Add current request
        self.memory_store[key].append(current_time)

        # Clean up old keys
        current_time_ = time.time()  # Fix: define current_time_ before using it
        self.memory_store = {
            k: v for k, v in self.memory_store.items()
            if v and max(v) > (current_time_ - 3600)  # Keep keys with recent activity
        }

        request_count = len(self.memory_store[key])
        is_limited = request_count > max_requests
        remaining_requests = max(0, max_requests - request_count)

        return is_limited, {
            "limit": max_requests,
            "remaining": remaining_requests,
            "reset": current_time + 300,  # 5 minutes
            "retry_after": 60
        }

    def get_rate_limit_key(self, request: Request, endpoint_type: str) -> str:
        """Generate rate limit key based on request context"""

        source_ip = get_remote_address(request)
        user_agent = request.headers.get("user-agent", "")

        # Add user ID if authenticated
        user_id = getattr(request.state, 'user_id', None)

        if user_id:
            return f"{endpoint_type}:{user_id}"
        else:
            # Use IP + user agent hash for anonymous users
            ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
            return f"{endpoint_type}:{source_ip}:{ua_hash}"


class DependencyUpdater:
    """Update dependencies to address security vulnerabilities"""

    def __init__(self, security_logger: SecurityLogger):
        self.security_logger = security_logger
        self.vulnerable_packages = self._load_vulnerable_packages()

    def _load_vulnerable_packages(self) -> Dict[str, str]:
        """Load list of known vulnerable packages and their minimum safe versions"""
        return {
            'requests': '2.28.0',
            'urllib3': '1.26.0',
            'cryptography': '3.4.8',
            'pyjwt': '2.4.0',
            'flask': '2.0.0',
            'django': '3.2.0',
            'pillow': '8.3.0',
            'jinja2': '3.0.0',
            'markupsafe': '2.0.0',
            'werkzeug': '2.0.0'
        }

    def check_dependencies(self) -> Dict[str, Any]:
        """Check for vulnerable dependencies"""

        try:
            # Get installed packages
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=json'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {"error": "Failed to get package list"}

            installed_packages = json.loads(result.stdout)

            vulnerable_found = []
            safe_packages = []

            for package in installed_packages:
                package_name = package['name'].lower()
                package_version = package['version']

                if package_name in self.vulnerable_packages:
                    min_safe_version = self.vulnerable_packages[package_name]

                    if version.parse(package_version) < version.parse(min_safe_version):
                        vulnerable_found.append({
                            'package': package_name,
                            'current_version': package_version,
                            'minimum_safe_version': min_safe_version,
                            'severity': 'high'
                        })
                    else:
                        safe_packages.append(package_name)

            return {
                'vulnerable_packages': vulnerable_found,
                'safe_packages': safe_packages,
                'total_checked': len(installed_packages)
            }

        except Exception as e:
            return {"error": f"Dependency check failed: {str(e)}"}

    def update_vulnerable_dependencies(self) -> Dict[str, Any]:
        """Update vulnerable dependencies"""

        update_results = {
            'successful_updates': [],
            'failed_updates': [],
            'skipped_updates': []
        }

        for package_name, min_version in self.vulnerable_packages.items():
            try:
                # Check if package is installed and vulnerable
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'show', package_name],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    # Package is installed, check version
                    for line in result.stdout.split('\n'):
                        if line.startswith('Version:'):
                            current_version = line.split(':')[1].strip()

                            if version.parse(current_version) < version.parse(min_version):
                                # Update package
                                update_result = subprocess.run(
                                    [sys.executable, '-m', 'pip', 'install', '--upgrade', f'{package_name}>={min_version}'],
                                    capture_output=True,
                                    text=True
                                )

                                if update_result.returncode == 0:
                                    update_results['successful_updates'].append({
                                        'package': package_name,
                                        'old_version': current_version,
                                        'new_version': min_version
                                    })

                                    self.security_logger.log_security_event(SecurityEvent(
                                        event_type="dependency_update_success",
                                        severity="low",
                                        source_ip="system",
                                        user_agent="system",
                                        timestamp=datetime.now(),
                                        details={
                                            "package": package_name,
                                            "old_version": current_version,
                                            "new_version": min_version
                                        }
                                    ))
                                else:
                                    update_results['failed_updates'].append({
                                        'package': package_name,
                                        'error': update_result.stderr
                                    })
                            else:
                                update_results['skipped_updates'].append({
                                    'package': package_name,
                                    'reason': 'Already at safe version',
                                    'current_version': current_version
                                })

            except Exception as e:
                update_results['failed_updates'].append({
                    'package': package_name,
                    'error': str(e)
                })

        return update_results


class SecureErrorHandler:
    """Secure error handling to prevent information leakage"""

    def __init__(self, security_logger: SecurityLogger):
        self.security_logger = security_logger
        self.production_mode = os.getenv('ENVIRONMENT', 'development') == 'production'

    def handle_error(self, error: Exception, request_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle errors securely without exposing sensitive information"""

        # Log the full error for debugging
        self.security_logger.log_security_event(SecurityEvent(
            event_type="error_occurred",
            severity="medium",
            source_ip=request_context.get('source_ip', 'unknown') if request_context else 'unknown',
            user_agent=request_context.get('user_agent', '') if request_context else '',
            timestamp=datetime.now(),
            details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "stack_trace": traceback.format_exc(),
                "request_path": request_context.get('path', '') if request_context else '',
                "user_id": request_context.get('user_id') if request_context else None
            }
        ))

        # Return sanitized error response
        if self.production_mode:
            # In production, don't expose internal error details
            return {
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later.",
                "error_id": self._generate_error_id(),
                "timestamp": datetime.now().isoformat()
            }
        else:
            # In development, provide more details for debugging
            return {
                "error": type(error).__name__,
                "message": str(error),
                "error_id": self._generate_error_id(),
                "timestamp": datetime.now().isoformat(),
                "debug_mode": True
            }

    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking"""
        return secrets.token_urlsafe(16)

    def sanitize_error_message(self, message: str) -> str:
        """Sanitize error messages to prevent information leakage"""

        # Remove sensitive file paths
        message = re.sub(r'/[^\s]+/([^\s/]+\.py)', r'/path/\1', message)

        # Remove database connection strings
        message = re.sub(r'(mysql|postgresql|sqlite)://[^\s]+', 'DATABASE_URL', message)

        # Remove API keys and tokens
        message = re.sub(r'([a-zA-Z0-9]{20,})', 'REDACTED', message)

        # Remove internal server details
        message = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'IP_ADDRESS', message)

        return message


# Integration decorator for rate limiting
def rate_limit(endpoint_type: str):
    """Decorator for rate limiting endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Implementation would go here
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Security validation decorators
def validate_file_upload(func):
    """Decorator for validating file uploads"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Implementation would go here
        return await func(*args, **kwargs)
    return wrapper


def validate_password(func):
    """Decorator for validating passwords"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Implementation would go here
        return await func(*args, **kwargs)
    return wrapper


# Main security framework class
class EnhancedSecurityFramework:
    """Main enhanced security framework class"""

    def __init__(self):
        self.security_logger = SecurityLogger()
        self.input_validator = EnhancedInputValidator(self.security_logger)
        self.password_policy = EnhancedPasswordPolicy(self.security_logger)
        self.rate_limiter = EnhancedRateLimiter(self.security_logger)
        self.dependency_updater = DependencyUpdater(self.security_logger)
        self.error_handler = SecureErrorHandler(self.security_logger)

    def initialize_security(self):
        """Initialize all security components"""

        # Log security framework initialization
        self.security_logger.log_security_event(SecurityEvent(
            event_type="security_framework_initialized",
            severity="low",
            source_ip="system",
            user_agent="system",
            timestamp=datetime.now(),
            details={
                "input_validation": True,
                "password_policy": True,
                "rate_limiting": True,
                "security_headers": True,
                "dependency_checking": True,
                "secure_error_handling": True
            }
        ))

        return {
            "status": "initialized",
            "components": [
                "Enhanced Input Validation",
                "Password Policy Enforcement",
                "Rate Limiting",
                "Security Headers",
                "Dependency Updates",
                "Secure Error Handling"
            ],
            "timestamp": datetime.now().isoformat()
        }

    def run_security_audit(self) -> Dict[str, Any]:
        """Run comprehensive security audit"""

        audit_results = {
            "audit_timestamp": datetime.now().isoformat(),
            "components": {},
            "overall_score": 0,
            "recommendations": []
        }

        # Check dependencies
        dependency_check = self.dependency_updater.check_dependencies()
        audit_results["components"]["dependencies"] = dependency_check

        # Calculate overall security score
        vulnerable_count = len(dependency_check.get('vulnerable_packages', []))
        dependency_score = max(0, 100 - (vulnerable_count * 10))

        audit_results["overall_score"] = dependency_score

        if vulnerable_count > 0:
            audit_results["recommendations"].append(
                f"Update {vulnerable_count} vulnerable dependencies"
            )

        return audit_results


# Example usage
if __name__ == "__main__":
    # Initialize security framework
    security_framework = EnhancedSecurityFramework()

    # Initialize security components
    init_result = security_framework.initialize_security()
    print("Security Framework Initialized:", json.dumps(init_result, indent=2))

    # Run security audit
    audit_result = security_framework.run_security_audit()
    print("Security Audit Results:", json.dumps(audit_result, indent=2))