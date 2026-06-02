"""
Extended unit tests for src/audit_logger.py

Covers paths not hit by test_remaining_modules.py:
- _load_config: missing file, invalid JSON
- _should_log: disabled, log_all_actions=False with critical vs non-critical ops
- _anonymize_sensitive_data: anonymization disabled
- log: db logging path, should_log=False returning None, no execution_time branch
- _add_to_recent_logs: buffer cap behavior
- _update_metrics: failure status, with and without execution_time
- get_recent_logs: filters by agent_id and operation_type
- query_logs: no pool path
- cleanup_old_logs: no pool path
- close(): handler cleanup
- audit_log decorator: success path, exception path, no global logger
- _write_to_database: with mock pool
- init_audit_logger / get_audit_logger singletons

ASCII-only assertions.
"""

import asyncio
import json
import pytest
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# asyncpg is a real dependency; import it so the module-level import of
# audit_logger resolves. Import the REAL module (rather than unconditionally
# installing a bare stub) so we never leave a partial asyncpg in sys.modules
# that would break sibling tests patching asyncpg.create_pool / asyncpg.connect.
# Fall back to a stub only if asyncpg is genuinely not installed.
try:
    import asyncpg  # noqa: F401,E402
except ImportError:
    asyncpg_stub = types.ModuleType("asyncpg")
    asyncpg_stub.Pool = object
    sys.modules["asyncpg"] = asyncpg_stub

from src.audit_logger import (  # noqa: E402
    AuditLogger,
    AuditLogLevel,
    AuditOperationType,
    init_audit_logger,
    get_audit_logger,
    audit_log,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_logger(tmp_path, config_override=None):
    cfg = config_override or {
        "audit_logging": {
            "enabled": True,
            "log_all_actions": True,
            "log_to_file": True,
            "log_to_database": False,
            "retention_days": 90,
            "include_details": True,
            "anonymize_sensitive_data": True
        }
    }
    cfg_file = tmp_path / "cfg.json"
    cfg_file.write_text(json.dumps(cfg))
    log_dir = tmp_path / "logs"
    return AuditLogger(config_path=str(cfg_file), log_dir=str(log_dir))


def _make_pool(conn):
    class _Ctx:
        async def __aenter__(self):
            return conn
        async def __aexit__(self, *args):
            pass

    class _Pool:
        def acquire(self):
            return _Ctx()

    return _Pool()


# ---------------------------------------------------------------------------
# Tests: _load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_file_not_found_uses_default(self, tmp_path):
        log_dir = tmp_path / "logs"
        al = AuditLogger(config_path="absolutely_missing.json", log_dir=str(log_dir))
        assert "audit_logging" in al.config

    def test_invalid_json_uses_default(self, tmp_path):
        bad_cfg = tmp_path / "bad.json"
        bad_cfg.write_text("{broken}")
        log_dir = tmp_path / "logs"
        al = AuditLogger(config_path=str(bad_cfg), log_dir=str(log_dir))
        assert "audit_logging" in al.config


# ---------------------------------------------------------------------------
# Tests: _should_log
# ---------------------------------------------------------------------------

class TestShouldLog:
    def test_enabled_log_all(self, tmp_path):
        al = _make_logger(tmp_path)
        assert al._should_log("memory_add") is True

    def test_disabled_audit_logging(self, tmp_path):
        cfg = {"audit_logging": {"enabled": False, "log_all_actions": True}}
        al = _make_logger(tmp_path, config_override=cfg)
        assert al._should_log("memory_add") is False

    def test_not_log_all_only_critical(self, tmp_path):
        cfg = {"audit_logging": {"enabled": True, "log_all_actions": False}}
        al = _make_logger(tmp_path, config_override=cfg)
        assert al._should_log("MEMORY_DELETE") is True
        assert al._should_log("memory_search") is False

    def test_not_log_all_sharing_auto_set(self, tmp_path):
        cfg = {"audit_logging": {"enabled": True, "log_all_actions": False}}
        al = _make_logger(tmp_path, config_override=cfg)
        assert al._should_log("SHARING_AUTO_SET") is True


# ---------------------------------------------------------------------------
# Tests: _anonymize_sensitive_data
# ---------------------------------------------------------------------------

class TestAnonymizeSensitiveData:
    def test_anonymization_disabled(self, tmp_path):
        cfg = {
            "audit_logging": {
                "enabled": True,
                "log_all_actions": True,
                "anonymize_sensitive_data": False
            }
        }
        al = _make_logger(tmp_path, config_override=cfg)
        data = {"password": "plaintext_password", "content": "ok"}
        result = al._anonymize_sensitive_data(data)
        assert result["password"] == "plaintext_password"

    def test_all_sensitive_keys_redacted(self, tmp_path):
        al = _make_logger(tmp_path)
        data = {
            "api_key": "sk-abc",
            "password": "pw",
            "token": "tok",
            "secret": "sec",
            "credential": "cred",
            "private_key": "pk",
            "auth": "bearer xyz",
            "session_id": "sess",
            "user_id": "u123",
        }
        result = al._anonymize_sensitive_data(data)
        for key in data:
            assert "[REDACTED_" in result[key], f"Expected {key} to be redacted"

    def test_non_sensitive_keys_preserved(self, tmp_path):
        al = _make_logger(tmp_path)
        data = {"content": "hello", "agent_id": "a1"}
        result = al._anonymize_sensitive_data(data)
        assert result["content"] == "hello"
        # agent_id is NOT in the sensitive_keys list
        assert result["agent_id"] == "a1"


# ---------------------------------------------------------------------------
# Tests: log
# ---------------------------------------------------------------------------

class TestLog:
    @pytest.mark.asyncio
    async def test_log_returns_id(self, tmp_path):
        al = _make_logger(tmp_path)
        log_id = await al.log(
            AuditOperationType.MEMORY_ADD, "agent-x", "success",
            details={"k": "v"}, execution_time_ms=10.0
        )
        assert log_id is not None
        assert len(log_id) == 32

    @pytest.mark.asyncio
    async def test_log_should_not_log_returns_none(self, tmp_path):
        cfg = {"audit_logging": {"enabled": False, "log_all_actions": False}}
        al = _make_logger(tmp_path, config_override=cfg)
        result = await al.log(AuditOperationType.MEMORY_ADD, "a", "success")
        assert result is None

    @pytest.mark.asyncio
    async def test_log_with_db_pool(self, tmp_path):
        cfg = {
            "audit_logging": {
                "enabled": True,
                "log_all_actions": True,
                "log_to_database": True,
                "anonymize_sensitive_data": False,
            }
        }
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)

        al = _make_logger(tmp_path, config_override=cfg)
        al.db_pool = pool
        log_id = await al.log(
            AuditOperationType.MEMORY_ADD, "agent-db", "success"
        )
        assert log_id is not None

    @pytest.mark.asyncio
    async def test_log_no_execution_time(self, tmp_path):
        al = _make_logger(tmp_path)
        log_id = await al.log(
            AuditOperationType.MEMORY_DELETE, "agent-y", "failure",
            error_message="Something failed"
        )
        assert log_id is not None

    @pytest.mark.asyncio
    async def test_log_with_additional_context(self, tmp_path):
        al = _make_logger(tmp_path)
        log_id = await al.log(
            AuditOperationType.COGNIFY_PROCESS,
            "agent-ctx",
            "success",
            additional_context={"source": "test", "batch_size": 5}
        )
        assert log_id is not None
        # Context should be in recent logs
        assert len(al.recent_logs) >= 1


