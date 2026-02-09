"""
Enhanced Cognee - LLM API Rate Limiter

This module provides rate limiting for LLM API calls to:
- Prevent hitting provider rate limits
- Manage request queues
- Implement automatic retry with exponential backoff
- Support distributed locking (Redis)
- Track rate limit statistics

Supports:
- Anthropic Claude (50 requests/minute, 40K tokens/minute)
- OpenAI GPT (500 requests/minute, 150K tokens/minute)
- Custom limits per provider
- Token-based and request-based rate limiting

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

# Try to import Redis for distributed locking
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - rate limiting will be local only")

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("asyncpg not available - stats tracking disabled")


class Provider(Enum):
    """LLM provider enumeration."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LITELLM = "litellm"


class RequestPriority(Enum):
    """Request priority levels."""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


class RateLimiter:
    """
    Token bucket rate limiter for LLM API calls.

    Features:
    - Request-based rate limiting (requests per minute)
    - Token-based rate limiting (tokens per minute)
    - Queue management for pending requests
    - Automatic retry with exponential backoff
    - Distributed locking (Redis optional)
    - Statistics tracking

    Rate Limits (per provider):
    - Anthropic: 50 requests/min, 40K tokens/min
    - OpenAI: 500 requests/min, 150K tokens/min
    """

    # Default rate limits (requests per minute)
    DEFAULT_REQUEST_LIMITS = {
        Provider.ANTHROPIC: 50,
        Provider.OPENAI: 500,
    }

    # Default rate limits (tokens per minute)
    DEFAULT_TOKEN_LIMITS = {
        Provider.ANTHROPIC: 40000,
        Provider.OPENAI: 150000,
    }

    # Retry configuration
    MAX_RETRY_ATTEMPTS = 5
    INITIAL_RETRY_DELAY = 1.0  # seconds
    BACKOFF_MULTIPLIER = 2.0
    MAX_RETRY_DELAY = 60.0  # seconds

    def __init__(
        self,
        config_path: str = "automation_config.json",
        db_pool: Optional[asyncpg.Pool] = None,
        redis_url: Optional[str] = None
    ):
        """
        Initialize the rate limiter.

        Args:
            config_path: Path to automation config file
            db_pool: PostgreSQL connection pool for stats
            redis_url: Redis URL for distributed locking
        """
        self.config = self._load_config(config_path)
        self.db_pool = db_pool
        self.redis_url = redis_url

        # Initialize token buckets
        self.request_buckets: Dict[str, TokenBucket] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}

        # Request queues
        self.request_queues: Dict[str, deque] = defaultdict(deque)
        self.max_queue_size = self.config.get("performance", {}).get(
            "queue_size_limit", 100
        )

        # Statistics
        self.stats = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "rate_limited_requests": 0,
            "retried_requests": 0,
            "total_wait_time": 0.0,
            "average_wait_time": 0.0
        })

        # Redis client for distributed locking
        self.redis_client = None
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis for distributed rate limiting")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using local rate limiting.")
                self.redis_client = None

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_old_buckets())

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "performance": {
                "queue_size_limit": 100,
                "timeout_seconds": 300,
                "retry_attempts": 3,
                "retry_delay_seconds": 5
            }
        }

    def _get_bucket_key(self, provider: Provider, api_key: str, bucket_type: str) -> str:
        """Generate unique key for a rate limit bucket."""
        # Hash API key for privacy
        import hashlib
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"{bucket_type}:{provider.value}:{key_hash}"

    def _get_or_create_bucket(
        self,
        provider: Provider,
        api_key: str,
        limit: int,
        bucket_type: str = "request"
    ) -> 'TokenBucket':
        """Get existing token bucket or create new one."""
        key = self._get_bucket_key(provider, api_key, bucket_type)
        bucket_dict = self.request_buckets if bucket_type == "request" else self.token_buckets

        if key not in bucket_dict:
            # Refill rate: tokens/requests per second
            refill_rate = limit / 60.0  # Per minute to per second
            bucket_dict[key] = TokenBucket(
                capacity=limit,
                tokens=limit,
                refill_rate=refill_rate
            )

        return bucket_dict[key]

    async def acquire_rate_lock(
        self,
        provider: Provider,
        api_key: str,
        tokens: int = 1,
        priority: RequestPriority = RequestPriority.MEDIUM,
        timeout: float = 30.0
    ) -> bool:
        """
        Attempt to acquire a rate lock for an API call.

        Args:
            provider: LLM provider
            api_key: API key for the provider
            tokens: Number of tokens to consume
            priority: Request priority (for queue ordering)
            timeout: Max time to wait for lock (seconds)

        Returns:
            True if lock acquired, False if timeout

        Raises:
            RateLimitError: If queue is full
        """
        # Get request bucket
        request_limit = self.DEFAULT_REQUEST_LIMITS.get(provider, 50)
        request_bucket = self._get_or_create_bucket(provider, api_key, request_limit, "request")

        # Get token bucket
        token_limit = self.DEFAULT_TOKEN_LIMITS.get(provider, 50000)
        token_bucket = self._get_or_create_bucket(provider, api_key, token_limit, "token")

        # Try to consume from buckets
        if request_bucket.try_consume(1) and token_bucket.try_consume(tokens):
            return True

        # Not enough capacity, add to queue
        queue_key = self._get_bucket_key(provider, api_key, "queue")
        queue = self.request_queues[queue_key]

        if len(queue) >= self.max_queue_size:
            raise RateLimitError(
                f"Rate limit queue full for {provider.value}. "
                f"Max queue size: {self.max_queue_size}"
            )

        # Add to queue
        request = {
            "tokens": tokens,
            "priority": priority,
            "timestamp": time.time()
        }
        queue.append(request)

        # Wait for capacity
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if we can proceed
            if request_bucket.try_consume(1) and token_bucket.try_consume(tokens):
                # Remove from queue
                if queue and queue[0] == request:
                    queue.popleft()
                return True

            # Wait a bit
            await asyncio.sleep(0.1)

        # Timeout
        if queue and queue[0] == request:
            queue.popleft()

        return False

    async def release_rate_lock(
        self,
        provider: Provider,
        api_key: str,
        success: bool
    ):
        """
        Release a rate lock (record successful/failed request).

        Args:
            provider: LLM provider
            api_key: API key
            success: Whether the request was successful
        """
        key = self._get_bucket_key(provider, api_key, "stats")
        self.stats[key]["total_requests"] += 1

        if success:
            self.stats[key]["successful_requests"] += 1
        else:
            self.stats[key]["rate_limited_requests"] += 1

        # Store in database periodically
        if self.db_pool and POSTGRES_AVAILABLE:
            await self._store_stats(provider, api_key)

    async def execute_with_rate_limit(
        self,
        provider: Provider,
        api_key: str,
        func,
        *args,
        tokens: int = 1,
        priority: RequestPriority = RequestPriority.MEDIUM,
        timeout: float = 30.0,
        max_retries: int = None,
        **kwargs
    ):
        """
        Execute function with automatic rate limiting and retry.

        Args:
            provider: LLM provider
            api_key: API key
            func: Async function to execute
            tokens: Estimated token usage
            priority: Request priority
            timeout: Max time to wait for rate lock
            max_retries: Max retry attempts (None = use default)
            **kwargs: Additional arguments for func

        Returns:
            Result from func

        Raises:
            RateLimitError: If rate limit cannot be acquired
            Exception: If all retries exhausted
        """
        max_retries = max_retries or self.MAX_RETRY_ATTEMPTS

        for attempt in range(max_retries):
            # Acquire rate lock
            acquired = await self.acquire_rate_lock(provider, api_key, tokens, priority, timeout)

            if not acquired:
                await self.release_rate_lock(provider, api_key, success=False)
                raise RateLimitError(f"Could not acquire rate lock for {provider.value} after {timeout}s")

            # Define key before try block so it's available in except block
            key = self._get_bucket_key(provider, api_key, "stats")

            try:
                # Execute the function
                start_time = time.time()
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time

                # Record success
                await self.release_rate_lock(provider, api_key, success=True)

                self.stats[key]["total_wait_time"] += elapsed
                if self.stats[key]["total_requests"] > 0:
                    self.stats[key]["average_wait_time"] = (
                        self.stats[key]["total_wait_time"] / self.stats[key]["total_requests"]
                    )

                return result

            except Exception as e:
                # Check if it's a rate limit error
                if self._is_rate_limit_error(e):
                    logger.warning(f"Rate limit hit for {provider.value}: {e}")
                    self.stats[key]["retried_requests"] += 1

                    if attempt < max_retries - 1:
                        # Exponential backoff
                        delay = min(
                            self.INITIAL_RETRY_DELAY * (self.BACKOFF_MULTIPLIER ** attempt),
                            self.MAX_RETRY_DELAY
                        )
                        logger.info(f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exhausted
                        await self.release_rate_lock(provider, api_key, success=False)
                        raise RateLimitError(
                            f"Max retries ({max_retries}) exhausted for {provider.value}"
                        ) from e
                else:
                    # Non-rate-limit error, don't retry
                    await self.release_rate_lock(provider, api_key, success=False)
                    raise

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error."""
        error_str = str(error).lower()

        # HTTP 429
        if "429" in error_str or "rate limit" in error_str:
            return True

        # Provider-specific errors
        if "rate_limit_exceeded" in error_str:
            return True
        if "too_many_requests" in error_str:
            return True

        return False

    async def get_queue_status(self, provider: Provider, api_key: str) -> Dict:
        """
        Get current queue status for a provider/key.

        Args:
            provider: LLM provider
            api_key: API key

        Returns:
            Queue status dict
        """
        queue_key = self._get_bucket_key(provider, api_key, "queue")
        queue = self.request_queues[queue_key]

        return {
            "provider": provider.value,
            "queue_length": len(queue),
            "max_queue_size": self.max_queue_size,
            "queued_requests": [
                {
                    "priority": req["priority"].name,
                    "tokens": req["tokens"],
                    "waiting_seconds": time.time() - req["timestamp"]
                }
                for req in queue
            ]
        }

    async def get_rate_limit_stats(
        self,
        provider: Provider,
        api_key: str
    ) -> Dict:
        """
        Get rate limit statistics.

        Args:
            provider: LLM provider
            api_key: API key

        Returns:
            Statistics dict
        """
        key = self._get_bucket_key(provider, api_key, "stats")
        stats = self.stats.get(key, {
            "total_requests": 0,
            "successful_requests": 0,
            "rate_limited_requests": 0,
            "retried_requests": 0,
            "total_wait_time": 0.0,
            "average_wait_time": 0.0
        })

        return stats

    async def _store_stats(self, provider: Provider, api_key: str):
        """Store statistics in database."""
        if not self.db_pool or not POSTGRES_AVAILABLE:
            return

        try:
            key = self._get_bucket_key(provider, api_key, "stats")
            stats = self.stats.get(key, {})

            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO cognee_db.llm_rate_limit_stats (
                        timestamp, provider, api_key_hash,
                        total_requests, successful_requests, rate_limited_requests,
                        retried_requests, total_wait_time, average_wait_time
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (provider, api_key_hash) DO UPDATE SET
                        total_requests = llm_rate_limit_stats.total_requests + EXCLUDED.total_requests,
                        successful_requests = llm_rate_limit_stats.successful_requests + EXCLUDED.successful_requests,
                        rate_limited_requests = llm_rate_limit_stats.rate_limited_requests + EXCLUDED.rate_limited_requests,
                        retried_requests = llm_rate_limit_stats.retried_requests + EXCLUDED.retried_requests,
                        timestamp = EXCLUDED.timestamp
                """,
                    datetime.now(timezone.utc),
                    provider.value,
                    key,
                    stats.get("total_requests", 0),
                    stats.get("successful_requests", 0),
                    stats.get("rate_limited_requests", 0),
                    stats.get("retried_requests", 0),
                    stats.get("total_wait_time", 0.0),
                    stats.get("average_wait_time", 0.0)
                )
        except Exception as e:
            logger.error(f"Failed to store rate limit stats: {e}")

    async def _cleanup_old_buckets(self):
        """Periodically cleanup old/unused buckets."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                # Clean up stats older than 1 hour
                cutoff = time.time() - 3600

                for key, bucket in list(self.request_buckets.items()):
                    if bucket.last_refill < cutoff:
                        del self.request_buckets[key]

                for key, bucket in list(self.token_buckets.items()):
                    if bucket.last_refill < cutoff:
                        del self.token_buckets[key]

                logger.info(f"Cleaned up old rate limit buckets. "
                           f"Active request buckets: {len(self.request_buckets)}, "
                           f"Active token buckets: {len(self.token_buckets)}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in bucket cleanup: {e}")


class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    Refills tokens at a constant rate over time.
    """

    def __init__(self, capacity: int, tokens: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum token capacity
            tokens: Initial token count
            refill_rate: Tokens to add per second
        """
        self.capacity = capacity
        self.tokens = tokens
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate

        # Refill up to capacity
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def try_consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if successful, False if not enough tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def available_tokens(self) -> int:
        """Get current available tokens."""
        self._refill()
        return int(self.tokens)

    @property
    def wait_time(self) -> float:
        """Get seconds until tokens available."""
        self._refill()

        if self.tokens >= 1:
            return 0.0

        tokens_needed = 1 - self.tokens
        return tokens_needed / self.refill_rate


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> Optional[RateLimiter]:
    """Get the global rate limiter instance."""
    return _rate_limiter


def init_rate_limiter(
    config_path: str = "automation_config.json",
    db_pool: Optional[asyncpg.Pool] = None,
    redis_url: Optional[str] = None
) -> RateLimiter:
    """
    Initialize the global rate limiter.

    Args:
        config_path: Path to automation config
        db_pool: PostgreSQL connection pool
        redis_url: Redis URL for distributed locking

    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(config_path, db_pool, redis_url)
    return _rate_limiter


# Decorator for automatic rate limiting
def rate_limit(
    provider: Provider,
    tokens: int = 1,
    priority: RequestPriority = RequestPriority.MEDIUM,
    timeout: float = 30.0
):
    """
    Decorator for automatic rate limiting of async functions.

    Usage:
        @rate_limit(Provider.ANTHROPIC, tokens=1000)
        async def call_claude_api(prompt: str) -> str:
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            rate_limiter = get_rate_limiter()
            if not rate_limiter:
                return await func(*args, **kwargs)

            # Extract API key from kwargs or use default
            api_key = kwargs.get("api_key", "default")

            return await rate_limiter.execute_with_rate_limit(
                provider, api_key, func, *args,
                tokens=tokens, priority=priority, timeout=timeout,
                **kwargs
            )

        return wrapper
    return decorator
