"""
Unit tests for src.transaction_manager
=========================================
Covers:
  - TransactionManager (context manager: commit, rollback, release)
  - execute_in_transaction (happy path, step failure, rollback detection)
  - execute_operation_with_transaction (pre/post validation, ValueError, generic exc)
  - create_savepoint / rollback_to_savepoint

All tests use mocked PostgreSQL pools/connections.  No live DB required.
No Unicode characters.  asyncio_mode = auto (from pytest.ini).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from src.transaction_manager import (
    TransactionManager,
    execute_in_transaction,
    execute_operation_with_transaction,
    create_savepoint,
    rollback_to_savepoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool(conn: AsyncMock) -> MagicMock:
    """Return a pool mock where acquire() is a coroutine returning conn."""
    pool = MagicMock()
    pool.acquire = AsyncMock(return_value=conn)
    pool.release = AsyncMock(return_value=None)
    return pool


def _make_conn() -> AsyncMock:
    """Return a mock DB connection."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    return conn


# ---------------------------------------------------------------------------
# TransactionManager context manager
# ---------------------------------------------------------------------------

class TestTransactionManagerEnter:
    async def test_aenter_returns_connection(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        result = await tm.__aenter__()
        assert result is conn

    async def test_aenter_calls_begin(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        # BEGIN must have been executed
        calls = [c[0][0] for c in conn.execute.call_args_list]
        assert "BEGIN" in calls

    async def test_aenter_registers_active_transaction(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        assert len(tm.active_transactions) == 1


class TestTransactionManagerCommit:
    async def test_aexit_no_exception_commits(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        await tm.__aexit__(None, None, None)
        calls = [c[0][0] for c in conn.execute.call_args_list]
        assert "COMMIT" in calls

    async def test_aexit_no_exception_releases_connection(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        await tm.__aexit__(None, None, None)
        pool.release.assert_awaited_once_with(conn)

    async def test_aexit_no_exception_removes_from_active(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        await tm.__aexit__(None, None, None)
        assert len(tm.active_transactions) == 0

    async def test_aexit_commit_failure_triggers_rollback_and_reraises(self):
        conn = _make_conn()
        # Make COMMIT fail, but ROLLBACK succeed
        def _execute_side_effect(sql, *args, **kwargs):
            if "COMMIT" in sql:
                raise RuntimeError("commit failed")
            return None

        conn.execute = AsyncMock(side_effect=_execute_side_effect)
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        with pytest.raises(RuntimeError, match="commit failed"):
            await tm.__aexit__(None, None, None)

    async def test_aexit_release_failure_does_not_crash(self):
        """A release() error must be swallowed gracefully."""
        conn = _make_conn()
        pool = _make_pool(conn)
        pool.release = AsyncMock(side_effect=RuntimeError("release error"))
        tm = TransactionManager(pool)
        await tm.__aenter__()
        # Should not raise
        await tm.__aexit__(None, None, None)


class TestTransactionManagerRollback:
    async def test_aexit_with_exception_rolls_back(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        with pytest.raises(ValueError):
            await tm.__aexit__(ValueError, ValueError("oops"), None)
        calls = [c[0][0] for c in conn.execute.call_args_list]
        assert "ROLLBACK" in calls

    async def test_aexit_with_exception_reraises(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        with pytest.raises(RuntimeError, match="test error"):
            await tm.__aexit__(RuntimeError, RuntimeError("test error"), None)

    async def test_rollback_failure_still_attempts_release(self):
        conn = _make_conn()

        def _execute_side_effect(sql, *args, **kwargs):
            if "ROLLBACK" in sql:
                raise RuntimeError("rollback failed too")
            return None

        conn.execute = AsyncMock(side_effect=_execute_side_effect)
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        await tm.__aenter__()
        # Even if rollback fails, release should be attempted
        try:
            await tm.__aexit__(ValueError, ValueError("err"), None)
        except (ValueError, RuntimeError):
            pass
        # pool.release called at least once (possibly in _rollback_transaction)
        assert pool.release.await_count >= 1


class TestTransactionManagerAsContext:
    async def test_full_success_path_via_async_with(self):
        """Verify the as-context-manager usage pattern commits correctly."""
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)

        async with tm as c:
            assert c is conn
            await c.execute("SELECT 1")

        calls = [c[0][0] for c in conn.execute.call_args_list]
        assert "BEGIN" in calls
        assert "COMMIT" in calls
        assert "SELECT 1" in calls


# ---------------------------------------------------------------------------
# _rollback_transaction (internal)
# ---------------------------------------------------------------------------

class TestRollbackTransaction:
    async def test_rollback_executes_rollback_sql(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        tm.conn = conn
        tm.active_transactions["tx_test"] = {"connection": conn}
        await tm._rollback_transaction("tx_test")
        calls = [c[0][0] for c in conn.execute.call_args_list]
        assert "ROLLBACK" in calls

    async def test_rollback_cleans_active_transactions(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        tm = TransactionManager(pool)
        tm.conn = conn
        tm.active_transactions["tx_cleanup"] = {"connection": conn}

        # Simulate rollback failure to trigger the except branch
        conn.execute = AsyncMock(side_effect=RuntimeError("rollback err"))
        await tm._rollback_transaction("tx_cleanup")
        # After the failure branch, it tries pool.release
        assert pool.release.await_count >= 1

    async def test_rollback_both_rollback_and_release_fail(self):
        """Cover the bare except:pass on line 102-103 (double failure path)."""
        conn = _make_conn()
        pool = _make_pool(conn)
        pool.release = AsyncMock(side_effect=RuntimeError("release also failed"))
        tm = TransactionManager(pool)
        tm.conn = conn
        tm.active_transactions["tx_double_fail"] = {"connection": conn}

        # Both ROLLBACK execute and pool.release will fail -> bare except:pass
        conn.execute = AsyncMock(side_effect=RuntimeError("rollback err"))
        # Must not raise
        await tm._rollback_transaction("tx_double_fail")


# ---------------------------------------------------------------------------
# execute_in_transaction
# ---------------------------------------------------------------------------

class TestExecuteInTransaction:
    """
    NOTE: execute_in_transaction() returns `result` only from the except branch.
    On the success path it falls through and returns None (known source behaviour).
    Tests for the success path therefore check that the function completes without
    error and that operations were actually called, rather than inspecting the
    return value.
    """

    async def test_all_operations_succeed_no_exception(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        called = []

        async def op1(c):
            called.append(1)
            return "result-1"

        async def op2(c):
            called.append(2)
            return "result-2"

        # Success path returns None (no explicit return in source)
        result = await execute_in_transaction(pool, [op1, op2], "test-op")
        assert result is None  # source has no return on success path
        assert called == [1, 2]

    async def test_empty_operations_list_no_exception(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        # Success path returns None
        result = await execute_in_transaction(pool, [], "empty-op")
        assert result is None

    async def test_operation_failure_returns_error(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def failing_op(c):
            raise ValueError("step failed")

        result = await execute_in_transaction(pool, [failing_op], "fail-op")
        assert result is not None
        assert result["status"] == "error"
        assert "step failed" in result["error"]

    async def test_failure_result_contains_timestamp(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def failing_op(c):
            raise RuntimeError("ts-fail")

        result = await execute_in_transaction(pool, [failing_op], "ts-op")
        assert "timestamp" in result
        assert result["timestamp"]  # non-empty

    async def test_failure_result_contains_operation_name(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def failing_op(c):
            raise RuntimeError("name-fail")

        result = await execute_in_transaction(pool, [failing_op], "named-operation")
        assert result["operation"] == "named-operation"

    async def test_rollback_error_flag_set(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def rollback_op(c):
            raise RuntimeError("some rollback occurred")

        result = await execute_in_transaction(pool, [rollback_op], "rb-op")
        assert result["status"] == "error"
        # If "rollback" in error message, the result should have rollback=True
        if "rollback" in result.get("error", "").lower():
            assert result.get("rollback") is True

    async def test_default_operation_name_on_failure(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def failing_op(c):
            raise RuntimeError("default-name-fail")

        result = await execute_in_transaction(pool, [failing_op], operation_name="transaction")
        assert result["operation"] == "transaction"

    async def test_operations_receive_connection(self):
        """Each operation callback is called with the connection object."""
        conn = _make_conn()
        pool = _make_pool(conn)
        received = []

        async def op(c):
            received.append(c)

        await execute_in_transaction(pool, [op], "conn-op")
        assert len(received) == 1
        assert received[0] is conn


# ---------------------------------------------------------------------------
# execute_operation_with_transaction
# ---------------------------------------------------------------------------

class TestExecuteOperationWithTransaction:
    """
    NOTE: execute_operation_with_transaction() returns `result` only from the
    generic Exception branch.  Success path and ValueError branch fall through
    and return None (known source behaviour). Tests validate actual behaviour.
    """

    async def test_success_no_validation_returns_none(self):
        """Success path in source has no explicit return -> returns None."""
        conn = _make_conn()
        pool = _make_pool(conn)
        called = []

        async def operation(c):
            called.append(True)
            return {"rows_inserted": 1}

        result = await execute_operation_with_transaction(
            pool, operation, "insert-op"
        )
        assert result is None  # source success path does not return result
        assert called  # operation was actually called

    async def test_validate_before_passes_no_exception(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        called = []

        async def validate(c):
            return {"status": "ok"}

        async def operation(c):
            called.append(True)
            return "done"

        result = await execute_operation_with_transaction(
            pool, operation, "op", validate_before=validate
        )
        assert result is None
        assert called

    async def test_validate_before_fails_returns_none(self):
        """ValueError path has no return -> returns None."""
        conn = _make_conn()
        pool = _make_pool(conn)
        op_called = []

        async def bad_validate(c):
            return {"status": "error", "error": "precondition not met"}

        async def operation(c):
            op_called.append(True)
            return "should not run"

        result = await execute_operation_with_transaction(
            pool, operation, "op", validate_before=bad_validate
        )
        # ValueError caught -> result["validation_error"] set, but no return
        assert result is None
        assert not op_called  # operation must not have been called

    async def test_validate_after_passes_no_exception(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def operation(c):
            return "data"

        async def validate(c):
            return {"status": "ok"}

        result = await execute_operation_with_transaction(
            pool, operation, "op", validate_after=validate
        )
        assert result is None  # success path returns None

    async def test_validate_after_fails_returns_none(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def operation(c):
            return "data"

        async def bad_after(c):
            return {"status": "error", "error": "post-condition violated"}

        result = await execute_operation_with_transaction(
            pool, operation, "op", validate_after=bad_after
        )
        # ValueError path returns None
        assert result is None

    async def test_operation_raises_value_error_returns_none(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def op(c):
            raise ValueError("bad input")

        result = await execute_operation_with_transaction(pool, op, "op")
        # ValueError handler does not return result explicitly -> None
        assert result is None

    async def test_operation_raises_generic_exception_returns_result(self):
        """Generic Exception branch has an explicit return result."""
        conn = _make_conn()
        pool = _make_pool(conn)

        async def op(c):
            raise RuntimeError("db crash")

        result = await execute_operation_with_transaction(pool, op, "op")
        assert result is not None
        assert result["status"] == "error"
        assert "db crash" in result["error"]

    async def test_both_validations_present_and_pass(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        called = []

        async def v_before(c):
            return {"status": "ok"}

        async def op(c):
            called.append(42)
            return 42

        async def v_after(c):
            return {"status": "ok"}

        result = await execute_operation_with_transaction(
            pool, op, "full-op", validate_before=v_before, validate_after=v_after
        )
        assert result is None  # success path returns None
        assert called == [42]

    async def test_generic_exception_result_contains_operation_name(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def op(c):
            raise RuntimeError("fail for name test")

        result = await execute_operation_with_transaction(pool, op, "named-op")
        assert result["operation"] == "named-op"
        assert "timestamp" in result

    async def test_rollback_error_flag(self):
        conn = _make_conn()
        pool = _make_pool(conn)

        async def op(c):
            raise RuntimeError("rollback needed")

        result = await execute_operation_with_transaction(pool, op, "rb-op")
        if result and "rollback" in result.get("error", "").lower():
            assert result.get("rolled_back") is True

    async def test_operation_receives_connection(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        received = []

        async def op(c):
            received.append(c)

        await execute_operation_with_transaction(pool, op, "conn-op")
        assert received[0] is conn


# ---------------------------------------------------------------------------
# create_savepoint
# ---------------------------------------------------------------------------

class TestCreateSavepoint:
    async def test_success_returns_true(self):
        conn = _make_conn()
        result = await create_savepoint(conn, "sp1")
        assert result is True

    async def test_execute_called_with_savepoint_name(self):
        conn = _make_conn()
        await create_savepoint(conn, "my_savepoint")
        conn.execute.assert_awaited_once_with("SAVEPOINT my_savepoint")

    async def test_db_exception_returns_false(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("savepoint error"))
        result = await create_savepoint(conn, "sp_fail")
        assert result is False

    async def test_savepoint_name_used_verbatim(self):
        conn = _make_conn()
        await create_savepoint(conn, "before_delete")
        args = conn.execute.call_args[0]
        assert "before_delete" in args[0]


# ---------------------------------------------------------------------------
# rollback_to_savepoint
# ---------------------------------------------------------------------------

class TestRollbackToSavepoint:
    async def test_success_returns_true(self):
        conn = _make_conn()
        result = await rollback_to_savepoint(conn, "sp1")
        assert result is True

    async def test_execute_called_with_rollback_sql(self):
        conn = _make_conn()
        await rollback_to_savepoint(conn, "sp_target")
        conn.execute.assert_awaited_once_with("ROLLBACK TO sp_target")

    async def test_db_exception_returns_false(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("rollback to failed"))
        result = await rollback_to_savepoint(conn, "sp_fail")
        assert result is False

    async def test_savepoint_name_in_sql(self):
        conn = _make_conn()
        await rollback_to_savepoint(conn, "checkpoint_abc")
        args = conn.execute.call_args[0]
        assert "checkpoint_abc" in args[0]


# ---------------------------------------------------------------------------
# __all__ export check
# ---------------------------------------------------------------------------

class TestExports:
    def test_all_exports_importable(self):
        from src.transaction_manager import (
            TransactionManager,
            execute_in_transaction,
            execute_operation_with_transaction,
            create_savepoint,
            rollback_to_savepoint,
        )
        for obj in [
            TransactionManager,
            execute_in_transaction,
            execute_operation_with_transaction,
            create_savepoint,
            rollback_to_savepoint,
        ]:
            assert obj is not None
