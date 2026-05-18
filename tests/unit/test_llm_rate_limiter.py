"""
Unit tests for src.llm.rate_limiter
======================================
Tests RateLimiter, TokenBucket, Provider, RequestPriority,
RateLimitError, get_rate_limiter, init_rate_limiter, and rate_limit decorator.
All external I/O (file, Redis, DB) is mocked.
No Unicode characters in assertions.
"""

import asyncio
import time
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_pool():
    """Build a minimal asyncpg pool mock."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    class MockAcquireCtx:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=MockAcquireCtx())
    return mock_pool, mock_conn


def _make_rate_limiter(config_path="nonexistent.json", db_pool=None, redis_url=None):
    """Create RateLimiter with asyncio task creation suppressed."""
    from src.llm.rate_limiter import RateLimiter
    with patch.object(asyncio, "create_task", return_value=MagicMock()):
        limiter = RateLimiter(
            config_path=config_path,
            db_pool=db_pool,
            redis_url=redis_url
        )
    return limiter


# ---------------------------------------------------------------------------
# Provider / RequestPriority enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_provider_values(self):
        from src.llm.rate_limiter import Provider
        assert Provider.ANTHROPIC.value == "anthropic"
        assert Provider.OPENAI.value == "openai"
        assert Provider.LITELLM.value == "litellm"

    def test_request_priority_ordering(self):
        from src.llm.rate_limiter import RequestPriority
        assert RequestPriority.HIGH.value < RequestPriority.MEDIUM.value
        assert RequestPriority.MEDIUM.value < RequestPriority.LOW.value


# ---------------------------------------------------------------------------
# RateLimitError
# ---------------------------------------------------------------------------

class TestRateLimitError:
    def test_is_exception(self):
        from src.llm.rate_limiter import RateLimitError
        with pytest.raises(RateLimitError):
            raise RateLimitError("rate limited")

    def test_message(self):
        from src.llm.rate_limiter import RateLimitError
        err = RateLimitError("exceeded")
        assert "exceeded" in str(err)


# ---------------------------------------------------------------------------
# TokenBucket
# ---------------------------------------------------------------------------

class TestTokenBucket:
    def test_init(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=100, tokens=100, refill_rate=1.0)
        assert bucket.capacity == 100
        assert bucket.tokens == 100
        assert bucket.refill_rate == 1.0

    def test_try_consume_success(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=100, tokens=10, refill_rate=0.0)
        assert bucket.try_consume(5) is True
        assert bucket.tokens == pytest.approx(5, abs=1)

    def test_try_consume_fails_when_insufficient(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=10, tokens=3, refill_rate=0.0)
        assert bucket.try_consume(5) is False

    def test_try_consume_exactly_available(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=10, tokens=5, refill_rate=0.0)
        assert bucket.try_consume(5) is True

    def test_refill_adds_tokens_over_time(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=100, tokens=0, refill_rate=10.0)
        # Simulate time passage by backdating last_refill
        bucket.last_refill = time.time() - 5.0  # 5 seconds ago, 50 tokens should be added
        bucket._refill()
        assert bucket.tokens == pytest.approx(50, abs=2)

    def test_refill_does_not_exceed_capacity(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=10, tokens=10, refill_rate=100.0)
        bucket.last_refill = time.time() - 10.0
        bucket._refill()
        assert bucket.tokens <= bucket.capacity

    def test_available_tokens_property(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=50, tokens=20, refill_rate=0.0)
        assert bucket.available_tokens == 20

    def test_wait_time_zero_when_tokens_available(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=50, tokens=10, refill_rate=1.0)
        assert bucket.wait_time == 0.0

    def test_wait_time_positive_when_no_tokens(self):
        from src.llm.rate_limiter import TokenBucket
        bucket = TokenBucket(capacity=50, tokens=0, refill_rate=1.0)
        wait = bucket.wait_time
        assert wait > 0.0


# ---------------------------------------------------------------------------
# RateLimiter - config loading
# ---------------------------------------------------------------------------

class TestRateLimiterConfig:
    def test_default_config_used_when_file_not_found(self):
        limiter = _make_rate_limiter(config_path="nonexistent_config_xyz.json")
        assert limiter.max_queue_size == 100  # default

    def test_invalid_json_uses_default(self):
        with patch("builtins.open", mock_open(read_data="NOT VALID JSON")):
            limiter = _make_rate_limiter(config_path="bad.json")
        assert limiter.max_queue_size == 100

    def test_valid_config_loaded(self):
        config = {"performance": {"queue_size_limit": 50}}
        with patch("builtins.open", mock_open(read_data=json.dumps(config))):
            limiter = _make_rate_limiter(config_path="valid.json")
        assert limiter.max_queue_size == 50

    def test_get_default_config(self):
        limiter = _make_rate_limiter()
        default = limiter._get_default_config()
        assert "performance" in default
        assert default["performance"]["queue_size_limit"] == 100


# ---------------------------------------------------------------------------
# RateLimiter - bucket key generation
# ---------------------------------------------------------------------------

class TestBucketKey:
    def test_key_format_is_consistent(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        k1 = limiter._get_bucket_key(Provider.ANTHROPIC, "api-key-123", "request")
        k2 = limiter._get_bucket_key(Provider.ANTHROPIC, "api-key-123", "request")
        assert k1 == k2

    def test_different_providers_give_different_keys(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        k1 = limiter._get_bucket_key(Provider.ANTHROPIC, "key", "request")
        k2 = limiter._get_bucket_key(Provider.OPENAI, "key", "request")
        assert k1 != k2

    def test_different_types_give_different_keys(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        k1 = limiter._get_bucket_key(Provider.ANTHROPIC, "key", "request")
        k2 = limiter._get_bucket_key(Provider.ANTHROPIC, "key", "token")
        assert k1 != k2


# ---------------------------------------------------------------------------
# RateLimiter - get_or_create_bucket
# ---------------------------------------------------------------------------

class TestGetOrCreateBucket:
    def test_creates_bucket_on_first_call(self):
        from src.llm.rate_limiter import Provider, TokenBucket
        limiter = _make_rate_limiter()
        bucket = limiter._get_or_create_bucket(Provider.ANTHROPIC, "key", 60, "request")
        assert isinstance(bucket, TokenBucket)

    def test_returns_same_bucket_on_second_call(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        b1 = limiter._get_or_create_bucket(Provider.ANTHROPIC, "key", 60, "request")
        b2 = limiter._get_or_create_bucket(Provider.ANTHROPIC, "key", 60, "request")
        assert b1 is b2

    def test_token_bucket_type(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        bucket = limiter._get_or_create_bucket(Provider.ANTHROPIC, "key", 60, "token")
        key = limiter._get_bucket_key(Provider.ANTHROPIC, "key", "token")
        assert key in limiter.token_buckets


# ---------------------------------------------------------------------------
# RateLimiter - acquire_rate_lock
# ---------------------------------------------------------------------------

class TestAcquireRateLock:
    async def test_acquire_succeeds_when_capacity_available(self):
        from src.llm.rate_limiter import Provider, RequestPriority
        limiter = _make_rate_limiter()
        result = await limiter.acquire_rate_lock(Provider.ANTHROPIC, "key", tokens=1)
        assert result is True

    async def test_queue_full_raises_rate_limit_error(self):
        from src.llm.rate_limiter import Provider, RateLimitError
        limiter = _make_rate_limiter()
        limiter.max_queue_size = 0

        # Drain the request bucket to force queuing
        request_bucket = limiter._get_or_create_bucket(
            Provider.ANTHROPIC, "key",
            limiter.DEFAULT_REQUEST_LIMITS[Provider.ANTHROPIC],
            "request"
        )
        request_bucket.tokens = 0

        with pytest.raises(RateLimitError, match="queue full"):
            await limiter.acquire_rate_lock(Provider.ANTHROPIC, "key", tokens=1, timeout=0.01)

    async def test_acquire_returns_false_on_timeout(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()

        # Drain both buckets
        req_bucket = limiter._get_or_create_bucket(
            Provider.ANTHROPIC, "key",
            limiter.DEFAULT_REQUEST_LIMITS[Provider.ANTHROPIC],
            "request"
        )
        req_bucket.tokens = 0
        tok_bucket = limiter._get_or_create_bucket(
            Provider.ANTHROPIC, "key",
            limiter.DEFAULT_TOKEN_LIMITS[Provider.ANTHROPIC],
            "token"
        )
        tok_bucket.tokens = 0

        result = await limiter.acquire_rate_lock(Provider.ANTHROPIC, "key", tokens=1, timeout=0.05)
        assert result is False


# ---------------------------------------------------------------------------
# RateLimiter - release_rate_lock
# ---------------------------------------------------------------------------

class TestReleaseRateLock:
    async def test_release_records_success(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        await limiter.release_rate_lock(Provider.ANTHROPIC, "key", success=True)
        key = limiter._get_bucket_key(Provider.ANTHROPIC, "key", "stats")
        assert limiter.stats[key]["successful_requests"] == 1

    async def test_release_records_failure(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        await limiter.release_rate_lock(Provider.ANTHROPIC, "key", success=False)
        key = limiter._get_bucket_key(Provider.ANTHROPIC, "key", "stats")
        assert limiter.stats[key]["rate_limited_requests"] == 1

    async def test_release_with_db_stores_stats(self):
        from src.llm.rate_limiter import Provider
        pool, conn = _make_db_pool()
        limiter = _make_rate_limiter(db_pool=pool)

        with patch("src.llm.rate_limiter.POSTGRES_AVAILABLE", True):
            await limiter.release_rate_lock(Provider.ANTHROPIC, "key", success=True)

        conn.execute.assert_called_once()


# ---------------------------------------------------------------------------
# RateLimiter - execute_with_rate_limit
# ---------------------------------------------------------------------------

class TestExecuteWithRateLimit:
    async def test_successful_execution(self):
        from src.llm.rate_limiter import Provider

        async def target_func(x):
            return x * 2

        limiter = _make_rate_limiter()
        result = await limiter.execute_with_rate_limit(
            Provider.ANTHROPIC, "key", target_func, 21
        )
        assert result == 42

    async def test_rate_limit_error_raised_on_acquire_failure(self):
        from src.llm.rate_limiter import Provider, RateLimitError

        async def target_func():
            return "ok"

        limiter = _make_rate_limiter()
        # Force acquire to fail
        with patch.object(limiter, "acquire_rate_lock", AsyncMock(return_value=False)):
            with pytest.raises(RateLimitError, match="Could not acquire"):
                await limiter.execute_with_rate_limit(
                    Provider.ANTHROPIC, "key", target_func, timeout=0.1
                )

    async def test_rate_limit_error_from_function_triggers_retry(self):
        from src.llm.rate_limiter import Provider, RateLimitError

        call_count = {"n": 0}

        async def flaky_func():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise Exception("429 rate limit")
            return "ok"

        limiter = _make_rate_limiter()
        result = await limiter.execute_with_rate_limit(
            Provider.ANTHROPIC, "key", flaky_func,
            max_retries=5, timeout=5.0
        )
        assert result == "ok"
        assert call_count["n"] == 3

    async def test_non_rate_limit_error_propagates_immediately(self):
        from src.llm.rate_limiter import Provider

        async def bad_func():
            raise ValueError("database connection timeout")

        limiter = _make_rate_limiter()
        with pytest.raises(ValueError, match="database connection timeout"):
            await limiter.execute_with_rate_limit(
                Provider.ANTHROPIC, "key", bad_func, max_retries=3
            )

    async def test_max_retries_exhausted_raises_rate_limit_error(self):
        from src.llm.rate_limiter import Provider, RateLimitError

        async def always_429():
            raise Exception("429 rate limit exceeded")

        limiter = _make_rate_limiter()
        with pytest.raises(RateLimitError, match="Max retries"):
            await limiter.execute_with_rate_limit(
                Provider.ANTHROPIC, "key", always_429,
                max_retries=2, timeout=5.0
            )


# ---------------------------------------------------------------------------
# _is_rate_limit_error
# ---------------------------------------------------------------------------

class TestIsRateLimitError:
    def test_429_in_error_string(self):
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(Exception("HTTP 429 Too Many Requests")) is True

    def test_rate_limit_in_error_string(self):
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(Exception("rate limit exceeded")) is True

    def test_rate_limit_exceeded_keyword(self):
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(Exception("rate_limit_exceeded")) is True

    def test_too_many_requests_keyword(self):
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(Exception("too_many_requests")) is True

    def test_regular_error_returns_false(self):
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(Exception("database connection failed")) is False

    def test_value_error_returns_false(self):
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(ValueError("invalid input")) is False

    # ----- BUG-FIX REGRESSION TESTS -----
    # Previously _is_rate_limit_error used a naive substring check on
    # `"rate limit" in error_str.lower()`, which caused false positives for
    # messages that *mentioned* rate limiting but did not describe one.
    # The fix uses class-name detection + HTTP status_code + word-anchored
    # regex with a negation guard. Verify all the false-positive cases.

    def test_negation_not_a_rate_limit_error(self):
        limiter = _make_rate_limiter()
        # Previously returned True (false positive). Now False.
        assert limiter._is_rate_limit_error(
            Exception("not a rate limit error")
        ) is False

    def test_negation_no_rate_limit_applicable(self):
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(
            Exception("no rate limit applicable to this endpoint")
        ) is False

    def test_negation_without_rate_limit(self):
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(
            Exception("operation completed without rate limit interference")
        ) is False

    def test_class_name_detection_anthropic_style(self):
        # Real-world: anthropic-py raises a RateLimitError class with empty
        # message. Substring check would have missed it; class-name check finds it.
        class RateLimitError(Exception):
            pass
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(RateLimitError("")) is True

    def test_class_name_detection_openai_style(self):
        class TooManyRequestsError(Exception):
            pass
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(TooManyRequestsError()) is True

    def test_http_status_attribute_detection(self):
        # httpx / requests-style: error carries a .status_code attribute
        err = Exception("Something happened")
        err.status_code = 429
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(err) is True

    def test_response_nested_status_detection(self):
        # openai-py / anthropic-py-style: status nested under .response
        class FakeResponse:
            status_code = 429
        err = Exception("API error")
        err.response = FakeResponse()
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(err) is True

    def test_429_not_standalone_returns_false(self):
        # "1429 transactions" should NOT match (was a false positive with
        # substring matching).
        limiter = _make_rate_limiter()
        assert limiter._is_rate_limit_error(
            Exception("Processed 1429 transactions in batch")
        ) is False


# ---------------------------------------------------------------------------
# get_queue_status
# ---------------------------------------------------------------------------

class TestGetQueueStatus:
    async def test_empty_queue_status(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        status = await limiter.get_queue_status(Provider.ANTHROPIC, "key")
        assert status["provider"] == "anthropic"
        assert status["queue_length"] == 0
        assert status["max_queue_size"] == limiter.max_queue_size

    async def test_queue_status_with_queued_requests(self):
        from src.llm.rate_limiter import Provider, RequestPriority
        limiter = _make_rate_limiter()
        queue_key = limiter._get_bucket_key(Provider.ANTHROPIC, "key", "queue")
        limiter.request_queues[queue_key].append({
            "tokens": 100,
            "priority": RequestPriority.HIGH,
            "timestamp": time.time() - 5
        })
        status = await limiter.get_queue_status(Provider.ANTHROPIC, "key")
        assert status["queue_length"] == 1
        assert status["queued_requests"][0]["tokens"] == 100
        assert status["queued_requests"][0]["waiting_seconds"] >= 5


# ---------------------------------------------------------------------------
# get_rate_limit_stats
# ---------------------------------------------------------------------------

class TestGetRateLimitStats:
    async def test_returns_default_stats_for_new_key(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        stats = await limiter.get_rate_limit_stats(Provider.ANTHROPIC, "new-key")
        assert stats["total_requests"] == 0
        assert stats["successful_requests"] == 0

    async def test_returns_recorded_stats(self):
        from src.llm.rate_limiter import Provider
        limiter = _make_rate_limiter()
        await limiter.release_rate_lock(Provider.ANTHROPIC, "key", success=True)
        await limiter.release_rate_lock(Provider.ANTHROPIC, "key", success=False)
        stats = await limiter.get_rate_limit_stats(Provider.ANTHROPIC, "key")
        assert stats["total_requests"] == 2
        assert stats["successful_requests"] == 1


# ---------------------------------------------------------------------------
# _store_stats (with DB)
# ---------------------------------------------------------------------------

class TestStoreStats:
    async def test_store_stats_exception_is_logged(self):
        from src.llm.rate_limiter import Provider
        pool, conn = _make_db_pool()
        conn.execute = AsyncMock(side_effect=Exception("DB down"))
        limiter = _make_rate_limiter(db_pool=pool)

        with patch("src.llm.rate_limiter.POSTGRES_AVAILABLE", True):
            # Should not raise
            await limiter._store_stats(Provider.ANTHROPIC, "key")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

class TestModuleHelpers:
    def test_init_returns_rate_limiter(self):
        from src.llm.rate_limiter import init_rate_limiter, RateLimiter
        with patch.object(asyncio, "create_task", return_value=MagicMock()):
            rl = init_rate_limiter()
        assert isinstance(rl, RateLimiter)

    def test_init_sets_singleton(self):
        from src.llm.rate_limiter import init_rate_limiter, get_rate_limiter
        with patch.object(asyncio, "create_task", return_value=MagicMock()):
            rl = init_rate_limiter()
        assert get_rate_limiter() is rl

    def test_get_before_init_returns_none_or_instance(self):
        from src.llm.rate_limiter import get_rate_limiter, RateLimiter
        result = get_rate_limiter()
        assert result is None or isinstance(result, RateLimiter)


# ---------------------------------------------------------------------------
# rate_limit decorator
# ---------------------------------------------------------------------------

class TestRateLimitDecorator:
    async def test_decorator_calls_function_without_rate_limiter(self):
        from src.llm.rate_limiter import rate_limit, Provider
        import src.llm.rate_limiter as rl_module

        # Ensure no global rate limiter
        original = rl_module._rate_limiter
        rl_module._rate_limiter = None

        @rate_limit(Provider.ANTHROPIC, tokens=100)
        async def test_fn(x):
            return x * 3

        result = await test_fn(7)
        assert result == 21

        rl_module._rate_limiter = original

    async def test_decorator_uses_rate_limiter_when_available(self):
        from src.llm.rate_limiter import rate_limit, Provider
        import src.llm.rate_limiter as rl_module

        mock_limiter = MagicMock()
        mock_limiter.execute_with_rate_limit = AsyncMock(return_value="mocked")
        original = rl_module._rate_limiter
        rl_module._rate_limiter = mock_limiter

        @rate_limit(Provider.ANTHROPIC, tokens=100)
        async def test_fn():
            return "direct"

        result = await test_fn()
        assert result == "mocked"
        mock_limiter.execute_with_rate_limit.assert_called_once()

        rl_module._rate_limiter = original

    async def test_decorator_uses_default_api_key_when_not_in_kwargs(self):
        """The decorator extracts 'api_key' from kwargs or uses 'default'."""
        from src.llm.rate_limiter import rate_limit, Provider
        import src.llm.rate_limiter as rl_module

        captured = {}
        mock_limiter = MagicMock()

        async def fake_execute(provider, api_key, func, *a, **kw):
            captured["api_key"] = api_key
            return "mocked"

        mock_limiter.execute_with_rate_limit = fake_execute
        original = rl_module._rate_limiter
        rl_module._rate_limiter = mock_limiter

        @rate_limit(Provider.ANTHROPIC, tokens=100)
        async def test_fn():
            return "ok"

        result = await test_fn()
        # When no api_key kwarg, defaults to "default"
        assert captured["api_key"] == "default"

        rl_module._rate_limiter = original
