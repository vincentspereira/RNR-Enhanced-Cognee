"""
Unit tests for src.llm.providers.anthropic
============================================
Tests AnthropicClient initialization, call, call_with_messages,
call_with_json_response, and _call_api internals.
All Anthropic SDK calls are mocked. No real API calls.
No Unicode characters in assertions.
"""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_anthropic_client(api_key="test-key", model=None, rate_limiter=None, token_counter=None):
    """Create an AnthropicClient with mocked anthropic SDK."""
    from src.llm.providers.anthropic import AnthropicClient

    with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
         patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
        mock_sdk_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_sdk_client
        mock_anthropic.APIError = Exception  # Reuse base Exception as APIError

        client = AnthropicClient(
            api_key=api_key,
            model=model,
            rate_limiter=rate_limiter,
            token_counter=token_counter
        )
        client._mock_sdk_client = mock_sdk_client
        client._mock_anthropic = mock_anthropic
        return client


def _make_message_response(text="response text"):
    """Create a mock Anthropic message response."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


# ---------------------------------------------------------------------------
# AnthropicClient initialization
# ---------------------------------------------------------------------------

class TestAnthropicClientInit:
    def test_init_with_explicit_api_key(self):
        client = _make_anthropic_client(api_key="my-key")
        assert client.api_key == "my-key"

    def test_init_with_env_api_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            from src.llm.providers.anthropic import AnthropicClient
            with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
                 patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
                mock_anthropic.AsyncAnthropic.return_value = MagicMock()
                mock_anthropic.APIError = Exception
                client = AnthropicClient()
                assert client.api_key == "env-key"

    def test_init_no_api_key_raises_value_error(self):
        from src.llm.providers.anthropic import AnthropicClient
        with patch.dict(os.environ, {}, clear=True):
            # Remove ANTHROPIC_API_KEY if present
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                AnthropicClient()

    def test_default_model(self):
        client = _make_anthropic_client()
        assert client.model == "claude-3-5-sonnet-20241022"

    def test_custom_model(self):
        client = _make_anthropic_client(model="claude-3-opus-20240229")
        assert client.model == "claude-3-opus-20240229"

    def test_sdk_unavailable_sets_client_to_none(self):
        from src.llm.providers.anthropic import AnthropicClient
        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", False):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
                client = AnthropicClient(api_key="test")
                assert client.client is None

    def test_rate_limiter_stored(self):
        mock_rl = MagicMock()
        client = _make_anthropic_client(rate_limiter=mock_rl)
        assert client.rate_limiter is mock_rl

    def test_token_counter_stored(self):
        mock_tc = MagicMock()
        client = _make_anthropic_client(token_counter=mock_tc)
        assert client.token_counter is mock_tc


# ---------------------------------------------------------------------------
# call() - no client
# ---------------------------------------------------------------------------

class TestCallNoClient:
    async def test_call_raises_runtime_error_when_no_client(self):
        from src.llm.providers.anthropic import AnthropicClient
        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", False):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
                client = AnthropicClient(api_key="test")
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.call("hello")


# ---------------------------------------------------------------------------
# _call_api - success path
# ---------------------------------------------------------------------------

class TestCallApi:
    async def test_call_api_returns_text(self):
        client = _make_anthropic_client()
        response = _make_message_response("hello world")

        # messages.create is a coroutine in async client
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            result = await client._call_api(prompt="test prompt")

        assert result == "hello world"

    async def test_call_api_with_system_prompt(self):
        client = _make_anthropic_client()
        response = _make_message_response("answer")
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            result = await client._call_api(
                prompt="test",
                system_prompt="You are helpful"
            )

        assert result == "answer"
        call_kwargs = client.client.messages.create.call_args[1]
        assert call_kwargs.get("system") == "You are helpful"

    async def test_call_api_with_token_counter(self):
        mock_tc = MagicMock()
        mock_tc.count_tokens_anthropic = MagicMock(return_value=10)
        mock_tc.log_token_usage = AsyncMock()

        client = _make_anthropic_client(token_counter=mock_tc)
        response = _make_message_response("result text")
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            result = await client._call_api(prompt="test", input_tokens=5)

        assert result == "result text"
        mock_tc.log_token_usage.assert_called_once()

    async def test_call_api_raises_anthropic_api_error(self):
        """anthropic.APIError should be re-raised."""
        client = _make_anthropic_client()

        class FakeAPIError(Exception):
            pass

        client.client.messages.create = AsyncMock(side_effect=FakeAPIError("api error"))

        with patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = FakeAPIError
            with pytest.raises(FakeAPIError):
                await client._call_api(prompt="test")

    async def test_call_api_raises_generic_exception(self):
        """Non-APIError exceptions should also be re-raised."""
        client = _make_anthropic_client()
        client.client.messages.create = AsyncMock(side_effect=RuntimeError("unexpected"))

        with patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            with pytest.raises(RuntimeError, match="unexpected"):
                await client._call_api(prompt="test")


# ---------------------------------------------------------------------------
# call() - rate limiter path
# ---------------------------------------------------------------------------

class TestCallWithRateLimiter:
    async def test_call_uses_rate_limiter_when_set(self):
        mock_rl = MagicMock()
        mock_rl.execute_with_rate_limit = AsyncMock(return_value="rate-limited-result")

        client = _make_anthropic_client(rate_limiter=mock_rl)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True):
            result = await client.call("hello")

        assert result == "rate-limited-result"
        mock_rl.execute_with_rate_limit.assert_called_once()

    async def test_call_uses_direct_call_without_rate_limiter(self):
        client = _make_anthropic_client()
        response = _make_message_response("direct result")
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            result = await client.call("prompt")

        assert result == "direct result"

    async def test_call_extracts_system_prompt_from_kwargs(self):
        """system_prompt kwarg should be extracted and not forwarded as extra kwarg."""
        client = _make_anthropic_client()
        response = _make_message_response("ok")
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            result = await client.call("prompt", system_prompt="You are a robot")

        assert result == "ok"

    async def test_call_with_token_counter_counts_system_prompt(self):
        """When token_counter is set, system_prompt tokens should be counted."""
        mock_tc = MagicMock()
        mock_tc.count_tokens_anthropic = MagicMock(return_value=15)
        mock_tc.log_token_usage = AsyncMock()

        client = _make_anthropic_client(token_counter=mock_tc)
        response = _make_message_response("x")
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            await client.call("prompt", system_prompt="system")

        # count_tokens_anthropic called for both prompt and system_prompt
        assert mock_tc.count_tokens_anthropic.call_count >= 2


# ---------------------------------------------------------------------------
# call_with_messages()
# ---------------------------------------------------------------------------

class TestCallWithMessages:
    async def test_call_with_messages_no_client_raises(self):
        from src.llm.providers.anthropic import AnthropicClient
        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", False):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
                client = AnthropicClient(api_key="test")
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.call_with_messages([{"role": "user", "content": "hi"}])

    async def test_call_with_messages_returns_text(self):
        client = _make_anthropic_client()
        response = _make_message_response("messages result")
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            messages = [{"role": "user", "content": "hello"}]
            result = await client.call_with_messages(messages)

        assert result == "messages result"

    async def test_call_with_messages_with_rate_limiter(self):
        mock_rl = MagicMock()
        mock_rl.execute_with_rate_limit = AsyncMock(return_value="rl-result")

        client = _make_anthropic_client(rate_limiter=mock_rl)
        messages = [{"role": "user", "content": "hello"}]

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True):
            result = await client.call_with_messages(messages)

        assert result == "rl-result"

    async def test_call_with_messages_with_token_counter(self):
        mock_tc = MagicMock()
        mock_tc.count_messages_tokens = MagicMock(return_value=20)
        mock_tc.count_tokens_anthropic = MagicMock(return_value=5)
        mock_tc.log_token_usage = AsyncMock()

        client = _make_anthropic_client(token_counter=mock_tc)
        response = _make_message_response("counted")
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            messages = [{"role": "user", "content": "hello"}]
            result = await client.call_with_messages(messages)

        mock_tc.count_messages_tokens.assert_called_once()
        assert result == "counted"


# ---------------------------------------------------------------------------
# _call_api_with_messages
# ---------------------------------------------------------------------------

class TestCallApiWithMessages:
    async def test_call_api_with_messages_logs_usage(self):
        mock_tc = MagicMock()
        mock_tc.count_tokens_anthropic = MagicMock(return_value=10)
        mock_tc.log_token_usage = AsyncMock()

        client = _make_anthropic_client(token_counter=mock_tc)
        response = _make_message_response("msg result")
        client.client.messages.create = AsyncMock(return_value=response)

        with patch("src.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True), \
             patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = Exception
            messages = [{"role": "user", "content": "test"}]
            result = await client._call_api_with_messages(
                messages=messages,
                input_tokens=15
            )

        assert result == "msg result"
        mock_tc.log_token_usage.assert_called_once()
        log_kwargs = mock_tc.log_token_usage.call_args[1]
        assert log_kwargs["input_tokens"] == 15

    async def test_call_api_with_messages_reraises_api_error(self):
        client = _make_anthropic_client()

        class FakeAPIError(Exception):
            pass

        client.client.messages.create = AsyncMock(side_effect=FakeAPIError("api error"))

        with patch("src.llm.providers.anthropic.anthropic") as mock_anthropic:
            mock_anthropic.APIError = FakeAPIError
            messages = [{"role": "user", "content": "test"}]
            with pytest.raises(FakeAPIError):
                await client._call_api_with_messages(messages=messages)


# ---------------------------------------------------------------------------
# call_with_json_response()
# ---------------------------------------------------------------------------

class TestCallWithJsonResponse:
    async def test_valid_json_response_parsed(self):
        client = _make_anthropic_client()
        client.call = AsyncMock(return_value='{"key": "value", "score": 42}')

        result = await client.call_with_json_response("describe something")
        assert result == {"key": "value", "score": 42}

    async def test_json_in_markdown_code_block_parsed(self):
        client = _make_anthropic_client()
        client.call = AsyncMock(return_value='```json\n{"result": true}\n```')

        result = await client.call_with_json_response("test prompt")
        assert result["result"] is True

    async def test_json_in_generic_code_block_parsed(self):
        client = _make_anthropic_client()
        client.call = AsyncMock(return_value='```\n{"value": 99}\n```')

        result = await client.call_with_json_response("test")
        assert result["value"] == 99

    async def test_invalid_json_raises_value_error(self):
        client = _make_anthropic_client()
        client.call = AsyncMock(return_value="this is not json at all")

        with pytest.raises(ValueError, match="valid JSON"):
            await client.call_with_json_response("test prompt")

    async def test_json_instruction_appended_to_prompt(self):
        """The JSON instruction should be added to the prompt."""
        client = _make_anthropic_client()
        captured_prompts = []

        async def capture_call(prompt, **kwargs):
            captured_prompts.append(prompt)
            return '{"ok": true}'

        client.call = capture_call
        await client.call_with_json_response("original prompt")

        assert "original prompt" in captured_prompts[0]
        assert "JSON" in captured_prompts[0]

    async def test_lower_temperature_used_for_json(self):
        """JSON responses should use lower temperature (0.3)."""
        client = _make_anthropic_client()
        captured_kwargs = {}

        async def capture_call(prompt, **kwargs):
            captured_kwargs.update(kwargs)
            return '{"done": true}'

        client.call = capture_call
        await client.call_with_json_response("test")
        assert captured_kwargs.get("temperature") == 0.3

    async def test_schema_accepted_as_none(self):
        client = _make_anthropic_client()
        client.call = AsyncMock(return_value='{"x": 1}')
        result = await client.call_with_json_response("test", schema=None)
        assert result == {"x": 1}

    async def test_kwargs_forwarded(self):
        """Extra kwargs should be forwarded to call()."""
        client = _make_anthropic_client()
        captured_kw = {}

        async def capture_call(prompt, **kwargs):
            captured_kw.update(kwargs)
            return '{"ok": true}'

        client.call = capture_call
        await client.call_with_json_response("test", max_tokens=512, system_prompt="sys")
        assert captured_kw.get("max_tokens") == 512


# ---------------------------------------------------------------------------
# Class-level constants
# ---------------------------------------------------------------------------

class TestClassConstants:
    def test_default_model(self):
        from src.llm.providers.anthropic import AnthropicClient
        assert AnthropicClient.DEFAULT_MODEL == "claude-3-5-sonnet-20241022"

    def test_max_tokens_table(self):
        from src.llm.providers.anthropic import AnthropicClient
        assert "claude-3-5-sonnet-20241022" in AnthropicClient.MAX_TOKENS

    def test_pricing_table(self):
        from src.llm.providers.anthropic import AnthropicClient
        assert "claude-3-5-sonnet-20241022" in AnthropicClient.PRICING
        assert AnthropicClient.PRICING["claude-3-5-sonnet-20241022"] == (3.0, 15.0)
