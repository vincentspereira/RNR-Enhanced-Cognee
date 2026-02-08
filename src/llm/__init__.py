"""
Enhanced Cognee - LLM Integration Module

This module provides LLM provider integrations for Enhanced Cognee's AI-powered features.

Supported Providers:
- Anthropic Claude (Claude 3.5 Sonnet, Haiku, Opus)
- OpenAI GPT (GPT-4, GPT-4 Turbo)
- LiteLLM (wrapper for multiple providers)

Features:
- Automatic token counting
- Rate limiting with retry logic
- Cost tracking
- Prompt template integration
- Async/await for high concurrency

Usage:
    from src.llm.providers.anthropic import AnthropicClient

    client = AnthropicClient()
    summary = await client.summarize(text, target_ratio=0.3)

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

from .base import BaseLLMClient, LLMProvider
from .providers.anthropic import AnthropicClient

__all__ = [
    "BaseLLMClient",
    "LLMProvider",
    "AnthropicClient"
]
