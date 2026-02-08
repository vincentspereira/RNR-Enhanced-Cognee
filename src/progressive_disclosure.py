"""
Enhanced Cognee - Progressive Disclosure Search

Implements 3-layer progressive disclosure for token-efficient search.
Achieves 10x token efficiency by returning compact results first.

Architecture:
Layer 1 (search_index): Returns compact results with IDs only (~50 tokens/result)
Layer 2 (get_timeline): Shows chronological context around a memory
Layer 3 (get_memory_batch): Get full details for multiple memories

Usage Pattern:
1. search_index("my query") -> Get list of relevant memory IDs with summaries
2. get_timeline(memory_id, before=5, after=5) -> Get context around interesting memory
3. get_memory_batch([id1, id2, id3]) -> Get full details for selected memories

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ProgressiveDisclosureSearch:
    """
    Progressive disclosure search engine.

    Implements 3-layer search for token efficiency.
    """

    def __init__(self, db_pool):
        """
        Initialize progressive disclosure search.

        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool
        self.stats = {
            "layer1_searches": 0,
            "layer2_timelines": 0,
            "layer3_batches": 0,
            "tokens_saved": 0
        }

    async def search_index(
        self,
        query: str,
        agent_id: str = "default",
        limit: int = 50,
        data_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Layer 1: Compact search results.

        Returns minimal information (ID + summary) for token efficiency.
        ~50 tokens per result instead of 500+ for full content.

        Args:
            query: Search query text
            agent_id: Agent identifier
            limit: Maximum results
            data_type: Optional filter by data type

        Returns:
            Search results with compact format
        """
        self.stats["layer1_searches"] += 1

        async with self.db_pool.acquire() as conn:
            # Build query
            if data_type:
                rows = await conn.fetch("""
                    SELECT
                        id,
                        COALESCE(summary, SUBSTRING(data_text FROM 1 FOR 200) || '...') AS summary,
                        data_type,
                        created_at,
                        ROUND(LENGTH(data_text) / 4.0) AS estimated_tokens
                    FROM shared_memory.documents
                    WHERE agent_id = $1
                      AND data_type = $2
                      AND (
                          data_text ILIKE '%' || $3 || '%'
                          OR summary ILIKE '%' || $3 || '%'
                      )
                    ORDER BY created_at DESC
                    LIMIT $4
                """, agent_id, data_type, query, limit)
            else:
                rows = await conn.fetch("""
                    SELECT
                        id,
                        COALESCE(summary, SUBSTRING(data_text FROM 1 FOR 200) || '...') AS summary,
                        data_type,
                        created_at,
                        ROUND(LENGTH(data_text) / 4.0) AS estimated_tokens
                    FROM shared_memory.documents
                    WHERE agent_id = $1
                      AND (
                          data_text ILIKE '%' || $2 || '%'
                          OR summary ILIKE '%' || $2 || '%'
                      )
                    ORDER BY created_at DESC
                    LIMIT $3
                """, agent_id, query, limit)

        results = [
            {
                "memory_id": str(row["id"]),
                "summary": row["summary"],
                "data_type": row["data_type"],
                "created_at": row["created_at"].isoformat(),
                "estimated_tokens": int(row["estimated_tokens"])
            }
            for row in rows
        ]

        # Calculate token savings
        total_full_tokens = sum(r["estimated_tokens"] for r in results)
        total_compact_tokens = len(results) * 50  # ~50 tokens per compact result
        tokens_saved = total_full_tokens - total_compact_tokens
        self.stats["tokens_saved"] += tokens_saved

        logger.info(f"Layer 1 search: {len(results)} results, saved ~{tokens_saved} tokens")

        return {
            "query": query,
            "layer": 1,
            "result_count": len(results),
            "results": results,
            "token_savings": {
                "estimated_full_tokens": total_full_tokens,
                "compact_tokens": total_compact_tokens,
                "tokens_saved": tokens_saved,
                "efficiency_percent": round((1 - total_compact_tokens / total_full_tokens) * 100, 1) if total_full_tokens > 0 else 0
            }
        }

    async def get_timeline(
        self,
        memory_id: str,
        before: int = 5,
        after: int = 5,
        include_summaries: bool = True
    ) -> Dict[str, Any]:
        """
        Layer 2: Get chronological context around a memory.

        Shows what happened before and after a specific memory.
        Provides context without loading all memories.

        Args:
            memory_id: Memory ID to get context for
            before: Number of memories before
            after: Number of memories after
            include_summaries: Include summary field

        Returns:
            Timeline context dict
        """
        self.stats["layer2_timelines"] += 1

        async with self.db_pool.acquire() as conn:
            # Get target memory timestamp
            target_row = await conn.fetchrow(
                "SELECT created_at FROM shared_memory.documents WHERE id = $1",
                memory_id
            )

            if not target_row:
                return {"error": "Memory not found"}

            target_created_at = target_row["created_at"]

            # Build query based on whether to include summaries
            if include_summaries:
                select_fields = """
                    id,
                    COALESCE(summary, SUBSTRING(data_text FROM 1 FOR 200) || '...') AS summary,
                    data_type,
                    created_at,
                    ROUND(LENGTH(data_text) / 4.0) AS estimated_tokens
                """
            else:
                select_fields = """
                    id,
                    data_type,
                    created_at,
                    ROUND(LENGTH(data_text) / 4.0) AS estimated_tokens
                """

            # Get memories before (chronological order, most recent first)
            before_rows = await conn.fetch(f"""
                SELECT {select_fields}
                FROM shared_memory.documents
                WHERE created_at < $1
                ORDER BY created_at DESC
                LIMIT $2
            """, target_created_at, before)

            # Get target memory
            target_row_full = await conn.fetchrow(f"""
                SELECT {select_fields}
                FROM shared_memory.documents
                WHERE id = $1
            """, memory_id)

            # Get memories after (chronological order)
            after_rows = await conn.fetch(f"""
                SELECT {select_fields}
                FROM shared_memory.documents
                WHERE created_at > $1
                ORDER BY created_at ASC
                LIMIT $2
            """, target_created_at, after)

        # Build timeline
        timeline = {
            "memory_id": memory_id,
            "layer": 2,
            "before": [],
            "current": None,
            "after": []
        }

        # Add memories before
        for row in reversed(before_rows):  # Reverse to chronological order
            memory = {
                "memory_id": str(row["id"]),
                "data_type": row["data_type"],
                "created_at": row["created_at"].isoformat(),
                "estimated_tokens": int(row["estimated_tokens"])
            }
            if include_summaries:
                memory["summary"] = row["summary"]
            timeline["before"].append(memory)

        # Add current memory
        if target_row_full:
            current = {
                "memory_id": str(target_row_full["id"]),
                "data_type": target_row_full["data_type"],
                "created_at": target_row_full["created_at"].isoformat(),
                "estimated_tokens": int(target_row_full["estimated_tokens"])
            }
            if include_summaries:
                current["summary"] = target_row_full["summary"]
            timeline["current"] = current

        # Add memories after
        for row in after_rows:
            memory = {
                "memory_id": str(row["id"]),
                "data_type": row["data_type"],
                "created_at": row["created_at"].isoformat(),
                "estimated_tokens": int(row["estimated_tokens"])
            }
            if include_summaries:
                memory["summary"] = row["summary"]
            timeline["after"].append(memory)

        logger.info(f"Layer 2 timeline: {len(timeline['before'])} before, 1 current, {len(timeline['after'])} after")

        return timeline

    async def get_memory_batch(
        self,
        memory_ids: List[str],
        include_metadata: bool = False
    ) -> Dict[str, Any]:
        """
        Layer 3: Get full details for multiple memories.

        Always batch multiple IDs for efficiency.
        This is the final layer when you need full content.

        Args:
            memory_ids: List of memory IDs
            include_metadata: Include metadata field

        Returns:
            Batch of full memory details
        """
        self.stats["layer3_batches"] += 1

        if not memory_ids:
            return {
                "layer": 3,
                "memories": [],
                "count": 0
            }

        async with self.db_pool.acquire() as conn:
            # Build query based on metadata inclusion
            if include_metadata:
                rows = await conn.fetch("""
                    SELECT
                        id,
                        data_text,
                        data_type,
                        summary,
                        created_at,
                        updated_at,
                        metadata,
                        agent_id
                    FROM shared_memory.documents
                    WHERE id = ANY($1)
                    ORDER BY created_at
                """, memory_ids)
            else:
                rows = await conn.fetch("""
                    SELECT
                        id,
                        data_text,
                        data_type,
                        summary,
                        created_at,
                        updated_at,
                        agent_id
                    FROM shared_memory.documents
                    WHERE id = ANY($1)
                    ORDER BY created_at
                """, memory_ids)

        memories = []
        for row in rows:
            memory = {
                "memory_id": str(row["id"]),
                "content": row["data_text"],
                "data_type": row["data_type"],
                "summary": row["summary"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
                "agent_id": row["agent_id"]
            }
            if include_metadata:
                memory["metadata"] = json.loads(row["metadata"]) if row.get("metadata") else {}

            memories.append(memory)

        logger.info(f"Layer 3 batch: Retrieved {len(memories)} memories")

        return {
            "layer": 3,
            "count": len(memories),
            "memories": memories
        }

    async def progressive_search_workflow(
        self,
        query: str,
        agent_id: str = "default",
        index_limit: int = 20,
        timeline_before: int = 3,
        timeline_after: int = 3,
        batch_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Complete progressive disclosure workflow.

        Demonstrates the 3-layer search pattern:
        1. Search index (compact results)
        2. Get timeline for selected memories
        3. Batch fetch full details

        Args:
            query: Search query
            agent_id: Agent identifier
            index_limit: Results for Layer 1
            timeline_before: Timeline context before
            timeline_after: Timeline context after
            batch_ids: Specific IDs to fetch (optional)

        Returns:
            Complete workflow results
        """
        logger.info(f"Progressive search workflow: query='{query}'")

        # Layer 1: Search index
        index_results = await self.search_index(
            query=query,
            agent_id=agent_id,
            limit=index_limit
        )

        # Layer 2: Get timeline for first result
        timeline_context = None
        if index_results["results"]:
            first_id = index_results["results"][0]["memory_id"]
            timeline_context = await self.get_timeline(
                memory_id=first_id,
                before=timeline_before,
                after=timeline_after
            )

        # Layer 3: Batch fetch specific IDs
        batch_results = None
        if batch_ids:
            batch_results = await self.get_memory_batch(
                memory_ids=batch_ids,
                include_metadata=True
            )

        # Return complete workflow
        return {
            "query": query,
            "workflow": "progressive_disclosure",
            "layer1_index": index_results,
            "layer2_timeline": timeline_context,
            "layer3_batch": batch_results,
            "stats": {
                "total_tokens_saved": self.stats["tokens_saved"],
                "layer1_searches": self.stats["layer1_searches"],
                "layer2_timelines": self.stats["layer2_timelines"],
                "layer3_batches": self.stats["layer3_batches"]
            }
        }

    async def get_token_efficiency_stats(self) -> Dict[str, Any]:
        """
        Get token efficiency statistics.

        Returns:
            Statistics dict
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*) AS total_memories,
                    COUNT(*) FILTER (WHERE char_count <= 500) AS small_memories,
                    COUNT(*) FILTER (WHERE char_count > 500 AND char_count <= 2000) AS medium_memories,
                    COUNT(*) FILTER (WHERE char_count > 2000) AS large_memories,
                    ROUND(AVG(ROUND(CHAR_LENGTH(data_text) / 4.0)), 2) AS avg_tokens_per_memory,
                    ROUND(AVG(CHAR_LENGTH(summary)), 2) AS avg_summary_chars,
                    ROUND(
                        (1.0 - (AVG(CHAR_LENGTH(summary)) / AVG(CHAR_LENGTH(data_text)))) * 100.0,
                        2
                    ) AS token_efficiency_percent
                FROM shared_memory.documents
            """)

        return {
            **self.stats,
            "database": {
                "total_memories": row["total_memories"],
                "small_memories": row["small_memories"],  # <= 500 chars
                "medium_memories": row["medium_memories"],  # 500-2000 chars
                "large_memories": row["large_memories"],  # > 2000 chars
                "avg_tokens_per_memory": float(row["avg_tokens_per_memory"]) if row["avg_tokens_per_memory"] else 0,
                "avg_summary_chars": float(row["avg_summary_chars"]) if row["avg_summary_chars"] else 0,
                "token_efficiency_percent": float(row["token_efficiency_percent"]) if row["token_efficiency_percent"] else 0
            }
        }


async def main():
    """Test progressive disclosure search."""
    print("Progressive disclosure search requires database connection")
    print("Use with PostgreSQL connection pool")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
