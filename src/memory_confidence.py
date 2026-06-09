"""
Memory Confidence Scoring - Phase 10 (15.3)
=============================================
Assigns and maintains a confidence score (0.0 - 1.0) on every memory entry
to reflect how reliable or accurate the stored content is believed to be.

Confidence semantics:
    1.0  - Ground truth (manually verified, authoritative source)
    0.8+ - High confidence  (auto-extracted from reliable source)
    0.5+ - Medium confidence (inferred, translated, or summarised)
    0.3+ - Low confidence   (speculative, requires review)
    <0.3 - Uncertain        (candidate for review or deletion)

The score is stored in documents.confidence (NUMERIC 5,4) added by
migration 0002_memory_versioning.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple


# Multi-tenant helper -- routes Postgres reads/writes to the per-tenant
# table when a TenantContext is active. See src/multi_tenant.py.
def _t_docs() -> str:
    from src.multi_tenant import tenant_scoped_table
    return tenant_scoped_table("shared_memory.documents")


def _t_embeddings() -> str:
    from src.multi_tenant import tenant_scoped_table
    return tenant_scoped_table("shared_memory.embeddings")


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Confidence thresholds
# ---------------------------------------------------------------------------

CONFIDENCE_GROUND_TRUTH = 1.0
CONFIDENCE_HIGH = 0.8
CONFIDENCE_MEDIUM = 0.5
CONFIDENCE_LOW = 0.3
CONFIDENCE_UNCERTAIN = 0.0


def _label(score: float) -> str:
    if score >= CONFIDENCE_HIGH:
        return "high"
    if score >= CONFIDENCE_MEDIUM:
        return "medium"
    if score >= CONFIDENCE_LOW:
        return "low"
    return "uncertain"


class MemoryConfidenceManager:
    f"""
    Read and write confidence scores on {_t_docs()}.
    All methods degrade gracefully when the pool is unavailable.
    """

    def __init__(self, postgres_pool: Any) -> None:
        self.pool = postgres_pool

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def set_confidence(
        self,
        memory_id: str,
        score: float,
    ) -> bool:
        """
        Set the confidence score for a memory entry.
        Score must be in [0.0, 1.0].
        Returns True on success.
        """
        if not self.pool:
            return False

        score = max(0.0, min(1.0, float(score)))
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    f"""
                    UPDATE {_t_docs()}
                       SET confidence = $1, updated_at = NOW()
                     WHERE id = $2
                    """,
                    score,
                    memory_id,
                )
            updated = int(result.split()[-1]) if result else 0
            if updated:
                logger.debug(
                    "Set confidence %.4f on memory %s (%s)",
                    score, memory_id, _label(score),
                )
            return updated > 0
        except Exception as exc:
            logger.error("set_confidence failed for %s: %s", memory_id, exc)
            return False

    async def get_confidence(self, memory_id: str) -> Optional[float]:
        """
        Return the confidence score for a memory entry, or None if absent.
        """
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                val = await conn.fetchval(
                    f"SELECT confidence FROM {_t_docs()} WHERE id = $1",
                    memory_id,
                )
            return float(val) if val is not None else None
        except Exception as exc:
            logger.error("get_confidence failed for %s: %s", memory_id, exc)
            return None

    async def get_low_confidence_memories(
        self,
        threshold: float = CONFIDENCE_LOW,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Return memories whose confidence is below *threshold*.
        Optionally filtered by agent_id.  Results ordered by confidence ASC.
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                if agent_id:
                    rows = await conn.fetch(
                        f"""
                        SELECT id, content, agent_id, confidence, created_at
                          FROM {_t_docs()}
                         WHERE confidence < $1
                           AND agent_id = $2
                         ORDER BY confidence ASC
                         LIMIT $3
                        """,
                        threshold,
                        agent_id,
                        limit,
                    )
                else:
                    rows = await conn.fetch(
                        f"""
                        SELECT id, content, agent_id, confidence, created_at
                          FROM {_t_docs()}
                         WHERE confidence < $1
                         ORDER BY confidence ASC
                         LIMIT $2
                        """,
                        threshold,
                        limit,
                    )

            return [
                {
                    "id": r["id"],
                    "content_preview": r["content"][:120] + "..."
                    if len(r["content"]) > 120
                    else r["content"],
                    "agent_id": r["agent_id"],
                    "confidence": float(r["confidence"]) if r["confidence"] is not None else None,
                    "confidence_label": _label(float(r["confidence"])) if r["confidence"] is not None else "unknown",
                    "created_at": str(r["created_at"]),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.error("get_low_confidence_memories failed: %s", exc)
            return []

    async def get_confidence_report(
        self, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate confidence distribution across all (or one agent's) memories.
        """
        if not self.pool:
            return {"error": "pool unavailable"}

        agent_filter = "AND agent_id = $1" if agent_id else ""
        params: Tuple[Any, ...] = (agent_id,) if agent_id else ()

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT
                        COUNT(*)                                        AS total,
                        COUNT(*) FILTER (WHERE confidence >= {CONFIDENCE_HIGH})
                                                                        AS high_count,
                        COUNT(*) FILTER (WHERE confidence >= {CONFIDENCE_MEDIUM}
                                             AND confidence < {CONFIDENCE_HIGH})
                                                                        AS medium_count,
                        COUNT(*) FILTER (WHERE confidence >= {CONFIDENCE_LOW}
                                             AND confidence < {CONFIDENCE_MEDIUM})
                                                                        AS low_count,
                        COUNT(*) FILTER (WHERE confidence < {CONFIDENCE_LOW})
                                                                        AS uncertain_count,
                        COUNT(*) FILTER (WHERE confidence IS NULL)      AS unscored_count,
                        ROUND(AVG(confidence)::numeric, 4)              AS avg_confidence
                      FROM {_t_docs()}
                     WHERE 1=1 {agent_filter}
                    """,
                    *params,
                )

            row = rows[0] if rows else {}
            return {
                "agent_id": agent_id or "all",
                "total_memories": int(row.get("total", 0)),
                "high_confidence": int(row.get("high_count", 0)),
                "medium_confidence": int(row.get("medium_count", 0)),
                "low_confidence": int(row.get("low_count", 0)),
                "uncertain": int(row.get("uncertain_count", 0)),
                "unscored": int(row.get("unscored_count", 0)),
                "average_confidence": float(row["avg_confidence"])
                if row.get("avg_confidence") is not None
                else None,
                "thresholds": {
                    "high": CONFIDENCE_HIGH,
                    "medium": CONFIDENCE_MEDIUM,
                    "low": CONFIDENCE_LOW,
                },
            }
        except Exception as exc:
            logger.error("get_confidence_report failed: %s", exc)
            return {"error": str(exc)}

    async def bulk_set_confidence(
        self,
        scores: Dict[str, float],
    ) -> int:
        """
        Set confidence scores for multiple memories at once.
        *scores* maps memory_id -> score.
        Returns number of rows successfully updated.
        """
        if not self.pool or not scores:
            return 0

        updated = 0
        for mid, score in scores.items():
            if await self.set_confidence(mid, score):
                updated += 1
        return updated


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_confidence_manager: Optional[MemoryConfidenceManager] = None


def init_confidence_manager(postgres_pool: Any) -> MemoryConfidenceManager:
    global _confidence_manager
    _confidence_manager = MemoryConfidenceManager(postgres_pool)
    logger.info("OK MemoryConfidenceManager initialized")
    return _confidence_manager


def get_confidence_manager() -> Optional[MemoryConfidenceManager]:
    return _confidence_manager
