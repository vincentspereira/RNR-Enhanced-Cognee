"""
Memory Management Module for Enhanced Cognee
Provides memory expiry, archival, and cleanup policies
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class RetentionPolicy(Enum):
    """Memory retention policies"""
    KEEP_ALL = "keep_all"
    KEEP_recent = "keep_recent"
    ARCHIVE_OLD = "archive_old"
    DELETE_OLD = "delete_old"


class MemoryManager:
    """Manages memory lifecycle including expiry, archival, and cleanup"""

    def __init__(self, postgres_pool, redis_client, qdrant_client):
        self.postgres_pool = postgres_pool
        self.redis_client = redis_client
        self.qdrant_client = qdrant_client

    async def expire_old_memories(
        self,
        days: int = 90,
        dry_run: bool = False,
        policy: RetentionPolicy = RetentionPolicy.DELETE_OLD
    ) -> Dict[str, Any]:
        """
        Expire or archive memories older than specified days

        Args:
            days: Number of days after which memories expire
            dry_run: If True, simulate without actually deleting
            policy: What to do with old memories

        Returns:
            Dict with results of the expiry operation
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                # Count memories to be affected
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM shared_memory.documents
                    WHERE created_at < NOW() - INTERVAL '$1 days'
                """, days)

                if dry_run:
                    logger.info(f"DRY RUN: Would expire {count} memories older than {days} days")
                    return {
                        "status": "dry_run",
                        "memories_affected": count,
                        "days": days,
                        "policy": policy.value
                    }

                if policy == RetentionPolicy.DELETE_OLD:
                    # Delete old memories
                    result = await conn.execute("""
                        DELETE FROM shared_memory.documents
                        WHERE created_at < NOW() - INTERVAL '$1 days'
                        RETURNING id, title
                    """, days)

                    logger.info(f"Expired {result} memories older than {days} days")

                    return {
                        "status": "success",
                        "action": "deleted",
                        "memories_affected": result,
                        "days": days
                    }

                elif policy == RetentionPolicy.ARCHIVE_OLD:
                    # Archive to separate table (implementation depends on schema)
                    # For now, we'll mark them as archived
                    result = await conn.execute("""
                        UPDATE shared_memory.documents
                        SET metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{archived}',
                            'true'
                        )
                        WHERE created_at < NOW() - INTERVAL '$1 days'
                    """, days)

                    logger.info(f"Archived {result} memories older than {days} days")

                    return {
                        "status": "success",
                        "action": "archived",
                        "memories_affected": result,
                        "days": days
                    }

                else:
                    return {
                        "status": "skipped",
                        "reason": f"Policy {policy.value} not implemented"
                    }

        except Exception as e:
            logger.error(f"Failed to expire old memories: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def cleanup_expired_cache(self) -> Dict[str, Any]:
        """Clean up expired entries from Redis cache"""
        try:
            # Redis handles TTL automatically, but we can get stats
            info = await self.redis_client.info("stats")

            # Get number of expired keys
            expired_keys = info.get("expired_keys", 0)

            return {
                "status": "success",
                "expired_keys": expired_keys,
                "note": "Redis automatically handles TTL cleanup"
            }

        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_memory_stats_by_age(self) -> Dict[str, Any]:
        """Get statistics about memory age distribution"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Memories by age bracket
                stats = await conn.fetch("""
                    SELECT
                        CASE
                            WHEN created_at > NOW() - INTERVAL '7 days' THEN '0-7 days'
                            WHEN created_at > NOW() - INTERVAL '30 days' THEN '8-30 days'
                            WHEN created_at > NOW() - INTERVAL '90 days' THEN '31-90 days'
                            ELSE '90+ days'
                        END as age_bracket,
                        COUNT(*) as count
                    FROM shared_memory.documents
                    GROUP BY age_bracket
                    ORDER BY age_bracket
                """)

                age_distribution = {row["age_bracket"]: row["count"] for row in stats}

                # Total memories and oldest/newest
                total = await conn.fetchval("SELECT COUNT(*) FROM shared_memory.documents")
                oldest = await conn.fetchval("SELECT MIN(created_at) FROM shared_memory.documents")
                newest = await conn.fetchval("SELECT MAX(created_at) FROM shared_memory.documents")

                return {
                    "total_memories": total,
                    "oldest_memory": str(oldest) if oldest else None,
                    "newest_memory": str(newest) if newest else None,
                    "age_distribution": age_distribution
                }

        except Exception as e:
            logger.error(f"Failed to get memory stats by age: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def archive_memories_by_category(
        self,
        memory_category: str,
        days: int = 180
    ) -> Dict[str, Any]:
        """
        Archive memories from a specific category older than specified days

        Args:
            memory_category: Category to archive (e.g., 'trading', 'development')
            days: Age threshold for archiving

        Returns:
            Dict with archival results
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                # Mark memories as archived
                result = await conn.execute("""
                    UPDATE shared_memory.documents
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{archived}',
                        'true'
                    )
                    WHERE memory_category = $1
                    AND created_at < NOW() - INTERVAL '$2 days'
                """, memory_category, days)

                logger.info(f"Archived {result} memories from category '{memory_category}'")

                return {
                    "status": "success",
                    "category": memory_category,
                    "memories_archived": result,
                    "days_threshold": days
                }

        except Exception as e:
            logger.error(f"Failed to archive memories by category: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def set_memory_ttl(
        self,
        memory_id: str,
        ttl_days: int
    ) -> Dict[str, Any]:
        """
        Set a time-to-live (TTL) for a specific memory

        Args:
            memory_id: ID of the memory
            ttl_days: Days until expiry (0 = no expiry)

        Returns:
            Dict with result
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                # Set expiry date in metadata
                expiry_date = datetime.now(timezone.utc) + timedelta(days=ttl_days) if ttl_days > 0 else None

                result = await conn.execute("""
                    UPDATE shared_memory.documents
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{expiry_date}',
                        $1
                    )
                    WHERE id = $2
                """, expiry_date.isoformat() if expiry_date else None, memory_id)

                if result == 0:
                    return {
                        "status": "not_found",
                        "memory_id": memory_id
                    }

                logger.info(f"Set TTL of {ttl_days} days for memory {memory_id}")

                return {
                    "status": "success",
                    "memory_id": memory_id,
                    "ttl_days": ttl_days,
                    "expiry_date": expiry_date.isoformat() if expiry_date else None
                }

        except Exception as e:
            logger.error(f"Failed to set memory TTL: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def bulk_set_ttl_by_category(
        self,
        memory_category: str,
        ttl_days: int
    ) -> Dict[str, Any]:
        """
        Bulk set TTL for all memories in a category

        Args:
            memory_category: Category to update
            ttl_days: Days until expiry

        Returns:
            Dict with result
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                expiry_date = datetime.now(timezone.utc) + timedelta(days=ttl_days)

                result = await conn.execute("""
                    UPDATE shared_memory.documents
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{expiry_date}',
                        $1
                    )
                    WHERE memory_category = $2
                """, expiry_date.isoformat(), memory_category)

                logger.info(f"Set TTL of {ttl_days} days for {result} memories in category '{memory_category}'")

                return {
                    "status": "success",
                    "category": memory_category,
                    "memories_updated": result,
                    "ttl_days": ttl_days
                }

        except Exception as e:
            logger.error(f"Failed to bulk set TTL: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
