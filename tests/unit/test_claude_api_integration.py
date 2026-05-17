"""
Unit tests for src/claude_api_integration.py

Mocks the Anthropic client so no real API calls are made.
Covers: ClaudeAPIClient init, _init_client (success, ImportError), _register_default_tools,
        tool handlers (add_memory, search_memories, get_memory, list_memories,
        intelligent_summarize, advanced_search), chat (non-stream), chat_stream scaffold,
        chat_with_memory, clear_history, get_history, ClaudeModel enum, dataclasses.
"""

import sys
import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Build a lightweight anthropic stub so the module can import
# ---------------------------------------------------------------------------

def _build_anthropic_stub():
    """Return a minimal fake 'anthropic' module that satisfies the import."""
    stub = types.ModuleType("anthropic")

    class _FakeAsyncAnthropic:
        def __init__(self, api_key=""):
            self.messages = _FakeMessages()

    class _FakeMessages:
        async def create(self, **kwargs):
            return _FakeResponse()

    class _FakeResponse:
        content = []
        usage = MagicMock(model_dump=MagicMock(return_value={"input_tokens": 10, "output_tokens": 20}))
        stop_reason = "end_turn"

    stub.AsyncAnthropic = _FakeAsyncAnthropic
    return stub


# Inject stub before module is imported
if "anthropic" not in sys.modules:
    sys.modules["anthropic"] = _build_anthropic_stub()

# Now import the module under test
from src.claude_api_integration import (
    ClaudeAPIClient, ClaudeModel, ClaudeMessage, ClaudeTool, ClaudeResponse
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_mock():
    m = AsyncMock()
    m.add_memory = AsyncMock(return_value="mem-123")
    m.search_memories = AsyncMock(return_value=[{"id": "1", "content": "result"}])
    m.get_memory = AsyncMock(return_value={"id": "1", "content": "mem content"})
    m.get_memories = AsyncMock(return_value=[{"id": "1"}])
    return m


@pytest.fixture
def client(memory_mock):
    """ClaudeAPIClient with mocked Anthropic client and memory integration."""
    c = ClaudeAPIClient(
        api_key="test-key",
        model=ClaudeModel.CLAUDE_3_5_SONNET,
        memory_integration=memory_mock,
    )
    return c


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

class TestDataclasses:
    @pytest.mark.unit
    def test_claude_message_creation(self):
        msg = ClaudeMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.metadata == {}

    @pytest.mark.unit
    def test_claude_response_defaults(self):
        resp = ClaudeResponse(content="hi", model="claude-3")
        assert resp.content == "hi"
        assert resp.tool_calls == []
        assert resp.stop_reason is None

    @pytest.mark.unit
    def test_claude_tool_creation(self):
        handler = AsyncMock()
        tool = ClaudeTool(
            name="test_tool",
            description="desc",
            input_schema={"type": "object"},
            handler=handler,
        )
        assert tool.name == "test_tool"

    @pytest.mark.unit
    def test_claude_model_enum_values(self):
        assert ClaudeModel.CLAUDE_3_5_SONNET.value == "claude-3-5-sonnet-20241022"
        assert ClaudeModel.CLAUDE_3_5_HAIKU.value == "claude-3-5-haiku-20241022"
        assert ClaudeModel.CLAUDE_3_OPUS.value == "claude-3-opus-20240229"


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInit:
    @pytest.mark.unit
    def test_api_key_stored(self, client):
        assert client.api_key == "test-key"

    @pytest.mark.unit
    def test_model_stored(self, client):
        assert client.model == ClaudeModel.CLAUDE_3_5_SONNET

    @pytest.mark.unit
    def test_default_tools_registered(self, client):
        assert "add_memory" in client.tools
        assert "search_memories" in client.tools
        assert "get_memory" in client.tools
        assert "list_memories" in client.tools
        assert "intelligent_summarize" in client.tools
        assert "advanced_search" in client.tools

    @pytest.mark.unit
    def test_conversation_history_empty(self, client):
        assert client.conversation_history == []

    @pytest.mark.unit
    def test_init_raises_without_anthropic(self):
        with patch.dict(sys.modules, {"anthropic": None}):
            # Force re-init which will hit ImportError branch
            c = ClaudeAPIClient.__new__(ClaudeAPIClient)
            c.api_key = "k"
            c.model = ClaudeModel.CLAUDE_3_5_SONNET
            c.max_tokens = 100
            c.temperature = 0.7
            c.memory_integration = None
            c.conversation_history = []
            c.tools = {}
            with pytest.raises(Exception):
                c._init_client()

    @pytest.mark.unit
    def test_memory_integration_none_accepted(self):
        c = ClaudeAPIClient(api_key="k")
        assert c.memory_integration is None


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

class TestToolHandlers:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_memory_no_integration(self, client):
        client.memory_integration = None
        result = await client._tool_add_memory(content="test")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_memory_success(self, client):
        result = await client._tool_add_memory(content="hello", agent_id="agent1")
        assert "OK" in result
        assert "mem-123" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_memory_invalid_json_metadata(self, client):
        result = await client._tool_add_memory(content="hi", metadata="{invalid}")
        assert "OK" in result  # metadata falls back to {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_memory_exception(self, client):
        client.memory_integration.add_memory = AsyncMock(side_effect=Exception("fail"))
        result = await client._tool_add_memory(content="test")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_memories_no_integration(self, client):
        client.memory_integration = None
        result = await client._tool_search_memories(query="test")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_memories_success(self, client):
        result = await client._tool_search_memories(query="hello", limit=5)
        assert "OK" in result
        assert "1" in result  # 1 result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_memories_exception(self, client):
        client.memory_integration.search_memories = AsyncMock(side_effect=Exception("err"))
        result = await client._tool_search_memories(query="test")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_memory_no_integration(self, client):
        client.memory_integration = None
        result = await client._tool_get_memory(memory_id="x")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_memory_found(self, client):
        result = await client._tool_get_memory(memory_id="1")
        assert "OK" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, client):
        client.memory_integration.get_memory = AsyncMock(return_value=None)
        result = await client._tool_get_memory(memory_id="missing")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_memory_exception(self, client):
        client.memory_integration.get_memory = AsyncMock(side_effect=Exception("e"))
        result = await client._tool_get_memory(memory_id="x")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_memories_no_integration(self, client):
        client.memory_integration = None
        result = await client._tool_list_memories()
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_memories_success(self, client):
        result = await client._tool_list_memories(limit=5)
        assert "OK" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_memories_exception(self, client):
        client.memory_integration.get_memories = AsyncMock(side_effect=Exception("e"))
        result = await client._tool_list_memories()
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_intelligent_summarize_exception(self, client):
        result = await client._tool_intelligent_summarize(memory_id="x", strategy="standard")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_advanced_search_no_integration(self, client):
        client.memory_integration = None
        result = await client._tool_advanced_search(query="test")
        assert "ERR" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_advanced_search_returns_result_string(self, client):
        # Even if advanced search fails internally it returns a string
        result = await client._tool_advanced_search(query="test")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# chat (non-streaming)
