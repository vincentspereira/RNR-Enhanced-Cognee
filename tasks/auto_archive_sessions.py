"""
Enhanced Cognee - Auto Archive Sessions Task

Scheduled task to archive sessions older than specified days.

Author: Enhanced Cognee Team
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def auto_archive_sessions(postgres_pool, days: int = 365) -> Dict[str, Any]:
    """
    Archive sessions older than specified days.

    Args:
        postgres_pool: PostgreSQL connection pool
        days: Age threshold in days

    Returns:
        Result dictionary
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)

        async with postgres_pool.acquire() as conn:
            # Count sessions to archive
            count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM shared_memory.sessions
                WHERE created_at < $1
                AND (metadata->>'archived') IS NULL OR (metadata->>'archived') = 'false'
            """, cutoff_date)

            # Mark sessions as archived
            result = await conn.execute("""
                UPDATE shared_memory.sessions
                SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{archived}',
                    'true',
                    '{archived_date}',
                    NOW()::text
                )
                WHERE created_at < $1
            """, cutoff_date)

            # Parse result
            archived_count = int(result.split()[-1]) if result else 0

            logger.info(f"Archived {archived_count} sessions older than {days} days")

            return {
                "status": "success",
                "sessions_archived": archived_count,
                "age_threshold_days": days,
                "cutoff_date": cutoff_date.isoformat()
            }

    except Exception as e:
        logger.error(f"Failed to archive sessions: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    # Test task
    logging.basicConfig(level=logging.INFO)
    print("[INFO] Auto archive sessions task")
