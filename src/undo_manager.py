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
Version: 1.1.0
Date: 2026-05-14
"""

import json as _json
import uuid as _uuid
from datetime import datetime, timezone, timedelta, UTC
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict

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

    # DDL for the undo log table (shared_memory schema)
    _SCHEMA_DDL = """
        CREATE TABLE IF NOT EXISTS shared_memory.undo_log (
            undo_id UUID PRIMARY KEY,
            operation_type TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            original_state JSONB NOT NULL DEFAULT '{}',
            new_state JSONB NOT NULL DEFAULT '{}',
            memory_id UUID,
            category TEXT,
            operation_chain_id UUID,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT,
            expiration_date TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'
        )
    """

    def __init__(
        self,
        config_path: str = "automation_config.json",
        db_pool: Optional["asyncpg.Pool"] = None
    ):
        """
        Initialize the undo manager.

        Args:
            config_path: Path to automation config file
            db_pool: PostgreSQL connection pool
        """
        self.config = self._load_config(config_path)
        self.db_pool = db_pool

        # Schema creation flag (lazy, created once)
        self._schema_created: bool = False

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
            with open(config_path, 'r') as f:
                loaded = _json.load(f)
                return loaded if isinstance(loaded, dict) else self._get_default_config()
        except FileNotFoundError:
            print(f"WARN: Config file not found: {config_path}")
            return self._get_default_config()
        except _json.JSONDecodeError as e:
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

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    async def _ensure_schema(self) -> None:
        """Create shared_memory.undo_log table if it does not yet exist.

        Guarded by _schema_created so the DDL round-trip happens at most once
        per UndoManager lifetime, regardless of how many concurrent callers
        trigger it.
        """
        if self._schema_created:
            return
        if not self.db_pool or not POSTGRES_AVAILABLE:
            self._schema_created = True  # Nothing we can do without a pool
            return
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(self._SCHEMA_DDL)
            self._schema_created = True
        except Exception as e:
            print(f"WARN: Failed to ensure undo_log schema: {e}")

    # ------------------------------------------------------------------
    # Entry persistence
    # ------------------------------------------------------------------

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
        undo_id = str(_uuid.uuid4())

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

    async def _save_undo_entry(self, entry: UndoEntry) -> None:
        """Save undo entry to database."""
        await self._ensure_schema()
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO shared_memory.undo_log (
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
                    _json.dumps(entry.original_state),
                    _json.dumps(entry.new_state),
                    entry.memory_id,
                    entry.category,
                    entry.operation_chain_id,
                    entry.status.value,
                    entry.error_message,
                    entry.expiration_date,
                    _json.dumps(entry.metadata)
                )
        except Exception as e:
            print(f"ERROR: Failed to save undo entry: {e}")

    async def _load_undo_entry(self, undo_id: str) -> Optional[UndoEntry]:
        """Load undo entry from database."""
        if not self.db_pool or not POSTGRES_AVAILABLE:
            return None

        await self._ensure_schema()
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM shared_memory.undo_log WHERE undo_id = $1",
                    undo_id
                )
                if row:
                    return UndoEntry.from_dict(dict(row))
        except Exception as e:
            print(f"ERROR: Failed to load undo entry: {e}")

        return None

    async def _update_undo_entry(self, entry: UndoEntry) -> None:
        """Update undo entry in database."""
        if not self.db_pool or not POSTGRES_AVAILABLE:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE shared_memory.undo_log
                    SET status = $1, error_message = $2
                    WHERE undo_id = $3
                """,
                    entry.status.value,
                    entry.error_message,
                    entry.undo_id
                )
        except Exception as e:
            print(f"ERROR: Failed to update undo entry: {e}")

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

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
            return await self._undo_memory_add(entry, agent_id, reason)

        elif op_type == UndoOperationType.MEMORY_UPDATE:
            return await self._undo_memory_update(entry, agent_id, reason)

        elif op_type == UndoOperationType.MEMORY_DELETE:
            return await self._undo_memory_delete(entry, agent_id, reason)

        elif op_type == UndoOperationType.MEMORY_SUMMARIZE:
            return await self._undo_memory_summarize(entry, agent_id, reason)

        elif op_type == UndoOperationType.MEMORY_DEDUPLICATE:
            return await self._undo_memory_deduplicate(entry, agent_id, reason)

        elif op_type == UndoOperationType.SHARING_SET:
            return await self._undo_sharing_set(entry, agent_id, reason)

        else:
            return {
                "success": False,
                "error": f"Unsupported undo operation type: {op_type.value}"
            }

    # ------------------------------------------------------------------
    # Undo implementations (previously stubs)
    # ------------------------------------------------------------------

    async def _undo_memory_add(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo memory addition by deleting the newly-created row."""
        memory_id = entry.new_state.get("memory_id") or entry.memory_id
        if not memory_id:
            return {
                "success": False,
                "error": "No memory_id found in new_state"
            }

        if not self.db_pool or not POSTGRES_AVAILABLE:
            # In-memory bookkeeping mode: no DB, but undo is still recorded
            return {
                "success": True,
                "message": f"Deleted memory {memory_id} (undo of add operation; no-db mode)",
                "memory_id": memory_id,
                "reason": reason,
                "no_db_mode": True,
            }

        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM shared_memory.documents WHERE id = $1",
                    memory_id
                )
            deleted = result.split()[-1] if result else "0"
            if deleted == "0":
                return {"success": False, "error": f"Memory {memory_id} not found"}
            return {
                "success": True,
                "message": f"Deleted memory {memory_id} (undo of add operation)",
                "memory_id": memory_id,
                "reason": reason
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _undo_memory_update(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo memory update by restoring the original content."""
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

        if not self.db_pool or not POSTGRES_AVAILABLE:
            return {
                "success": True,
                "message": f"Reverted memory {memory_id} to original content (no-db mode)",
                "memory_id": memory_id,
                "reason": reason,
                "no_db_mode": True,
            }

        try:
            async with self.db_pool.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT id FROM shared_memory.documents WHERE id = $1",
                    memory_id
                )
                if not exists:
                    return {"success": False, "error": f"Memory {memory_id} not found"}
                await conn.execute(
                    "UPDATE shared_memory.documents SET content = $2 WHERE id = $1",
                    memory_id, original_content
                )
            return {
                "success": True,
                "message": f"Reverted memory {memory_id} to original content",
                "memory_id": memory_id,
                "reason": reason
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _undo_memory_delete(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo memory deletion by re-inserting the original row."""
        original_data = entry.original_state

        if not self.db_pool or not POSTGRES_AVAILABLE:
            return {
                "success": True,
                "message": "Restored deleted memory (no-db mode)",
                "restored_id": original_data.get("id"),
                "reason": reason,
                "no_db_mode": True,
            }

        try:
            new_id = original_data.get("id") or str(_uuid.uuid4())
            content = original_data.get("content", "")
            owner = original_data.get("agent_id", entry.agent_id)
            meta = original_data.get("metadata", {})
            created_at = datetime.now(UTC).replace(tzinfo=None)

            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO shared_memory.documents
                        (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                """, new_id, "Restored memory", content, owner, "general", [], meta, created_at)

            return {
                "success": True,
                "message": "Restored deleted memory",
                "restored_id": new_id,
                "reason": reason
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _undo_memory_summarize(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo memory summarization by restoring the original full content."""
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
                "error": "No original_content found in original_state"
            }

        if not self.db_pool or not POSTGRES_AVAILABLE:
            return {
                "success": True,
                "message": f"Restored original content for memory {memory_id} (no-db mode)",
                "memory_id": memory_id,
                "reason": reason,
                "no_db_mode": True,
            }

        try:
            async with self.db_pool.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT id FROM shared_memory.documents WHERE id = $1",
                    memory_id
                )
                if not exists:
                    return {"success": False, "error": f"Memory {memory_id} not found"}
                await conn.execute(
                    "UPDATE shared_memory.documents SET content = $2 WHERE id = $1",
                    memory_id, original_content
                )
            return {
                "success": True,
                "message": f"Restored original content for memory {memory_id}",
                "memory_id": memory_id,
                "reason": reason
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _undo_memory_deduplicate(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo deduplication by restoring each merged memory."""
        merged_ids = entry.original_state.get("merged_memory_ids", [])
        if not merged_ids:
            return {
                "success": False,
                "error": "No merged memory IDs found in original_state"
            }

        if not self.db_pool or not POSTGRES_AVAILABLE:
            return {
                "success": True,
                "message": f"Restored {len(merged_ids)} merged memories (no-db mode)",
                "reason": reason,
                "no_db_mode": True,
            }

        restored = 0
        errors = []
        created_at = datetime.now(UTC).replace(tzinfo=None)

        try:
            async with self.db_pool.acquire() as conn:
                for mem_data in merged_ids:
                    try:
                        mem_id = mem_data.get("id") or str(_uuid.uuid4())
                        content = mem_data.get("content", "")
                        owner = mem_data.get("agent_id", entry.agent_id)
                        meta = mem_data.get("metadata", {})
                        await conn.execute("""
                            INSERT INTO shared_memory.documents
                                (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                        """, mem_id, "Restored memory", content, owner, "general", [], meta, created_at)
                        restored += 1
                    except Exception as e:
                        errors.append(str(e))

            if errors:
                return {
                    "success": restored > 0,
                    "message": f"Restored {restored} of {len(merged_ids)} merged memories",
                    "errors": errors,
                    "reason": reason
                }
            return {
                "success": True,
                "message": f"Restored {restored} merged memories",
                "reason": reason
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _undo_sharing_set(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Undo sharing policy change by reverting to the original policy."""
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
                "error": "No original sharing policy found in original_state"
            }

        if not self.db_pool or not POSTGRES_AVAILABLE:
            return {
                "success": True,
                "message": f"Reverted sharing policy for memory {memory_id} (no-db mode)",
                "memory_id": memory_id,
                "original_policy": original_policy,
                "reason": reason,
                "no_db_mode": True,
            }

        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE shared_memory.documents
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{{}}'::jsonb),
                        '{{sharing}}',
                        $1::jsonb
                    )
                    WHERE id = $2
                """, _json.dumps(original_policy), memory_id)
            updated = result.split()[-1] if result else "0"
            if updated == "0":
                return {"success": False, "error": f"Memory {memory_id} not found"}
            return {
                "success": True,
                "message": f"Reverted sharing policy for memory {memory_id}",
                "memory_id": memory_id,
                "original_policy": original_policy,
                "reason": reason
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Redo
    # ------------------------------------------------------------------

    async def redo(
        self,
        agent_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Re-apply the most recently undone operation for an agent.

        Args:
            agent_id: Agent requesting the redo
            reason: Reason for the redo

        Returns:
            Result dictionary with status and details
        """
        # Find the most recent redo entry for this agent (last item in list is newest)
        entry = None
        for e in reversed(self.redo_history):
            if e.agent_id == agent_id:
                entry = e
                break

        if not entry:
            return {
                "success": False,
                "error": f"No redoable operations found for agent: {agent_id}"
            }

        try:
            result = await self._perform_redo(entry, agent_id, reason)

            if result["success"]:
                # Move back to undo_history as PENDING so it can be undone again
                self.redo_history.remove(entry)
                entry.status = UndoStatus.PENDING
                entry.error_message = None
                self.undo_history.append(entry)
                if len(self.undo_history) > self.max_history:
                    self.undo_history.pop(0)

                # Persist updated status
                if self.db_pool and POSTGRES_AVAILABLE:
                    await self._update_undo_entry(entry)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _perform_redo(
        self,
        entry: UndoEntry,
        agent_id: str,
        reason: Optional[str]
    ) -> Dict[str, Any]:
        """Re-apply the new_state captured in the undo entry."""
        op_type = entry.operation_type

        if op_type == UndoOperationType.MEMORY_ADD:
            # Redo add = re-insert the memory
            new_data = entry.new_state
            if not self.db_pool or not POSTGRES_AVAILABLE:
                return {
                    "success": True,
                    "message": "Re-added memory (no-db mode)",
                    "memory_id": new_data.get("memory_id") or new_data.get("id"),
                    "reason": reason,
                    "no_db_mode": True,
                }
            try:
                mem_id = new_data.get("memory_id") or new_data.get("id") or str(_uuid.uuid4())
                content = new_data.get("content", "")
                owner = new_data.get("agent_id", entry.agent_id)
                meta = new_data.get("metadata", {})
                created_at = datetime.now(UTC).replace(tzinfo=None)
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO shared_memory.documents
                            (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                    """, mem_id, "Re-added memory", content, owner, "general", [], meta, created_at)
                return {
                    "success": True,
                    "message": f"Re-added memory {mem_id} (redo of add operation)",
                    "memory_id": mem_id,
                    "reason": reason
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif op_type in (UndoOperationType.MEMORY_UPDATE, UndoOperationType.MEMORY_SUMMARIZE):
            # Redo update / summarize = apply new_state content
            memory_id = entry.memory_id
            if not memory_id:
                return {"success": False, "error": "No memory_id in redo entry"}
            new_content = entry.new_state.get("content") or entry.new_state.get("summarized_content")
            if not new_content:
                return {"success": False, "error": "No new content found in new_state"}
            if not self.db_pool or not POSTGRES_AVAILABLE:
                return {
                    "success": True,
                    "message": f"Re-applied update to memory {memory_id} (no-db mode)",
                    "memory_id": memory_id,
                    "reason": reason,
                    "no_db_mode": True,
                }
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE shared_memory.documents SET content = $2 WHERE id = $1",
                        memory_id, new_content
                    )
                return {
                    "success": True,
                    "message": f"Re-applied update to memory {memory_id}",
                    "memory_id": memory_id,
                    "reason": reason
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif op_type == UndoOperationType.MEMORY_DELETE:
            # Redo delete = delete again
            memory_id = entry.memory_id or entry.new_state.get("memory_id")
            if not memory_id:
                return {"success": False, "error": "No memory_id in redo entry"}
            if not self.db_pool or not POSTGRES_AVAILABLE:
                return {
                    "success": True,
                    "message": f"Re-deleted memory {memory_id} (no-db mode)",
                    "memory_id": memory_id,
                    "reason": reason,
                    "no_db_mode": True,
                }
            try:
                async with self.db_pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM shared_memory.documents WHERE id = $1",
                        memory_id
                    )
                return {
                    "success": True,
                    "message": f"Re-deleted memory {memory_id}",
                    "memory_id": memory_id,
                    "reason": reason
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif op_type == UndoOperationType.SHARING_SET:
            # Redo sharing = apply new_state policy
            memory_id = entry.memory_id
            if not memory_id:
                return {"success": False, "error": "No memory_id in redo entry"}
            new_policy = entry.new_state.get("sharing_policy")
            if not new_policy:
                return {"success": False, "error": "No new sharing policy in new_state"}
            if not self.db_pool or not POSTGRES_AVAILABLE:
                return {
                    "success": True,
                    "message": f"Re-applied sharing policy for memory {memory_id} (no-db mode)",
                    "memory_id": memory_id,
                    "new_policy": new_policy,
                    "reason": reason,
                    "no_db_mode": True,
                }
            try:
                async with self.db_pool.acquire() as conn:
                    result = await conn.execute("""
                        UPDATE shared_memory.documents
                        SET metadata = jsonb_set(
                            COALESCE(metadata, '{{}}'::jsonb),
                            '{{sharing}}',
                            $1::jsonb
                        )
                        WHERE id = $2
                    """, _json.dumps(new_policy), memory_id)
                updated = result.split()[-1] if result else "0"
                if updated == "0":
                    return {"success": False, "error": f"Memory {memory_id} not found"}
                return {
                    "success": True,
                    "message": f"Re-applied sharing policy for memory {memory_id}",
                    "memory_id": memory_id,
                    "reason": reason
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        else:
            return {
                "success": False,
                "error": f"Redo not supported for operation type: {op_type.value}"
            }

    # ------------------------------------------------------------------
    # Chain undo
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # History and maintenance
    # ------------------------------------------------------------------

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

    async def cleanup_expired_entries(self) -> None:
        """Remove expired undo entries from history and database."""
        now = datetime.now(timezone.utc)

        # Clean in-memory history
        self.undo_history = [
            e for e in self.undo_history
            if not e.expiration_date or e.expiration_date >= now
        ]

        # Clean database
        if self.db_pool and POSTGRES_AVAILABLE:
            await self._ensure_schema()
            try:
                async with self.db_pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM shared_memory.undo_log WHERE expiration_date < $1",
                        now
                    )
                    print(f"INFO: Cleaned up {result} expired undo entries")
            except Exception as e:
                print(f"ERROR: Failed to cleanup expired entries: {e}")


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

# Global undo manager instance
_undo_manager: Optional[UndoManager] = None


def get_undo_manager() -> Optional[UndoManager]:
    """Get the global undo manager instance."""
    return _undo_manager


def init_undo_manager(
    config_path: str = "automation_config.json",
    db_pool: Optional["asyncpg.Pool"] = None
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
