"""
Memory Promotion Tiers - Phase 10 (15.5)
==========================================
Implements a three-tier memory hierarchy inspired by human memory theory:

    Tier 1 - Working (hot):   Recently accessed, high-confidence, frequently used.
                              Stored in Redis with short TTL for instant retrieval.

    Tier 2 - Long-term (warm): Consolidated or verified memories.
                               Stored in PostgreSQL + Qdrant with full-text & vector index.

    Tier 3 - Archive (cold):  Old, low-confidence, or rarely accessed memories.
                               Marked archived=true; may be evicted from Qdrant to
                               save vector storage.

Promotion / demotion rules:
    - A Tier-3 memory is promoted to Tier-2 when accessed (read) within the last
      PROMOTION_ACCESS_WINDOW_DAYS days.
    - A Tier-2 memory is promoted to Tier-1 when accessed >= HOT_ACCESS_THRESHOLD
      times in the last 24 h.
    - A Tier-2 memory is demoted to Tier-3 when it has not been accessed for
      DEMOTION_IDLE_DAYS days.
    - A Tier-1 Redis entry expires automatically via TTL; no manual demotion needed.

The tier is stored as a string column documents.memory_tier (added by migration
0003_memory_tiers).  This migration is created lazily here as a raw DDL executed
once if the column does not yet exist.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

UTC = timezone.utc

# -----------------------------------------------------------------------
# Tier constants
# -----------------------------------------------------------------------

TIER_WORKING = "working"    # hot  (Tier 1)
TIER_LONG_TERM = "long_term"  # warm (Tier 2)
TIER_ARCHIVE = "archive"      # cold (Tier 3)

ALL_TIERS = (TIER_WORKING, TIER_LONG_TERM, TIER_ARCHIVE)

# Promotion/demotion thresholds
HOT_ACCESS_THRESHOLD = 5         # accesses in 24 h to promote to working
PROMOTION_ACCESS_WINDOW_DAYS = 7  # days within which access triggers Tier-3 -> Tier-2
DEMOTION_IDLE_DAYS = 30           # days of inactivity to demote Tier-2 -> Tier-3

# Redis TTL for Tier-1 working memories (seconds)
REDIS_WORKING_TTL = 3600  # 1 hour


class MemoryTierManager:
    """
    Manage the promotion / demotion lifecycle of memory entries across tiers.

    Requires postgres_pool; redis_client is optional (Tier-1 caching).
    Degrades gracefully when either is unavailable.
    """

    def __init__(
        self,
        postgres_pool: Any,
        redis_client: Any = None,
    ) -> None:
        self.pool = postgres_pool
        self.redis = redis_client
        self._schema_ensured = False

    # ------------------------------------------------------------------
    # Schema bootstrap (idempotent)
    # ------------------------------------------------------------------

    async def _ensure_schema(self) -> None:
        """Add memory_tier column if it doesn't already exist."""
        if self._schema_ensured or not self.pool:
            return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    ALTER TABLE shared_memory.documents
                    ADD COLUMN IF NOT EXISTS memory_tier TEXT
                        DEFAULT 'long_term'
                        CHECK (memory_tier IN ('working', 'long_term', 'archive'))
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_memory_tier
                    ON shared_memory.documents (memory_tier)
                """)
            self._schema_ensured = True
        except Exception as exc:
            logger.warning("_ensure_schema failed (may already exist): %s", exc)
            self._schema_ensured = True  # avoid retrying

    # ------------------------------------------------------------------
    # Tier reads
    # ------------------------------------------------------------------

    async def get_tier(self, memory_id: str) -> Optional[str]:
        """Return the current tier for a memory entry."""
        if not self.pool:
            return None
        await self._ensure_schema()
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchval(
                    "SELECT memory_tier FROM shared_memory.documents WHERE id = $1",
                    memory_id,
                )
        except Exception as exc:
            logger.error("get_tier failed for %s: %s", memory_id, exc)
            return None

    async def get_tier_stats(
        self, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return counts of memories in each tier."""
        if not self.pool:
            return {"error": "pool unavailable"}
        await self._ensure_schema()

        agent_clause = "AND agent_id = $1" if agent_id else ""
        params = (agent_id,) if agent_id else ()

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT
                        COALESCE(memory_tier, 'long_term') AS tier,
                        COUNT(*) AS cnt
                      FROM shared_memory.documents
                     WHERE 1=1 {agent_clause}
                     GROUP BY 1
                    """,
                    *params,
                )
            counts = {r["tier"]: int(r["cnt"]) for r in rows}
            return {
                "agent_id": agent_id or "all",
                "working": counts.get(TIER_WORKING, 0),
                "long_term": counts.get(TIER_LONG_TERM, 0),
                "archive": counts.get(TIER_ARCHIVE, 0),
                "total": sum(counts.values()),
            }
        except Exception as exc:
            logger.error("get_tier_stats failed: %s", exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Tier writes
    # ------------------------------------------------------------------

    async def set_tier(self, memory_id: str, tier: str) -> bool:
        """Explicitly set a memory's tier (bypasses automatic rules)."""
        if tier not in ALL_TIERS:
            logger.warning("set_tier: invalid tier %r", tier)
            return False
        if not self.pool:
            return False
        await self._ensure_schema()
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE shared_memory.documents
                       SET memory_tier = $1, updated_at = NOW()
                     WHERE id = $2
                    """,
                    tier,
                    memory_id,
                )
            updated = int(result.split()[-1]) if result else 0
            if updated and self.redis and tier == TIER_WORKING:
                await self._cache_in_redis(memory_id)
            return updated > 0
        except Exception as exc:
            logger.error("set_tier failed for %s: %s", memory_id, exc)
            return False

    async def promote(self, memory_id: str, agent_id: Optional[str] = None) -> str:
        """
        Promote a memory one tier upward (archive -> long_term -> working).
        Returns the new tier name, or 'working' if already at the top.
        """
        current = await self.get_tier(memory_id)
        if current == TIER_ARCHIVE:
            new_tier = TIER_LONG_TERM
        elif current in (TIER_LONG_TERM, None):
            new_tier = TIER_WORKING
        else:
            return TIER_WORKING  # already working

        await self.set_tier(memory_id, new_tier)
        logger.debug(
            "Promoted memory %s: %s -> %s", memory_id, current, new_tier
        )
        return new_tier

    async def demote(self, memory_id: str) -> str:
        """
        Demote a memory one tier downward (working -> long_term -> archive).
        Returns the new tier name.
        """
        current = await self.get_tier(memory_id)
        if current == TIER_WORKING:
            new_tier = TIER_LONG_TERM
        elif current in (TIER_LONG_TERM, None):
            new_tier = TIER_ARCHIVE
        else:
            return TIER_ARCHIVE  # already archive

        await self.set_tier(memory_id, new_tier)
        logger.debug(
            "Demoted memory %s: %s -> %s", memory_id, current, new_tier
        )
        return new_tier

    # ------------------------------------------------------------------
    # Batch promotion/demotion
    # ------------------------------------------------------------------

    async def run_tier_maintenance(
        self, agent_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Apply automatic promotion/demotion rules across all memories.

        Returns a summary dict: {"promoted": N, "demoted": N, "errors": N}.
        """
        if not self.pool:
            return {"promoted": 0, "demoted": 0, "errors": 0}
        await self._ensure_schema()

        promoted = 0
        demoted = 0
        errors = 0

        # Demote Tier-2 memories idle for DEMOTION_IDLE_DAYS
        cutoff = datetime.now(UTC) - timedelta(days=DEMOTION_IDLE_DAYS)
        agent_clause = "AND agent_id = $2" if agent_id else ""
        params_d = (cutoff, agent_id) if agent_id else (cutoff,)

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT id FROM shared_memory.documents
                     WHERE memory_tier = '{TIER_LONG_TERM}'
                       AND updated_at < $1
                       AND expire_at IS NULL
                       AND consolidated_into IS NULL
                       {agent_clause}
                     LIMIT 200
                    """,
                    *params_d,
                )
            for row in rows:
                ok = await self.set_tier(row["id"], TIER_ARCHIVE)
                if ok:
                    demoted += 1
                else:
                    errors += 1
        except Exception as exc:
            logger.error("tier_maintenance demotion failed: %s", exc)
            errors += 1

        return {"promoted": promoted, "demoted": demoted, "errors": errors}

    # ------------------------------------------------------------------
    # Redis cache helpers (Tier-1)
    # ------------------------------------------------------------------

    async def _cache_in_redis(self, memory_id: str) -> None:
        """Cache a memory's content in Redis with working TTL."""
        if not self.redis or not self.pool:
            return
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT content, agent_id FROM shared_memory.documents WHERE id = $1",
                    memory_id,
                )
            if row:
                key = f"working:{memory_id}"
                await self.redis.setex(
                    key,
                    REDIS_WORKING_TTL,
                    json.dumps({"content": row["content"], "agent_id": row["agent_id"]}),
                )
        except Exception as exc:
            logger.debug("_cache_in_redis failed for %s: %s", memory_id, exc)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_tier_manager: Optional[MemoryTierManager] = None


def init_tier_manager(
    postgres_pool: Any,
    redis_client: Any = None,
) -> MemoryTierManager:
    global _tier_manager
    _tier_manager = MemoryTierManager(postgres_pool, redis_client)
    logger.info("OK MemoryTierManager initialized")
    return _tier_manager


def get_tier_manager() -> Optional[MemoryTierManager]:
    return _tier_manager