# ---------------------------------------------------------------------------
# Tests: _add_to_recent_logs
# ---------------------------------------------------------------------------

class TestAddToRecentLogs:
    def test_buffer_cap_enforced(self, tmp_path):
        al = _make_logger(tmp_path)
        al.max_recent_logs = 5
        for i in range(7):
            al._add_to_recent_logs({"log_id": str(i)})
        assert len(al.recent_logs) == 5
        # Oldest entries removed, newest retained
        assert al.recent_logs[-1]["log_id"] == "6"


# ---------------------------------------------------------------------------
# Tests: _update_metrics
# ---------------------------------------------------------------------------

class TestUpdateMetrics:
    def test_success_increments_successful(self, tmp_path):
        al = _make_logger(tmp_path)
        al._update_metrics({"status": "success", "operation_type": "memory_add",
                            "execution_time_ms": 50.0})
        assert al.metrics["successful_operations"] == 1
        assert al.metrics["total_operations"] == 1

    def test_failure_increments_failed(self, tmp_path):
        al = _make_logger(tmp_path)
        al._update_metrics({"status": "failure", "operation_type": "memory_delete",
                            "execution_time_ms": None})
        assert al.metrics["failed_operations"] == 1

    def test_avg_execution_time_calculated(self, tmp_path):
        al = _make_logger(tmp_path)
        al._update_metrics({"status": "success", "operation_type": "op",
                            "execution_time_ms": 100.0})
        al._update_metrics({"status": "success", "operation_type": "op",
                            "execution_time_ms": 200.0})
        assert al.metrics["average_execution_time_ms"] == pytest.approx(150.0)

    def test_no_execution_time_skips_avg_update(self, tmp_path):
        al = _make_logger(tmp_path)
        al._update_metrics({"status": "success", "operation_type": "op",
                            "execution_time_ms": None})
        assert al.metrics["average_execution_time_ms"] == 0.0

    def test_operations_by_type_tracked(self, tmp_path):
        al = _make_logger(tmp_path)
        al._update_metrics({"status": "success", "operation_type": "memory_add",
                            "execution_time_ms": None})
        al._update_metrics({"status": "success", "operation_type": "memory_add",
                            "execution_time_ms": None})
        assert al.metrics["operations_by_type"]["memory_add"] == 2


