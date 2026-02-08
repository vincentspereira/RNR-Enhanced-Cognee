"""
Enhanced Cognee - Anthropic Claude LLM Provider

Implementation of Anthropic Claude API integration for Enhanced Cognee.

Supports:
- Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)
- Claude 3.5 Haiku (claude-3-5-haiku-20241022)
- Claude 3 Opus (claude-3-opus-20240229)
- Claude 3 Sonnet (claude-3-sonnet-20240229)
- Claude 3 Haiku (claude-3-haiku-20240307)

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging

from .base import BaseLLMClient, LLMProvider
from ..rate_limiter import RateLimiter, Provider as RateLimitProvider, RequestPriority
from ..token_counter import TokenCounter

logger = logging.getLogger(__name__)

# Try to import anthropic SDK
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic package not available - API calls will fail")


class AnthropicClient(BaseLLMClient):
    """
    Anthropic Claude API client.

    Features:
    - Async API calls with proper error handling
    - Automatic retry on rate limits
    - Token counting integration
    - Rate limiting integration
    - JSON response parsing
    - Message-based API (Claude 3 format)
    """

    # Default model
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    # Max tokens per model
    MAX_TOKENS = {
        "claude-3-5-sonnet-20241022": 8192,
        "claude-3-5-haiku-20241022": 8192,
        "claude-3-opus-20240229": 4096,
        "claude-3-sonnet-20240229": 4096,
        "claude-3-haiku-20240307": 4096,
    }

    # Cost per 1M tokens (input/output)
    PRICING = {
        "claude-3-5-sonnet-20241022": (3.0, 15.0),
        "claude-3-5-haiku-20241022": (0.8, 4.0),
        "claude-3-opus-20240229": (15.0, 75.0),
        "claude-3-sonnet-20240229": (3.0, 15.0),
        "claude-3-haiku-20240307": (0.25, 1.25),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = None,
        config_path: str = "automation_config.json",
        rate_limiter: Optional[RateLimiter] = None,
        token_counter: Optional[TokenCounter] = None
    ):
        """
        Initialize Anthropic Claude client.

        Args:
            api_key: Anthropic API key (default from env)
            model: Model name (default: claude-3-5-sonnet-20241022)
            config_path: Path to automation config
            rate_limiter: Rate limiter instance
            token_counter: Token counter instance
        """
        # Get API key from environment if not provided
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")

        super().__init__(api_key, model or self.DEFAULT_MODEL, config_path)

        # Initialize Anthropic client
        if ANTHROPIC_AVAILABLE:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self.client = None
            logger.error("Cannot initialize Anthropic client - anthropic package not installed")

        # Integrations
        self.rate_limiter = rate_limiter
        self.token_counter = token_counter

    async def call(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Make a basic Claude API call.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 1.0)
            **kwargs: Additional parameters (system_prompt, etc.)

        Returns:
            Claude response text
        """
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")

        # Extract system prompt if provided
        system_prompt = kwargs.pop("system_prompt", None)

        # Count input tokens
        input_tokens = 0
        if self.token_counter:
            input_tokens = self.token_counter.count_tokens_anthropic(prompt, self.model)
            if system_prompt:
                input_tokens += self.token_counter.count_tokens_anthropic(system_prompt, self.model)

        # Execute with rate limiting
        if self.rate_limiter:
            return await self.rate_limiter.execute_with_rate_limit(
                RateLimitProvider.ANTHROPIC,
                self.api_key,
                self._call_api,
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                input_tokens=input_tokens,
                **kwargs
            )
        else:
            return await self._call_api(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

    async def _call_api(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        input_tokens: int = 0,
        **kwargs
    ) -> str:
        """
        Internal method to call Claude API.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            input_tokens: Pre-counted input tokens
            **kwargs: Additional parameters

        Returns:
            Claude response text
        """
        try:
            # Create message
            message = anthropic.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            # Get response
            response = await message

            # Extract text
            response_text = response.content[0].text

            # Count output tokens
            output_tokens = 0
            if self.token_counter:
                output_tokens = self.token_counter.count_tokens_anthropic(response_text, self.model)

                # Log usage
                await self.token_counter.log_token_usage(
                    agent_id="enhanced-cognee",
                    operation="claude_api_call",
                    provider=LLMProvider.ANTHROPIC,
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    metadata={
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )

            return response_text

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}")
            raise

    async def call_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Make a Claude API call with message history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Claude response text
        """
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")

        # Count input tokens
        input_tokens = 0
        if self.token_counter:
            input_tokens = self.token_counter.count_messages_tokens(
                messages,
                self.model,
                LLMProvider.ANTHROPIC
            )

        # Execute with rate limiting
        if self.rate_limiter:
            return await self.rate_limiter.execute_with_rate_limit(
                RateLimitProvider.ANTHROPIC,
                self.api_key,
                self._call_api_with_messages,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                input_tokens=input_tokens,
                **kwargs
            )
        else:
            return await self._call_api_with_messages(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

    async def _call_api_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        input_tokens: int = 0,
        **kwargs
    ) -> str:
        """
        Internal method to call Claude API with messages.

        Args:
            messages: Message history
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            input_tokens: Pre-counted input tokens
            **kwargs: Additional parameters

        Returns:
            Claude response text
        """
        try:
            # Call API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )

            # Extract text
            response_text = response.content[0].text

            # Count output tokens
            output_tokens = 0
            if self.token_counter:
                output_tokens = self.token_counter.count_tokens_anthropic(response_text, self.model)

                # Log usage
                await self.token_counter.log_token_usage(
                    agent_id="enhanced-cognee",
                    operation="claude_api_call",
                    provider=LLMProvider.ANTHROPIC,
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    metadata={
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "num_messages": len(messages)
                    }
                )

            return response_text

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}")
            raise

    async def call_with_json_response(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,  # Lower temperature for JSON
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a Claude API call expecting JSON response.

        Args:
            prompt: The prompt to send
            schema: JSON schema (for documentation only)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (lower for JSON)
            **kwargs: Additional parameters

        Returns:
            Parsed JSON response as dict
        """
        # Add JSON instruction to prompt
        json_instruction = "\n\nYou must respond with valid JSON only. No markdown, no code blocks, just the raw JSON object.\n\n"

        enhanced_prompt = prompt + json_instruction

        # Call API
        response_text = await self.call(
            prompt=enhanced_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_dict = json.loads(response_text)
            return response_dict

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {response_text[:500]}")
            raise ValueError(f"Claude did not return valid JSON: {e}") from e
