"""
Unit tests for src.rate_limiter
================================
Covers RateLimiter, init_rate_limiter, and get_rate_limiter.
All tests are offline (mocked Redis).  No Unicode characters.
asyncio_mode = auto (from pytest.ini), so no extra markers needed.
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Always import the module under test using its package path.
import src.rate_limiter as rl_module
from src.rate_limiter import (
    RateLimiter,
    init_rate_limiter,
    get_rate_limiter,
    _DEFAULT_RULES,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _fresh_limiter(redis_client=None, rules=None) -> RateLimiter:
    """Return a new RateLimiter with an empty in-memory store."""
    rl_module._memory_store.clear()
    return RateLimiter(redis_client=redis_client, rules=rules)


def _make_redis_mock(pipeline_count_result: int = 0, oldest_ts: float = None):
    """
    Build a redis mock that simulates the sliding-window pipeline.

    pipeline_count_result  -- value returned for zcard (count before adding)
    oldest_ts              -- if given, zrange returns [(member, oldest_ts)]
    """
    mock_redis = AsyncMock()

    # Pipeline mock
    mock_pipe = MagicMock()
    mock_pipe.zremrangebyscore = MagicMock()
    mock_pipe.zcard = MagicMock()
    mock_pipe.zadd = MagicMock()
    mock_pipe.expire = MagicMock()
    # execute returns [zremrangebyscore_result, count, zadd_result, expire_result]
    mock_pipe.execute = AsyncMock(
        return_value=[0, pipeline_count_result, 1, True]
    )

    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    if oldest_ts is not None:
        mock_redis.zrange = AsyncMock(return_value=[("member", oldest_ts)])
    else:
        mock_redis.zrange = AsyncMock(return_value=[])

    # get_usage helpers
    mock_redis.zremrangebyscore = AsyncMock(return_value=0)
    mock_redis.zcard = AsyncMock(return_value=pipeline_count_result)

    return mock_redis


# ---------------------------------------------------------------------------
# _get_rule
# ---------------------------------------------------------------------------

class TestGetRule:
    def test_known_tool_returns_specific_rule(self):
        limiter = _fresh_limiter()
        rule = limiter._get_rule("add_memory")
        assert rule["requests"] == 30
        assert rule["window_seconds"] == 60

    def test_unknown_tool_falls_back_to_wildcard(self):
        limiter = _fresh_limiter()
        rule = limiter._get_rule("nonexistent_tool")
        assert rule == _DEFAULT_RULES["*"]

    def test_custom_rule_overrides_default(self):
        custom = {"my_tool": {"requests": 5, "window_seconds": 10}}
        limiter = _fresh_limiter(rules=custom)
        rule = limiter._get_rule("my_tool")
        assert rule["requests"] == 5
        assert rule["window_seconds"] == 10

    def test_wildcard_missing_returns_hardcoded_fallback(self):
        # Remove "*" entirely from rules
        limiter = _fresh_limiter(rules={"*": {"requests": 99, "window_seconds": 1}})
        limiter.rules.pop("*", None)
        rule = limiter._get_rule("anything")
        # Should not raise; returns the hardcoded fallback inside _get_rule
        assert "requests" in rule


# ---------------------------------------------------------------------------
# _redis_key
# ---------------------------------------------------------------------------

class TestRedisKey:
    def test_format(self):
        limiter = _fresh_limiter()
        key = limiter._redis_key("agent-1", "add_memory")
        assert key == "rl:agent-1:add_memory"

    def test_wildcard_tool(self):
        limiter = _fresh_limiter()
        key = limiter._redis_key("agent-1", "*")
        assert key == "rl:agent-1:*"


# ---------------------------------------------------------------------------
# check() - in-memory path (no Redis)
# ---------------------------------------------------------------------------

class TestCheckMemoryPath:
    async def test_first_request_is_allowed(self):
        limiter = _fresh_limiter()
        allowed, wait = await limiter.check("agent-1", "add_memory")
        assert allowed is True
        assert wait == 0.0

    async def test_within_limit_allowed(self):
        limiter = _fresh_limiter()
        # add_memory allows 30/min; make 5 calls
        for _ in range(5):
            allowed, wait = await limiter.check("agent-a", "add_memory")
            assert allowed is True

    async def test_exceeds_limit_denied(self):
        limiter = _fresh_limiter(rules={"test_tool": {"requests": 3, "window_seconds": 60}})
        for _ in range(3):
            allowed, _ = await limiter.check("agent-b", "test_tool")
            assert allowed is True
        # 4th request should be denied
        allowed, retry = await limiter.check("agent-b", "test_tool")
        assert allowed is False
        assert retry >= 0.0

    async def test_retry_after_is_positive_when_denied(self):
        limiter = _fresh_limiter(rules={"t": {"requests": 1, "window_seconds": 30}})
        await limiter.check("agent-c", "t")  # consume quota
        allowed, retry = await limiter.check("agent-c", "t")
        assert not allowed
        assert retry > 0.0

    async def test_old_timestamps_pruned(self):
        """Entries older than the window must be discarded."""
        limiter = _fresh_limiter(rules={"t2": {"requests": 1, "window_seconds": 60}})
        agent = "agent-d"
        # Manually plant a very old timestamp so it gets pruned
        key = f"{agent}:t2"
        rl_module._memory_store[key] = [time.time() - 120]  # 2 minutes ago
        # Even though store had 1 entry, it's outside the window -> allowed
        allowed, wait = await limiter.check(agent, "t2")
        assert allowed is True
        assert wait == 0.0

    async def test_different_agents_isolated(self):
        limiter = _fresh_limiter(rules={"t3": {"requests": 1, "window_seconds": 60}})
        await limiter.check("agent-x", "t3")   # agent-x hits its limit
        allowed, _ = await limiter.check("agent-y", "t3")  # agent-y should still be OK
        assert allowed is True

    async def test_wildcard_tool_uses_global_rule(self):
        limiter = _fresh_limiter()
        allowed, wait = await limiter.check("agent-e", "*")
        assert allowed is True
        assert wait == 0.0


# ---------------------------------------------------------------------------
# check() - Redis path
# ---------------------------------------------------------------------------

class TestCheckRedisPath:
    async def test_redis_allows_when_under_limit(self):
        redis = _make_redis_mock(pipeline_count_result=5)
        limiter = _fresh_limiter(redis_client=redis)
        # 5 < 30 (add_memory limit)
        allowed, wait = await limiter.check("agent-r1", "add_memory")
        assert allowed is True
        assert wait == 0.0

    async def test_redis_denies_when_at_limit_no_oldest(self):
        redis = _make_redis_mock(pipeline_count_result=30, oldest_ts=None)
        limiter = _fresh_limiter(redis_client=redis)
        # 30 >= 30 (add_memory limit)
        allowed, wait = await limiter.check("agent-r2", "add_memory")
        assert allowed is False
        assert wait == 0.0  # no oldest entry -> 0

    async def test_redis_denies_with_retry_after(self):
        now = time.time()
        oldest = now - 10  # 10 seconds into a 60s window -> retry = 50s
        redis = _make_redis_mock(pipeline_count_result=30, oldest_ts=oldest)
        limiter = _fresh_limiter(redis_client=redis)
        allowed, wait = await limiter.check("agent-r3", "add_memory")
        assert allowed is False
        assert wait > 0.0

    async def test_redis_error_falls_back_and_allows(self):
        redis = AsyncMock()
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.zadd = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(side_effect=ConnectionError("Redis down"))
        redis.pipeline = MagicMock(return_value=mock_pipe)

        limiter = _fresh_limiter(redis_client=redis)
        assert limiter._redis_ok is True

        # On error the limiter must still allow and mark _redis_ok = False
        allowed, wait = await limiter.check("agent-r4", "add_memory")
        assert allowed is True
        assert wait == 0.0
        assert limiter._redis_ok is False

    async def test_redis_flag_false_uses_memory_fallback(self):
        redis = MagicMock()  # has .redis but _redis_ok is False
        limiter = _fresh_limiter(redis_client=redis)
        limiter._redis_ok = False
        # Should go through the memory path, not call redis
        allowed, wait = await limiter.check("agent-r5", "cognify")
        assert allowed is True
        redis.pipeline.assert_not_called()


# ---------------------------------------------------------------------------
# set_rule / get_rules
# ---------------------------------------------------------------------------

class TestRuleManagement:
    def test_set_rule_overrides_existing(self):
        limiter = _fresh_limiter()
        limiter.set_rule("add_memory", requests=5, window_seconds=10)
        rule = limiter._get_rule("add_memory")
        assert rule["requests"] == 5
        assert rule["window_seconds"] == 10

    def test_set_rule_adds_new_tool(self):
        limiter = _fresh_limiter()
        limiter.set_rule("brand_new_tool", requests=100, window_seconds=120)
        rule = limiter._get_rule("brand_new_tool")
        assert rule["requests"] == 100

    def test_get_rules_returns_dict_with_expected_keys(self):
        limiter = _fresh_limiter()
        rules = limiter.get_rules()
        assert isinstance(rules, dict)
        assert "add_memory" in rules
        assert "cognify" in rules
        assert "*" in rules

    def test_get_rules_values_are_correct(self):
        limiter = _fresh_limiter()
        rules = limiter.get_rules()
        assert rules["add_memory"]["requests"] == 30
        assert rules["cognify"]["requests"] == 5


# ---------------------------------------------------------------------------
# get_usage()
# ---------------------------------------------------------------------------

class TestGetUsage:
    async def test_get_usage_memory_path_no_requests(self):
        # Use fresh_limiter which clears the module-level store
        limiter = _fresh_limiter()
        # Use a unique agent key that is not polluted by prior tests
        usage = await limiter.get_usage("agent-usage-fresh", "add_memory")
        assert usage["used"] == 0
        assert usage["limit"] == 30
        assert usage["remaining"] == 30
        assert usage["agent_id"] == "agent-usage-fresh"
        assert usage["tool"] == "add_memory"

    async def test_get_usage_memory_path_after_requests(self):
        limiter = _fresh_limiter(rules={"ut": {"requests": 5, "window_seconds": 60}})
        for _ in range(3):
            await limiter.check("agent-u2", "ut")
        usage = await limiter.get_usage("agent-u2", "ut")
        assert usage["used"] == 3
        assert usage["remaining"] == 2

    async def test_get_usage_redis_path(self):
        redis = _make_redis_mock(pipeline_count_result=7)
        limiter = _fresh_limiter(redis_client=redis)
        usage = await limiter.get_usage("agent-u3", "search_memories")
        assert usage["used"] == 7
        assert usage["limit"] == 120
        assert usage["remaining"] == 113

    async def test_get_usage_redis_exception_falls_back(self):
        redis = AsyncMock()
        redis.zremrangebyscore = AsyncMock(side_effect=RuntimeError("boom"))
        limiter = _fresh_limiter(redis_client=redis)
        # Must not raise; falls back to in-memory
        usage = await limiter.get_usage("agent-u4", "add_memory")
        assert isinstance(usage, dict)
        assert "used" in usage


# ---------------------------------------------------------------------------
# Module-level helpers: init_rate_limiter / get_rate_limiter
# ---------------------------------------------------------------------------

class TestModuleHelpers:
    def test_init_returns_rate_limiter(self):
        limiter = init_rate_limiter()
        assert isinstance(limiter, RateLimiter)

    def test_init_sets_singleton(self):
        limiter = init_rate_limiter()
        assert get_rate_limiter() is limiter

    def test_init_with_custom_rules(self):
        limiter = init_rate_limiter(rules={"custom": {"requests": 7, "window_seconds": 5}})
        rule = limiter._get_rule("custom")
        assert rule["requests"] == 7

    def test_get_rate_limiter_before_init_returns_none_or_instance(self):
        # After any previous init call the singleton is set; just verify type
        result = get_rate_limiter()
        assert result is None or isinstance(result, RateLimiter)

    def test_init_without_redis_sets_redis_ok_false(self):
        limiter = init_rate_limiter(redis_client=None)
        assert limiter._redis_ok is False

    def test_init_with_redis_sets_redis_ok_true(self):
        mock_redis = AsyncMock()
        limiter = init_rate_limiter(redis_client=mock_redis)
        assert limiter._redis_ok is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    async def test_no_redis_no_rules_uses_defaults(self):
        limiter = RateLimiter()
        assert "*" in limiter.rules

    async def test_ingest_db_very_low_limit(self):
        limiter = _fresh_limiter()
        # ingest_db limit is 2/min
        for _ in range(2):
            allowed, _ = await limiter.check("agent-e1", "ingest_db")
            assert allowed is True
        allowed, wait = await limiter.check("agent-e1", "ingest_db")
        assert allowed is False
        assert wait >= 0.0

    async def test_restore_backup_limit_one_in_five_min(self):
        limiter = _fresh_limiter()
        allowed, _ = await limiter.check("agent-e2", "restore_backup")
        assert allowed is True
        allowed, wait = await limiter.check("agent-e2", "restore_backup")
        assert allowed is False
        assert wait > 0.0

    async def test_memory_store_cleanup_each_call(self):
        """Verify _memory_store is pruned on each call (no unbounded growth)."""
        limiter = _fresh_limiter(rules={"t4": {"requests": 100, "window_seconds": 1}})
        key = "agent-e3:t4"
        # Seed old timestamps that are outside the window
        old = [time.time() - 10] * 50
        rl_module._memory_store[key] = old
        # After check, old timestamps should be pruned
        await limiter.check("agent-e3", "t4")
        assert len(rl_module._memory_store[key]) < 50
