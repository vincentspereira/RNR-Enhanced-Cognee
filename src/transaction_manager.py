"""
Enhanced Cognee - Transaction Manager

Provides database transaction support with rollback capability for multi-step operations.

This ensures atomic operations - either all steps succeed, or all are rolled back.
"""

import asyncio
import logging
from typing import Optional, Callable, Any, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TransactionManager:
    """
    Manages database transactions with automatic rollback on failure.

    Usage:
        async with transaction_manager(postgres_pool) as conn:
            # Perform operations
            await conn.execute("...")
            await conn.execute("...")
            # If any operation fails, automatic rollback
    """

    def __init__(self, pool: Any) -> None:
        """
        Initialize transaction manager.

        Args:
            pool: PostgreSQL connection pool
        """
        self.pool = pool
        self.active_transactions: Dict[str, Dict[str, Any]] = {}

    async def __aenter__(self):
        """Enter transaction context."""
        # Get connection from pool
        self.conn = await self.pool.acquire()
        # Begin transaction
        await self.conn.execute("BEGIN")
        transaction_id = f"tx_{datetime.now().timestamp()}"
        self.active_transactions[transaction_id] = {
            "connection": self.conn,
            "started_at": datetime.now()
        }
        logger.info(f"Transaction started: {transaction_id}")
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context with commit or rollback."""
        transaction_id = list(self.active_transactions.keys())[-1] if self.active_transactions else None

        if exc_type is None:
            # No exception - commit transaction
            try:
                await self.conn.execute("COMMIT")
                logger.info(f"Transaction committed: {transaction_id}")
            except Exception as e:
                logger.error(f"Failed to commit transaction {transaction_id}: {e}")
                await self._rollback_transaction(transaction_id)
                raise
        else:
            # Exception occurred - rollback transaction
            logger.warning(f"Transaction failed, rolling back: {transaction_id}")
            await self._rollback_transaction(transaction_id)
            # Re-raise the exception
            if exc_type:
                raise exc_type(exc_val).with_traceback(exc_tb) if exc_tb else exc_type(exc_val)

        # Release connection back to pool
        try:
            await self.pool.release(self.conn)
        except Exception as e:
            logger.error(f"Failed to release connection: {e}")

        # Remove from active transactions
        if transaction_id and transaction_id in self.active_transactions:
            del self.active_transactions[transaction_id]

    async def _rollback_transaction(self, transaction_id: str) -> None:
        """
        Perform transaction rollback.

        Args:
            transaction_id: Transaction identifier
        """
        try:
            await self.conn.execute("ROLLBACK")
            logger.info(f"Transaction rolled back: {transaction_id}")
        except Exception as e:
            logger.error(f"Failed to rollback transaction {transaction_id}: {e}")
            # Connection may be broken, remove it from pool
            try:
                await self.pool.release(self.conn)
                # Remove from active transactions
                if transaction_id in self.active_transactions:
                    del self.active_transactions[transaction_id]
            except:
                pass


async def execute_in_transaction(
    pool,
    operations: List[Callable],
    operation_name: str = "transaction"
) -> Dict[str, Any]:
    """
    Execute multiple operations in a single transaction.

    All operations must succeed, or all will be rolled back.

    Args:
        pool: PostgreSQL connection pool
        operations: List of async functions to execute
        operation_name: Name for logging

    Returns:
        Dictionary with status, data, error, timestamp
    """
    from datetime import timezone

    result = {
        "status": "error",
        "data": None,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation_name
    }

    transaction_manager = TransactionManager(pool)

    try:
        async with transaction_manager as conn:
            results = []
            for i, operation in enumerate(operations):
                logger.debug(f"Executing step {i+1}/{len(operations)} in transaction")
                step_result = await operation(conn)
                results.append(step_result)

            result["status"] = "success"
            result["data"] = {
                "steps_executed": len(operations),
                "results": results
            }
            logger.info(f"Transaction completed successfully: {operation_name}")

    except Exception as e:
        logger.error(f"Transaction failed: {operation_name} - {e}")
        result["error"] = str(e)
        if "rollback" in str(e).lower():
            result["rollback"] = True
        return result


async def execute_operation_with_transaction(
    pool,
    operation: Callable,
    operation_name: str,
    validate_before: Optional[Callable] = None,
    validate_after: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Execute a single operation with transaction support and validation.

    Args:
        pool: PostgreSQL connection pool
        operation: Async operation to execute
        operation_name: Name for logging
        validate_before: Optional validation before operation
        validate_after: Optional validation after operation

    Returns:
        Dictionary with status, data, error, timestamp
    """
    from datetime import timezone

    result = {
        "status": "error",
        "data": None,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation_name
    }

    transaction_manager = TransactionManager(pool)

    try:
        async with transaction_manager as conn:
            # Pre-operation validation
            if validate_before:
                validation_result = await validate_before(conn)
                if validation_result.get("status") == "error":
                    raise ValueError(f"Pre-validation failed: {validation_result.get('error')}")
                logger.info(f"Pre-validation passed: {operation_name}")

            # Execute operation
            logger.debug(f"Executing operation with transaction: {operation_name}")
            operation_result = await operation(conn)

            # Post-operation validation
            if validate_after:
                validation_result = await validate_after(conn)
                if validation_result.get("status") == "error":
                    raise ValueError(f"Post-validation failed: {validation_result.get('error')}")
                logger.info(f"Post-validation passed: {operation_name}")

            result["status"] = "success"
            result["data"] = operation_result
            logger.info(f"Operation completed successfully: {operation_name}")

    except ValueError as e:
        logger.error(f"Validation failed: {operation_name} - {e}")
        result["error"] = f"Validation failed: {str(e)}"
        result["validation_error"] = True
    except Exception as e:
        logger.error(f"Operation failed: {operation_name} - {e}")
        result["error"] = str(e)
        if "rollback" in str(e).lower():
            result["rolled_back"] = True
        return result


async def create_savepoint(
    conn,
    savepoint_name: str
) -> bool:
    """
    Create a transaction savepoint.

    Args:
        conn: Database connection
        savepoint_name: Name for savepoint

    Returns:
        True if successful
    """
    try:
        await conn.execute(f"SAVEPOINT {savepoint_name}")
        logger.debug(f"Savepoint created: {savepoint_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to create savepoint {savepoint_name}: {e}")
        return False


async def rollback_to_savepoint(
    conn,
    savepoint_name: str
) -> bool:
    """
    Rollback to a specific savepoint.

    Args:
        conn: Database connection
        savepoint_name: Savepoint name to rollback to

    Returns:
        True if successful
    """
    try:
        await conn.execute(f"ROLLBACK TO {savepoint_name}")
        logger.info(f"Rolled back to savepoint: {savepoint_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to rollback to savepoint {savepoint_name}: {e}")
        return False


# Export main components
__all__ = [
    "TransactionManager",
    "execute_in_transaction",
    "execute_operation_with_transaction",
    "create_savepoint",
    "rollback_to_savepoint"
]