# ---------------------------------------------------------------------------

class TestChat:
    @pytest.fixture
    def fake_block_text(self):
        """A fake content block with type='text'."""
        b = MagicMock()
        b.type = "text"
        b.text = "Hello there!"
        return b

    @pytest.fixture
    def fake_response(self, fake_block_text):
        resp = MagicMock()
        resp.content = [fake_block_text]
        resp.usage = MagicMock(model_dump=MagicMock(return_value={"input_tokens": 5}))
        resp.stop_reason = "end_turn"
        return resp

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_nonstream_returns_claude_response(self, client, fake_response):
        client.client.messages.create = AsyncMock(return_value=fake_response)
        result = await client.chat("Hello", tools_enabled=False)
        assert isinstance(result, ClaudeResponse)
        assert result.content == "Hello there!"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_adds_to_history(self, client, fake_response):
        client.client.messages.create = AsyncMock(return_value=fake_response)
        await client.chat("Hello", tools_enabled=False)
        # user message + assistant message
        assert len(client.conversation_history) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_with_tools_enabled(self, client, fake_response):
        client.client.messages.create = AsyncMock(return_value=fake_response)
        result = await client.chat("use tools", tools_enabled=True)
        assert isinstance(result, ClaudeResponse)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_tool_use_block(self, client):
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "t1"
        tool_block.name = "add_memory"
        tool_block.input = {"content": "test"}

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "OK"

        resp = MagicMock()
        resp.content = [text_block, tool_block]
        resp.usage = MagicMock(model_dump=MagicMock(return_value={}))
        resp.stop_reason = "tool_use"
        client.client.messages.create = AsyncMock(return_value=resp)
        result = await client.chat("add memory", tools_enabled=True)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "add_memory"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_exception_propagates(self, client):
        client.client.messages.create = AsyncMock(side_effect=Exception("API error"))
        with pytest.raises(Exception, match="API error"):
            await client.chat("test")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_stream_returns_generator(self, client):
        # When stream=True, chat returns the async generator directly
        result = await client.chat("test", stream=True)
        # It's an async generator object, not a ClaudeResponse
        import inspect
        assert inspect.isasyncgen(result)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_no_tools_when_empty_tools(self, client):
        client.tools = {}
        fake_block = MagicMock()
        fake_block.type = "text"
        fake_block.text = "ok"
        resp = MagicMock()
        resp.content = [fake_block]
        resp.usage = MagicMock(model_dump=MagicMock(return_value={}))
        resp.stop_reason = "end_turn"
        client.client.messages.create = AsyncMock(return_value=resp)
        result = await client.chat("hello", tools_enabled=True)
        assert isinstance(result, ClaudeResponse)