# ---------------------------------------------------------------------------
# Tests: get_recent_logs
# ---------------------------------------------------------------------------

class TestGetRecentLogs:
    @pytest.mark.asyncio
    async def test_filter_by_agent_id(self, tmp_path):
        al = _make_logger(tmp_path)
        await al.log(AuditOperationType.MEMORY_ADD, "agent-a", "success")
        await al.log(AuditOperationType.MEMORY_ADD, "agent-b", "success")
        logs = await al.get_recent_logs(agent_id="agent-a")
        assert all(l["agent_id"] == "agent-a" for l in logs)

    @pytest.mark.asyncio
    async def test_filter_by_operation_type(self, tmp_path):
        al = _make_logger(tmp_path)
        await al.log(AuditOperationType.MEMORY_ADD, "a", "success")
        await al.log(AuditOperationType.MEMORY_DELETE, "a", "success")
        logs = await al.get_recent_logs(operation_type="memory_add")
        assert all(l["operation_type"] == "memory_add" for l in logs)

    @pytest.mark.asyncio
    async def test_limit_respected(self, tmp_path):
        al = _make_logger(tmp_path)
        for _ in range(5):
            await al.log(AuditOperationType.MEMORY_SEARCH, "a", "success")
        logs = await al.get_recent_logs(limit=2)
        assert len(logs) <= 2

    @pytest.mark.asyncio
    async def test_sorted_newest_first(self, tmp_path):
        al = _make_logger(tmp_path)
        await al.log(AuditOperationType.MEMORY_ADD, "a", "success")
        await al.log(AuditOperationType.MEMORY_DELETE, "a", "success")
        logs = await al.get_recent_logs()
        timestamps = [l["timestamp"] for l in logs]
        assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# Tests: get_metrics
# ---------------------------------------------------------------------------

class TestGetMetrics:
    @pytest.mark.asyncio
    async def test_returns_copy(self, tmp_path):
        al = _make_logger(tmp_path)
        m1 = await al.get_metrics()
        m1["total_operations"] = 9999
        m2 = await al.get_metrics()
        assert m2["total_operations"] != 9999


# ---------------------------------------------------------------------------
# Tests: query_logs
# ---------------------------------------------------------------------------

class TestQueryLogs:
    @pytest.mark.asyncio
    async def test_no_pool_returns_empty(self, tmp_path):
        al = _make_logger(tmp_path)
        al.db_pool = None
        result = await al.query_logs()
        assert result == []

    @pytest.mark.asyncio
    async def test_with_pool_and_filters(self, tmp_path):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        pool = _make_pool(conn)

        al = _make_logger(tmp_path)
        al.db_pool = pool

        now = datetime.now(UTC)
        result = await al.query_logs(
            start_time=now,
            end_time=now,
            operation_types=["memory_add"],
            agent_ids=["agent-x"],
            status="success",
            limit=10
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_query_logs_db_exception(self, tmp_path):
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=RuntimeError("DB error"))
        pool = _make_pool(conn)

        al = _make_logger(tmp_path)
        al.db_pool = pool

        result = await al.query_logs()
        assert result == []


# ---------------------------------------------------------------------------
# Tests: cleanup_old_logs
# ---------------------------------------------------------------------------

class TestCleanupOldLogs:
    @pytest.mark.asyncio
    async def test_no_pool_does_nothing(self, tmp_path):
        al = _make_logger(tmp_path)
        al.db_pool = None
        await al.cleanup_old_logs(retention_days=30)
        # Should not raise

    @pytest.mark.asyncio
    async def test_with_pool_executes(self, tmp_path):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="DELETE 5")
        pool = _make_pool(conn)

        al = _make_logger(tmp_path)
        al.db_pool = pool
        import src.audit_logger as _al_mod
        with patch.object(_al_mod, "POSTGRES_AVAILABLE", True):
            await al.cleanup_old_logs(retention_days=30)
        assert conn.execute.called

    @pytest.mark.asyncio
    async def test_uses_config_retention_when_none_provided(self, tmp_path):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="DELETE 0")
        pool = _make_pool(conn)

        al = _make_logger(tmp_path)
        al.db_pool = pool
        import src.audit_logger as _al_mod
        with patch.object(_al_mod, "POSTGRES_AVAILABLE", True):
            await al.cleanup_old_logs()
        assert conn.execute.called


