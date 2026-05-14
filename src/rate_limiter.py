"""
Phase 9 - 14.4: Per-Agent Rate Limiter
========================================
Implements a sliding-window rate limiter backed by Redis.

Each agent has a configurable request quota per time window.  When an
agent exceeds its quota the limiter returns a "rate limited" response
without calling the underlying tool.

Fallback: when Redis is unavailable the limiter degrades gracefully
(all requests are allowed through) and logs a warning.

ASCII-only: no Unicode in string literals or log messages.

Usage
-----
    from src.rate_limiter import RateLimiter, init_rate_limiter

    # At server startup
    rate_limiter = init_rate_limiter(redis_client=redis_client)

    # In an MCP tool
    ok, wait_seconds = await rate_limiter.check(agent_id="claude-code", tool_name="add_memory")
    if not ok:
        return f"ERR Rate limit exceeded. Try again in {wait_seconds:.0f}s."
"""

import logging
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_RULES: Dict[str, Dict] = {
    # tool_name or "*" (wildcard) -> {requests, window_seconds}
    "*": {"requests": 60, "window_seconds": 60},         # 60 req/min global
    "add_memory": {"requests": 30, "window_seconds": 60},
    "search_memories": {"requests": 120, "window_seconds": 60},
    "delete_memory": {"requests": 10, "window_seconds": 60},
    "cognify": {"requests": 5, "window_seconds": 60},
    "ingest_url": {"requests": 3, "window_seconds": 60},
    "ingest_db": {"requests": 2, "window_seconds": 60},
    "restore_backup": {"requests": 1, "window_seconds": 300},
}

# In-memory fallback (agent_id+tool -> list of timestamps)
_memory_store: Dict[str, list] = {}

# Singleton
_rate_limiter: Optional["RateLimiter"] = None


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    Sliding-window rate limiter with Redis backend and in-memory fallback.

    The sliding window is implemented using a Redis sorted set where each
    member is a unique timestamp (with nanosecond precision) and the score
    is the UNIX timestamp.  Old entries are pruned before counting.
    """

    def __init__(
        self,
        redis_client=None,
        rules: Optional[Dict[str, Dict]] = None,
    ):
        self.redis = redis_client
        self.rules: Dict[str, Dict] = {**_DEFAULT_RULES, **(rules or {})}
        self._redis_ok: bool = redis_client is not None

    def _get_rule(self, tool_name: str) -> Dict:
        """Return the most specific rule for a tool, falling back to '*'."""
        return self.rules.get(tool_name, self.rules.get("*", {"requests": 60, "window_seconds": 60}))

    def _redis_key(self, agent_id: str, tool_name: str) -> str:
        return f"rl:{agent_id}:{tool_name}"

    async def check(
        self,
        agent_id: str,
        tool_name: str = "*",
    ) -> Tuple[bool, float]:
        """
        Check whether the agent is within rate limits for a tool.

        Returns:
            (allowed, retry_after_seconds) where allowed=True means the
            request is permitted.  retry_after_seconds is 0 when allowed.
        """
        rule = self._get_rule(tool_name)
        max_requests = rule["requests"]
        window = rule["window_seconds"]
        now = time.time()
        cutoff = now - window

        if self.redis and self._redis_ok:
            return await self._check_redis(agent_id, tool_name, max_requests, window, now, cutoff)
        else:
            return self._check_memory(agent_id, tool_name, max_requests, window, now, cutoff)

    async def _check_redis(
        self, agent_id, tool_name, max_requests, window, now, cutoff
    ) -> Tuple[bool, float]:
        """Redis sliding-window implementation."""
        try:
            key = self._redis_key(agent_id, tool_name)
            pipe = self.redis.pipeline()
            # Remove entries outside the window
            pipe.zremrangebyscore(key, 0, cutoff)
            # Count remaining
            pipe.zcard(key)
            # Add this request
            pipe.zadd(key, {f"{now:.9f}": now})
            # Set key expiry to window length
            pipe.expire(key, int(window) + 1)
            results = await pipe.execute()
            count = results[1]  # count before adding current request
            if count >= max_requests:
                # Find oldest entry to calculate retry-after
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                retry_after = 0.0
                if oldest:
                    oldest_ts = oldest[0][1]
                    retry_after = max(0.0, (oldest_ts + window) - now)
                return False, retry_after
            return True, 0.0
        except Exception as exc:
            logger.warning(f"RateLimiter Redis error (allowing through): {exc}")
            self._redis_ok = False
            return True, 0.0

    def _check_memory(
        self, agent_id, tool_name, max_requests, window, now, cutoff
    ) -> Tuple[bool, float]:
        """In-memory sliding-window fallback."""
        key = f"{agent_id}:{tool_name}"
        timestamps = _memory_store.get(key, [])
        # Prune old entries
        timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= max_requests:
            oldest = min(timestamps)
            retry_after = max(0.0, (oldest + window) - now)
            _memory_store[key] = timestamps
            return False, retry_after
        timestamps.append(now)
        _memory_store[key] = timestamps
        return True, 0.0

    def set_rule(self, tool_name: str, requests: int, window_seconds: int) -> None:
        """Set or override a rate limit rule for a tool."""
        self.rules[tool_name] = {"requests": requests, "window_seconds": window_seconds}
        logger.info(f"Rate limit rule set: {tool_name} -> {requests} req/{window_seconds}s")

    def get_rules(self) -> Dict[str, Dict]:
        """Return all configured rate limit rules."""
        return dict(self.rules)

    async def get_usage(self, agent_id: str, tool_name: str = "*") -> Dict:
        """Return current usage stats for an agent/tool pair."""
        rule = self._get_rule(tool_name)
        max_requests = rule["requests"]
        window = rule["window_seconds"]
        now = time.time()
        cutoff = now - window

        if self.redis and self._redis_ok:
            try:
                key = self._redis_key(agent_id, tool_name)
                await self.redis.zremrangebyscore(key, 0, cutoff)
                count = await self.redis.zcard(key)
                return {
                    "agent_id": agent_id,
                    "tool": tool_name,
                    "used": count,
                    "limit": max_requests,
                    "window_seconds": window,
                    "remaining": max(0, max_requests - count),
                }
            except Exception:
                pass

        # In-memory fallback
        key = f"{agent_id}:{tool_name}"
        timestamps = [t for t in _memory_store.get(key, []) if t > cutoff]
        return {
            "agent_id": agent_id,
            "tool": tool_name,
            "used": len(timestamps),
            "limit": max_requests,
            "window_seconds": window,
            "remaining": max(0, max_requests - len(timestamps)),
        }


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def init_rate_limiter(
    redis_client=None,
    rules: Optional[Dict[str, Dict]] = None,
) -> "RateLimiter":
    """Initialize the global rate limiter singleton."""
    global _rate_limiter
    _rate_limiter = RateLimiter(redis_client=redis_client, rules=rules)
    return _rate_limiter


def get_rate_limiter() -> Optional["RateLimiter"]:
    """Return the global rate limiter, or None if not initialized."""
    return _rate_limiter
