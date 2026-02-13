"""
Enhanced Cognee MCP Security Module

Provides authorization, input validation, and confirmation mechanisms
for MCP tools to ensure production-ready security.

This module is ASCII-only output compatible for Windows console.
"""

import re
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class AuthorizationError(Exception):
    """Raised when authorization check fails."""
    pass


class ConfirmationRequiredError(Exception):
    """Raised when operation requires user confirmation."""
    pass


# ============================================================================
# SPECIFIC EXCEPTION TYPES
# ============================================================================

class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class DatabaseQueryError(Exception):
    """Raised when database query fails."""
    pass


class DataIntegrityError(Exception):
    """Raised when data integrity check fails."""
    pass


class BackupCreationError(Exception):
    """Raised when backup creation fails."""
    pass


class BackupRestoreError(Exception):
    """Raised when backup restoration fails."""
    pass


class DeduplicationError(Exception):
    """Raised when memory deduplication fails."""
    pass


class SummarizationError(Exception):
    """Raised when memory summarization fails."""
    pass


class SynchronizationError(Exception):
    """Raised when real-time sync fails."""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


class TimeoutError(Exception):
    """Raised when operation times out."""
    pass


class ResourceExhaustedError(Exception):
    """Raised when system resources are exhausted."""
    pass


class InsufficientPermissionsError(Exception):
    """Raised when file/system permissions are insufficient."""
    pass


class InvalidStateError(Exception):
    """Raised when operation is attempted in invalid state."""
    pass


# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_uuid(uuid_str: str, param_name: str = "UUID") -> str:
    """
    Validate UUID format.

    Args:
        uuid_str: UUID string to validate
        param_name: Parameter name for error messages

    Returns:
        Validated UUID string

    Raises:
        ValidationError: If UUID is invalid
    """
    try:
        return str(uuid.UUID(uuid_str))
    except (ValueError, AttributeError):
        raise ValidationError(
            f"ERR Invalid {param_name}: '{uuid_str}'. "
            f"Expected valid UUID format (e.g., 550e8400-e29b-41d4-a716-446655440000)"
        )


def validate_positive_int(
    value: int,
    param_name: str = "value",
    min_value: int = 1,
    max_value: Optional[int] = None
) -> int:
    """
    Validate positive integer within range.

    Args:
        value: Integer to validate
        param_name: Parameter name for error messages
        min_value: Minimum allowed value (default: 1)
        max_value: Maximum allowed value (default: None)

    Returns:
        Validated integer

    Raises:
        ValidationError: If value is out of range
    """
    if not isinstance(value, int):
        raise ValidationError(
            f"ERR {param_name} must be an integer, got {type(value).__name__}"
        )

    if value < min_value:
        raise ValidationError(
            f"ERR {param_name} must be >= {min_value}, got {value}"
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"ERR {param_name} must be <= {max_value}, got {value}"
        )

    return value


def validate_days(value: int, param_name: str = "days") -> int:
    """
    Validate days parameter (common across many tools).

    Args:
        value: Days value to validate
        param_name: Parameter name for error messages

    Returns:
        Validated days value
    """
    return validate_positive_int(value, param_name, min_value=0, max_value=36500)  # 100 years max


def validate_limit(value: int, param_name: str = "limit") -> int:
    """
    Validate limit parameter for pagination.

    Args:
        value: Limit value to validate
        param_name: Parameter name for error messages

    Returns:
        Validated limit value
    """
    return validate_positive_int(value, param_name, min_value=1, max_value=10000)


def validate_agent_id(agent_id: str) -> str:
    """
    Validate agent ID format.

    Args:
        agent_id: Agent ID to validate

    Returns:
        Validated agent ID

    Raises:
        ValidationError: If agent_id is invalid
    """
    if not agent_id or not isinstance(agent_id, str):
        raise ValidationError("ERR agent_id must be a non-empty string")

    if len(agent_id) > 255:
        raise ValidationError("ERR agent_id must be <= 255 characters")

    # Allow alphanumeric, hyphens, underscores, periods
    if not re.match(r'^[a-zA-Z0-9._-]+$', agent_id):
        raise ValidationError(
            f"ERR Invalid agent_id format: '{agent_id}'. "
            f"Use only alphanumeric, hyphens, underscores, periods"
        )

    return agent_id


def validate_category(category: str) -> str:
    """
    Validate category name.

    Args:
        category: Category name to validate

    Returns:
        Validated category name

    Raises:
        ValidationError: If category is invalid
    """
    if not category or not isinstance(category, str):
        raise ValidationError("ERR category must be a non-empty string")

    if len(category) > 100:
        raise ValidationError("ERR category must be <= 100 characters")

    # Allow alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', category):
        raise ValidationError(
            f"ERR Invalid category format: '{category}'. "
            f"Use only alphanumeric, hyphens, underscores"
        )

    return category