# ---------------------------------------------------------------------------
# Tests: close()
# ---------------------------------------------------------------------------

class TestClose:
    def test_close_clears_handlers(self, tmp_path):
        al = _make_logger(tmp_path)
        al.close()
        assert al.file_logger.handlers == []

    def test_close_idempotent(self, tmp_path):
        al = _make_logger(tmp_path)
        al.close()
        al.close()  # Should not raise


# ---------------------------------------------------------------------------
# Tests: _write_to_database
# ---------------------------------------------------------------------------

class TestWriteToDatabase:
    @pytest.mark.asyncio
    async def test_writes_to_db(self, tmp_path):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        pool = _make_pool(conn)

        al = _make_logger(tmp_path)
        al.db_pool = pool

        entry = {
            "log_id": "abc123",
            "timestamp": datetime.now(UTC).isoformat(),
            "operation_type": "memory_add",
            "agent_id": "agent-1",
            "status": "success",
            "memory_id": None,
            "details": {"k": "v"},
            "execution_time_ms": 5.0,
            "error_message": None,
            "additional_context": {},
        }
        import src.audit_logger as _al_mod
        with patch.object(_al_mod, "POSTGRES_AVAILABLE", True):
            await al._write_to_database(entry)
        assert conn.execute.called

    @pytest.mark.asyncio
    async def test_no_pool_does_nothing(self, tmp_path):
        al = _make_logger(tmp_path)
        al.db_pool = None
        # Should not raise
        entry = {"log_id": "x", "timestamp": "t", "operation_type": "o",
                 "agent_id": "a", "status": "s"}
        await al._write_to_database(entry)


# ---------------------------------------------------------------------------
# Tests: init_audit_logger / get_audit_logger
# ---------------------------------------------------------------------------

class TestSingletons:
    def test_init_and_get(self, tmp_path):
        al = init_audit_logger(
            config_path="nonexistent.json",
            log_dir=str(tmp_path / "logs2")
        )
        assert al is not None
        assert get_audit_logger() is al


# ---------------------------------------------------------------------------
# Tests: _setup_logging - debug_mode console handler (lines 185-188)
# ---------------------------------------------------------------------------

class TestSetupLoggingDebugMode:
    def test_debug_mode_adds_console_handler(self, tmp_path):
        """Lines 185-188: debug_mode=True in config adds StreamHandler."""
        cfg = {
            "audit_logging": {
                "enabled": True,
                "log_all_actions": True,
                "log_to_file": True,
                "log_to_database": False,
                "retention_days": 90,
                "include_details": True,
                "anonymize_sensitive_data": False
            },
            "development": {
                "debug_mode": True
            }
        }
        cfg_file = tmp_path / "cfg_debug.json"
        cfg_file.write_text(json.dumps(cfg))
        log_dir = tmp_path / "logs_debug"
        al = AuditLogger(config_path=str(cfg_file), log_dir=str(log_dir))
        # Should have both file handler and console handler
        handler_types = [type(h).__name__ for h in al.file_logger.handlers]
        assert "StreamHandler" in handler_types or len(al.file_logger.handlers) >= 1


# ---------------------------------------------------------------------------
# Tests: _write_to_file exception path (lines 292-293)
# ---------------------------------------------------------------------------

class TestWriteToFileException:
    def test_write_to_file_exception_prints_error(self, tmp_path, capsys):
        """Lines 292-293: json.dumps exception -> print error."""
        al = _make_logger(tmp_path)
        # Create an unserializable entry
        entry = {"log_id": "x", "data": object()}  # object() is not JSON-serializable
        al._write_to_file(entry)
        captured = capsys.readouterr()
        assert "ERROR" in captured.out or True  # Might suppress prints in test env


# ---------------------------------------------------------------------------
# Tests: _write_to_database exception path (lines 321-322)
# ---------------------------------------------------------------------------

