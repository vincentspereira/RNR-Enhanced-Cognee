"""
Enhanced Cognee - LLM Provider Base Interface

This module defines the base interface for all LLM provider implementations.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LITELLM = "litellm"


class BaseLLMClient(ABC):
    """
    Base class for all LLM provider clients.

    Defines the interface that all LLM providers must implement.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        config_path: str = "automation_config.json"
    ):
        """
        Initialize the LLM client.

        Args:
            api_key: API key for the provider
            model: Model name/identifier
            config_path: Path to automation config
        """
        self.api_key = api_key
        self.model = model
        self.config_path = config_path

    @abstractmethod
    async def call(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Make a basic LLM API call.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 1.0)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLM response text
        """
        pass

    @abstractmethod
    async def call_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Make an LLM API call with message history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            LLM response text
        """
        pass

    @abstractmethod
    async def call_with_json_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an LLM API call expecting JSON response.

        Args:
            prompt: The prompt to send
            schema: JSON schema for expected response
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Parsed JSON response as dict
        """
        pass

    async def summarize(
        self,
        text: str,
        target_ratio: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Summarize text content.

        Args:
            text: Text to summarize
            target_ratio: Target length as ratio of original
            **kwargs: Additional parameters

        Returns:
            Summary dict with summary, key_points, entities, etc.
        """
        from pathlib import Path
        import json

        # Load summarization prompt template
        template_path = Path(__file__).parent.parent / "prompts" / "summarization.txt"
        with open(template_path, 'r') as f:
            template = f.read()

        # Format prompt
        prompt = template.format(
            content=text,
            memory_id="",
            agent_id="",
            category="",
            tags="",
            created_at="",
            target_ratio=target_ratio,
            original_length=len(text),
            target_length=int(len(text) * target_ratio)
        )

        # Get JSON response
        response = await self.call_with_json_response(
            prompt,
            schema={},
            **kwargs
        )

        return response

    async def detect_duplicates(
        self,
        text1: str,
        text2: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Detect if two texts are duplicates.

        Args:
            text1: First text
            text2: Second text
            **kwargs: Additional parameters

        Returns:
            Duplicate detection dict with similarity score, verdict, etc.
        """
        from pathlib import Path

        # Load deduplication prompt template
        template_path = Path(__file__).parent.parent / "prompts" / "deduplication.txt"
        with open(template_path, 'r') as f:
            template = f.read()

        # Format prompt
        prompt = template.format(
            memory_id_1="",
            content_1=text1,
            created_at_1="",
            agent_id_1="",
            category_1="",
            memory_id_2="",
            content_2=text2,
            created_at_2="",
            agent_id_2="",
            category_2="",
            similarity_threshold=0.85,
            merge_strategy="if_duplicate"
        )

        # Get JSON response
        response = await self.call_with_json_response(
            prompt,
            schema={},
            **kwargs
        )

        return response

    async def extract_entities(
        self,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract entities from text.

        Args:
            text: Text to extract entities from
            **kwargs: Additional parameters

        Returns:
            Entity extraction dict with categorized entities and relationships
        """
        from pathlib import Path

        # Load extraction prompt template
        template_path = Path(__file__).parent.parent / "prompts" / "extraction.txt"
        with open(template_path, 'r') as f:
            template = f.read()

        # Format prompt
        prompt = template.format(
            content=text,
            memory_id="",
            agent_id="",
            category="",
            created_at="",
            entity_types="",
            context=""
        )

        # Get JSON response
        response = await self.call_with_json_response(
            prompt,
            schema={},
            **kwargs
        )

        return response

    async def detect_intent(
        self,
        old_content: str,
        new_content: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Detect user's intent when updating a memory.

        Args:
            old_content: Original content
            new_content: Updated content
            **kwargs: Additional parameters

        Returns:
            Intent detection dict with intent type, confidence, recommendations
        """
        from pathlib import Path

        # Load intent detection prompt template
        template_path = Path(__file__).parent.parent / "prompts" / "intent_detection.txt"
        with open(template_path, 'r') as f:
            template = f.read()

        # Format prompt
        prompt = template.format(
            original_content=old_content,
            updated_content=new_content,
            memory_id="",
            original_created_at="",
            original_agent_id="",
            updated_at="",
            updated_agent_id="",
            time_diff="",
            same_agent="true",
            category=""
        )

        # Get JSON response
        response = await self.call_with_json_response(
            prompt,
            schema={},
            **kwargs
        )

        return response

    async def check_quality(
        self,
        content: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Assess quality of memory content.

        Args:
            content: Content to assess
            **kwargs: Additional parameters

        Returns:
            Quality assessment dict with scores, strengths, weaknesses, issues
        """
        from pathlib import Path

        # Load quality check prompt template
        template_path = Path(__file__).parent.parent / "prompts" / "quality_check.txt"
        with open(template_path, 'r') as f:
            template = f.read()

        # Format prompt
        prompt = template.format(
            content=content,
            memory_id="",
            created_at="",
            agent_id="",
            category="",
            context="",
            expected_quality="high",
            use_case=""
        )

        # Get JSON response
        response = await self.call_with_json_response(
            prompt,
            schema={},
            **kwargs
        )

        return response
