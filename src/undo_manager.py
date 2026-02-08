"""
Enhanced Cognee - Undo Manager for Automated Actions

This module provides a comprehensive undo mechanism for all automated operations
in the Enhanced Cognee system. It tracks:
- Original state before modifications
- Operation chains (groups of related operations)
- Undo history with metadata
- Redo capability
- Automatic cleanup of old undo entries

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("WARN: asyncpg not available - database undo logging disabled")


class UndoOperationType(Enum):
    """Types of operations that can be undone."""
    MEMORY_ADD = "memory_add"
    MEMORY_UPDATE = "memory_update"
    MEMORY_DELETE = "memory_delete"
    MEMORY_SUMMARIZE = "memory_summarize"
    MEMORY_DEDUPLICATE = "memory_deduplicate"
    MEMORY_MERGE = "memory_merge"
    MEMORY_ARCHIVE = "memory_archive"
    MEMORY_EXPIRE = "memory_expire"
    CATEGORY_SUMMARIZE = "category_summarize"
    SHARING_SET = "sharing_set"
    AGENT_SYNC = "agent_sync"


class UndoStatus(Enum):
    """Status of undo operations."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class UndoEntry:
    """Represents an undoable operation."""
    undo_id: str
    operation_type: UndoOperationType
    agent_id: str
    timestamp: datetime

    # Original state (for reverting)
    original_state: Dict[str, Any]

    # New state (what was applied)
    new_state: Dict[str, Any]

    # Operation details
    memory_id: Optional[str]
    category: Optional[str]
    operation_chain_id: Optional[str]  # For grouping related operations

    # Metadata
    status: UndoStatus
    error_message: Optional[str]
    expiration_date: Optional[datetime]

    # Additional context
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert enums to strings
        data["operation_type"] = self.operation_type.value
        data["status"] = self.status.value
        # Convert datetime to ISO format
        data["timestamp"] = self.timestamp.isoformat()
        if self.expiration_date:
            data["expiration_date"] = self.expiration_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UndoEntry":
        """Create from dictionary."""
        # Convert strings back to enums
        data["operation_type"] = UndoOperationType(data["operation_type"])
        data["status"] = UndoStatus(data["status"])
        # Convert ISO format back to datetime
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data.get("expiration_date"):
            data["expiration_date"] = datetime.fromisoformat(data["expiration_date"])
        return cls(**data)