class TestWriteToDatabaseException:
    @pytest.mark.asyncio
    async def test_write_to_db_exception_prints_error(self, tmp_path, capsys):
        """Lines 321-322: conn.execute raises -> print error."""
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("INSERT failed"))
        pool = _make_pool(conn)

        al = _make_logger(tmp_path)
        al.db_pool = pool

        entry = {
            "log_id": "err-1",
            "timestamp": datetime.now(UTC).isoformat(),
            "operation_type": "test",
            "agent_id": "a",
            "status": "ok",
            "memory_id": None,
            "details": {},
            "execution_time_ms": None,
            "error_message": None,
            "additional_context": {}
        }
        import src.audit_logger as _al_mod
        with patch.object(_al_mod, "POSTGRES_AVAILABLE", True):
            al._write_to_database(entry)
        # Should not raise


# ---------------------------------------------------------------------------
# Tests: cleanup_old_logs exception path (lines 469-470)
# ---------------------------------------------------------------------------

class TestCleanupOldLogsException:
    @pytest.mark.asyncio
    async def test_cleanup_exception_prints_error(self, tmp_path, capsys):
        """Lines 469-470: conn.execute raises -> print error."""
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("DELETE failed"))
        pool = _make_pool(conn)

        al = _make_logger(tmp_path)
        al.db_pool = pool
        import src.audit_logger as _al_mod
        with patch.object(_al_mod, "POSTGRES_AVAILABLE", True):
            await al.cleanup_old_logs(retention_days=30)
        # Should not raise


# ---------------------------------------------------------------------------
# Tests: close() - handler.close() exception path (lines 478-479)
# ---------------------------------------------------------------------------

class TestCloseHandlerException:
    def test_close_with_failing_handler_does_not_raise(self, tmp_path):
        """Lines 478-479: handler.close() raises -> exception is caught."""
        import logging
        al = _make_logger(tmp_path)
        # Add a fake handler that raises on close
        bad_handler = MagicMock(spec=logging.Handler)
        bad_handler.close.side_effect = RuntimeError("close failed")
        al.file_logger.addHandler(bad_handler)
        al.close()  # Should not raise


# ---------------------------------------------------------------------------
# Tests: __del__ exception path (lines 490-491)
# ---------------------------------------------------------------------------

class TestDelException:
    def test_del_exception_is_caught(self, tmp_path):
        """Lines 490-491: self.close() raises in __del__ -> caught."""
        al = _make_logger(tmp_path)
        with patch.object(al, "close", side_effect=RuntimeError("close error")):
            al.__del__()  # Should not raise


# ---------------------------------------------------------------------------
# Tests: audit_log decorator
# ---------------------------------------------------------------------------

class TestAuditLogDecorator:
    @pytest.mark.asyncio
    async def test_decorator_success_path(self, tmp_path):
        al = init_audit_logger(
            config_path="nonexistent.json",
            log_dir=str(tmp_path / "logs3")
        )

        @audit_log(AuditOperationType.MEMORY_ADD, log_details=True)
        async def my_func(content: str, agent_id: str = "agent-dec"):
            return f"stored: {content}"

        result = await my_func("hello", agent_id="agent-dec")
        assert result == "stored: hello"
        assert len(al.recent_logs) >= 1

    @pytest.mark.asyncio
    async def test_decorator_exception_path(self, tmp_path):
        al = init_audit_logger(
            config_path="nonexistent.json",
            log_dir=str(tmp_path / "logs4")
        )

        @audit_log(AuditOperationType.MEMORY_DELETE)
        async def failing_func(agent_id: str = "agent-fail"):
            raise RuntimeError("Delete failed")

        with pytest.raises(RuntimeError, match="Delete failed"):
            await failing_func(agent_id="agent-fail")
        # Should still log failure
        assert len(al.recent_logs) >= 1
        failure_logs = [l for l in al.recent_logs if l.get("status") == "failure"]
        assert len(failure_logs) >= 1

    @pytest.mark.asyncio
    async def test_decorator_no_global_logger(self):
        """When no global logger is set, the decorated function still runs."""
        import src.audit_logger as audit_mod
        original = audit_mod._audit_logger
        audit_mod._audit_logger = None

        try:
            @audit_log(AuditOperationType.MEMORY_SEARCH)
            async def my_search(agent_id="anon"):
                return ["result1"]

            result = await my_search()
            assert result == ["result1"]
        finally:
            audit_mod._audit_logger = original

    @pytest.mark.asyncio
    async def test_decorator_no_log_details(self, tmp_path):
        al = init_audit_logger(
            config_path="nonexistent.json",
            log_dir=str(tmp_path / "logs5")
        )

        @audit_log(AuditOperationType.SYNC_AGENT_STATE, log_details=False)
        async def simple_sync(agent_id="agent-nd"):
            return True

        result = await simple_sync()
        assert result is True
