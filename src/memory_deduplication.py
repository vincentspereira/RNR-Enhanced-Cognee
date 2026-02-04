"""
Memory Deduplication Module for Enhanced Cognee
Prevents duplicate memories using vector similarity and text matching
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json

logger = logging.getLogger(__name__)


class MemoryDeduplicator:
    """Detects and handles duplicate memories"""

    def __init__(self, postgres_pool, qdrant_client, similarity_threshold: float = 0.95):
        self.postgres_pool = postgres_pool
        self.qdrant_client = qdrant_client
        self.similarity_threshold = similarity_threshold

    async def check_duplicate(
        self,
        content: str,
        embedding: Optional[List[float]] = None,
        agent_id: str = "default",
        memory_category: str = "general"
    ) -> Dict[str, Any]:
        """
        Check if a memory is duplicate before adding

        Args:
            content: Memory content to check
            embedding: Vector embedding of content
            agent_id: Agent adding the memory
            memory_category: Category of the memory

        Returns:
            Dict with duplicate check results
        """
        try:
            # Check 1: Exact text match in PostgreSQL
            exact_duplicate = await self._check_exact_match(content, agent_id)

            if exact_duplicate:
                return {
                    "is_duplicate": True,
                    "duplicate_type": "exact",
                    "existing_id": exact_duplicate["id"],
                    "action": "skip",
                    "reason": "Exact duplicate found"
                }

            # Check 2: Vector similarity (if embedding provided)
            if embedding and qdrant_client:
                similar = await self._check_vector_similarity(
                    content, embedding, agent_id, memory_category
                )

                if similar:
                    return {
                        "is_duplicate": True,
                        "duplicate_type": "similar",
                        "existing_id": similar["id"],
                        "similarity_score": similar["score"],
                        "action": "merge",
                        "reason": f"Very similar memory found (score: {similar['score']:.3f})"
                    }

            # No duplicate found
            return {
                "is_duplicate": False,
                "action": "add",
                "reason": "No duplicate found"
            }

        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return {
                "is_duplicate": False,
                "action": "add",
                "error": str(e)
            }

    async def _check_exact_match(self, content: str, agent_id: str) -> Optional[Dict]:
        """Check for exact text match"""
        try:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, content, created_at
                    FROM shared_memory.documents
                    WHERE agent_id = $1
                    AND content = $2
                    ORDER BY created_at DESC
                    LIMIT 1
                """, agent_id, content)

                if row:
                    return {"id": row["id"], "created_at": str(row["created_at"])}
                return None

        except Exception as e:
            logger.error(f"Exact match check failed: {e}")
            return None

    async def _check_vector_similarity(
        self,
        content: str,
        embedding: List[float],
        agent_id: str,
        memory_category: str
    ) -> Optional[Dict]:
        """Check for similar memories using vector search"""
        try:
            collection_name = f"cognee_{memory_category}_memory"

            # Search for similar vectors
            search_result = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=embedding,
                limit=1,
                score_threshold=self.similarity_threshold
            )

            if search_result and len(search_result) > 0:
                hit = search_result[0]
                return {
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.payload.get("content", "")
                }

            return None

        except Exception as e:
            logger.error(f"Vector similarity check failed: {e}")
            return None

    async def merge_duplicates(
        self,
        memory_id: str,
        new_content: str,
        merge_strategy: str = "keep_newest"
    ) -> Dict[str, Any]:
        """
        Merge duplicate memories

        Args:
            memory_id: ID of the memory to merge
            new_content: New content to merge
            merge_strategy: Strategy for merging (keep_newest, keep_both, append)

        Returns:
            Dict with merge result
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                if merge_strategy == "keep_newest":
                    # Update with new content
                    await conn.execute("""
                        UPDATE shared_memory.documents
                        SET content = $1,
                            updated_at = NOW()
                        WHERE id = $2
                    """, new_content, memory_id)

                    logger.info(f"Merged duplicate memory {memory_id} (kept newest)")

                    return {
                        "status": "success",
                        "action": "updated",
                        "memory_id": memory_id
                    }

                elif merge_strategy == "append":
                    # Append new content to existing
                    await conn.execute("""
                        UPDATE shared_memory.documents
                        SET content = content || '\n\n---\n\n' || $1,
                            updated_at = NOW()
                        WHERE id = $2
                    """, new_content, memory_id)

                    return {
                        "status": "success",
                        "action": "appended",
                        "memory_id": memory_id
                    }

                else:
                    return {
                        "status": "error",
                        "error": f"Unknown merge strategy: {merge_strategy}"
                    }

        except Exception as e:
            logger.error(f"Failed to merge duplicates: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get statistics about deduplication"""
        try:
            stats = {
                "similarity_threshold": self.similarity_threshold,
                "exact_duplicates_found": 0,
                "similar_duplicates_found": 0,
                "total_duplicates_prevented": 0
            }

            # Count potential duplicates based on content hash
            async with self.postgres_pool.acquire() as conn:
                # This is a simplified check - in production you'd use content hashes
                result = await conn.fetch("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(DISTINCT content) as unique_content
                    FROM shared_memory.documents
                """)

                if result:
                    total = result["total"]
                    unique = result["unique_content"]
                    duplicates = total - unique
                    stats["total_duplicates_prevented"] = duplicates
                    stats["exact_duplicates_found"] = duplicates

            return stats

        except Exception as e:
            logger.error(f"Failed to get deduplication stats: {e}")
            return {"error": str(e)}

    async def auto_deduplicate(self, agent_id: str = None) -> Dict[str, Any]:
        """
        Automatically find and handle duplicate memories

        Args:
            agent_id: Optional agent ID to scope deduplication

        Returns:
            Dict with deduplication results
        """
        try:
            results = {
                "processed": 0,
                "duplicates_found": 0,
                "merged": 0,
                "deleted": 0
            }

            async with self.postgres_pool.acquire() as conn:
                # Get all memories (optionally filtered by agent)
                if agent_id:
                    memories = await conn.fetch("""
                        SELECT id, content, agent_id, memory_category
                        FROM shared_memory.documents
                        WHERE agent_id = $1
                        ORDER BY created_at ASC
                    """, agent_id)
                else:
                    memories = await conn.fetch("""
                        SELECT id, content, agent_id, memory_category
                        FROM shared_memory.documents
                        ORDER BY created_at ASC
                    """)

                logger.info(f"Checking {len(memories)} memories for duplicates...")

                # Check each memory
                checked_ids = set()
                for memory in memories:
                    memory_id = memory["id"]
                    if memory_id in checked_ids:
                        continue

                    # Check for duplicates
                    duplicate_check = await self._check_exact_match(
                        memory["content"],
                        memory["agent_id"]
                    )

                    if duplicate_check:
                        # Found duplicate - delete it
                        await conn.execute("""
                            DELETE FROM shared_memory.documents WHERE id = $1
                        """, duplicate_check["id"])

                        results["duplicates_found"] += 1
                        results["deleted"] += 1

                    checked_ids.add(memory_id)
                    results["processed"] += 1

                logger.info(f"Auto-deduplication complete: {results}")

                return {
                    "status": "success",
                    "results": results
                }

        except Exception as e:
            logger.error(f"Auto-deduplication failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