# ---------------------------------------------------------------------------
# chat_with_memory
# ---------------------------------------------------------------------------

class TestChatWithMemory:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_with_memory_uses_search(self, client):
        fake_block = MagicMock()
        fake_block.type = "text"
        fake_block.text = "response"
        resp = MagicMock()
        resp.content = [fake_block]
        resp.usage = MagicMock(model_dump=MagicMock(return_value={}))
        resp.stop_reason = "end_turn"
        client.client.messages.create = AsyncMock(return_value=resp)
        result = await client.chat_with_memory("question about memories")
        client.memory_integration.search_memories.assert_called_once()
        assert isinstance(result, ClaudeResponse)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_with_memory_no_integration(self, client):
        client.memory_integration = None
        fake_block = MagicMock()
        fake_block.type = "text"
        fake_block.text = "ok"
        resp = MagicMock()
        resp.content = [fake_block]
        resp.usage = MagicMock(model_dump=MagicMock(return_value={}))
        resp.stop_reason = "end_turn"
        client.client.messages.create = AsyncMock(return_value=resp)
        result = await client.chat_with_memory("question", context_memories=3)
        assert isinstance(result, ClaudeResponse)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_with_memory_uses_custom_system_prompt(self, client):
        fake_block = MagicMock()
        fake_block.type = "text"
        fake_block.text = "answer"
        resp = MagicMock()
        resp.content = [fake_block]
        resp.usage = MagicMock(model_dump=MagicMock(return_value={}))
        resp.stop_reason = "end_turn"
        client.client.messages.create = AsyncMock(return_value=resp)
        result = await client.chat_with_memory("q", system_prompt="Be concise.")
        assert isinstance(result, ClaudeResponse)


# ---------------------------------------------------------------------------
# chat_stream
# ---------------------------------------------------------------------------

class TestChatStream:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_stream_yields_text_chunks(self, client):
        """chat_stream should yield text chunks from the streaming API."""
        # Build a mock async context manager for client.messages.stream()
        class _FakeStreamCtx:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *a):
                pass
            @property
            def text_stream(self):
                async def _gen():
                    yield "Hello"
                    yield " world"
                return _gen()

        client.client.messages.stream = MagicMock(return_value=_FakeStreamCtx())

        chunks = []
        async for chunk in client.chat_stream("Tell me something"):
            chunks.append(chunk)
        assert chunks == ["Hello", " world"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_stream_appends_history(self, client):
        class _FakeStreamCtx:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            @property
            def text_stream(self):
                async def _gen():
                    yield "chunk"
                return _gen()

        client.client.messages.stream = MagicMock(return_value=_FakeStreamCtx())
        async for _ in client.chat_stream("hi"):
            pass
        # user message + assistant message
        assert len(client.conversation_history) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chat_stream_tools_disabled(self, client):
        class _FakeStreamCtx:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            @property
            def text_stream(self):
                async def _gen():
                    yield "ok"
                return _gen()

        client.client.messages.stream = MagicMock(return_value=_FakeStreamCtx())
        chunks = []
        async for chunk in client.chat_stream("hello", tools_enabled=False):
            chunks.append(chunk)
        assert chunks == ["ok"]


# ---------------------------------------------------------------------------
# _create_streaming_response (internal)
# ---------------------------------------------------------------------------

class TestCreateStreamingResponse:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_yields_chunks(self, client):
        class _FakeStreamCtx:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            @property
            def text_stream(self):
                async def _gen():
                    yield "a"
                    yield "b"
                return _gen()

        client.client.messages.stream = MagicMock(return_value=_FakeStreamCtx())
        messages = [{"role": "user", "content": "hello"}]
        chunks = []
        async for c in client._create_streaming_response(messages, None, None):
            chunks.append(c)
        assert chunks == ["a", "b"]


# ---------------------------------------------------------------------------
# clear_history / get_history
# ---------------------------------------------------------------------------

class TestHistory:
    @pytest.mark.unit
    def test_clear_history_empties_list(self, client):
        client.conversation_history = [ClaudeMessage(role="user", content="hi")]
        client.clear_history()
        assert client.conversation_history == []

    @pytest.mark.unit
    def test_get_history_returns_list(self, client):
        client.conversation_history = [ClaudeMessage(role="user", content="hello")]
        hist = client.get_history()
        assert len(hist) == 1
        assert hist[0].content == "hello"

    @pytest.mark.unit
    def test_get_history_empty_initially(self, client):
        assert client.get_history() == []
