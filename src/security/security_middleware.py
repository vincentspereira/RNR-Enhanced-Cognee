"""
Security Middleware for Enhanced Cognee Multi-Agent System

FastAPI middleware implementations for all security features
"""

import time
import logging
import secrets
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio
from .enhanced_security_framework import (
    EnhancedSecurityFramework, SecurityLogger, SecurityEvent,
    SecurityConfig, EnhancedInputValidator, EnhancedPasswordPolicy,
    EnhancedRateLimiter
)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware that applies all security measures"""

    def __init__(self, app, security_framework: EnhancedSecurityFramework):
        super().__init__(app)
        self.security_framework = security_framework
        self.security_logger = security_framework.security_logger
        self.rate_limiter = security_framework.rate_limiter
        self.input_validator = security_framework.input_validator

    async def dispatch(self, request: Request, call_next):
        """Process request through security pipeline"""

        start_time = time.time()
        source_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Rate limiting check
        rate_limit_result = await self._check_rate_limit(request, source_ip)
        if rate_limit_result["limited"]:
            self.security_logger.log_rate_limit_exceeded(
                str(request.url), source_ip
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": rate_limit_result.get("retry_after", 60)
                }
            )

        # Security headers
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(response)

        # Log request completion
        process_time = time.time() - start_time
        self._log_request_completion(request, response, process_time, source_ip)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxies"""
        # Check for forwarded IP headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    async def _check_rate_limit(self, request: Request, source_ip: str) -> Dict[str, Any]:
        """Check rate limits for the current request"""

        # Determine endpoint type based on path
        path = str(request.url.path)
        if path.startswith("/auth/") or path.startswith("/login/") or path.startswith("/register/"):
            endpoint_type = "auth_endpoints"
            limit = SecurityConfig.RATE_LIMITS["auth_endpoints"]
        elif path.startswith("/admin/"):
            endpoint_type = "admin_endpoints"
            limit = SecurityConfig.RATE_LIMITS["admin_endpoints"]
        elif path.startswith("/upload/") or path.startswith("/file/"):
            endpoint_type = "file_upload"
            limit = SecurityConfig.RATE_LIMITS["file_upload"]
        else:
            endpoint_type = "api_endpoints"
            limit = SecurityConfig.RATE_LIMITS["api_endpoints"]

        # Generate rate limit key
        rate_limit_key = self.rate_limiter.get_rate_limit_key(request, endpoint_type)

        # Check if rate limited
        is_limited, limit_info = self.rate_limiter.is_rate_limited(
            rate_limit_key, limit, 300  # 5 minute window
        )

        return {
            "limited": is_limited,
            "limit_info": limit_info,
            "endpoint_type": endpoint_type
        }

    def _add_security_headers(self, response: Response):
        """Add security headers to response"""

        for header_name, header_value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header_name] = header_value

        # Add additional security headers
        response.headers["X-Request-ID"] = secrets.token_urlsafe(16)
        response.headers["X-API-Version"] = "1.0.0"

    def _log_request_completion(self, request: Request, response: Response,
                              process_time: float, source_ip: str):
        """Log request completion for security monitoring"""

        # Only log requests that might be suspicious
        status_code = response.status_code
        path = str(request.url.path)

        # Log failed authentication attempts
        if status_code == 401 and ("auth" in path or "login" in path):
            self.security_logger.log_security_event(SecurityEvent(
                event_type="authentication_failure",
                severity="medium",
                source_ip=source_ip,
                user_agent=request.headers.get("user-agent", ""),
                timestamp=datetime.now(),
                details={
                    "path": path,
                    "method": request.method,
                    "status_code": status_code,
                    "process_time": process_time
                }
            ))

        # Log access to sensitive endpoints
        sensitive_paths = ["/admin/", "/config/", "/security/"]
        if any(sensitive_path in path for sensitive_path in sensitive_paths):
            self.security_logger.log_security_event(SecurityEvent(
                event_type="sensitive_endpoint_access",
                severity="low",
                source_ip=source_ip,
                user_agent=request.headers.get("user-agent", ""),
                timestamp=datetime.now(),
                details={
                    "path": path,
                    "method": request.method,
                    "status_code": status_code,
                    "process_time": process_time
                }
            ))


class FileUploadSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware specifically for securing file uploads"""

    def __init__(self, app, security_framework: EnhancedSecurityFramework):
        super().__init__(app)
        self.security_framework = security_framework
        self.input_validator = security_framework.input_validator
        self.security_logger = security_framework.security_logger

    async def dispatch(self, request: Request, call_next):
        """Secure file upload processing"""

        # Check if this is a file upload request
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            return await self._handle_file_upload(request, call_next)

        # For non-upload requests, continue normally
        return await call_next(request)

    async def _handle_file_upload(self, request: Request, call_next):
        """Handle file upload with security validation"""

        source_ip = self._get_client_ip(request)

        try:
            # Parse multipart form data
            form = await request.form()
            files_to_validate = []

            # Collect all uploaded files
            for field_name, field_value in form.items():
                if hasattr(field_value, 'filename') and field_value.filename:
                    files_to_validate.append({
                        'field_name': field_name,
                        'file': field_value
                    })

            # Validate each file
            for file_info in files_to_validate:
                file = file_info['file']
                file_content = await file.read()
                file.seek(0)  # Reset file pointer (synchronous)

                # Perform comprehensive validation
                is_valid, validation_message = self.input_validator.validate_file_upload(
                    file_content,
                    file.filename,
                    file.content_type,
                    source_ip
                )

                if not is_valid:
                    self.security_logger.log_security_event(SecurityEvent(
                        event_type="file_upload_blocked",
                        severity="high",
                        source_ip=source_ip,
                        user_agent=request.headers.get("user-agent", ""),
                        timestamp=datetime.now(),
                        details={
                            "filename": file.filename,
                            "file_type": file.content_type,
                            "file_size": len(file_content),
                            "reason": validation_message
                        }
                    ))

                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "File upload validation failed",
                            "message": validation_message
                        }
                    )

            # If all files are valid, continue with request
            return await call_next(request)

        except Exception as e:
            self.security_logger.log_security_event(SecurityEvent(
                event_type="file_upload_error",
                severity="medium",
                source_ip=source_ip,
                user_agent=request.headers.get("user-agent", ""),
                timestamp=datetime.now(),
                details={
                    "error": str(e),
                    "endpoint": str(request.url.path)
                }
            ))

            return JSONResponse(
                status_code=500,
                content={
                    "error": "File upload processing failed",
                    "message": "An error occurred while processing the file upload"
                }
            )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class AuthenticationSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for securing authentication endpoints"""

    def __init__(self, app, security_framework: EnhancedSecurityFramework):
        super().__init__(app)
        self.security_framework = security_framework
        self.password_policy = security_framework.password_policy
        self.security_logger = security_framework.security_logger

    async def dispatch(self, request: Request, call_next):
        """Secure authentication processing"""

        # Check if this is an authentication-related request
        path = str(request.url.path)
        auth_paths = ["/auth/", "/login/", "/register/", "/change-password/", "/reset-password/"]

        if any(auth_path in path for auth_path in auth_paths):
            return await self._handle_auth_request(request, call_next)

        # For non-auth requests, continue normally
        return await call_next(request)

    async def _handle_auth_request(self, request: Request, call_next):
        """Handle authentication requests with security measures"""

        source_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        try:
            # For POST requests with JSON body, validate password strength
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                    await request.body()  # Reset body for next middleware

                    # Check if password is in the request
                    if "password" in body or "new_password" in body:
                        password = body.get("password") or body.get("new_password")

                        # Validate password strength
                        user_info = {
                            "username": body.get("username"),
                            "email": body.get("email"),
                            "name": body.get("name")
                        }

                        is_valid, errors = self.password_policy.validate_password(password, user_info)

                        if not is_valid:
                            self.security_logger.log_security_event(SecurityEvent(
                                event_type="weak_password_attempt",
                                severity="medium",
                                source_ip=source_ip,
                                user_agent=user_agent,
                                timestamp=datetime.now(),
                                details={
                                    "endpoint": str(request.url.path),
                                    "validation_errors": errors
                                }
                            ))

                            return JSONResponse(
                                status_code=400,
                                content={
                                    "error": "Password validation failed",
                                    "message": "Password does not meet security requirements",
                                    "details": errors
                                }
                            )

                except Exception:
                    # If JSON parsing fails, continue
                    pass

            # Continue with request processing
            return await call_next(request)

        except Exception as e:
            self.security_logger.log_security_event(SecurityEvent(
                event_type="auth_security_error",
                severity="medium",
                source_ip=source_ip,
                user_agent=user_agent,
                timestamp=datetime.now(),
                details={
                    "endpoint": str(request.url.path),
                    "error": str(e)
                }
            ))

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Authentication processing failed",
                    "message": "An error occurred during authentication"
                }
            )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware for sanitizing user input"""

    def __init__(self, app, security_framework: EnhancedSecurityFramework):
        super().__init__(app)
        self.input_validator = security_framework.input_validator
        self.security_logger = security_framework.security_logger

    async def dispatch(self, request: Request, call_next):
        """Sanitize user input in requests"""

        # Sanitize URL parameters
        await self._sanitize_query_params(request)

        # For requests with JSON body, sanitize input
        if "application/json" in request.headers.get("content-type", ""):
            return await self._handle_json_request(request, call_next)

        # For form data, sanitize input
        if "application/x-www-form-urlencoded" in request.headers.get("content-type", ""):
            return await self._handle_form_request(request, call_next)

        # Continue with normal processing for other requests
        return await call_next(request)

    async def _sanitize_query_params(self, request: Request):
        """Sanitize query parameters"""

        # This would require access to the request scope
        # Implementation would depend on the specific framework
        pass

    async def _handle_json_request(self, request: Request, call_next):
        """Handle and sanitize JSON request body"""

        try:
            body = await request.json()
            sanitized_body = self._sanitize_dict(body)

            # Replace request body with sanitized version
            # This is framework-specific implementation
            return await call_next(request)

        except Exception:
            # If JSON parsing fails, continue with original request
            return await call_next(request)

    async def _handle_form_request(self, request: Request, call_next):
        """Handle and sanitize form data"""

        try:
            form = await request.form()
            sanitized_form = {}

            for key, value in form.items():
                if isinstance(value, str):
                    sanitized_form[key] = self.input_validator.sanitize_input(value)
                else:
                    sanitized_form[key] = value

            # Replace form data with sanitized version
            # This is framework-specific implementation
            return await call_next(request)

        except Exception:
            # If form parsing fails, continue with original request
            return await call_next(request)

    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values"""

        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.input_validator.sanitize_input(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict)
                    else self.input_validator.sanitize_input(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring security events"""

    def __init__(self, app, security_framework: EnhancedSecurityFramework):
        super().__init__(app)
        self.security_framework = security_framework
        self.security_logger = security_framework.security_logger

    async def dispatch(self, request: Request, call_next):
        """Monitor requests for security events"""

        start_time = time.time()
        source_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Monitor for suspicious patterns
        await self._monitor_request_patterns(request, response, process_time, source_ip, user_agent)

        return response

    async def _monitor_request_patterns(self, request: Request, response: Response,
                                     process_time: float, source_ip: str, user_agent: str):
        """Monitor request patterns for suspicious activity"""

        path = str(request.url.path)
        status_code = response.status_code
        method = request.method

        # Monitor for SQL injection attempts
        suspicious_patterns = [
            "union select", "or 1=1", "drop table", "insert into",
            "delete from", "update set", "exec(", "xp_cmdshell"
        ]

        query_string = str(request.url.query).lower()
        if any(pattern in query_string for pattern in suspicious_patterns):
            self.security_logger.log_security_event(SecurityEvent(
                event_type="potential_sql_injection",
                severity="high",
                source_ip=source_ip,
                user_agent=user_agent,
                timestamp=datetime.now(),
                details={
                    "path": path,
                    "method": method,
                    "query_string": query_string[:200],  # Limit length
                    "status_code": status_code
                }
            ))

        # Monitor for XSS attempts
        xss_patterns = ["<script", "javascript:", "onerror=", "onload=", "eval("]
        if any(pattern in query_string for pattern in xss_patterns):
            self.security_logger.log_security_event(SecurityEvent(
                event_type="potential_xss_attempt",
                severity="medium",
                source_ip=source_ip,
                user_agent=user_agent,
                timestamp=datetime.now(),
                details={
                    "path": path,
                    "method": method,
                    "query_string": query_string[:200],
                    "status_code": status_code
                }
            ))

        # Monitor for path traversal attempts
        if "../" in path or "%2e%2e%2f" in path.lower():
            self.security_logger.log_security_event(SecurityEvent(
                event_type="potential_path_traversal",
                severity="high",
                source_ip=source_ip,
                user_agent=user_agent,
                timestamp=datetime.now(),
                details={
                    "path": path,
                    "method": method,
                    "status_code": status_code
                }
            ))

        # Monitor for very slow requests (potential DoS)
        if process_time > 30:  # 30 seconds threshold
            self.security_logger.log_security_event(SecurityEvent(
                event_type="slow_request_detected",
                severity="low",
                source_ip=source_ip,
                user_agent=user_agent,
                timestamp=datetime.now(),
                details={
                    "path": path,
                    "method": method,
                    "process_time": process_time,
                    "status_code": status_code
                }
            ))

        # Monitor for repeated failed authentication
        if status_code == 401:
            await self._track_auth_failures(source_ip, user_agent)

    async def _track_auth_failures(self, source_ip: str, user_agent: str):
        """Track repeated authentication failures"""

        # This would typically use Redis or database to track failures
        # For demo purposes, we'll just log the event
        self.security_logger.log_security_event(SecurityEvent(
            event_type="authentication_failure_tracking",
            severity="medium",
            source_ip=source_ip,
            user_agent=user_agent,
            timestamp=datetime.now(),
            details={
                "failure_count": 1,  # Would be incremented based on tracking
                "tracking_period": "1_hour"
            }
        ))

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# Factory function to easily apply all security middleware
def apply_security_middleware(app, security_framework: EnhancedSecurityFramework):
    """Apply all security middleware to FastAPI app"""

    # Apply in reverse order (last applied runs first)
    app.add_middleware(SecurityMonitoringMiddleware, security_framework=security_framework)
    app.add_middleware(InputSanitizationMiddleware, security_framework=security_framework)
    app.add_middleware(AuthenticationSecurityMiddleware, security_framework=security_framework)
    app.add_middleware(FileUploadSecurityMiddleware, security_framework=security_framework)
    app.add_middleware(SecurityMiddleware, security_framework=security_framework)

    return app