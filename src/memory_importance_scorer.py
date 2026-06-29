"""
Memory Importance Scorer - Phase 12 (18.4)
=============================================
Assigns a heuristic importance score (0.0 - 1.0) to every memory entry
without requiring any external ML dependencies.

Scoring formula:
    score = access_count * 0.4
          + recency      * 0.3
          + confidence   * 0.2
          + source_type  * 0.1

Component derivations:
    access_count  = min(1.0, raw_access_count / 50.0)
    recency       = max(0.0, 1.0 - days_since_last_access / 365.0)
    confidence    = clamp(raw_confidence, 0.0, 1.0)
    source_type   = lookup from SOURCE_TYPE_WEIGHTS, default 0.5

The computed score is stored in an importance_score FLOAT column that this
module adds (ADD COLUMN IF NOT EXISTS) to shared_memory.documents the first
time update_importance_scores is called.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Multi-tenant helper -- routes Postgres reads/writes to the per-tenant
# table when a TenantContext is active. See src/multi_tenant.py.
def _t_docs() -> str:
    from src.multi_tenant import tenant_scoped_table
    return tenant_scoped_table("shared_memory.documents")


def _t_embeddings() -> str:
    from src.multi_tenant import tenant_scoped_table
    return tenant_scoped_table("shared_memory.embeddings")


logger = logging.getLogger(__name__)

UTC = timezone.utc

# Component weights
_W_ACCESS = 0.4
_W_RECENCY = 0.3
_W_CONFIDENCE = 0.2
_W_SOURCE = 0.1

# Source-type bonus table
SOURCE_TYPE_WEIGHTS: Dict[str, float] = {
    "verified": 1.0,
    "agent": 0.8,
    "user": 0.7,
    "system": 0.5,
    "unknown": 0.3,
}

# Normalisation constants
_MAX_ACCESS_COUNT = 50.0
_MAX_AGE_DAYS = 365.0


def _component_access(raw_count: int) -> float:
    return min(1.0, raw_count / _MAX_ACCESS_COUNT)


def _component_recency(last_accessed_at: Optional[Any]) -> float:
    if last_accessed_at is None:
        return 0.0
    try:
        if isinstance(last_accessed_at, str):
            # Handle both offset-aware and naive ISO strings
            last_accessed_at = datetime.fromisoformat(last_accessed_at)
        now = datetime.now(UTC)
        # Make naive datetimes UTC-aware for comparison
        if last_accessed_at.tzinfo is None:
            last_accessed_at = last_accessed_at.replace(tzinfo=UTC)
        delta_days = (now - last_accessed_at).total_seconds() / 86400.0
        return float(max(0.0, 1.0 - delta_days / _MAX_AGE_DAYS))
    except Exception:
        return 0.0


def _component_confidence(raw_confidence: Optional[float]) -> float:
    if raw_confidence is None:
        return 0.5  # neutral default
    return max(0.0, min(1.0, float(raw_confidence)))


def _component_source_type(source_type: Optional[str]) -> float:
    if not source_type:
        return SOURCE_TYPE_WEIGHTS["unknown"]
    return SOURCE_TYPE_WEIGHTS.get(str(source_type).lower(), 0.5)


class MemoryImportanceScorer:
    """
    Heuristic importance scoring for RNR Enhanced Cognee memory entries.

    All methods degrade gracefully when the pool is unavailable.
    """

    def __init__(self, postgres_pool: Optional[Any] = None) -> None:
        self.pool = postgres_pool

    # ------------------------------------------------------------------
    # Core scoring logic
    # ------------------------------------------------------------------

    def _score_memory(self, memory: Dict[str, Any]) -> float:
        """
        Compute an importance score in [0.0, 1.0] from a memory dict.

        Expected keys (all optional, use sensible defaults if absent):
            access_count       int
            last_accessed_at   datetime | ISO str | None
            confidence_score   float | None
            metadata           dict | None  (checked for "source_type" key)
        """
        raw_access = int(memory.get("access_count") or 0)
        access = _component_access(raw_access)

        recency = _component_recency(memory.get("last_accessed_at"))

        confidence = _component_confidence(memory.get("confidence_score"))

        # source_type may be a top-level key or nested in metadata
        source_type = memory.get("source_type")
        if source_type is None:
            meta = memory.get("metadata") or {}
            if isinstance(meta, dict):
                source_type = meta.get("source_type")

        source = _component_source_type(source_type)

        score = (
            access * _W_ACCESS
            + recency * _W_RECENCY
            + confidence * _W_CONFIDENCE
            + source * _W_SOURCE
        )
        return round(max(0.0, min(1.0, score)), 6)

    def _breakdown(self, memory: Dict[str, Any]) -> Dict[str, float]:
        """Return per-component contribution values (before weighting)."""
        return {
            "access": _component_access(int(memory.get("access_count") or 0)),
            "recency": _component_recency(memory.get("last_accessed_at")),
            "confidence": _component_confidence(memory.get("confidence_score")),
            "source_type": _component_source_type(
                memory.get("source_type")
                or (
                    (memory.get("metadata") or {}).get("source_type")
                    if isinstance(memory.get("metadata"), dict)
                    else None
                )
            ),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_memory_importance(self, memory_id: str) -> Dict[str, Any]:
        """
        Fetch a single memory from PostgreSQL and compute its importance score.

        Returns a dict with keys: memory_id, importance_score, breakdown.
        Falls back to importance_score=0.5 when the pool is unavailable.
        """
        if not self.pool:
            return {
                "memory_id": memory_id,
                "importance_score": 0.5,
                "breakdown": {
                    "access": 0.0,
                    "recency": 0.0,
                    "confidence": 0.5,
                    "source_type": 0.5,
                },
                "note": "pool unavailable - returned neutral defaults",
            }

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"""
                    SELECT id,
                           content,
                           access_count,
                           last_accessed_at,
                           confidence_score,
                           metadata
                      FROM {_t_docs()}
                     WHERE id = $1
                    """,
                    memory_id,
                )
        except Exception as exc:
            logger.error("get_memory_importance fetch failed for %s: %s", memory_id, exc)
            return {
                "memory_id": memory_id,
                "importance_score": 0.5,
                "breakdown": {},
                "error": str(exc),
            }

        if row is None:
            return {
                "memory_id": memory_id,
                "importance_score": 0.0,
                "breakdown": {},
                "note": "memory not found",
            }

        memory = dict(row)
        score = self._score_memory(memory)
        breakdown = self._breakdown(memory)

        return {
            "memory_id": memory_id,
            "importance_score": score,
            "breakdown": breakdown,
        }

    async def update_importance_scores(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Fetch up to *limit* memories, score each, and UPSERT importance_score.

        Adds the importance_score column to documents if it does not exist yet.
        Optionally filters to a single agent_id.

        Returns {"updated": int, "mean_score": float}.
        """
        if not self.pool:
            logger.warning("update_importance_scores: pool unavailable")
            return {"updated": 0, "mean_score": 0.0}

        try:
            async with self.pool.acquire() as conn:
                # Ensure the column exists (idempotent)
                await conn.execute(
                    f"""
                    ALTER TABLE {_t_docs()}
                        ADD COLUMN IF NOT EXISTS importance_score FLOAT DEFAULT 0.5
                    """
                )

                if agent_id:
                    rows = await conn.fetch(
                        f"""
                        SELECT id,
                               access_count,
                               last_accessed_at,
                               confidence_score,
                               metadata
                          FROM {_t_docs()}
                         WHERE agent_id = $1
                         LIMIT $2
                        """,
                        agent_id,
                        limit,
                    )
                else:
                    rows = await conn.fetch(
                        f"""
                        SELECT id,
                               access_count,
                               last_accessed_at,
                               confidence_score,
                               metadata
                          FROM {_t_docs()}
                         LIMIT $1
                        """,
                        limit,
                    )

                updated = 0
                total_score = 0.0

                for row in rows:
                    memory = dict(row)
                    score = self._score_memory(memory)
                    await conn.execute(
                        f"""
                        UPDATE {_t_docs()}
                           SET importance_score = $1,
                               updated_at = NOW()
                         WHERE id = $2
                        """,
                        score,
                        str(row["id"]),
                    )
                    total_score += score
                    updated += 1

            mean_score = round(total_score / updated, 6) if updated else 0.0
            logger.info(
                "OK update_importance_scores: updated=%d mean_score=%.4f agent=%s",
                updated,
                mean_score,
                agent_id or "all",
            )
            return {"updated": updated, "mean_score": mean_score}

        except Exception as exc:
            logger.error("update_importance_scores failed: %s", exc)
            return {"updated": 0, "mean_score": 0.0, "error": str(exc)}

    async def get_top_important_memories(
        self,
        agent_id: Optional[str] = None,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Return the top *top_n* memories ordered by importance_score descending.

        NULLs are pushed to the bottom (NULLS LAST).
        Optionally filters to a single agent_id.
        """
        if not self.pool:
            logger.warning("get_top_important_memories: pool unavailable")
            return []

        try:
            async with self.pool.acquire() as conn:
                if agent_id:
                    rows = await conn.fetch(
                        f"""
                        SELECT id,
                               agent_id,
                               content,
                               importance_score,
                               confidence_score,
                               access_count,
                               last_accessed_at,
                               created_at
                          FROM {_t_docs()}
                         WHERE agent_id = $1
                         ORDER BY importance_score DESC NULLS LAST
                         LIMIT $2
                        """,
                        agent_id,
                        top_n,
                    )
                else:
                    rows = await conn.fetch(
                        f"""
                        SELECT id,
                               agent_id,
                               content,
                               importance_score,
                               confidence_score,
                               access_count,
                               last_accessed_at,
                               created_at
                          FROM {_t_docs()}
                         ORDER BY importance_score DESC NULLS LAST
                         LIMIT $1
                        """,
                        top_n,
                    )

            return [
                {
                    "id": str(r["id"]),
                    "agent_id": r["agent_id"],
                    "content_preview": (
                        r["content"][:120] + "..."
                        if r["content"] and len(r["content"]) > 120
                        else (r["content"] or "")
                    ),
                    "importance_score": float(r["importance_score"])
                    if r["importance_score"] is not None
                    else None,
                    "confidence_score": float(r["confidence_score"])
                    if r["confidence_score"] is not None
                    else None,
                    "access_count": int(r["access_count"]) if r["access_count"] is not None else 0,
                    "last_accessed_at": str(r["last_accessed_at"]) if r["last_accessed_at"] else None,
                    "created_at": str(r["created_at"]) if r["created_at"] else None,
                }
                for r in rows
            ]

        except Exception as exc:
            logger.error("get_top_important_memories failed: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_importance_scorer: Optional[MemoryImportanceScorer] = None


def init_importance_scorer(postgres_pool: Optional[Any] = None) -> MemoryImportanceScorer:
    """Create and store the global MemoryImportanceScorer singleton."""
    global _importance_scorer
    _importance_scorer = MemoryImportanceScorer(postgres_pool)
    logger.info("OK MemoryImportanceScorer initialized")
    return _importance_scorer


def get_importance_scorer() -> Optional[MemoryImportanceScorer]:
    """Return the global MemoryImportanceScorer singleton, or None if not initialised."""
    return _importance_scorer
