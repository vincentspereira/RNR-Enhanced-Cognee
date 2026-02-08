"""
Enhanced Cognee - Auto Expire Memories Task

Scheduled task to delete memories older than specified days.

Author: Enhanced Cognee Team
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def auto_expire_memories(postgres_pool, days: int = 90) -> Dict[str, Any]:
    """
    Delete memories older than specified days.

    Args:
        postgres_pool: PostgreSQL connection pool
        days: Age threshold in days

    Returns:
        Result dictionary
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)

        async with postgres_pool.acquire() as conn:
            # Count memories to expire
            count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM shared_memory.documents
                WHERE created_at < $1
            """, cutoff_date)

            # Delete memories
            result = await conn.execute("""
                DELETE FROM shared_memory.documents
                WHERE created_at < $1
            """, cutoff_date)

            # Parse result (PostgreSQL returns "DELETE <count>")
            deleted_count = int(result.split()[-1]) if result else 0

            logger.info(f"Expired {deleted_count} memories older than {days} days")

            return {
                "status": "success",
                "memories_expired": deleted_count,
                "age_threshold_days": days,
                "cutoff_date": cutoff_date.isoformat()
            }

    except Exception as e:
        logger.error(f"Failed to expire memories: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    # Test task
    logging.basicConfig(level=logging.INFO)
    print("[INFO] Auto expire memories task")