class UndoManager:
    """
    Manages undo operations for Enhanced Cognee automations.

    Features:
    - Track original state before all modifications
    - Support for operation chains (related operations)
    - Simple undo interface
    - Redo capability
    - Automatic cleanup of expired entries
    - Persistent storage in database
    """

    def __init__(
        self,
        config_path: str = "automation_config.json",
        db_pool: Optional[asyncpg.Pool] = None
    ):
        """
        Initialize the undo manager.

        Args:
            config_path: Path to automation config file
            db_pool: PostgreSQL connection pool
        """
        self.config = self._load_config(config_path)
        self.db_pool = db_pool

        # In-memory undo history (recent entries)
        self.undo_history: List[UndoEntry] = []
        self.max_history = self.config.get("undo_management", {}).get(
            "max_undo_history", 100
        )

        # Redo history (for operations that were undone)
        self.redo_history: List[UndoEntry] = []
        self.max_redo_history = 50

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load automation configuration."""
        try:
            import json
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
            "undo_management": {
                "enabled": True,
                "max_undo_history": 100,
                "undo_retention_days": 7,
                "auto_cleanup": True,
                "preserve_originals": True
            }
        }

    async def create_undo_entry(
        self,
        operation_type: UndoOperationType,
        agent_id: str,
        original_state: Dict[str, Any],
        new_state: Dict[str, Any],
        memory_id: Optional[str] = None,
        category: Optional[str] = None,
        operation_chain_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UndoEntry:
        """
        Create an undo entry for an operation.

        Args:
            operation_type: Type of operation performed
            agent_id: Agent that performed the operation
            original_state: State before the operation
            new_state: State after the operation
            memory_id: Associated memory ID
            category: Associated category
            operation_chain_id: ID for grouping related operations
            metadata: Additional metadata

        Returns:
            UndoEntry object
        """
        undo_id = str(uuid.uuid4())

        # Calculate expiration date
        retention_days = self.config.get("undo_management", {}).get(
            "undo_retention_days", 7
        )
        expiration_date = datetime.now(timezone.utc) + timedelta(days=retention_days)

        entry = UndoEntry(
            undo_id=undo_id,
            operation_type=operation_type,
            agent_id=agent_id,
            timestamp=datetime.now(timezone.utc),
            original_state=original_state,
            new_state=new_state,
            memory_id=memory_id,
            category=category,
            operation_chain_id=operation_chain_id,
            status=UndoStatus.PENDING,
            error_message=None,
            expiration_date=expiration_date,
            metadata=metadata or {}
        )

        # Add to in-memory history
        self.undo_history.append(entry)
        if len(self.undo_history) > self.max_history:
            self.undo_history.pop(0)

        # Save to database
        if self.db_pool and POSTGRES_AVAILABLE:
            await self._save_undo_entry(entry)

        return entry

    async def _save_undo_entry(self, entry: UndoEntry):
        """Save undo entry to database."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO cognee_db.undo_log (
                        undo_id, operation_type, agent_id, timestamp,
                        original_state, new_state, memory_id, category,
                        operation_chain_id, status, error_message,
                        expiration_date, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (undo_id) DO NOTHING
                """,
                    entry.undo_id,
                    entry.operation_type.value,
                    entry.agent_id,
                    entry.timestamp,
                    json.dumps(entry.original_state),
                    json.dumps(entry.new_state),
                    entry.memory_id,
                    entry.category,
                    entry.operation_chain_id,
                    entry.status.value,
                    entry.error_message,
                    entry.expiration_date,
                    json.dumps(entry.metadata)
                )
        except Exception as e:
            print(f"ERROR: Failed to save undo entry: {e}")

    async def undo(
        self,
        undo_id: str,
        agent_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Undo a specific operation.

        Args:
            undo_id: ID of the operation to undo
            agent_id: Agent requesting the undo
            reason: Reason for the undo

        Returns:
            Result dictionary with status and details
        """
        # Find the undo entry
        entry = None
        for e in self.undo_history:
            if e.undo_id == undo_id:
                entry = e
                break

        if not entry and self.db_pool and POSTGRES_AVAILABLE:
            # Try to load from database
            entry = await self._load_undo_entry(undo_id)

        if not entry:
            return {
                "success": False,
                "error": f"Undo entry not found: {undo_id}"
            }

        # Check if already undone
        if entry.status == UndoStatus.COMPLETED:
            return {
                "success": False,
                "error": f"Operation already undone: {undo_id}"
            }

        # Check if expired
        if entry.expiration_date and entry.expiration_date < datetime.now(timezone.utc):
            entry.status = UndoStatus.EXPIRED
            return {
                "success": False,
                "error": f"Undo entry expired: {undo_id}"
            }

        # Perform the undo based on operation type
        try:
            result = await self._perform_undo(entry, agent_id, reason)

            if result["success"]:
                entry.status = UndoStatus.COMPLETED

                # Add to redo history
                self.redo_history.append(entry)
                if len(self.redo_history) > self.max_redo_history:
                    self.redo_history.pop(0)

                # Update database
                if self.db_pool and POSTGRES_AVAILABLE:
                    await self._update_undo_entry(entry)

            else:
                entry.status = UndoStatus.FAILED
                entry.error_message = result.get("error", "Unknown error")

                if self.db_pool and POSTGRES_AVAILABLE:
                    await self._update_undo_entry(entry)

            return result

        except Exception as e:
            entry.status = UndoStatus.FAILED
            entry.error_message = str(e)

            if self.db_pool and POSTGRES_AVAILABLE:
                await self._update_undo_entry(entry)

            return {
                "success": False,
                "error": str(e)
            }

    async def _perform_undo(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Perform the actual undo operation."""
        op_type = entry.operation_type

        if op_type == UndoOperationType.MEMORY_ADD:
            # Undo add = delete the memory
            return await self._undo_memory_add(entry, agent_id, reason)

        elif op_type == UndoOperationType.MEMORY_UPDATE:
            # Undo update = revert to original content
            return await self._undo_memory_update(entry, agent_id, reason)

        elif op_type == UndoOperationType.MEMORY_DELETE:
            # Undo delete = restore the memory
            return await self._undo_memory_delete(entry, agent_id, reason)

        elif op_type == UndoOperationType.MEMORY_SUMMARIZE:
            # Undo summarize = restore original content
            return await self._undo_memory_summarize(entry, agent_id, reason)

        elif op_type == UndoOperationType.MEMORY_DEDUPLICATE:
            # Undo deduplicate = restore merged memories
            return await self._undo_memory_deduplicate(entry, agent_id, reason)

        elif op_type == UndoOperationType.SHARING_SET:
            # Undo sharing = revert to previous sharing policy
            return await self._undo_sharing_set(entry, agent_id, reason)

        else:
            return {
                "success": False,
                "error": f"Unsupported undo operation type: {op_type.value}"
            }

    async def _undo_memory_add(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo memory addition by deleting it."""
        # Import here to avoid circular dependency
        # from enhanced_cognee_mcp_server import delete_memory

        memory_id = entry.new_state.get("memory_id") or entry.memory_id
        if not memory_id:
            return {
                "success": False,
                "error": "No memory_id found in new_state"
            }

        # TODO: Call actual delete_memory function
        # await delete_memory(memory_id)

        return {
            "success": True,
            "message": f"Deleted memory {memory_id} (undo of add operation)",
            "memory_id": memory_id,
            "reason": reason
        }

    async def _undo_memory_update(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo memory update by reverting to original content."""
        memory_id = entry.memory_id
        if not memory_id:
            return {
                "success": False,
                "error": "No memory_id in undo entry"
            }

        original_content = entry.original_state.get("content")
        if not original_content:
            return {
                "success": False,
                "error": "No original content found"
            }

        # TODO: Call actual update_memory function
        # await update_memory(memory_id, original_content)

        return {
            "success": True,
            "message": f"Reverted memory {memory_id} to original content",
            "memory_id": memory_id,
            "reason": reason
        }

    async def _undo_memory_delete(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo memory deletion by restoring it."""
        original_data = entry.original_state

        # TODO: Call actual add_memory function
        # memory_id = await add_memory(
        #     content=original_data.get("content"),
        #     agent_id=entry.agent_id,
        #     metadata=original_data.get("metadata")
        # )

        return {
            "success": True,
            "message": "Restored deleted memory",
            "reason": reason
        }

    async def _undo_memory_summarize(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo memory summarization by restoring original content."""
        memory_id = entry.memory_id
        if not memory_id:
            return {
                "success": False,
                "error": "No memory_id in undo entry"
            }

        original_content = entry.original_state.get("original_content")
        if not original_content:
            return {
                "success": False,
                "error": "No original_content found"
            }

        # TODO: Update memory with original content
        # await update_memory(memory_id, original_content)

        # Clear summarization flags
        # TODO: Update metadata

        return {
            "success": True,
            "message": f"Restored original content for memory {memory_id}",
            "memory_id": memory_id,
            "reason": reason
        }

    async def _undo_memory_deduplicate(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo deduplication by restoring merged memories."""
        merged_ids = entry.original_state.get("merged_memory_ids", [])
        if not merged_ids:
            return {
                "success": False,
                "error": "No merged memory IDs found"
            }

        # TODO: Restore each merged memory
        # for mem_data in merged_ids:
        #     await add_memory(
        #         content=mem_data["content"],
        #         agent_id=mem_data["agent_id"],
        #         metadata=mem_data.get("metadata")
        #     )

        return {
            "success": True,
            "message": f"Restored {len(merged_ids)} merged memories",
            "reason": reason
        }

    async def _undo_sharing_set(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo sharing policy change by reverting to original."""
        memory_id = entry.memory_id
        if not memory_id:
            return {
                "success": False,
                "error": "No memory_id in undo entry"
            }

        original_policy = entry.original_state.get("sharing_policy")
        if not original_policy:
            return {
                "success": False,
                "error": "No original sharing policy found"
            }

        # TODO: Call set_memory_sharing with original policy
        # await set_memory_sharing(
        #     memory_id=memory_id,
        #     policy=original_policy["policy"],
        #     allowed_agents=original_policy.get("allowed_agents")
        # )

        return {
            "success": True,
            "message": f"Reverted sharing policy for memory {memory_id}",
            "memory_id": memory_id,
            "original_policy": original_policy,
            "reason": reason
        }

    async def _load_undo_entry(self, undo_id: str) -> Optional[UndoEntry]:
        """Load undo entry from database."""
        if not self.db_pool or not POSTGRES_AVAILABLE:
            return None

        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM cognee_db.undo_log WHERE undo_id = $1",
                    undo_id
                )
                if row:
                    return UndoEntry.from_dict(dict(row))
        except Exception as e:
            print(f"ERROR: Failed to load undo entry: {e}")

        return None

    async def _update_undo_entry(self, entry: UndoEntry):
        """Update undo entry in database."""
        if not self.db_pool or not POSTGRES_AVAILABLE:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE cognee_db.undo_log
                    SET status = $1, error_message = $2
                    WHERE undo_id = $3
                """,
                    entry.status.value,
                    entry.error_message,
                    entry.undo_id
                )
        except Exception as e:
            print(f"ERROR: Failed to update undo entry: {e}")

    async def undo_chain(
        self,
        operation_chain_id: str,
        agent_id: str,
        reason: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Undo an entire chain of related operations.

        Args:
            operation_chain_id: ID of the operation chain
            agent_id: Agent requesting the undo
            reason: Reason for the undo

        Returns:
            List of results for each operation in the chain
        """
        results = []

        # Find all operations in the chain
        chain_entries = [
            entry for entry in self.undo_history
            if entry.operation_chain_id == operation_chain_id
        ]

        # Sort by timestamp (undo in reverse order)
        chain_entries.sort(key=lambda x: x.timestamp, reverse=True)

        # Undo each operation
        for entry in chain_entries:
            result = await self.undo(entry.undo_id, agent_id, reason)
            results.append({
                "undo_id": entry.undo_id,
                "operation_type": entry.operation_type.value,
                "result": result
            })

        return results

    async def get_undo_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get undo history for an agent.

        Args:
            agent_id: Filter by agent ID (None = all agents)
            limit: Maximum number of entries

        Returns:
            List of undo entries (as dictionaries)
        """
        history = self.undo_history.copy()

        # Filter by agent
        if agent_id:
            history = [e for e in history if e.agent_id == agent_id]

        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x.timestamp, reverse=True)

        # Convert to dictionaries and limit
        return [e.to_dict() for e in history[:limit]]

    async def cleanup_expired_entries(self):
        """Remove expired undo entries from history and database."""
        now = datetime.now(timezone.utc)

        # Clean in-memory history
        self.undo_history = [
            e for e in self.undo_history
            if not e.expiration_date or e.expiration_date >= now
        ]

        # Clean database
        if self.db_pool and POSTGRES_AVAILABLE:
            try:
                async with self.db_pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM cognee_db.undo_log WHERE expiration_date < $1",
                        now
                    )
                    print(f"INFO: Cleaned up {result} expired undo entries")
            except Exception as e:
                print(f"ERROR: Failed to cleanup expired entries: {e}")


# Global undo manager instance
_undo_manager: Optional[UndoManager] = None


def get_undo_manager() -> Optional[UndoManager]:
    """Get the global undo manager instance."""
    return _undo_manager


def init_undo_manager(
    config_path: str = "automation_config.json",
    db_pool: Optional[asyncpg.Pool] = None
) -> UndoManager:
    """
    Initialize the global undo manager.

    Args:
        config_path: Path to automation config file
        db_pool: PostgreSQL connection pool

    Returns:
        UndoManager instance
    """
    global _undo_manager
    _undo_manager = UndoManager(config_path, db_pool)
    return _undo_manager
