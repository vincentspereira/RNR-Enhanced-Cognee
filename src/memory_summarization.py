"""
Memory Summarization Module for Enhanced Cognee
Automatically summarizes old or large memories to save space
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class MemorySummarizer:
    """Summarizes old or large memories to save storage space"""

    def __init__(self, postgres_pool, llm_config: Dict[str, Any]):
        self.postgres_pool = postgres_pool
        self.llm_config = llm_config

    async def summarize_old_memories(
        self,
        days: int = 30,
        min_length: int = 1000,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Summarize memories older than specified days

        Args:
            days: Age threshold for summarization
            min_length: Minimum content length to summarize
            dry_run: If True, simulate without summarizing

        Returns:
            Dict with summarization results
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                # Find memories to summarize
                memories = await conn.fetch("""
                    SELECT id, title, content, created_at
                    FROM shared_memory.documents
                    WHERE created_at < NOW() - INTERVAL '$1 days'
                    AND LENGTH(content) > $2
                    AND (metadata->>'summarized') IS NULL OR (metadata->>'summarized') = 'false')
                    ORDER BY created_at ASC
                    LIMIT 100
                """, days, min_length)

                if not memories:
                    return {
                        "status": "success",
                        "memories_summarized": 0,
                        "message": "No memories found to summarize"
                    }

                results = {
                    "status": "success",
                    "candidates_found": len(memories),
                    "memories_summarized": 0,
                    "space_saved_bytes": 0,
                    "summaries": []
                }

                for memory in memories:
                    memory_id = memory["id"]
                    original_length = len(memory["content"])

                    # Generate summary (in real implementation, use LLM here)
                    summary = await self._generate_summary(memory["content"])

                    if dry_run:
                        logger.info(f"DRY RUN: Would summarize memory {memory_id}")
                        results["summaries"].append({
                            "memory_id": memory_id,
                            "original_length": original_length,
                            "summary_length": len(summary),
                            "compression_ratio": f"{(1 - len(summary)/original_length)*100:.1f}%"
                        })
                    else:
                        # Update memory with summary
                        await conn.execute("""
                            UPDATE shared_memory.documents
                            SET
                                content = $1,
                                metadata = jsonb_set(
                                    COALESCE(metadata, '{}'::jsonb),
                                    '{summarized}',
                                    'true',
                                    '{original_length}',
                                    $2,
                                    '{summary_date}',
                                    NOW()::text
                                ),
                                updated_at = NOW()
                            WHERE id = $3
                        """, summary, str(original_length), memory_id)

                        results["memories_summarized"] += 1
                        results["space_saved_bytes"] += (original_length - len(summary))

                        logger.info(f"Summarized memory {memory_id}: {original_length} -> {len(summary)} chars")

                return results

        except Exception as e:
            logger.error(f"Failed to summarize memories: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _generate_summary(self, content: str) -> str:
        """
        Generate a summary of the content

        In production, this would call an LLM API.
        For now, we'll do a simple extractive summary.
        """
        # Simple extractive summary (first 2 sentences)
        sentences = content.split('. ')
        if len(sentences) > 2:
            summary = '. '.join(sentences[:2]) + '.'
        else:
            summary = content[:500] + '...' if len(content) > 500 else content

        return summary.strip()

    async def get_summary_stats(self) -> Dict[str, Any]:
        """Get statistics about memory summarization"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Get summary statistics
                stats = await conn.fetch("""
                    SELECT
                        COUNT(*) as total_memories,
                        COUNT(CASE WHEN metadata->>'summarized' = 'true' THEN 1 END) as summarized_memories,
                        COUNT(CASE WHEN metadata->>'summarized' = 'true' OR metadata->>'summarized' IS NULL THEN 1 END) as full_memories,
                        AVG(LENGTH(content)) as avg_length,
                        AVG(CASE WHEN metadata->>'summarized' = 'true' THEN CAST(metadata->>'original_length' AS INTEGER) ELSE LENGTH(content) END) as avg_original_length
                    FROM shared_memory.documents
                """)

                if stats:
                    row = stats[0]
                    total = row["total_memories"] or 0
                    summarized = row["summarized_memories"] or 0
                    full = row["full_memories"] or 0

                    # Calculate space saved
                    avg_original = row["avg_original_length"] or 0
                    avg_summary = row["avg_length"] or 0
                    space_saved = (avg_original - avg_summary) * summarized

                    return {
                        "total_memories": total,
                        "summarized_memories": summarized,
                        "full_memories": full,
                        "summarization_ratio": f"{(summarized/total*100):.1f}%" if total > 0 else "0%",
                        "avg_length": f"{avg_avg_length:.0f}" if row["avg_length"] else 0,
                        "estimated_space_saved_bytes": int(space_saved),
                        "estimated_space_saved_mb": f"{space_saved/1024/1024:.2f} MB"
                    }

                return {"error": "No statistics available"}

        except Exception as e:
            logger.error(f"Failed to get summary stats: {e}")
            return {"error": str(e)}

    async def summarize_by_category(
        self,
        memory_category: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Summarize all memories in a category older than specified days

        Args:
            memory_category: Category to summarize
            days: Age threshold

        Returns:
            Dict with results
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                memories = await conn.fetch("""
                    SELECT id, content
                    FROM shared_memory.documents
                    WHERE memory_category = $1
                    AND created_at < NOW() - INTERVAL '$2 days'
                    AND LENGTH(content) > 500
                """, memory_category, days)

                results = {
                    "category": memory_category,
                    "days_threshold": days,
                    "candidates_found": len(memories),
                    "memories_summarized": 0,
                    "space_saved": 0
                }

                for memory in memories:
                    summary = await self._generate_summary(memory["content"])
                    original_length = len(memory["content"])

                    await conn.execute("""
                        UPDATE shared_memory.documents
                        SET
                            content = $1,
                            metadata = jsonb_set(
                                COALESCE(metadata, '{}'::jsonb),
                                '{summarized}',
                                'true',
                                '{original_length}',
                                $2
                            )
                        WHERE id = $3
                    """, summary, str(original_length), memory["id"])

                    results["memories_summarized"] += 1
                    results["space_saved"] += (original_length - len(summary))

                logger.info(f"Summarized {results['memories_summarized']} memories in category '{memory_category}'")

                return {
                    "status": "success",
                    "results": results
                }

        except Exception as e:
            logger.error(f"Failed to summarize by category: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
