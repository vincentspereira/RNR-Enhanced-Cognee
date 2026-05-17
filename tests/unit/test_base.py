"""
Unit tests for src.llm.base
============================
Tests the BaseLLMClient abstract class and its concrete methods:
summarize, detect_duplicates, extract_entities, detect_intent, check_quality.
All prompt-file reads and JSON calls are mocked. No real LLM calls.
No Unicode characters in assertions.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch


# ---------------------------------------------------------------------------
# Concrete subclass for testing BaseLLMClient (it's abstract)
# ---------------------------------------------------------------------------

class _ConcreteClient:
    """Minimal concrete implementation of BaseLLMClient methods for testing."""

    def __init__(self, api_key="test-key", model="test-model"):
        from src.llm.base import BaseLLMClient
        # We cannot instantiate ABC directly, so patch abstractmethods
        pass


# Use a fixture that patches abstractmethods so we can instantiate BaseLLMClient
@pytest.fixture
def base_client():
    """Return a BaseLLMClient instance with abstract methods patched."""
    from src.llm.base import BaseLLMClient

    # Patch abstract methods so the class can be instantiated
    with patch.multiple(
        BaseLLMClient,
        call=AsyncMock(return_value="response text"),
        call_with_messages=AsyncMock(return_value="messages response"),
        call_with_json_response=AsyncMock(return_value={"result": "ok"}),
    ):
        # Create concrete subclass dynamically
        class _Client(BaseLLMClient):
            async def call(self, prompt, max_tokens=4096, temperature=0.7, **kwargs):
                return "response text"

            async def call_with_messages(self, messages, max_tokens=4096, temperature=0.7, **kwargs):
                return "messages response"

            async def call_with_json_response(self, prompt, schema, max_tokens=4096, temperature=0.7, **kwargs):
                return {"result": "ok"}

        return _Client(api_key="test-key", model="claude-3-5-sonnet-20241022")


# ---------------------------------------------------------------------------
# LLMProvider enum
# ---------------------------------------------------------------------------

class TestLLMProvider:
    def test_provider_values(self):
        from src.llm.base import LLMProvider
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.LITELLM.value == "litellm"

    def test_provider_members(self):
        from src.llm.base import LLMProvider
        assert len(LLMProvider) == 3


# ---------------------------------------------------------------------------
# BaseLLMClient.__init__
# ---------------------------------------------------------------------------

class TestBaseLLMClientInit:
    def test_stores_api_key_and_model(self, base_client):
        assert base_client.api_key == "test-key"
        assert base_client.model == "claude-3-5-sonnet-20241022"

    def test_default_config_path(self, base_client):
        assert base_client.config_path == "automation_config.json"

    def test_custom_config_path(self):
        from src.llm.base import BaseLLMClient

        class _Client(BaseLLMClient):
            async def call(self, prompt, max_tokens=4096, temperature=0.7, **kwargs):
                return ""
            async def call_with_messages(self, messages, max_tokens=4096, temperature=0.7, **kwargs):
                return ""
            async def call_with_json_response(self, prompt, schema, max_tokens=4096, temperature=0.7, **kwargs):
                return {}

        c = _Client(api_key="k", model="m", config_path="custom.json")
        assert c.config_path == "custom.json"


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------

class TestSummarize:
    async def test_summarize_calls_json_response(self, base_client):
        """summarize() should call call_with_json_response and return the result."""
        template_content = (
            "Content: {content}\nID: {memory_id}\nAgent: {agent_id}\n"
            "Category: {category}\nTags: {tags}\nCreated: {created_at}\n"
            "Ratio: {target_ratio}\nLen: {original_length}\nTarget: {target_length}"
        )
        mock_response = {"summary": "short text", "key_points": ["point1"]}

        base_client.call_with_json_response = AsyncMock(return_value=mock_response)

        with patch("builtins.open", mock_open(read_data=template_content)):
            result = await base_client.summarize("some long text", target_ratio=0.3)

        assert result == mock_response
        base_client.call_with_json_response.assert_called_once()

    async def test_summarize_uses_target_ratio(self, base_client):
        """The prompt should include the target ratio."""
        template = (
            "Content: {content}\nID: {memory_id}\nAgent: {agent_id}\n"
            "Category: {category}\nTags: {tags}\nCreated: {created_at}\n"
            "Ratio: {target_ratio}\nLen: {original_length}\nTarget: {target_length}"
        )
        captured_prompts = []

        async def capture_json_call(prompt, schema=None, **kwargs):
            captured_prompts.append(prompt)
            return {"summary": "x"}

        base_client.call_with_json_response = capture_json_call

        with patch("builtins.open", mock_open(read_data=template)):
            await base_client.summarize("hello world", target_ratio=0.5)

        assert "0.5" in captured_prompts[0]

    async def test_summarize_passes_kwargs(self, base_client):
        """Extra kwargs should be forwarded to call_with_json_response."""
        template = (
            "{content}{memory_id}{agent_id}{category}{tags}{created_at}"
            "{target_ratio}{original_length}{target_length}"
        )
        mock_json = AsyncMock(return_value={"summary": "s"})
        base_client.call_with_json_response = mock_json

        with patch("builtins.open", mock_open(read_data=template)):
            await base_client.summarize("text", target_ratio=0.2, extra_param="ep")

        _, kwargs = mock_json.call_args
        assert kwargs.get("extra_param") == "ep"


# ---------------------------------------------------------------------------
# detect_duplicates
# ---------------------------------------------------------------------------

class TestDetectDuplicates:
    async def test_detect_duplicates_returns_dict(self, base_client):
        template = (
            "{memory_id_1}{content_1}{created_at_1}{agent_id_1}{category_1}"
            "{memory_id_2}{content_2}{created_at_2}{agent_id_2}{category_2}"
            "{similarity_threshold}{merge_strategy}"
        )
        expected = {"is_duplicate": True, "similarity_score": 0.95}
        base_client.call_with_json_response = AsyncMock(return_value=expected)

        with patch("builtins.open", mock_open(read_data=template)):
            result = await base_client.detect_duplicates("text1", "text2")

        assert result == expected

    async def test_detect_duplicates_includes_both_texts(self, base_client):
        template = (
            "{memory_id_1}{content_1}{created_at_1}{agent_id_1}{category_1}"
            "{memory_id_2}{content_2}{created_at_2}{agent_id_2}{category_2}"
            "{similarity_threshold}{merge_strategy}"
        )
        captured = []

        async def capture(prompt, schema=None, **kwargs):
            captured.append(prompt)
            return {}

        base_client.call_with_json_response = capture

        with patch("builtins.open", mock_open(read_data=template)):
            await base_client.detect_duplicates("hello", "world")

        assert "hello" in captured[0]
        assert "world" in captured[0]


# ---------------------------------------------------------------------------
# extract_entities
# ---------------------------------------------------------------------------

class TestExtractEntities:
    async def test_extract_entities_returns_result(self, base_client):
        template = "{content}{memory_id}{agent_id}{category}{created_at}{entity_types}{context}"
        expected = {"entities": ["Alice", "Bob"], "relationships": []}
        base_client.call_with_json_response = AsyncMock(return_value=expected)

        with patch("builtins.open", mock_open(read_data=template)):
            result = await base_client.extract_entities("Alice knows Bob.")

        assert result == expected

    async def test_extract_entities_includes_content(self, base_client):
        template = "{content}{memory_id}{agent_id}{category}{created_at}{entity_types}{context}"
        captured = []

        async def capture(prompt, schema=None, **kwargs):
            captured.append(prompt)
            return {}

        base_client.call_with_json_response = capture

        with patch("builtins.open", mock_open(read_data=template)):
            await base_client.extract_entities("Hello, my name is Test.")

        assert "Hello, my name is Test." in captured[0]


# ---------------------------------------------------------------------------
# detect_intent
# ---------------------------------------------------------------------------

class TestDetectIntent:
    async def test_detect_intent_returns_result(self, base_client):
        template = (
            "{original_content}{updated_content}{memory_id}{original_created_at}"
            "{original_agent_id}{updated_at}{updated_agent_id}{time_diff}{same_agent}{category}"
        )
        expected = {"intent": "update", "confidence": 0.9}
        base_client.call_with_json_response = AsyncMock(return_value=expected)

        with patch("builtins.open", mock_open(read_data=template)):
            result = await base_client.detect_intent("old text", "new text")

        assert result == expected

    async def test_detect_intent_includes_both_contents(self, base_client):
        template = (
            "{original_content}{updated_content}{memory_id}{original_created_at}"
            "{original_agent_id}{updated_at}{updated_agent_id}{time_diff}{same_agent}{category}"
        )
        captured = []

        async def capture(prompt, schema=None, **kwargs):
            captured.append(prompt)
            return {}

        base_client.call_with_json_response = capture

        with patch("builtins.open", mock_open(read_data=template)):
            await base_client.detect_intent("original", "updated")

        assert "original" in captured[0]
        assert "updated" in captured[0]


# ---------------------------------------------------------------------------
# check_quality
# ---------------------------------------------------------------------------

class TestCheckQuality:
    async def test_check_quality_returns_result(self, base_client):
        template = (
            "{content}{memory_id}{created_at}{agent_id}{category}{context}"
            "{expected_quality}{use_case}"
        )
        expected = {"score": 0.8, "strengths": ["clarity"], "issues": []}
        base_client.call_with_json_response = AsyncMock(return_value=expected)

        with patch("builtins.open", mock_open(read_data=template)):
            result = await base_client.check_quality("good quality content")

        assert result == expected

    async def test_check_quality_includes_content(self, base_client):
        template = (
            "{content}{memory_id}{created_at}{agent_id}{category}{context}"
            "{expected_quality}{use_case}"
        )
        captured = []

        async def capture(prompt, schema=None, **kwargs):
            captured.append(prompt)
            return {}

        base_client.call_with_json_response = capture

        with patch("builtins.open", mock_open(read_data=template)):
            await base_client.check_quality("my content to check")

        assert "my content to check" in captured[0]

    async def test_check_quality_passes_kwargs(self, base_client):
        template = (
            "{content}{memory_id}{created_at}{agent_id}{category}{context}"
            "{expected_quality}{use_case}"
        )
        mock_json = AsyncMock(return_value={"score": 0.5})
        base_client.call_with_json_response = mock_json

        with patch("builtins.open", mock_open(read_data=template)):
            await base_client.check_quality("content", temperature=0.1)

        _, kwargs = mock_json.call_args
        assert kwargs.get("temperature") == 0.1


# ---------------------------------------------------------------------------
# Abstract interface enforcement
# ---------------------------------------------------------------------------

class TestAbstractInterface:
    def test_cannot_instantiate_directly(self):
        """BaseLLMClient is abstract - direct instantiation must fail."""
        from src.llm.base import BaseLLMClient
        with pytest.raises(TypeError):
            BaseLLMClient("key", "model")

    def test_subclass_missing_call_cannot_instantiate(self):
        from src.llm.base import BaseLLMClient

        class _Incomplete(BaseLLMClient):
            async def call_with_messages(self, messages, max_tokens=4096, temperature=0.7, **kwargs):
                return ""
            async def call_with_json_response(self, prompt, schema, max_tokens=4096, temperature=0.7, **kwargs):
                return {}

        with pytest.raises(TypeError):
            _Incomplete("k", "m")

    def test_complete_subclass_instantiates(self):
        from src.llm.base import BaseLLMClient

        class _Complete(BaseLLMClient):
            async def call(self, prompt, max_tokens=4096, temperature=0.7, **kwargs):
                return ""
            async def call_with_messages(self, messages, max_tokens=4096, temperature=0.7, **kwargs):
                return ""
            async def call_with_json_response(self, prompt, schema, max_tokens=4096, temperature=0.7, **kwargs):
                return {}

        c = _Complete("k", "m")
        assert c.api_key == "k"
        assert c.model == "m"
