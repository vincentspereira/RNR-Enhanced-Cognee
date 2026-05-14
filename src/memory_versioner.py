"""
Memory Versioner - Phase 10 (15.1)
====================================
Tracks every content-changing write to shared_memory.documents as an
immutable version row so the full edit history can be replayed or reverted.

Schema (created by Alembic migration 0002_memory_versioning):

    shared_memory.memory_versions
    ├── id              BIGSERIAL PRIMARY KEY
    ├── memory_id       TEXT  NOT NULL  REFERENCES documents(id) ON DELETE CASCADE
    ├── version_number  INTEGER NOT NULL  (starts at 1, monotonically increasing)
    ├── content         TEXT  NOT NULL  (snapshot of documents.content at that point)
    ├── agent_id        TEXT
    ├── change_reason   TEXT            (optional free-text explanation)
    ├── metadata        JSONB
    └── created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

Usage:
    versioner = MemoryVersioner(postgres_pool)
    vid = await versioner.snapshot(memory_id, new_content, agent_id, reason)
    history = await versioner.get_history(memory_id, limit=20)
    ok = await versioner.revert(memory_id, version_number)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

UTC = timezone.utc

# ---------------------------------------------------------------------------
# MemoryVersioner
# ---------------------------------------------------------------------------

class MemoryVersioner:
    """
    Write-once version ledger for Enhanced Cognee memory entries.

    Every time a memory's content changes the caller must invoke
    snapshot() BEFORE applying the update so the old content is
    preserved.  On revert(), documents.content is restored from the
    chosen version row.
    """

    def __init__(self, postgres_pool: Any) -> None:
        self.pool = postgres_pool

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def snapshot(
        self,
        memory_id: str,
        content: str,
        agent_id: Optional[str] = None,
        change_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Record a snapshot of *content* as the next version for memory_id.

        Returns the new version_number, or None when the pool is unavailable.
        """
        if not self.pool:
            logger.warning("MemoryVersioner.snapshot: postgres_pool is None")
            return None

        try:
            async with self.pool.acquire() as conn:
                # Determine next version number
                last_ver = await conn.fetchval(
                    """
                    SELECT COALESCE(MAX(version_number), 0)
                      FROM shared_memory.memory_versions
                     WHERE memory_id = $1
                    """,
                    memory_id,
                )
                next_ver = last_ver + 1
                meta_json = json.dumps(metadata) if metadata else None

                await conn.execute(
                    """
                    INSERT INTO shared_memory.memory_versions
                           (memory_id, version_number, content, agent_id,
                            change_reason, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW())
                    """,
                    memory_id,
                    next_ver,
                    content,
                    agent_id,
                    change_reason,
                    meta_json,
                )
                logger.debug(
                    "Snapshotted memory %s as version %d", memory_id, next_ver
                )
                return next_ver

        except Exception as exc:
            logger.error("snapshot failed for memory %s: %s", memory_id, exc)
            return None

    async def get_history(
        self,
        memory_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Return up to *limit* version rows for memory_id, newest first.
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, memory_id, version_number, content,
                           agent_id, change_reason, metadata, created_at
                      FROM shared_memory.memory_versions
                     WHERE memory_id = $1
                     ORDER BY version_number DESC
                     LIMIT $2
                    """,
                    memory_id,
                    limit,
                )

            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "memory_id": row["memory_id"],
                    "version_number": row["version_number"],
                    "content": row["content"],
                    "agent_id": row["agent_id"],
                    "change_reason": row["change_reason"],
                    "metadata": row["metadata"],
                    "created_at": str(row["created_at"]),
                })
            return result

        except Exception as exc:
            logger.error("get_history failed for memory %s: %s", memory_id, exc)
            return []

    async def revert(
        self,
        memory_id: str,
        version_number: int,
        agent_id: Optional[str] = None,
    ) -> bool:
        """
        Revert documents.content to the content recorded in *version_number*.

        Also snapshots the current content first so the revert itself is
        tracked in the version ledger.

        Returns True on success, False on any error.
        """
        if not self.pool:
            logger.warning("MemoryVersioner.revert: postgres_pool is None")
            return False

        try:
            async with self.pool.acquire() as conn:
                # Fetch target version content
                target_row = await conn.fetchrow(
                    """
                    SELECT content FROM shared_memory.memory_versions
                     WHERE memory_id = $1 AND version_number = $2
                    """,
                    memory_id,
                    version_number,
                )
                if not target_row:
                    logger.warning(
                        "revert: version %d not found for memory %s",
                        version_number, memory_id,
                    )
                    return False

                # Snapshot current state before overwriting
                current_content = await conn.fetchval(
                    "SELECT content FROM shared_memory.documents WHERE id = $1",
                    memory_id,
                )
                if current_content is None:
                    logger.warning(
                        "revert: memory %s not found in documents", memory_id
                    )
                    return False

            # Snapshot the current content (before revert)
            await self.snapshot(
                memory_id,
                current_content,
                agent_id=agent_id,
                change_reason=f"pre-revert snapshot (reverting to v{version_number})",
            )

            # Apply revert
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE shared_memory.documents
                       SET content = $1, updated_at = NOW()
                     WHERE id = $2
                    """,
                    target_row["content"],
                    memory_id,
                )

            # Snapshot the reverted state
            await self.snapshot(
                memory_id,
                target_row["content"],
                agent_id=agent_id,
                change_reason=f"reverted to version {version_number}",
            )

            updated = int(result.split()[-1]) if result else 0
            if updated == 0:
                logger.warning(
                    "revert: UPDATE matched 0 rows for memory %s", memory_id
                )
                return False

            logger.info(
                "Reverted memory %s to version %d", memory_id, version_number
            )
            return True

        except Exception as exc:
            logger.error(
                "revert failed for memory %s v%d: %s", memory_id, version_number, exc
            )
            return False

    async def get_version_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Return summary statistics about the version ledger.
        Optionally scoped to a specific agent.
        """
        if not self.pool:
            return {"error": "pool unavailable"}

        try:
            async with self.pool.acquire() as conn:
                if agent_id:
                    total = await conn.fetchval(
                        "SELECT COUNT(*) FROM shared_memory.memory_versions WHERE agent_id = $1",
                        agent_id,
                    )
                    memories_with_versions = await conn.fetchval(
                        "SELECT COUNT(DISTINCT memory_id) FROM shared_memory.memory_versions WHERE agent_id = $1",
                        agent_id,
                    )
                else:
                    total = await conn.fetchval(
                        "SELECT COUNT(*) FROM shared_memory.memory_versions"
                    )
                    memories_with_versions = await conn.fetchval(
                        "SELECT COUNT(DISTINCT memory_id) FROM shared_memory.memory_versions"
                    )

                most_revised = await conn.fetchrow(
                    """
                    SELECT memory_id, COUNT(*) AS revisions
                      FROM shared_memory.memory_versions
                     GROUP BY memory_id
                     ORDER BY revisions DESC
                     LIMIT 1
                    """
                )

            stats = {
                "total_version_rows": int(total),
                "memories_with_versions": int(memories_with_versions),
            }
            if most_revised:
                stats["most_revised_memory_id"] = most_revised["memory_id"]
                stats["most_revised_count"] = int(most_revised["revisions"])
            return stats

        except Exception as exc:
            logger.error("get_version_stats failed: %s", exc)
            return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_memory_versioner: Optional[MemoryVersioner] = None


def init_memory_versioner(postgres_pool: Any) -> MemoryVersioner:
    """Initialise the module-level MemoryVersioner singleton."""
    global _memory_versioner
    _memory_versioner = MemoryVersioner(postgres_pool)
    logger.info("OK MemoryVersioner initialized")
    return _memory_versioner


def get_memory_versioner() -> Optional[MemoryVersioner]:
    """Return the module-level singleton (may be None if not yet initialised)."""
    return _memory_versioner
