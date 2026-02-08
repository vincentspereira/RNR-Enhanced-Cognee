"""
Enhanced Cognee - Audit Logger for Automated Actions

This module provides comprehensive audit logging for all automated operations
in the Enhanced Cognee system. It tracks:
- All automated MCP tool calls
- Success/failure status
- Performance metrics
- Security-relevant events
- Undo operation history

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path
from enum import Enum
import hashlib
import os

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("WARN: asyncpg not available - database logging disabled")


class AuditLogLevel(Enum):
    """Audit log severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditOperationType(Enum):
    """Types of automated operations."""
    # Memory operations
    MEMORY_ADD = "memory_add"
    MEMORY_UPDATE = "memory_update"
    MEMORY_DELETE = "memory_delete"
    MEMORY_SEARCH = "memory_search"

    # Deduplication
    DEDUPLICATE_RUN = "deduplicate_run"
    DEDUPLICATE_DRY_RUN = "deduplicate_dry_run"

    # Summarization
    SUMMARIZE_RUN = "summarize_run"
    SUMMARIZE_CATEGORY = "summarize_category"

    # Cognify
    COGNIFY_PROCESS = "cognify_process"

    # Sharing
    SHARING_SET = "sharing_set"
    SHARING_AUTO_SET = "sharing_auto_set"

    # Sync
    SYNC_AGENT_STATE = "sync_agent_state"
    SYNC_PUBLISH_EVENT = "sync_publish_event"

    # Undo operations
    UNDO_EXECUTE = "undo_execute"
    UNDO_REDO = "undo_redo"

    # System operations
    SYSTEM_START = "system_start"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIG_CHANGE = "config_change"


