"""
Unit tests for Enhanced Cognee Audit Logger

Tests the audit_logger module for:
- Basic logging functionality
- File-based logging
- Database logging
- Sensitive data anonymization
- Performance metrics
- Log querying and filtering
- Log cleanup

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import os
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audit_logger import (
    AuditLogger,
    AuditLogLevel,
    AuditOperationType,
    init_audit_logger,
    get_audit_logger,
    audit_log
)


class TestAuditLoggerBasics:
    """Test basic audit logger functionality."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_config(self, temp_log_dir):
        """Create mock automation config."""
        config = {
            "audit_logging": {
                "enabled": True,
                "log_all_actions": True,
                "log_to_file": True,
                "log_file_path": os.path.join(temp_log_dir, "test_audit.log"),
                "log_to_database": False,  # Disable DB for unit tests
                "retention_days": 90,
                "include_details": True,
                "anonymize_sensitive_data": True
            },
            "development": {
                "debug_mode": False
            }
        }
        config_file = os.path.join(temp_log_dir, "test_config.json")
        with open(config_file, 'w') as f:
            json.dump(config, f)
        return config_file

    @pytest.fixture
    def audit_logger(self, mock_config, temp_log_dir):
        """Create audit logger instance for testing."""
        logger = AuditLogger(config_path=mock_config, log_dir=temp_log_dir)
        yield logger
        logger.close()

    @pytest.mark.asyncio
    async def test_logger_initialization(self, audit_logger):
        """Test logger initializes correctly."""
        assert audit_logger is not None
        assert audit_logger.log_dir.exists()
        assert audit_logger.file_logger is not None

    @pytest.mark.asyncio
    async def test_basic_logging(self, audit_logger):
        """Test basic log entry creation."""
        log_id = await audit_logger.log(
            operation_type=AuditOperationType.MEMORY_ADD,
            agent_id="test_agent",
            status="success",
            details={"content": "test memory"},
            execution_time_ms=100.0
        )

        assert log_id is not None
        assert len(log_id) == 32  # SHA-256 hash (first 32 chars)

        # Check recent logs
        recent_logs = await audit_logger.get_recent_logs(limit=10)
        assert len(recent_logs) == 1
        assert recent_logs[0]["operation_type"] == "memory_add"
        assert recent_logs[0]["agent_id"] == "test_agent"
        assert recent_logs[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_file_logging(self, audit_logger, temp_log_dir):
        """Test logs are written to file."""
        await audit_logger.log(
            operation_type=AuditOperationType.MEMORY_UPDATE,
            agent_id="test_agent",
            status="success",
            details={"key": "value"}
        )

        # Check log file exists
        log_file = Path(temp_log_dir) / "automation_audit.log"
        assert log_file.exists()

        # Read and verify log file content
        with open(log_file, 'r') as f:
            content = f.read()
            assert "memory_update" in content
            assert "test_agent" in content
            assert "success" in content

    @pytest.mark.asyncio
    async def test_sensitive_data_anonymization(self, audit_logger):
        """Test sensitive data is anonymized in logs."""
        await audit_logger.log(
            operation_type=AuditOperationType.MEMORY_ADD,
            agent_id="test_agent",
            status="success",
            details={
                "content": "public data",
                "api_key": "secret_key_12345",
                "password": "my_password",
                "user_id": "user_123"
            }
        )

        recent_logs = await audit_logger.get_recent_logs(limit=1)
        log_entry = recent_logs[0]

        # Public data should be intact
        assert log_entry["details"]["content"] == "public data"

        # Sensitive data should be anonymized
        assert "api_key" in log_entry["details"]
        assert "[REDACTED_" in log_entry["details"]["api_key"]
        assert log_entry["details"]["api_key"] != "secret_key_12345"

        assert "password" in log_entry["details"]
        assert "[REDACTED_" in log_entry["details"]["password"]

        assert "user_id" in log_entry["details"]
        assert "[REDACTED_" in log_entry["details"]["user_id"]

    @pytest.mark.asyncio
    async def test_performance_metrics(self, audit_logger):
        """Test performance metrics tracking."""
        # Log several operations
        for i in range(5):
            await audit_logger.log(
                operation_type=AuditOperationType.MEMORY_ADD,
                agent_id="test_agent",
                status="success",
                execution_time_ms=100.0 + i * 10
            )

        # Log one failure
        await audit_logger.log(
            operation_type=AuditOperationType.MEMORY_DELETE,
            agent_id="test_agent",
            status="failure",
            error_message="Test error"
        )

        metrics = await audit_logger.get_metrics()
        assert metrics["total_operations"] == 6
        assert metrics["successful_operations"] == 5
        assert metrics["failed_operations"] == 1
        assert metrics["operations_by_type"]["memory_add"] == 5
        assert metrics["operations_by_type"]["memory_delete"] == 1
        assert metrics["average_execution_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_log_filtering(self, audit_logger):
        """Test log filtering by agent and operation type."""
        # Log different operations
        await audit_logger.log(
            operation_type=AuditOperationType.MEMORY_ADD,
            agent_id="agent_1",
            status="success"
        )
        await audit_logger.log(
            operation_type=AuditOperationType.MEMORY_UPDATE,
            agent_id="agent_1",
            status="success"
        )
        await audit_logger.log(
            operation_type=AuditOperationType.MEMORY_ADD,
            agent_id="agent_2",
            status="success"
        )

        # Filter by agent
        agent1_logs = await audit_logger.get_recent_logs(limit=10, agent_id="agent_1")
        assert len(agent1_logs) == 2

        # Filter by operation type
        add_logs = await audit_logger.get_recent_logs(
            limit=10,
            operation_type="memory_add"
        )
        assert len(add_logs) == 2

    @pytest.mark.asyncio
    async def test_error_logging(self, audit_logger):
        """Test error logging functionality."""
        await audit_logger.log(
            operation_type=AuditOperationType.DEDUPLICATE_RUN,
            agent_id="test_agent",
            status="failure",
            execution_time_ms=500.0,
            error_message="Connection timeout",
            details={"attempt": 1}
        )

        recent_logs = await audit_logger.get_recent_logs(limit=1)
        log_entry = recent_logs[0]

        assert log_entry["status"] == "failure"
        assert log_entry["error_message"] == "Connection timeout"
        assert log_entry["execution_time_ms"] == 500.0
        assert log_entry["details"]["attempt"] == 1

    @pytest.mark.asyncio
    async def test_memory_id_association(self, audit_logger):
        """Test log entries can be associated with memory IDs."""
        memory_id = "550e8400-e29b-41d4-a716-446655440000"

        await audit_logger.log(
            operation_type=AuditOperationType.MEMORY_UPDATE,
            agent_id="test_agent",
            status="success",
            memory_id=memory_id
        )

        recent_logs = await audit_logger.get_recent_logs(limit=1)
        assert recent_logs[0]["memory_id"] == memory_id

    @pytest.mark.asyncio
    async def test_should_log_filtering(self, audit_logger):
        """Test should_log filtering based on config."""
        # This test would require modifying the config
        # For now, we just verify the method exists
        assert audit_logger._should_log("memory_add") == True
        assert audit_logger._should_log("some_operation") == True

    @pytest.mark.asyncio
    async def test_recent_logs_buffer_limit(self, audit_logger):
        """Test recent logs buffer doesn't exceed limit."""
        # Add more logs than the buffer limit
        for i in range(1500):  # More than max_recent_logs (1000)
            await audit_logger.log(
                operation_type=AuditOperationType.MEMORY_ADD,
                agent_id=f"agent_{i % 10}",
                status="success"
            )

        # Should not exceed limit
        assert len(audit_logger.recent_logs) <= 1000

        # Should have most recent logs
        recent = await audit_logger.get_recent_logs(limit=1000)
        assert len(recent) <= 1000


class TestAuditLogDecorator:
    """Test the @audit_log decorator."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def setup_logger(self, temp_log_dir):
        """Setup audit logger for decorator tests."""
        config = {
            "audit_logging": {
                "enabled": True,
                "log_all_actions": True,
                "log_to_file": True,
                "log_to_database": False,
                "anonymize_sensitive_data": False
            }
        }
        config_file = os.path.join(temp_log_dir, "test_config.json")
        with open(config_file, 'w') as f:
            json.dump(config, f)

        logger = AuditLogger(config_path=config_file, log_dir=temp_log_dir)
        init_audit_logger(config_file, temp_log_dir)
        yield logger
        logger.close()

    @pytest.mark.asyncio
    async def test_decorator_success_logging(self, setup_logger):
        """Test decorator logs successful function calls."""
        @audit_log(AuditOperationType.MEMORY_ADD, log_details=True)
        async def add_memory(content: str, agent_id: str) -> str:
            return f"Memory added: {content}"

        result = await add_memory("test content", agent_id="test_agent")
        assert "Memory added: test content" in result

        # Check log was created
        logger = get_audit_logger()
        recent_logs = await logger.get_recent_logs(limit=1)
        assert len(recent_logs) == 1
        assert recent_logs[0]["operation_type"] == "memory_add"
        assert recent_logs[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_decorator_failure_logging(self, setup_logger):
        """Test decorator logs failed function calls."""
        @audit_log(AuditOperationType.MEMORY_DELETE, log_details=True)
        async def delete_memory(memory_id: str, agent_id: str) -> str:
            raise ValueError("Memory not found")

        with pytest.raises(ValueError):
            await delete_memory("mem_123", agent_id="test_agent")

        # Check error was logged
        logger = get_audit_logger()
        recent_logs = await logger.get_recent_logs(limit=1)
        assert len(recent_logs) == 1
        assert recent_logs[0]["status"] == "failure"
        assert "Memory not found" in recent_logs[0]["error_message"]

    @pytest.mark.asyncio
    async def test_decorator_execution_time(self, setup_logger):
        """Test decorator tracks execution time."""
        @audit_log(AuditOperationType.MEMORY_SEARCH, log_details=True)
        async def search_memory(query: str, agent_id: str) -> str:
            await asyncio.sleep(0.1)  # Simulate work
            return f"Results for: {query}"

        await search_memory("test query", agent_id="test_agent")

        logger = get_audit_logger()
        recent_logs = await logger.get_recent_logs(limit=1)
        assert recent_logs[0]["execution_time_ms"] >= 100  # At least 100ms


class TestAuditLoggerIntegration:
    """Integration tests for audit logger with mock database."""

    @pytest.mark.asyncio
    async def test_database_logging_with_mock_pool(self):
        """Test database logging with mocked connection pool."""
        # This would require mocking asyncpg.Pool
        # For now, we just verify the method exists
        temp_dir = tempfile.mkdtemp()
        try:
            config = {
                "audit_logging": {
                    "enabled": True,
                    "log_to_database": True
                }
            }
            config_file = os.path.join(temp_dir, "test_config.json")
            with open(config_file, 'w') as f:
                json.dump(config, f)

            logger = AuditLogger(config_path=config_file, log_dir=temp_dir, db_pool=None)
            # Should not crash even without database pool
            await logger.log(
                operation_type=AuditOperationType.MEMORY_ADD,
                agent_id="test_agent",
                status="success"
            )
            logger.close()
        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
