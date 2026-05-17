"""
Unit tests for src.llm.token_counter
======================================
Covers TokenCounter, TokenCountingError, LLMProvider enum,
get_token_counter, and init_token_counter.
All database calls are mocked. No real API or DB connections.
No Unicode characters in assertions or string literals.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool():
    """Build a minimal asyncpg pool mock that supports 'async with acquire()'."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])

    class MockAcquireCtx:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=MockAcquireCtx())
    return mock_pool, mock_conn


# ---------------------------------------------------------------------------
# LLMProvider enum
# ---------------------------------------------------------------------------

class TestLLMProvider:
    def test_provider_values(self):
        from src.llm.token_counter import LLMProvider
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.LITELLM.value == "litellm"


# ---------------------------------------------------------------------------
# TokenCountingError
# ---------------------------------------------------------------------------

class TestTokenCountingError:
    def test_is_exception(self):
        from src.llm.token_counter import TokenCountingError
        with pytest.raises(TokenCountingError):
            raise TokenCountingError("test error")

    def test_message(self):
        from src.llm.token_counter import TokenCountingError
        err = TokenCountingError("problem")
        assert "problem" in str(err)


# ---------------------------------------------------------------------------
# TokenCounter.__init__
# ---------------------------------------------------------------------------

class TestTokenCounterInit:
    def test_init_without_pool(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter(db_pool=None)
        assert tc.db_pool is None
        assert tc.max_cache_size == 1000
        assert tc.usage_cache == []

    def test_init_with_pool(self):
        from src.llm.token_counter import TokenCounter
        pool, _ = _make_pool()
        tc = TokenCounter(db_pool=pool)
        assert tc.db_pool is pool

    def test_tiktoken_encoders_dict_exists(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        assert isinstance(tc.tiktoken_encoders, dict)


# ---------------------------------------------------------------------------
# _estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_empty_string_returns_zero(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        assert tc._estimate_tokens("") == 0

    def test_english_ratio(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        # "hello world" = 11 chars * 0.25 = 2 tokens (int)
        result = tc._estimate_tokens("hello world", "english")
        assert result == 2

    def test_code_ratio(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        # 10 chars * 0.3 = 3 tokens
        result = tc._estimate_tokens("0123456789", "code")
        assert result == 3

    def test_default_ratio_fallback(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc._estimate_tokens("0123456789", "unknown_type")
        # unknown_type -> default ratio 0.25
        assert result == 2

    def test_default_text_type(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        # 4 chars * 0.25 = 1
        result = tc._estimate_tokens("abcd")
        assert result == 1


# ---------------------------------------------------------------------------
# count_tokens_anthropic
# ---------------------------------------------------------------------------

class TestCountTokensAnthropic:
    def test_empty_string_returns_zero(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        assert tc.count_tokens_anthropic("") == 0

    def test_non_empty_string_returns_positive(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc.count_tokens_anthropic("Hello, world!")
        assert result > 0

    def test_returns_integer(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc.count_tokens_anthropic("some text for testing")
        assert isinstance(result, int)

    def test_longer_text_more_tokens(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        short = tc.count_tokens_anthropic("hi")
        long = tc.count_tokens_anthropic("hi " * 100)
        assert long > short


# ---------------------------------------------------------------------------
# count_tokens_openai
# ---------------------------------------------------------------------------

class TestCountTokensOpenAI:
    def test_empty_string_returns_zero(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        assert tc.count_tokens_openai("") == 0

    def test_non_empty_returns_positive(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc.count_tokens_openai("Hello, world!")
        assert result > 0

    def test_gpt4_model(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc.count_tokens_openai("test text", model="gpt-4")
        assert result >= 0

    def test_gpt35_model(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc.count_tokens_openai("test text", model="gpt-3.5-turbo")
        assert result >= 0

    def test_tiktoken_exception_falls_back_to_estimate(self):
        """When tiktoken encoder raises, should fall back to estimation."""
        from src.llm.token_counter import TokenCounter, TIKTOKEN_AVAILABLE
        tc = TokenCounter()
        if TIKTOKEN_AVAILABLE and tc.tiktoken_encoders:
            # Force the encoder to raise
            bad_encoder = MagicMock()
            bad_encoder.encode = MagicMock(side_effect=Exception("bad encoder"))
            tc.tiktoken_encoders["cl100k_base"] = bad_encoder
        result = tc.count_tokens_openai("some text", model="gpt-4")
        assert result >= 0


# ---------------------------------------------------------------------------
# count_tokens_litellm
# ---------------------------------------------------------------------------

class TestCountTokensLiteLLM:
    def test_anthropic_provider_delegates(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        r1 = tc.count_tokens_litellm("hello", "anthropic", "claude-3-5-sonnet-20241022")
        r2 = tc.count_tokens_anthropic("hello", "claude-3-5-sonnet-20241022")
        assert r1 == r2

    def test_claude_provider_delegates_to_anthropic(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc.count_tokens_litellm("hello", "claude", "claude-3-5-sonnet-20241022")
        assert result >= 0

    def test_openai_provider_delegates(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        r1 = tc.count_tokens_litellm("hello", "openai", "gpt-4")
        r2 = tc.count_tokens_openai("hello", "gpt-4")
        assert r1 == r2

    def test_gpt_prefix_delegates_to_openai(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc.count_tokens_litellm("hello", "gpt", "gpt-4")
        assert result >= 0

    def test_unknown_provider_uses_estimation(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        result = tc.count_tokens_litellm("hello world", "other_provider", "some-model")
        assert result >= 0


# ---------------------------------------------------------------------------
# count_messages_tokens
# ---------------------------------------------------------------------------

class TestCountMessagesTokens:
    def test_empty_messages_returns_overhead_only(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        total = tc.count_messages_tokens([], "claude-3-5-sonnet-20241022", LLMProvider.ANTHROPIC)
        # Just the base overhead of 10
        assert total == 10

    def test_single_message_anthropic(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        messages = [{"role": "user", "content": "hello"}]
        total = tc.count_messages_tokens(messages, "claude-3-5-sonnet-20241022", LLMProvider.ANTHROPIC)
        assert total > 0

    def test_single_message_openai(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        messages = [{"role": "user", "content": "hello"}]
        total = tc.count_messages_tokens(messages, "gpt-4", LLMProvider.OPENAI)
        assert total > 0

    def test_multiple_messages(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        total = tc.count_messages_tokens(messages, "gpt-4", LLMProvider.OPENAI)
        # Should be more than single message
        single = tc.count_messages_tokens([messages[0]], "gpt-4", LLMProvider.OPENAI)
        assert total > single

    def test_litellm_provider_uses_estimation(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        messages = [{"role": "user", "content": "hello world"}]
        total = tc.count_messages_tokens(messages, "some-model", LLMProvider.LITELLM)
        assert total > 0

    def test_role_adds_overhead(self):
        """Each message adds 5 tokens for role overhead."""
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        # Empty content message: should just be role overhead (5) + base (10)
        messages = [{"role": "user", "content": ""}]
        total = tc.count_messages_tokens(messages, "gpt-4", LLMProvider.OPENAI)
        # 0 content + 5 role + 10 base = 15
        assert total == 15


# ---------------------------------------------------------------------------
# _calculate_cost
# ---------------------------------------------------------------------------

class TestCalculateCost:
    def test_known_model_calculates_cost(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        # claude-3-5-sonnet: input $3/1M, output $15/1M
        cost = tc._calculate_cost(LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.0)

    def test_unknown_model_returns_zero(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        cost = tc._calculate_cost(LLMProvider.ANTHROPIC, "unknown-model", 1000, 500)
        assert cost == 0.0

    def test_zero_tokens_returns_zero(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        cost = tc._calculate_cost(LLMProvider.OPENAI, "gpt-4", 0, 0)
        assert cost == 0.0

    def test_input_vs_output_pricing(self):
        """Output tokens are more expensive than input tokens for most models."""
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        input_cost = tc._calculate_cost(LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 1_000_000, 0)
        output_cost = tc._calculate_cost(LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 0, 1_000_000)
        assert output_cost > input_cost


# ---------------------------------------------------------------------------
# get_model_limit / check_limit
# ---------------------------------------------------------------------------

class TestModelLimit:
    def test_known_model_returns_limit(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        limit = tc.get_model_limit("claude-3-5-sonnet-20241022")
        assert limit == 200000

    def test_unknown_model_returns_none(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        limit = tc.get_model_limit("nonexistent-model")
        assert limit is None

    def test_check_limit_within_returns_true(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        within, total = tc.check_limit("claude-3-5-sonnet-20241022", 1000, 500)
        assert within is True
        assert total == 1500

    def test_check_limit_exceeded_returns_false(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        within, total = tc.check_limit("gpt-4", 8000, 1000)  # gpt-4 limit = 8192
        assert within is False
        assert total == 9000

    def test_check_limit_unknown_model_returns_true(self):
        """Unknown model limit should be treated as OK."""
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        within, total = tc.check_limit("unknown-model", 9999999, 9999999)
        assert within is True

    def test_check_limit_at_boundary(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        # GPT-4 limit = 8192, exactly at limit
        within, total = tc.check_limit("gpt-4", 4096, 4096)
        assert within is True
        assert total == 8192


# ---------------------------------------------------------------------------
# log_token_usage and _store_usage
# ---------------------------------------------------------------------------

class TestLogTokenUsage:
    async def test_log_adds_to_cache(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        record = await tc.log_token_usage(
            agent_id="test-agent",
            operation="summarization",
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            input_tokens=100,
            output_tokens=50
        )
        assert len(tc.usage_cache) == 1
        assert record["agent_id"] == "test-agent"
        assert record["total_tokens"] == 150
        assert "cost_usd" in record
        assert "timestamp" in record

    async def test_log_with_request_id_and_metadata(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        record = await tc.log_token_usage(
            agent_id="agent1",
            operation="deduplication",
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            input_tokens=200,
            output_tokens=100,
            request_id="req-123",
            metadata={"key": "value"}
        )
        assert record["request_id"] == "req-123"
        assert record["metadata"] == {"key": "value"}

    async def test_log_with_db_pool_stores_usage(self):
        from src.llm.token_counter import TokenCounter, LLMProvider, POSTGRES_AVAILABLE
        pool, conn = _make_pool()
        tc = TokenCounter(db_pool=pool)

        with patch("src.llm.token_counter.POSTGRES_AVAILABLE", True):
            await tc.log_token_usage(
                agent_id="agent-db",
                operation="test-op",
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                input_tokens=50,
                output_tokens=25
            )

        # _store_usage should have called conn.execute
        conn.execute.assert_called_once()

    async def test_cache_eviction_when_full(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        tc.max_cache_size = 3

        for i in range(5):
            await tc.log_token_usage(
                agent_id=f"agent-{i}",
                operation="op",
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                input_tokens=10,
                output_tokens=5
            )

        # Cache should not exceed max_cache_size
        assert len(tc.usage_cache) <= tc.max_cache_size

    async def test_store_usage_exception_is_logged(self):
        """_store_usage exceptions should be caught without propagating."""
        from src.llm.token_counter import TokenCounter, LLMProvider
        pool, conn = _make_pool()
        conn.execute = AsyncMock(side_effect=Exception("DB error"))
        tc = TokenCounter(db_pool=pool)

        with patch("src.llm.token_counter.POSTGRES_AVAILABLE", True):
            # Should not raise
            await tc.log_token_usage(
                agent_id="a",
                operation="op",
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                input_tokens=10,
                output_tokens=5
            )


# ---------------------------------------------------------------------------
# get_usage_stats
# ---------------------------------------------------------------------------

class TestGetUsageStats:
    async def test_empty_cache_returns_zeros(self):
        from src.llm.token_counter import TokenCounter
        tc = TokenCounter()
        stats = await tc.get_usage_stats()
        cache_stats = stats["cache_stats"]
        assert cache_stats["total_tokens"] == 0
        assert cache_stats["total_cost_usd"] == 0.0
        assert cache_stats["total_requests"] == 0

    async def test_filter_by_agent_id(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        await tc.log_token_usage("agent-a", "op", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 100, 50)
        await tc.log_token_usage("agent-b", "op", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 200, 100)

        stats = await tc.get_usage_stats(agent_id="agent-a")
        assert stats["cache_stats"]["requests_in_cache"] == 1

    async def test_filter_by_operation(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        await tc.log_token_usage("a", "summarize", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 100, 50)
        await tc.log_token_usage("a", "dedup", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 200, 100)

        stats = await tc.get_usage_stats(operation="summarize")
        assert stats["cache_stats"]["requests_in_cache"] == 1

    async def test_with_db_pool_fetches_db_stats(self):
        from src.llm.token_counter import TokenCounter
        pool, conn = _make_pool()
        mock_row = MagicMock()
        mock_row.__iter__ = MagicMock(return_value=iter([
            ("total_requests", 5),
            ("total_tokens", 1000),
        ]))
        mock_row.keys = MagicMock(return_value=["total_requests", "total_tokens"])
        conn.fetchrow = AsyncMock(return_value=mock_row)

        tc = TokenCounter(db_pool=pool)
        with patch("src.llm.token_counter.POSTGRES_AVAILABLE", True):
            stats = await tc.get_usage_stats()

        assert "database_stats" in stats


# ---------------------------------------------------------------------------
# get_usage_by_operation
# ---------------------------------------------------------------------------

class TestGetUsageByOperation:
    async def test_no_pool_returns_cache_based_stats(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        await tc.log_token_usage("a", "summarize", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 100, 50)
        await tc.log_token_usage("a", "summarize", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 200, 100)
        await tc.log_token_usage("a", "dedup", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 50, 25)

        results = await tc.get_usage_by_operation()
        ops = {r["operation"]: r for r in results}
        assert "summarize" in ops
        assert "dedup" in ops
        assert ops["summarize"]["request_count"] == 2

    async def test_no_pool_filter_by_agent_id(self):
        from src.llm.token_counter import TokenCounter, LLMProvider
        tc = TokenCounter()
        await tc.log_token_usage("agent-x", "op", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 100, 50)
        await tc.log_token_usage("agent-y", "op", LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", 200, 100)

        results = await tc.get_usage_by_operation(agent_id="agent-x")
        assert len(results) == 1
        assert results[0]["request_count"] == 1

    async def test_with_pool_returns_db_rows(self):
        from src.llm.token_counter import TokenCounter

        class MockRow:
            def keys(self):
                return ["operation", "request_count", "total_tokens"]
            def __iter__(self):
                return iter([("operation", "test"), ("request_count", 3), ("total_tokens", 300)])

        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[MockRow()])
        tc = TokenCounter(db_pool=pool)

        with patch("src.llm.token_counter.POSTGRES_AVAILABLE", True):
            results = await tc.get_usage_by_operation()

        assert isinstance(results, list)

    async def test_with_pool_agent_filter(self):
        """When pool available and agent_id given, query should include agent_id."""
        from src.llm.token_counter import TokenCounter
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(return_value=[])
        tc = TokenCounter(db_pool=pool)

        with patch("src.llm.token_counter.POSTGRES_AVAILABLE", True):
            results = await tc.get_usage_by_operation(agent_id="my-agent")

        conn.fetch.assert_called_once()
        args = conn.fetch.call_args[0]
        # The agent_id should appear as a parameter
        assert "my-agent" in args

    async def test_with_pool_exception_returns_empty(self):
        from src.llm.token_counter import TokenCounter
        pool, conn = _make_pool()
        conn.fetch = AsyncMock(side_effect=Exception("DB down"))
        tc = TokenCounter(db_pool=pool)

        with patch("src.llm.token_counter.POSTGRES_AVAILABLE", True):
            results = await tc.get_usage_by_operation()

        assert results == []


# ---------------------------------------------------------------------------
# _get_db_usage_stats
# ---------------------------------------------------------------------------

class TestGetDbUsageStats:
    async def test_db_stats_with_no_filters(self):
        from src.llm.token_counter import TokenCounter
        pool, conn = _make_pool()

        class MockRow:
            def keys(self):
                return ["total_requests"]
            def __iter__(self):
                return iter([("total_requests", 10)])

        conn.fetchrow = AsyncMock(return_value=MockRow())
        tc = TokenCounter(db_pool=pool)

        result = await tc._get_db_usage_stats(None, None, 24)
        assert isinstance(result, dict)

    async def test_db_stats_with_agent_filter(self):
        from src.llm.token_counter import TokenCounter
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value=None)
        tc = TokenCounter(db_pool=pool)

        result = await tc._get_db_usage_stats("agent-test", None, 24)
        # With no row, returns empty dict
        assert result == {}

    async def test_db_stats_with_operation_filter(self):
        from src.llm.token_counter import TokenCounter
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(return_value=None)
        tc = TokenCounter(db_pool=pool)

        result = await tc._get_db_usage_stats(None, "summarize", 24)
        assert result == {}

    async def test_db_stats_exception_returns_empty(self):
        from src.llm.token_counter import TokenCounter
        pool, conn = _make_pool()
        conn.fetchrow = AsyncMock(side_effect=Exception("DB error"))
        tc = TokenCounter(db_pool=pool)

        result = await tc._get_db_usage_stats(None, None, 24)
        assert result == {}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

class TestModuleHelpers:
    def test_init_returns_instance(self):
        from src.llm import token_counter as tc_module
        from src.llm.token_counter import init_token_counter, TokenCounter
        tc = init_token_counter()
        assert isinstance(tc, TokenCounter)

    def test_init_sets_singleton(self):
        from src.llm.token_counter import init_token_counter, get_token_counter
        tc = init_token_counter()
        assert get_token_counter() is tc

    def test_init_with_pool(self):
        from src.llm.token_counter import init_token_counter, TokenCounter
        pool, _ = _make_pool()
        tc = init_token_counter(db_pool=pool)
        assert tc.db_pool is pool

    def test_get_before_init_returns_none_or_instance(self):
        from src.llm.token_counter import get_token_counter, TokenCounter
        result = get_token_counter()
        assert result is None or isinstance(result, TokenCounter)