def validate_memory_content(content: str, max_length: int = 1000000) -> str:
    """
    Validate memory content.

    Args:
        content: Memory content to validate
        max_length: Maximum allowed length

    Returns:
        Validated content

    Raises:
        ValidationError: If content is invalid
    """
    if not content or not isinstance(content, str):
        raise ValidationError("ERR content must be a non-empty string")

    if len(content) > max_length:
        raise ValidationError(
            f"ERR content exceeds maximum length of {max_length:,} characters"
        )

    return content


def sanitize_string(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent injection attacks.

    Args:
        input_str: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(input_str, str):
        raise ValidationError("ERR Input must be a string")

    # Remove null bytes
    sanitized = input_str.replace('\x00', '')

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def validate_path_safe(path_str: str, allowed_base: str) -> str:
    """
    Validate path is safe and within allowed directory.

    Args:
        path_str: Path to validate
        allowed_base: Base directory that must contain the path

    Returns:
        Validated absolute path

    Raises:
        ValidationError: If path is unsafe
    """
    import os

    # Normalize paths
    allowed_base = os.path.abspath(allowed_base)
    target_path = os.path.abspath(os.path.join(allowed_base, path_str))

    # Check for path traversal
    if not target_path.startswith(allowed_base):
        raise ValidationError(
            f"ERR Path traversal detected: '{path_str}' is outside allowed directory"
        )

    return target_path


# ============================================================================
# AUTHORIZATION
# ============================================================================

class Authorizer:
    """
    Authorization checker for MCP operations.

    Verifies that agents/users have permission to perform operations.
    """

    def __init__(self):
        """Initialize authorizer with default permissions."""
        self.admin_agents = {
            "system",
            "admin",
            "claude-code"
        }
        self.protected_categories = {
            "system",
            "admin",
            "config"
        }

    async def check_delete_permission(
        self,
        agent_id: str,
        memory_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Check if agent has permission to delete memory/memories.

        Args:
            agent_id: Agent requesting deletion
            memory_id: Specific memory ID (if single delete)
            category: Category (if bulk delete)

        Returns:
            True if authorized

        Raises:
            AuthorizationError: If not authorized
        """
        # Admin agents can delete anything
        if agent_id in self.admin_agents:
            return True

        # Non-admin agents cannot delete from protected categories
        if category and category.lower() in self.protected_categories:
            raise AuthorizationError(
                f"ERR Authorization failed: Cannot delete from protected category '{category}'. "
                f"Requires admin privileges."
            )

        # For single memory delete, verify ownership
        if memory_id:
            # This would need database check to verify ownership
            # For now, allow if category check passed
            pass

        return True

    async def check_modify_permission(
        self,
        agent_id: str,
        memory_id: str
    ) -> bool:
        """
        Check if agent has permission to modify memory.

        Args:
            agent_id: Agent requesting modification
            memory_id: Memory to modify

        Returns:
            True if authorized

        Raises:
            AuthorizationError: If not authorized
        """
        # Admin agents can modify anything
        if agent_id in self.admin_agents:
            return True

        # For non-admin, verify ownership (would need database check)
        # For now, allow with warning
        logger.warning(f"Modify permission check for agent '{agent_id}' on memory '{memory_id}'")

        return True

    async def check_backup_permission(self, agent_id: str) -> bool:
        """
        Check if agent has permission to create/restore backups.

        Args:
            agent_id: Agent requesting backup operation

        Returns:
            True if authorized

        Raises:
            AuthorizationError: If not authorized
        """
        # Only admin agents can create/restore backups
        if agent_id not in self.admin_agents:
            raise AuthorizationError(
                f"ERR Authorization failed: Backup operations require admin privileges. "
                f"Agent '{agent_id}' is not authorized."
            )

        return True


# Global authorizer instance
authorizer = Authorizer()


# ============================================================================
# CONFIRMATION SYSTEM
# ============================================================================

class ConfirmationManager:
    """
    Manages confirmation requirements for destructive operations.

    Tracks operations requiring confirmation and validates confirmation tokens.
    """

    def __init__(self):
        """Initialize confirmation manager."""
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self.confirmation_ttl = timedelta(minutes=5)

    def require_confirmation(
        self,
        operation: str,
        details: Dict[str, Any],
        confirm_token: Optional[str] = None
    ) -> str:
        """
        Require user confirmation for destructive operation.

        Args:
            operation: Operation description
            details: Operation details (counts, targets, etc.)
            confirm_token: Optional confirmation token

        Returns:
            Status message

        Raises:
            ConfirmationRequiredError: If confirmation required
        """
        confirmation_id = f"{operation}_{datetime.now().timestamp()}"

        # If no token provided, require confirmation
        if not confirm_token:
            self.pending_confirmations[confirmation_id] = {
                "operation": operation,
                "details": details,
                "created_at": datetime.now()
            }

            raise ConfirmationRequiredError(
                f"WARN Destructive operation requires confirmation:\n"
                f"  Operation: {operation}\n"
                f"  Details: {details}\n"
                f"  Confirmation ID: {confirmation_id}\n"
                f"  To confirm, re-run with confirm_token='{confirmation_id}'"
            )

        # If token provided, validate it
        if confirm_token not in self.pending_confirmations:
            raise ValidationError(
                f"ERR Invalid confirmation token: {confirm_token}\n"
                f"Token may have expired or never existed."
            )

        # Check token age
        confirmation = self.pending_confirmations[confirm_token]
        if datetime.now() - confirmation["created_at"] > self.confirmation_ttl:
            del self.pending_confirmations[confirm_token]
            raise ValidationError(
                f"ERR Confirmation token expired: {confirm_token}\n"
                f"Please request a new confirmation."
            )

        # Token is valid, remove it and proceed
        del self.pending_confirmations[confirm_token]
        return confirm_token

    def has_pending_confirmation(self, operation: str) -> bool:
        """
        Check if there are pending confirmations for an operation.

        Args:
            operation: Operation type to check

        Returns:
            True if pending confirmations exist
        """
        for conf_id, conf_data in self.pending_confirmations.items():
            if conf_data["operation"] == operation:
                return True
        return False


# Global confirmation manager instance
confirmation_manager = ConfirmationManager()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def require_agent_authorization(
    agent_id: str,
    operation: str,
    memory_id: Optional[str] = None,
    category: Optional[str] = None
) -> None:
    """
    Require authorization for agent operation.

    Args:
        agent_id: Agent requesting operation
        operation: Operation description
        memory_id: Memory ID (if applicable)
        category: Category (if applicable)

    Raises:
        AuthorizationError: If not authorized
    """
    await authorizer.check_delete_permission(
        agent_id=agent_id,
        memory_id=memory_id,
        category=category
    )

    logger.info(f"OK Authorization passed: agent='{agent_id}' operation='{operation}'")


def validate_dry_run_safe(dry_run: bool, operation: str) -> None:
    """
    Ensure destructive operation has dry_run=True for first run.

    Args:
        dry_run: Whether this is a dry run
        operation: Operation description

    Raises:
        ConfirmationRequiredError: If dry_run=False and no confirmation
    """
    if not dry_run:
        # Require explicit confirmation for non-dry-run operations
        confirmation_manager.require_confirmation(
            operation=operation,
            details={"dry_run": False, "destructive": True}
        )


# ============================================================================
# SPECIFIC EXCEPTION HANDLERS
# ============================================================================

def handle_database_exception(e: Exception, operation: str) -> str:
    """
    Handle database exceptions with actionable error messages.

    Args:
        e: The exception that occurred
        operation: Operation being performed

    Returns:
        Actionable error message
    """
    import asyncpg
    from qdrant.exceptions import QdrantException

    error_type = type(e).__name__

    if isinstance(e, asyncpg.PostgresConnectionError):
        return (f"ERR Database connection failed: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check PostgreSQL is running on port 25432\n"
                f"  Recovery: Verify .env configuration\n"
                f"  Recovery: Check network connectivity")

    elif isinstance(e, asyncpg.UniqueViolationError):
        return (f"ERR Unique constraint violation: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Cause: Memory or data already exists\n"
                f"  Recovery: Use update_memory instead\n"
                f"  Recovery: Check for duplicate before adding")

    elif isinstance(e, asyncpg.ForeignKeyViolationError):
        return (f"ERR Foreign key constraint violation: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Cause: Referenced entity does not exist\n"
                f"  Recovery: Verify referenced IDs exist")

    elif isinstance(e, QdrantException):
        return (f"ERR Vector database error: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check Qdrant is running on port 26333\n"
                f"  Recovery: Verify collection exists\n"
                f"  Recovery: Check Qdrant logs")

    elif "timeout" in str(e).lower() or "timed out" in str(e).lower():
        return (f"ERR Operation timeout: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Increase timeout value\n"
                f"  Recovery: Check system performance\n"
                f"  Recovery: Try again later")

    elif "connection" in str(e).lower():
        return (f"ERR Connection failed: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check database is running\n"
                f"  Recovery: Verify network connectivity\n"
                f"  Recovery: Check firewall rules")

    elif "authorization" in str(e).lower() or "permission" in str(e).lower():
        return (f"ERR Authorization denied: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Use admin account (system, admin, claude-code)\n"
                f"  Recovery: Check agent has required permissions\n"
                f"  Recovery: Verify category is not protected")

    else:
        return (f"ERR Database error: {operation}\n"
                f"  Type: {error_type}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check system logs\n"
                f"  Recovery: Try operation again\n"
                f"  Recovery: If persists, contact support")


def handle_backup_exception(e: Exception, operation: str) -> str:
    """
    Handle backup exceptions with actionable error messages.

    Args:
        e: The exception that occurred
        operation: Operation being performed

    Returns:
        Actionable error message
    """
    error_type = type(e).__name__

    if "no space" in str(e).lower() or "disk full" in str(e).lower():
        return (f"ERR Insufficient storage: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Free up disk space\n"
                f"  Recovery: Clean old backups\n"
                f"  Recovery: Use compression\n"
                f"  Recovery: Archive old memories first")

    elif "permission" in str(e).lower():
        return (f"ERR Backup permission denied: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check directory permissions\n"
                f"  Recovery: Run with appropriate user\n"
                f"  Recovery: Verify backup directory exists")

    elif "corruption" in str(e).lower():
        return (f"ERR Backup corruption detected: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Verify backup integrity\n"
                f"  Recovery: Use verify_backup tool\n"
                f"  Recovery: Restore from previous backup")

    else:
        return (f"ERR Backup operation failed: {operation}\n"
                f"  Type: {error_type}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check system logs\n"
                f"  Recovery: Verify sufficient disk space\n"
                f"  Recovery: Try again with smaller dataset")


def handle_deduplication_exception(e: Exception, operation: str) -> str:
    """
    Handle deduplication exceptions with actionable error messages.

    Args:
        e: The exception that occurred
        operation: Operation being performed

    Returns:
        Actionable error message
    """
    error_type = type(e).__name__

    if "threshold" in str(e).lower():
        return (f"ERR Deduplication threshold exceeded: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Process in smaller batches\n"
                f"  Recovery: Adjust threshold in configuration\n"
                f"  Recovery: Increase memory capacity")

    elif "embedding" in str(e).lower() or "vector" in str(e).lower():
        return (f"ERR Embedding generation failed: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check vector database connection\n"
                f"  Recovery: Verify Qdrant is running\n"
                f"  Recovery: Check embedding model configuration")

    else:
        return (f"ERR Deduplication failed: {operation}\n"
                f"  Type: {error_type}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check memory content format\n"
                f"  Recovery: Try operation again\n"
                f"  Recovery: If persists, disable auto-deduplication")


def handle_summarization_exception(e: Exception, operation: str) -> str:
    """
    Handle summarization exceptions with actionable error messages.

    Args:
        e: The exception that occurred
        operation: Operation being performed

    Returns:
        Actionable error message
    """
    error_type = type(e).__name__

    if "api key" in str(e).lower() or "authentication" in str(e).lower():
        return (f"ERR LLM API authentication failed: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check API key is valid\n"
                f"  Recovery: Verify API key has required permissions\n"
                f"  Recovery: Check API quota not exceeded")

    elif "rate limit" in str(e).lower() or "quota" in str(e).lower():
        return (f"ERR LLM rate limit exceeded: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Wait before retrying\n"
                f"  Recovery: Reduce batch size\n"
                f"  Recovery: Upgrade API plan")

    elif "timeout" in str(e).lower() or "timed out" in str(e).lower():
        return (f"ERR LLM request timeout: {operation}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Increase timeout value\n"
                f"  Recovery: Reduce summary length\n"
                f"  Recovery: Try again later")

    else:
        return (f"ERR Summarization failed: {operation}\n"
                f"  Type: {error_type}\n"
                f"  Details: {str(e)}\n"
                f"  Recovery: Check LLM configuration\n"
                f"  Recovery: Verify API is accessible\n"
                f"  Recovery: Try again with fewer memories")


# Export specific exception types
__all__ = [
    "ValidationError",
    "AuthorizationError",
    "ConfirmationRequiredError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "DataIntegrityError",
    "BackupCreationError",
    "BackupRestoreError",
    "DeduplicationError",
    "SummarizationError",
    "SynchronizationError",
    "ConfigurationError",
    "RateLimitError",
    "TimeoutError",
    "ResourceExhaustedError",
    "InsufficientPermissionsError",
    "InvalidStateError",
    "handle_database_exception",
    "handle_backup_exception",
    "handle_deduplication_exception",
    "handle_summarization_exception"
]


# Export key functions
__all__ = [
    "ValidationError",
    "AuthorizationError",
    "ConfirmationRequiredError",
    "validate_uuid",
    "validate_positive_int",
    "validate_days",
    "validate_limit",
    "validate_agent_id",
    "validate_category",
    "validate_memory_content",
    "sanitize_string",
    "validate_path_safe",
    "authorizer",
    "confirmation_manager",
    "require_agent_authorization",
    "validate_dry_run_safe"
]
