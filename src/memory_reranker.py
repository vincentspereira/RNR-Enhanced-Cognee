"""
Memory Reranker - Phase 12 (18.5)
====================================
Heuristic re-ranker that combines vector similarity, importance, recency, and
confidence into a single final_score for ordering search results.

Scoring formula:
    final_score = similarity * 0.50
                + importance * 0.25
                + recency    * 0.15
                + confidence * 0.10

All inputs and the output are clamped to [0.0, 1.0].

Recency uses the same formula as MemoryImportanceScorer:
    max(0.0, 1.0 - days_since_last_access / 365.0)

No external ML dependencies required.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

UTC = timezone.utc

# Component weights
_W_SIMILARITY = 0.50
_W_IMPORTANCE = 0.25
_W_RECENCY = 0.15
_W_CONFIDENCE = 0.10

_MAX_AGE_DAYS = 365.0


# ---------------------------------------------------------------------------
# Component helpers (module-level, stateless)
# ---------------------------------------------------------------------------

def _recency_from_timestamp(last_accessed_at: Optional[Any]) -> float:
    """Return a recency score in [0.0, 1.0] derived from a last-access timestamp."""
    if last_accessed_at is None:
        return 0.0
    try:
        if isinstance(last_accessed_at, str):
            last_accessed_at = datetime.fromisoformat(last_accessed_at)
        now = datetime.now(UTC)
        if last_accessed_at.tzinfo is None:
            last_accessed_at = last_accessed_at.replace(tzinfo=UTC)
        delta_days = (now - last_accessed_at).total_seconds() / 86400.0
        return max(0.0, 1.0 - delta_days / _MAX_AGE_DAYS)
    except Exception:
        return 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class MemoryReranker:
    """
    Re-rank a list of memory search results using a weighted heuristic formula.

    The postgres_pool parameter is accepted for API consistency with other
    modules in this package but is not used internally; all scoring is
    performed from fields already present on the result dicts.
    """

    def __init__(self, postgres_pool: Optional[Any] = None) -> None:
        self.pool = postgres_pool

    # ------------------------------------------------------------------
    # Core scoring
    # ------------------------------------------------------------------

    def _compute_final_score(
        self,
        similarity: float,
        importance: float,
        recency: float,
        confidence: float,
    ) -> float:
        """
        Combine four component scores into a single final score.

        All inputs should be in [0.0, 1.0]; the result is also clamped to
        that range.
        """
        raw = (
            _clamp(similarity) * _W_SIMILARITY
            + _clamp(importance) * _W_IMPORTANCE
            + _clamp(recency) * _W_RECENCY
            + _clamp(confidence) * _W_CONFIDENCE
        )
        return round(_clamp(raw), 6)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def rerank_search_results(
        self,
        results: List[Dict[str, Any]],
        query: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Re-rank *results* using the heuristic formula and return them sorted
        by final_score descending.

        Each dict in *results* may contain any of the following optional keys:
            similarity_score   float  - vector similarity from the search engine
            importance_score   float  - pre-computed importance (see MemoryImportanceScorer)
            last_accessed_at   any    - datetime or ISO string for recency
            confidence_score   float  - confidence level
            content            str    - memory content (not used in scoring, preserved)

        A "rerank_score" key is added to each result dict.

        The *query* parameter is accepted for API extensibility (e.g. future
        query-length or keyword-overlap bonuses) but is not used in the current
        heuristic implementation.
        """
        if not results:
            return results

        scored: List[Dict[str, Any]] = []
        for result in results:
            similarity = float(result.get("similarity_score") or 0.5)
            importance = float(result.get("importance_score") or 0.5)
            recency = _recency_from_timestamp(result.get("last_accessed_at"))
            confidence = float(result.get("confidence_score") or 0.5)

            final_score = self._compute_final_score(
                similarity, importance, recency, confidence
            )

            # Shallow copy so we don't mutate the caller's dicts
            enriched = dict(result)
            enriched["rerank_score"] = final_score
            scored.append(enriched)

        scored.sort(key=lambda r: r["rerank_score"], reverse=True)
        logger.debug(
            "rerank_search_results: ranked %d results; top score=%.4f",
            len(scored),
            scored[0]["rerank_score"] if scored else 0.0,
        )
        return scored


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_reranker: Optional[MemoryReranker] = None


def init_reranker(postgres_pool: Optional[Any] = None) -> MemoryReranker:
    """Create and store the global MemoryReranker singleton."""
    global _reranker
    _reranker = MemoryReranker(postgres_pool)
    logger.info("OK MemoryReranker initialized")
    return _reranker


def get_reranker() -> Optional[MemoryReranker]:
    """Return the global MemoryReranker singleton, or None if not initialised."""
    return _reranker
