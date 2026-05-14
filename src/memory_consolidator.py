"""
Memory Consolidator - Phase 10 (15.4)
========================================
Identifies clusters of related, overlapping, or redundant memories and
merges them into a single authoritative entry.  The constituent entries
are marked consolidated_into pointing at the surviving document.

Unlike deduplication (which removes near-identical text), consolidation
targets *semantically related* memories: partial answers that together
form a complete picture.

Algorithm overview:
    1. Candidate detection: find memories with high Qdrant cosine similarity
       (above a configurable threshold, default 0.75) that are NOT already
       marked as duplicates.
    2. Merge: concatenate content of candidates, label the result with
       consolidation metadata, write a new document row.
    3. Mark: set consolidated_into = <new_id> on each source row.

This module does NOT call an LLM by default -- it performs mechanical
concatenation.  An optional summarisation step can be wired in via the
IntelligentSummarization class when an LLM client is available.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

UTC = timezone.utc

# Default similarity threshold for consolidation candidates
DEFAULT_SIMILARITY_THRESHOLD = 0.75
# Maximum number of candidates per consolidation run
MAX_CANDIDATES_PER_RUN = 200


class MemoryConsolidator:
    """
    Detect and merge semantically related memory entries.

    Requires both postgres_pool (for CRUD) and qdrant_client (for vector
    similarity search).  Degrades gracefully when either is unavailable.
    """

    def __init__(
        self,
        postgres_pool: Any,
        qdrant_client: Any = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        collection_name: str = "memories",
    ) -> None:
        self.pool = postgres_pool
        self.qdrant = qdrant_client
        self.similarity_threshold = similarity_threshold
        self.collection_name = collection_name

    # ------------------------------------------------------------------
    # Candidate detection
    # ------------------------------------------------------------------

    async def find_candidates(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Return groups of memory IDs that are candidates for consolidation.

        Each element of the returned list is a dict::

            {
                "anchor_id":    "<memory id>",
                "anchor_preview": "<first 100 chars>",
                "candidates": [
                    {"id": "...", "similarity": 0.82, "preview": "..."},
                    ...
                ]
            }

        When Qdrant is unavailable, falls back to a simple keyword-overlap
        heuristic using PostgreSQL full-text search.
        """
        if not self.pool:
            return []

        if self.qdrant:
            return await self._candidates_via_qdrant(agent_id, limit)
        return await self._candidates_via_postgres(agent_id, limit)

    async def _candidates_via_qdrant(
        self, agent_id: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Vector-similarity based candidate detection."""
        try:
            async with self.pool.acquire() as conn:
                if agent_id:
                    anchors = await conn.fetch(
                        """
                        SELECT id, content
                          FROM shared_memory.documents
                         WHERE agent_id = $1
                           AND consolidated_into IS NULL
                           AND expire_at IS NULL
                         ORDER BY created_at DESC
                         LIMIT $2
                        """,
                        agent_id,
                        limit,
                    )
                else:
                    anchors = await conn.fetch(
                        """
                        SELECT id, content
                          FROM shared_memory.documents
                         WHERE consolidated_into IS NULL
                           AND expire_at IS NULL
                         ORDER BY created_at DESC
                         LIMIT $1
                        """,
                        limit,
                    )

            groups: List[Dict[str, Any]] = []
            seen: set = set()

            for anchor in anchors:
                anchor_id = anchor["id"]
                if anchor_id in seen:
                    continue

                try:
                    hits = self.qdrant.search(
                        collection_name=self.collection_name,
                        query_vector=[0.0],  # placeholder; real usage needs embedding
                        limit=5,
                        score_threshold=self.similarity_threshold,
                        query_filter={
                            "must": [{"key": "doc_id", "match": {"value": anchor_id}}]
                        },
                    )
                except Exception:
                    hits = []

                candidates = []
                for hit in hits:
                    hit_id = hit.payload.get("doc_id") if hasattr(hit, "payload") else None
                    if hit_id and hit_id != anchor_id and hit_id not in seen:
                        candidates.append({
                            "id": hit_id,
                            "similarity": round(hit.score, 4),
                            "preview": "",
                        })

                if candidates:
                    seen.add(anchor_id)
                    for c in candidates:
                        seen.add(c["id"])
                    groups.append({
                        "anchor_id": anchor_id,
                        "anchor_preview": anchor["content"][:100],
                        "candidates": candidates,
                    })

            return groups

        except Exception as exc:
            logger.error("_candidates_via_qdrant failed: %s", exc)
            return []

    async def _candidates_via_postgres(
        self, agent_id: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback: use trigram similarity (pg_trgm) or LIKE-based grouping
        when Qdrant is unavailable.
        """
        try:
            async with self.pool.acquire() as conn:
                if agent_id:
                    rows = await conn.fetch(
                        """
                        SELECT a.id AS aid, a.content AS acontent,
                               b.id AS bid, b.content AS bcontent
                          FROM shared_memory.documents a
                          JOIN shared_memory.documents b
                            ON a.id < b.id
                           AND a.agent_id = b.agent_id
                           AND similarity(a.content, b.content) > $1
                         WHERE a.agent_id = $2
                           AND a.consolidated_into IS NULL
                           AND b.consolidated_into IS NULL
                         LIMIT $3
                        """,
                        self.similarity_threshold,
                        agent_id,
                        limit,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT a.id AS aid, a.content AS acontent,
                               b.id AS bid, b.content AS bcontent
                          FROM shared_memory.documents a
                          JOIN shared_memory.documents b
                            ON a.id < b.id
                           AND a.agent_id = b.agent_id
                           AND similarity(a.content, b.content) > $1
                         WHERE a.consolidated_into IS NULL
                           AND b.consolidated_into IS NULL
                         LIMIT $2
                        """,
                        self.similarity_threshold,
                        limit,
                    )

            groups: Dict[str, Dict] = {}
            for row in rows:
                aid, bid = row["aid"], row["bid"]
                if aid not in groups:
                    groups[aid] = {
                        "anchor_id": aid,
                        "anchor_preview": row["acontent"][:100],
                        "candidates": [],
                    }
                groups[aid]["candidates"].append({
                    "id": bid,
                    "similarity": None,
                    "preview": row["bcontent"][:100],
                })

            return list(groups.values())

        except Exception as exc:
            # pg_trgm extension may not be installed — return empty
            logger.warning("_candidates_via_postgres failed (pg_trgm?): %s", exc)
            return []

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    async def consolidate(
        self,
        memory_ids: List[str],
        agent_id: Optional[str] = None,
        summary_content: Optional[str] = None,
    ) -> Optional[str]:
        """
        Merge a list of memories into one consolidated entry.

        If *summary_content* is provided it is used as the consolidated
        content; otherwise the contents are concatenated with separators.

        Returns the new memory_id (UUID) on success, or None on failure.
        """
        if not self.pool or not memory_ids:
            return None

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, content, agent_id, metadata
                      FROM shared_memory.documents
                     WHERE id = ANY($1::text[])
                       AND consolidated_into IS NULL
                    """,
                    memory_ids,
                )

            if not rows:
                logger.warning("consolidate: no unconsolidated rows found")
                return None

            # Build consolidated content
            if summary_content:
                merged_content = summary_content
            else:
                parts = [f"[Memory {r['id']}]\n{r['content']}" for r in rows]
                merged_content = "\n\n---\n\n".join(parts)

            effective_agent_id = agent_id or (rows[0]["agent_id"] if rows else None)
            new_id = str(uuid.uuid4())
            prov = json.dumps({
                "source": "consolidation",
                "author": effective_agent_id or "system",
                "ingested_at": datetime.now(UTC).isoformat(),
                "consolidated_from": [r["id"] for r in rows],
                "verified": False,
            })

            async with self.pool.acquire() as conn:
                # Insert consolidated document
                await conn.execute(
                    """
                    INSERT INTO shared_memory.documents
                           (id, content, agent_id, provenance,
                            confidence, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4::jsonb, 1.0, $5::jsonb, NOW(), NOW())
                    """,
                    new_id,
                    merged_content,
                    effective_agent_id,
                    prov,
                    json.dumps({"consolidated": True, "source_count": len(rows)}),
                )

                # Mark sources as consolidated
                await conn.execute(
                    """
                    UPDATE shared_memory.documents
                       SET consolidated_into = $1,
                           consolidation_score = $2,
                           updated_at = NOW()
                     WHERE id = ANY($3::text[])
                    """,
                    new_id,
                    self.similarity_threshold,
                    [r["id"] for r in rows],
                )

            logger.info(
                "Consolidated %d memories into %s", len(rows), new_id
            )
            return new_id

        except Exception as exc:
            logger.error("consolidate failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def get_consolidation_report(
        self, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Return statistics about consolidation activity.
        """
        if not self.pool:
            return {"error": "pool unavailable"}

        agent_clause = "AND agent_id = $1" if agent_id else ""
        params: Tuple = (agent_id,) if agent_id else ()

        try:
            async with self.pool.acquire() as conn:
                total = await conn.fetchval(
                    f"""
                    SELECT COUNT(*)
                      FROM shared_memory.documents
                     WHERE 1=1 {agent_clause}
                    """,
                    *params,
                )
                consolidated_out = await conn.fetchval(
                    f"""
                    SELECT COUNT(*)
                      FROM shared_memory.documents
                     WHERE consolidated_into IS NOT NULL {agent_clause}
                    """,
                    *params,
                )
                consolidation_targets = await conn.fetchval(
                    f"""
                    SELECT COUNT(DISTINCT consolidated_into)
                      FROM shared_memory.documents
                     WHERE consolidated_into IS NOT NULL {agent_clause}
                    """,
                    *params,
                )

            return {
                "agent_id": agent_id or "all",
                "total_memories": int(total),
                "consolidated_out": int(consolidated_out),
                "consolidation_targets": int(consolidation_targets),
                "active_memories": int(total) - int(consolidated_out),
                "consolidation_ratio": round(
                    int(consolidated_out) / max(int(total), 1), 4
                ),
            }
        except Exception as exc:
            logger.error("get_consolidation_report failed: %s", exc)
            return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_consolidator: Optional[MemoryConsolidator] = None


def init_consolidator(
    postgres_pool: Any,
    qdrant_client: Any = None,
) -> MemoryConsolidator:
    global _consolidator
    _consolidator = MemoryConsolidator(postgres_pool, qdrant_client)
    logger.info("OK MemoryConsolidator initialized")
    return _consolidator


def get_consolidator() -> Optional[MemoryConsolidator]:
    return _consolidator
