"""
Enhanced Cognee - Clear Cache Task

Scheduled task to clear Redis cache.

Author: Enhanced Cognee Team
Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def clear_cache(redis_client) -> Dict[str, Any]:
    """
    Clear Redis cache.

    Args:
        redis_client: Redis client

    Returns:
        Result dictionary
    """
    try:
        # Get key count before clearing
        keys_before = len(redis_client.keys("*"))

        # Clear all keys
        redis_client.flushall()

        keys_after = len(redis_client.keys("*"))

        logger.info(f"Cleared {keys_before} cache entries")

        return {
            "status": "success",
            "keys_cleared": keys_before,
            "keys_remaining": keys_after
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    # Test task
    logging.basicConfig(level=logging.INFO)
    print("[INFO] Clear cache task")
