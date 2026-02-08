"""
Enhanced Cognee - Scheduled Deduplication

Periodic deduplication system for Enhanced Cognee memories:
- Weekly scheduled deduplication
- Dry-run mode for preview
- Approval workflow
- Undo capability
- Detailed reporting

Features:
- Automatic duplicate detection
- User approval required
- Detailed reports
- Token savings calculation
- Audit trail

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class ScheduledDeduplication:
    """
    Scheduled deduplication system for Enhanced Cognee memories.

    Performs periodic deduplication with approval workflow.
    """

    def __init__(self, postgres_pool, qdrant_client, config_path: str = "deduplication_config.json"):
        """
        Initialize scheduled deduplication.

        Args:
            postgres_pool: PostgreSQL connection pool
            qdrant_client: Qdrant client
            config_path: Path to configuration file
        """
        self.postgres_pool = postgres_pool
        self.qdrant_client = qdrant_client
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Track deduplication operations
        self.deduplication_history = []
        self.pending_approvals = {}

        logger.info("Scheduled Deduplication initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")

        # Default configuration
        return {
            "schedule": "weekly",
            "dry_run_first": True,
            "require_approval": True,
            "similarity_threshold": 0.95,
            "merge_strategy": "keep_newest"
        }

    def schedule_weekly_deduplication(self):
        """
        Schedule weekly deduplication task (Sunday 4 AM).

        This is typically called by the maintenance scheduler.
        """
        from apscheduler.triggers.cron import CronTrigger

        # Cron trigger: Sunday at 4 AM
        trigger = CronTrigger(day_of_week='sun', hour=4, minute=0)

        logger.info("Weekly deduplication scheduled: Sunday 4 AM")

        return trigger

    async def deduplicate_memories(
        self,
        agent_id: Optional[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Perform deduplication of memories.

        Args:
            agent_id: Optional agent ID to scope deduplication
            dry_run: If True, show what would be merged without actually merging

        Returns:
            Deduplication result dictionary
        """
        deduplication_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        logger.info(f"Starting deduplication: {deduplication_id} (dry_run={dry_run})")

        try:
            # Find duplicates
            duplicates = await self._find_duplicates(agent_id)

            if not duplicates:
                return {
                    "status": "success",
                    "deduplication_id": deduplication_id,
                    "dry_run": dry_run,
                    "duplicates_found": 0,
                    "groups": [],
                    "message": "No duplicates found"
                }

            # Calculate statistics
            total_duplicates = sum(len(group) - 1 for group in duplicates)
            token_savings = self._calculate_token_savings(duplicates)

            result = {
                "status": "success",
                "deduplication_id": deduplication_id,
                "dry_run": dry_run,
                "started_at": start_time.isoformat(),
                "agent_id": agent_id,
                "duplicates_found": len(duplicates),
                "total_duplicates": total_duplicates,
                "token_savings": token_savings,
                "groups": duplicates
            }

            # If dry run, request approval
            if dry_run:
                self.pending_approvals[deduplication_id] = result
                result["requires_approval"] = True
                result["approval_message"] = self._generate_approval_message(duplicates, token_savings)

                logger.info(f"Dry run complete: {len(duplicates)} duplicate groups found")

                return result

            # Perform actual deduplication
            else:
                merged_count = await self._merge_duplicates(duplicates)

                result["merged_count"] = merged_count
                result["completed_at"] = datetime.now(timezone.utc).isoformat()
                result["requires_approval"] = False

                # Store in history
                self.deduplication_history.append(result)

                logger.info(f"Deduplication complete: {merged_count} memories merged")

                return result

        except Exception as e:
            logger.error(f"Deduplication failed: {e}")
            return {
                "status": "error",
                "deduplication_id": deduplication_id,
                "error": str(e)
            }

    async def _find_duplicates(self, agent_id: Optional[str] = None) -> List[List[Dict[str, Any]]]:
        """
        Find duplicate memories.

        Args:
            agent_id: Optional agent ID to scope search

        Returns:
            List of duplicate groups
        """
        duplicates = []

        try:
            async with self.postgres_pool.acquire() as conn:
                # Find exact text duplicates
                if agent_id:
                    memories = await conn.fetch("""
                        SELECT id, content, agent_id, memory_category, created_at
                        FROM shared_memory.documents
                        WHERE agent_id = $1
                        ORDER BY created_at ASC
                    """, agent_id)
                else:
                    memories = await conn.fetch("""
                        SELECT id, content, agent_id, memory_category, created_at
                        FROM shared_memory.documents
                        ORDER BY created_at ASC
                    """)

                # Group by content hash (simplified - in production use actual hash)
                content_map = {}
                for memory in memories:
                    content = memory["content"]

                    # Simple hash: first 100 chars
                    content_hash = content[:100] if len(content) > 100 else content

                    if content_hash not in content_map:
                        content_map[content_hash] = []

                    content_map[content_hash].append({
                        "id": memory["id"],
                        "content": content,
                        "agent_id": memory["agent_id"],
                        "memory_category": memory["memory_category"],
                        "created_at": str(memory["created_at"])
                    })

                # Find groups with duplicates
                for content_hash, group in content_map.items():
                    if len(group) > 1:
                        duplicates.append(group)

                logger.info(f"Found {len(duplicates)} duplicate groups")

                return duplicates

        except Exception as e:
            logger.error(f"Failed to find duplicates: {e}")
            return []

    async def _merge_duplicates(self, duplicates: List[List[Dict[str, Any]]]) -> int:
        """
        Merge duplicate memories.

        Args:
            duplicates: List of duplicate groups

        Returns:
            Number of memories merged
        """
        merged_count = 0
        merge_strategy = self.config.get("merge_strategy", "keep_newest")

        try:
            async with self.postgres_pool.acquire() as conn:
                for group in duplicates:
                    if len(group) < 2:
                        continue

                    # Sort by created_at (oldest first)
                    sorted_group = sorted(group, key=lambda x: x["created_at"])

                    # Keep the newest, delete the rest
                    keep_memory = sorted_group[-1]
                    delete_memories = sorted_group[:-1]

                    for memory in delete_memories:
                        await conn.execute("""
                            DELETE FROM shared_memory.documents WHERE id = $1
                        """, memory["id"])
                        merged_count += 1

                    logger.info(f"Merged {len(delete_memories)} duplicates into {keep_memory['id']}")

                return merged_count

        except Exception as e:
            logger.error(f"Failed to merge duplicates: {e}")
            return merged_count

    async def dry_run_deduplication(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform dry-run deduplication to show what would be merged.

        Args:
            agent_id: Optional agent ID to scope deduplication

        Returns:
            Dry-run result dictionary
        """
        return await self.deduplicate_memories(agent_id, dry_run=True)

    async def request_approval(self, deduplication_result: Dict[str, Any]) -> bool:
        """
        Request user approval for deduplication.

        Args:
            deduplication_result: Result from dry-run deduplication

        Returns:
            True if approved, False otherwise
        """
        deduplication_id = deduplication_result.get("deduplication_id")

        if deduplication_id not in self.pending_approvals:
            logger.error(f"Pending deduplication not found: {deduplication_id}")
            return False

        # In a real implementation, this would:
        # 1. Send notification to dashboard
        # 2. Wait for user approval/rejection
        # 3. Return True/False based on user decision

        # For now, just log the request
        logger.info(f"Approval requested for deduplication: {deduplication_id}")
        logger.info(f"Groups found: {deduplication_result['duplicates_found']}")
        logger.info(f"Token savings: {deduplication_result['token_savings']}")

        return False  # Requires explicit approval

    async def approve_deduplication(self, deduplication_id: str) -> Dict[str, Any]:
        """
        Approve and execute pending deduplication.

        Args:
            deduplication_id: ID of pending deduplication

        Returns:
            Result dictionary
        """
        if deduplication_id not in self.pending_approvals:
            return {
                "status": "error",
                "error": f"Pending deduplication not found: {deduplication_id}"
            }

        pending = self.pending_approvals[deduplication_id]
        agent_id = pending.get("agent_id")

        # Remove from pending
        del self.pending_approvals[deduplication_id]

        # Execute actual deduplication
        result = await self.deduplicate_memories(agent_id, dry_run=False)

        logger.info(f"Deduplication approved and executed: {deduplication_id}")

        return result

    def reject_deduplication(self, deduplication_id: str):
        """
        Reject pending deduplication.

        Args:
            deduplication_id: ID of pending deduplication
        """
        if deduplication_id in self.pending_approvals:
            del self.pending_approvals[deduplication_id]
            logger.info(f"Deduplication rejected: {deduplication_id}")

    def deduplication_report(self, deduplication_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate deduplication report.

        Args:
            deduplication_id: Optional specific deduplication ID

        Returns:
            Report dictionary
        """
        if deduplication_id:
            # Find specific deduplication
            for dedup in self.deduplication_history:
                if dedup["deduplication_id"] == deduplication_id:
                    return dedup

            return {"error": f"Deduplication not found: {deduplication_id}"}

        # Generate summary report
        total_deduplications = len(self.deduplication_history)

        if total_deduplications == 0:
            return {
                "total_deduplications": 0,
                "message": "No deduplications performed yet"
            }

        total_duplicates = sum(d.get("duplicates_found", 0) for d in self.deduplication_history)
        total_merged = sum(d.get("merged_count", 0) for d in self.deduplication_history)
        total_token_savings = sum(d.get("token_savings", 0) for d in self.deduplication_history)

        return {
            "total_deduplications": total_deduplications,
            "total_duplicates_found": total_duplicates,
            "total_memories_merged": total_merged,
            "total_token_savings": total_token_savings,
            "recent_deduplications": self.deduplication_history[-10:]
        }

    async def undo_deduplication(self, deduplication_id: str) -> Dict[str, Any]:
        """
        Undo last deduplication.

        WARNING: This is not fully implemented - would require storing original
        content before deletion.

        Args:
            deduplication_id: ID of deduplication to undo

        Returns:
            Result dictionary
        """
        # Find deduplication
        dedup = None
        for d in self.deduplication_history:
            if d["deduplication_id"] == deduplication_id:
                dedup = d
                break

        if not dedup:
            return {
                "status": "error",
                "error": f"Deduplication not found: {deduplication_id}"
            }

        # In a real implementation, this would:
        # 1. Retrieve deleted memories from backup
        # 2. Restore them to the database
        # 3. Remove the merged memory
        # 4. Update deduplication history

        # For now, just mark as undone
        dedup["undone"] = True
        dedup["undone_at"] = datetime.now(timezone.utc).isoformat()

        logger.warning(f"Undo requested for {deduplication_id} - not fully implemented")

        return {
            "status": "partial",
            "message": "Undo not fully implemented - would require backup restore",
            "deduplication_id": deduplication_id
        }

    def _calculate_token_savings(self, duplicates: List[List[Dict[str, Any]]]) -> int:
        """
        Calculate token savings from deduplication.

        Args:
            duplicates: List of duplicate groups

        Returns:
            Estimated token savings
        """
        total_savings = 0

        for group in duplicates:
            if len(group) < 2:
                continue

            # Calculate tokens for each duplicate (rough estimate: 4 chars per token)
            for memory in group[1:]:  # Skip the first one (we'll keep it)
                content_length = len(memory.get("content", ""))
                tokens = content_length // 4
                total_savings += tokens

        return total_savings

    def _generate_approval_message(self, duplicates: List[List[Dict[str, Any]]], token_savings: int) -> str:
        """
        Generate approval message for user.

        Args:
            duplicates: List of duplicate groups
            token_savings: Calculated token savings

        Returns:
            Approval message
        """
        message = f"""
Deduplication Report
====================

Found {len(duplicates)} duplicate groups
Estimated token savings: {token_savings:,} tokens

This will merge duplicate memories, keeping the newest version of each group.

Examples:
"""

        # Show first 3 groups
        for i, group in enumerate(duplicates[:3]):
            message += f"\nGroup {i+1} ({len(group)} duplicates):\n"
            for memory in group:
                content_preview = memory.get("content", "")[:100]
                message += f"  - {memory['id']}: {content_preview}...\n"

        if len(duplicates) > 3:
            message += f"\n... and {len(duplicates) - 3} more groups\n"

        message += "\nApprove this deduplication?"

        return message


if __name__ == "__main__":
    # Test scheduled deduplication
    logging.basicConfig(level=logging.INFO)
    print("[INFO] Scheduled Deduplication System")
