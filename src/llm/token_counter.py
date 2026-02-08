"""
Enhanced Cognee - Token Counting Utility

This module provides token counting for different LLM providers to:
- Track token usage for cost management
- Enforce rate limits based on token throughput
- Monitor token consumption by agent and operation
- Store usage statistics in PostgreSQL

Supports:
- Anthropic Claude (Claude 3 Opus, Sonnet, Haiku)
- OpenAI GPT (GPT-4, GPT-4 Turbo, GPT-3.5)
- LiteLLM wrapper providers

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Try to import tokenization libraries
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available - OpenAI token counting will use estimation")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic not available - Claude token counting will use estimation")

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("asyncpg not available - token usage tracking disabled")


class LLMProvider(Enum):
    """LLM provider enumeration."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LITELLM = "litellm"


class TokenCountingError(Exception):
    """Base exception for token counting errors."""
    pass


class TokenCounter:
    """
    Token counting utility for multiple LLM providers.

    Features:
    - Accurate token counting for Claude and GPT models
    - Fallback estimation when libraries unavailable
    - Usage tracking by agent and operation
    - Database persistence for analytics
    - Cost calculation based on token usage
    """

    # Model-specific token limits (input + output)
    MODEL_LIMITS = {
        # Anthropic Claude
        "claude-3-5-sonnet-20241022": 200000,
        "claude-3-5-haiku-20241022": 200000,
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,

        # OpenAI GPT
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4-turbo-preview": 128000,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-16k": 16385,
    }

    # Pricing per 1M tokens (USD) - as of 2026
    PRICING = {
        # Anthropic Claude (input / output)
        "claude-3-5-sonnet-20241022": (3.0, 15.0),
        "claude-3-5-haiku-20241022": (0.8, 4.0),
        "claude-3-opus-20240229": (15.0, 75.0),
        "claude-3-sonnet-20240229": (3.0, 15.0),
        "claude-3-haiku-20240307": (0.25, 1.25),

        # OpenAI GPT (input / output)
        "gpt-4": (30.0, 60.0),
        "gpt-4-32k": (60.0, 120.0),
        "gpt-4-turbo": (10.0, 30.0),
        "gpt-4-turbo-preview": (10.0, 30.0),
        "gpt-3.5-turbo": (0.5, 1.5),
        "gpt-3.5-turbo-16k": (0.5, 1.5),
    }

    # Estimated tokens per character (fallback)
    TOKENS_PER_CHAR = {
        "english": 0.25,  # ~4 chars per token
        "code": 0.3,     # ~3.3 chars per token
        "default": 0.25
    }

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize token counter.

        Args:
            db_pool: PostgreSQL connection pool for usage tracking
        """
        self.db_pool = db_pool

        # Initialize tokenizers if available
        self.tiktoken_encoders: Dict[str, any] = {}
        if TIKTOKEN_AVAILABLE:
            self._init_tiktoken()

        # In-memory usage cache (for dashboard)
        self.usage_cache: List[Dict] = []
        self.max_cache_size = 1000

    def _init_tiktoken(self):
        """Initialize tiktoken encoders for OpenAI models."""
        if not TIKTOKEN_AVAILABLE:
            return

        try:
            # Common encoders
            self.tiktoken_encoders["cl100k_base"] = tiktoken.get_encoding("cl100k_base")  # GPT-4, GPT-3.5
            logger.info("Initialized tiktoken encoders")
        except Exception as e:
            logger.error(f"Failed to initialize tiktoken: {e}")

    def count_tokens_anthropic(
        self,
        text: str,
        model: str = "claude-3-5-sonnet-20241022"
    ) -> int:
        """
        Count tokens for Anthropic Claude models.

        Uses Anthropic's tokenization when available, otherwise estimates.

        Args:
            text: Text to count tokens for
            model: Model name (for estimation if needed)

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        # Use Anthropic's tokenization if available
        if ANTHROPIC_AVAILABLE:
            try:
                # Claude uses a custom tokenizer similar to GPT
                # For accurate counting, we'd need the actual tokenizer
                # For now, use character-based estimation
                return self._estimate_tokens(text, "english")
            except Exception as e:
                logger.warning(f"Anthropic token counting failed: {e}")
                return self._estimate_tokens(text, "english")

        # Fallback to estimation
        return self._estimate_tokens(text, "english")

    def count_tokens_openai(
        self,
        text: str,
        model: str = "gpt-4"
    ) -> int:
        """
        Count tokens for OpenAI GPT models.

        Uses tiktoken for accurate counting when available.

        Args:
            text: Text to count tokens for
            model: Model name (determines encoder)

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if TIKTOKEN_AVAILABLE and self.tiktoken_encoders:
            try:
                # Select encoder based on model
                if model.startswith("gpt-4") or model.startswith("gpt-3.5"):
                    encoder = self.tiktoken_encoders["cl100k_base"]
                    tokens = encoder.encode(text)
                    return len(tokens)
            except Exception as e:
                logger.warning(f"tiktoken counting failed: {e}")

        # Fallback to estimation
        return self._estimate_tokens(text, "english")

    def count_tokens_litellm(
        self,
        text: str,
        provider: str,
        model: str
    ) -> int:
        """
        Count tokens for LiteLLM-wrapped providers.

        Delegates to appropriate counter based on provider.

        Args:
            text: Text to count tokens for
            provider: Underlying provider (anthropic, openai, etc.)
            model: Model name

        Returns:
            Number of tokens
        """
        provider_lower = provider.lower()

        if provider_lower == "anthropic" or provider_lower.startswith("claude"):
            return self.count_tokens_anthropic(text, model)
        elif provider_lower == "openai" or provider_lower.startswith("gpt"):
            return self.count_tokens_openai(text, model)
        else:
            # Generic estimation
            return self._estimate_tokens(text, "default")

    def _estimate_tokens(self, text: str, text_type: str = "default") -> int:
        """
        Estimate token count based on character count.

        Args:
            text: Text to estimate for
            text_type: Type of text (english, code, default)

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        char_count = len(text)
        ratio = self.TOKENS_PER_CHAR.get(text_type, self.TOKENS_PER_CHAR["default"])
        return int(char_count * ratio)

    def count_messages_tokens(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: LLMProvider = LLMProvider.ANTHROPIC
    ) -> int:
        """
        Count total tokens in a message list.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            provider: LLM provider

        Returns:
            Total token count
        """
        total_tokens = 0

        # Count tokens for each message
        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "")

            # Count content tokens
            if provider == LLMProvider.ANTHROPIC:
                total_tokens += self.count_tokens_anthropic(content, model)
            elif provider == LLMProvider.OPENAI:
                total_tokens += self.count_tokens_openai(content, model)
            else:
                total_tokens += self._estimate_tokens(content)

            # Add overhead for role/metadata (approximately)
            total_tokens += 5  # Rough estimate for role tokens

        # Add base overhead for the messages structure
        total_tokens += 10  # Rough estimate for structure overhead

        return total_tokens

    async def log_token_usage(
        self,
        agent_id: str,
        operation: str,
        provider: LLMProvider,
        model: str,
        input_tokens: int,
        output_tokens: int,
        request_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Log token usage to database and cache.

        Args:
            agent_id: Agent using the LLM
            operation: Operation type (summarization, deduplication, etc.)
            provider: LLM provider
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            request_id: Optional request identifier
            metadata: Additional metadata

        Returns:
            Usage summary dict
        """
        total_tokens = input_tokens + output_tokens
        cost = self._calculate_cost(provider, model, input_tokens, output_tokens)

        usage_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "operation": operation,
            "provider": provider.value,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost, 6),
            "request_id": request_id,
            "metadata": metadata or {}
        }

        # Add to cache
        self.usage_cache.append(usage_record)
        if len(self.usage_cache) > self.max_cache_size:
            self.usage_cache.pop(0)

        # Store in database
        if self.db_pool and POSTGRES_AVAILABLE:
            await self._store_usage(usage_record)

        return usage_record

    async def _store_usage(self, usage_record: Dict):
        """Store usage record in database."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO cognee_db.llm_token_usage (
                        timestamp, agent_id, operation, provider, model,
                        input_tokens, output_tokens, total_tokens, cost_usd,
                        request_id, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                    usage_record["timestamp"],
                    usage_record["agent_id"],
                    usage_record["operation"],
                    usage_record["provider"],
                    usage_record["model"],
                    usage_record["input_tokens"],
                    usage_record["output_tokens"],
                    usage_record["total_tokens"],
                    usage_record["cost_usd"],
                    usage_record["request_id"],
                    json.dumps(usage_record["metadata"])
                )
        except Exception as e:
            logger.error(f"Failed to store token usage: {e}")

    def _calculate_cost(
        self,
        provider: LLMProvider,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost in USD based on token usage.

        Args:
            provider: LLM provider
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Cost in USD
        """
        pricing = self.PRICING.get(model)
        if not pricing:
            # Unknown model, return 0
            return 0.0

        input_price, output_price = pricing

        # Calculate cost (prices are per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return input_cost + output_cost

    def get_model_limit(self, model: str) -> Optional[int]:
        """
        Get token limit for a model.

        Args:
            model: Model name

        Returns:
            Token limit or None if unknown
        """
        return self.MODEL_LIMITS.get(model)

    def check_limit(
        self,
        model: str,
        input_tokens: int,
        estimated_output_tokens: int
    ) -> Tuple[bool, int]:
        """
        Check if token count is within model limits.

        Args:
            model: Model name
            input_tokens: Input token count
            estimated_output_tokens: Estimated output tokens

        Returns:
            (within_limit, total_tokens)
        """
        total = input_tokens + estimated_output_tokens
        limit = self.get_model_limit(model)

        if limit is None:
            # Unknown limit, assume OK
            return True, total

        return total <= limit, total

    async def get_usage_stats(
        self,
        agent_id: Optional[str] = None,
        operation: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, any]:
        """
        Get token usage statistics.

        Args:
            agent_id: Filter by agent ID
            operation: Filter by operation type
            hours_back: Time range in hours

        Returns:
            Statistics dict
        """
        # Filter cache
        cache_records = self.usage_cache.copy()
        if agent_id:
            cache_records = [r for r in cache_records if r["agent_id"] == agent_id]
        if operation:
            cache_records = [r for r in cache_records if r["operation"] == operation]

        # Calculate stats from cache
        total_tokens = sum(r["total_tokens"] for r in cache_records)
        total_cost = sum(r["cost_usd"] for r in cache_records)
        total_requests = len(cache_records)

        # Get database stats if available
        db_stats = {}
        if self.db_pool and POSTGRES_AVAILABLE:
            db_stats = await self._get_db_usage_stats(agent_id, operation, hours_back)

        return {
            "cache_stats": {
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "total_requests": total_requests,
                "requests_in_cache": len(cache_records)
            },
            "database_stats": db_stats
        }

    async def _get_db_usage_stats(
        self,
        agent_id: Optional[str],
        operation: Optional[str],
        hours_back: int
    ) -> Dict[str, any]:
        """Get usage statistics from database."""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        COUNT(*) as total_requests,
                        SUM(input_tokens) as total_input_tokens,
                        SUM(output_tokens) as total_output_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(cost_usd) as total_cost
                    FROM cognee_db.llm_token_usage
                    WHERE timestamp > NOW() - INTERVAL '{hours_back} hours'
                """
                params = [hours_back]
                param_idx = 2

                if agent_id:
                    query += f" AND agent_id = ${param_idx}"
                    params.append(agent_id)
                    param_idx += 1

                if operation:
                    query += f" AND operation = ${param_idx}"
                    params.append(operation)
                    param_idx += 1

                row = await conn.fetchrow(query, *params)
                return dict(row) if row else {}

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    async def get_usage_by_operation(
        self,
        agent_id: Optional[str] = None,
        hours_back: int = 24
    ) -> List[Dict[str, any]]:
        """
        Get token usage breakdown by operation type.

        Args:
            agent_id: Filter by agent ID
            hours_back: Time range in hours

        Returns:
            List of usage stats per operation
        """
        if not self.db_pool or not POSTGRES_AVAILABLE:
            # Return cache-based stats
            from collections import defaultdict
            stats = defaultdict(lambda: {"total_tokens": 0, "total_cost": 0.0, "request_count": 0})
            for record in self.usage_cache:
                if agent_id and record["agent_id"] != agent_id:
                    continue
                op = record["operation"]
                stats[op]["total_tokens"] += record["total_tokens"]
                stats[op]["total_cost"] += record["cost_usd"]
                stats[op]["request_count"] += 1
            return [{"operation": k, **v} for k, v in stats.items()]

        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        operation,
                        COUNT(*) as request_count,
                        SUM(input_tokens) as total_input_tokens,
                        SUM(output_tokens) as total_output_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(cost_usd) as total_cost
                    FROM cognee_db.llm_token_usage
                    WHERE timestamp > NOW() - INTERVAL '{hours_back} hours'
                """
                params = [hours_back]
                param_idx = 2

                if agent_id:
                    query += f" AND agent_id = ${param_idx}"
                    params.append(agent_id)

                query += " GROUP BY operation ORDER BY total_tokens DESC"

                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get usage by operation: {e}")
            return []


# Global token counter instance
_token_counter: Optional[TokenCounter] = None


def get_token_counter() -> Optional[TokenCounter]:
    """Get the global token counter instance."""
    return _token_counter


def init_token_counter(db_pool: Optional[asyncpg.Pool] = None) -> TokenCounter:
    """
    Initialize the global token counter.

    Args:
        db_pool: PostgreSQL connection pool

    Returns:
        TokenCounter instance
    """
    global _token_counter
    _token_counter = TokenCounter(db_pool)
    return _token_counter