class AuditLogger:
    """
    Comprehensive audit logging system for Enhanced Cognee automations.

    Features:
    - Multi-channel logging (file, database, console)
    - Structured logging with JSON format
    - Automatic log rotation
    - Sensitive data anonymization
    - Performance metrics tracking
    - Async/non-blocking design
    """

    def __init__(
        self,
        config_path: str = "automation_config.json",
        log_dir: str = "logs",
        db_pool: Optional[asyncpg.Pool] = None
    ):
        """
        Initialize the audit logger.

        Args:
            config_path: Path to automation config file
            log_dir: Directory for log files
            db_pool: PostgreSQL connection pool (optional)
        """
        self.config = self._load_config(config_path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.db_pool = db_pool

        # Setup file-based logger
        self._setup_file_logger()

        # In-memory buffer for recent logs (for dashboard)
        self.recent_logs: List[Dict[str, Any]] = []
        self.max_recent_logs = 1000

        # Performance metrics
        self.metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "operations_by_type": {},
            "average_execution_time_ms": 0.0
        }

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load automation configuration."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"WARN: Config file not found: {config_path}")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in config file: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "audit_logging": {
                "enabled": True,
                "log_all_actions": True,
                "log_to_file": True,
                "log_file_path": "logs/automation_audit.log",
                "log_to_database": False,
                "retention_days": 90,
                "include_details": True,
                "anonymize_sensitive_data": True
            }
        }

    def _setup_file_logger(self):
        """Setup file-based logger."""
        self.file_logger = logging.getLogger("cognee_audit")
        self.file_logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.file_logger.handlers.clear()

        # File handler
        log_file = self.log_dir / "automation_audit.log"
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(logging.DEBUG)

        # JSON formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.file_logger.addHandler(handler)

        # Console handler (for development)
        if self.config.get("development", {}).get("debug_mode", False):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.file_logger.addHandler(console_handler)

    def _should_log(self, operation: str) -> bool:
        """Check if operation should be logged based on config."""
        audit_config = self.config.get("audit_logging", {})
        if not audit_config.get("enabled", True):
            return False
        if not audit_config.get("log_all_actions", True):
            # Only log critical operations
            critical_ops = ["MEMORY_DELETE", "SHARING_AUTO_SET", "UNDO_EXECUTE"]
            return operation in critical_ops
        return True

    def _anonymize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize sensitive data in log entries."""
        if not self.config.get("audit_logging", {}).get("anonymize_sensitive_data", True):
            return data

        sensitive_keys = [
            "api_key", "password", "token", "secret", "credential",
            "private_key", "auth", "session_id", "user_id"
        ]

        anonymized = data.copy()
        for key in sensitive_keys:
            if key in anonymized:
                value = str(anonymized[key])
                # Hash the value for traceability but hide content
                hashed = hashlib.sha256(value.encode()).hexdigest()[:16]
                anonymized[key] = f"[REDACTED_{hashed}]"

        return anonymized

    async def log(
        self,
        operation_type: AuditOperationType,
        agent_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        memory_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an automated operation.

        Args:
            operation_type: Type of operation
            agent_id: Agent performing the operation
            status: Operation status (success, failure, partial)
            details: Operation details (inputs, outputs, etc.)
            execution_time_ms: Execution time in milliseconds
            error_message: Error message if failed
            memory_id: Associated memory ID (if applicable)
            additional_context: Additional context information

        Returns:
            Log entry ID
        """
        if not self._should_log(operation_type.value):
            return None

        # Create log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation_type": operation_type.value,
            "agent_id": agent_id,
            "status": status,
            "memory_id": memory_id,
            "details": self._anonymize_sensitive_data(details or {}),
            "execution_time_ms": execution_time_ms,
            "error_message": error_message,
            "additional_context": additional_context or {}
        }

        # Generate log ID
        log_id = hashlib.sha256(
            f"{log_entry['timestamp']}_{operation_type.value}_{agent_id}".encode()
        ).hexdigest()[:32]

        log_entry["log_id"] = log_id

        # Write to file
        self._write_to_file(log_entry)

        # Write to database (async)
        if self.config.get("audit_logging", {}).get("log_to_database", False):
            if self.db_pool and POSTGRES_AVAILABLE:
                await self._write_to_database(log_entry)

        # Add to recent logs buffer
        self._add_to_recent_logs(log_entry)

        # Update metrics
        self._update_metrics(log_entry)

        return log_id

    def _write_to_file(self, log_entry: Dict[str, Any]):
        """Write log entry to file."""
        try:
            log_line = json.dumps(log_entry, ensure_ascii=False)
            self.file_logger.info(log_line)
        except Exception as e:
            print(f"ERROR: Failed to write to log file: {e}")

    async def _write_to_database(self, log_entry: Dict[str, Any]):
        """Write log entry to PostgreSQL database."""
        if not self.db_pool or not POSTGRES_AVAILABLE:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO cognee_db.audit_log (
                        log_id, timestamp, operation_type, agent_id,
                        status, memory_id, details, execution_time_ms,
                        error_message, additional_context
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (log_id) DO NOTHING
                """,
                    log_entry["log_id"],
                    log_entry["timestamp"],
                    log_entry["operation_type"],
                    log_entry["agent_id"],
                    log_entry["status"],
                    log_entry.get("memory_id"),
                    json.dumps(log_entry["details"]),
                    log_entry.get("execution_time_ms"),
                    log_entry.get("error_message"),
                    json.dumps(log_entry.get("additional_context", {}))
                )
        except Exception as e:
            print(f"ERROR: Failed to write to database: {e}")

    def _add_to_recent_logs(self, log_entry: Dict[str, Any]):
        """Add log entry to recent logs buffer."""
        self.recent_logs.append(log_entry)
        if len(self.recent_logs) > self.max_recent_logs:
            self.recent_logs.pop(0)

    def _update_metrics(self, log_entry: Dict[str, Any]):
        """Update performance metrics."""
        self.metrics["total_operations"] += 1

        if log_entry["status"] == "success":
            self.metrics["successful_operations"] += 1
        else:
            self.metrics["failed_operations"] += 1

        # Track by operation type
        op_type = log_entry["operation_type"]
        if op_type not in self.metrics["operations_by_type"]:
            self.metrics["operations_by_type"][op_type] = 0
        self.metrics["operations_by_type"][op_type] += 1

        # Update average execution time
        if log_entry.get("execution_time_ms"):
            total_time = self.metrics["average_execution_time_ms"] * (self.metrics["total_operations"] - 1)
            new_time = log_entry["execution_time_ms"]
            self.metrics["average_execution_time_ms"] = (total_time + new_time) / self.metrics["total_operations"]

    async def get_recent_logs(
        self,
        limit: int = 100,
        agent_id: Optional[str] = None,
        operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent log entries.

        Args:
            limit: Maximum number of entries to return
            agent_id: Filter by agent ID
            operation_type: Filter by operation type

        Returns:
            List of log entries
        """
        logs = self.recent_logs.copy()

        # Apply filters
        if agent_id:
            logs = [log for log in logs if log["agent_id"] == agent_id]
        if operation_type:
            logs = [log for log in logs if log["operation_type"] == operation_type]

        # Sort by timestamp (newest first) and limit
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        return logs[:limit]

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.metrics.copy()

    async def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        operation_types: Optional[List[str]] = None,
        agent_ids: Optional[List[str]] = None,
        status: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs from database.

        Args:
            start_time: Start of time range
            end_time: End of time range
            operation_types: Filter by operation types
            agent_ids: Filter by agent IDs
            status: Filter by status
            limit: Maximum results

        Returns:
            List of matching log entries
        """
        if not self.db_pool or not POSTGRES_AVAILABLE:
            return []

        try:
            async with self.db_pool.acquire() as conn:
                query = "SELECT * FROM cognee_db.audit_log WHERE 1=1"
                params = []
                param_idx = 1

                if start_time:
                    query += f" AND timestamp >= ${param_idx}"
                    params.append(start_time.isoformat())
                    param_idx += 1

                if end_time:
                    query += f" AND timestamp <= ${param_idx}"
                    params.append(end_time.isoformat())
                    param_idx += 1

                if operation_types:
                    query += f" AND operation_type = ANY(${param_idx})"
                    params.append(operation_types)
                    param_idx += 1

                if agent_ids:
                    query += f" AND agent_id = ANY(${param_idx})"
                    params.append(agent_ids)
                    param_idx += 1

                if status:
                    query += f" AND status = ${param_idx}"
                    params.append(status)
                    param_idx += 1

                query += f" ORDER BY timestamp DESC LIMIT ${param_idx}"
                params.append(limit)

                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]

        except Exception as e:
            print(f"ERROR: Failed to query logs: {e}")
            return []

    async def cleanup_old_logs(self, retention_days: Optional[int] = None):
        """
        Clean up old log entries based on retention policy.

        Args:
            retention_days: Number of days to retain (overrides config)
        """
        retention = retention_days or self.config.get("audit_logging", {}).get("retention_days", 90)

        if self.db_pool and POSTGRES_AVAILABLE:
            try:
                async with self.db_pool.acquire() as conn:
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention)
                    result = await conn.execute(
                        "DELETE FROM cognee_db.audit_log WHERE timestamp < $1",
                        cutoff_date
                    )
                    print(f"INFO: Cleaned up old audit logs: {result}")
            except Exception as e:
                print(f"ERROR: Failed to cleanup old logs: {e}")

    def close(self):
        """Close the audit logger and cleanup resources."""
        for handler in self.file_logger.handlers:
            handler.close()
        self.file_logger.handlers.clear()


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> Optional[AuditLogger]:
    """Get the global audit logger instance."""
    return _audit_logger


def init_audit_logger(
    config_path: str = "automation_config.json",
    log_dir: str = "logs",
    db_pool: Optional[asyncpg.Pool] = None
) -> AuditLogger:
    """
    Initialize the global audit logger.

    Args:
        config_path: Path to automation config file
        log_dir: Directory for log files
        db_pool: PostgreSQL connection pool

    Returns:
        AuditLogger instance
    """
    global _audit_logger
    _audit_logger = AuditLogger(config_path, log_dir, db_pool)
    return _audit_logger


# Decorator for automatic audit logging
def audit_log(
    operation_type: AuditOperationType,
    log_details: bool = True
):
    """
    Decorator to automatically audit log function calls.

    Args:
        operation_type: Type of operation being logged
        log_details: Whether to log function parameters and results

    Usage:
        @audit_log(AuditOperationType.MEMORY_ADD)
        async def add_memory(content: str, agent_id: str) -> str:
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = get_audit_logger()
            if not logger:
                return await func(*args, **kwargs)

            start_time = datetime.now(timezone.utc)
            agent_id = kwargs.get("agent_id", "unknown")

            details = {}
            if log_details:
                details["input_args"] = str(args)
                details["input_kwargs"] = {k: v for k, v in kwargs.items() if k != "api_key"}

            try:
                result = await func(*args, **kwargs)

                execution_time = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() * 1000

                await logger.log(
                    operation_type=operation_type,
                    agent_id=agent_id,
                    status="success",
                    details=details if log_details else None,
                    execution_time_ms=execution_time
                )

                return result

            except Exception as e:
                execution_time = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() * 1000

                await logger.log(
                    operation_type=operation_type,
                    agent_id=agent_id,
                    status="failure",
                    details=details if log_details else None,
                    execution_time_ms=execution_time,
                    error_message=str(e)
                )
                raise

        return wrapper
    return decorator
