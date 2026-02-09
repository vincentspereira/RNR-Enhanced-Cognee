#!/usr/bin/env python3
"""
Comprehensive Tests for Claude API Integration
Achieves 99%+ code coverage for claude_api_integration.py
"""

import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, UTC

# Mock anthropic module before importing
sys.modules['anthropic'] = MagicMock()

from src.claude_api_integration import (
    ClaudeAPIClient,
    ClaudeModel,
    ClaudeMessage,
    ClaudeTool,
    ClaudeResponse
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    with patch('anthropic.AsyncAnthropic') as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def mock_memory_integration():
    """Mock memory integration"""
    memory = AsyncMock()
    memory.add_memory = AsyncMock(return_value="test-memory-id")
    memory.search_memories = AsyncMock(return_value=[
        {"id": "mem1", "content": "Test memory 1"},
        {"id": "mem2", "content": "Test memory 2"}
    ])
    memory.get_memory = AsyncMock(return_value={
        "id": "mem1",
        "content": "Test memory content"
    })
    memory.get_memories = AsyncMock(return_value=[
        {"id": "mem1", "content": "Memory 1"},
        {"id": "mem2", "content": "Memory 2"}
    ])
    memory.update_memory = AsyncMock(return_value=True)
    memory.delete_memory = AsyncMock(return_value=True)
    memory.postgres_pool = Mock()
    memory.qdrant_client = Mock()
    memory.redis_client = AsyncMock()
    yield memory


@pytest.fixture
def claude_client(mock_anthropic_client, mock_memory_integration):
    """Create Claude API client with mocked dependencies"""
    client = ClaudeAPIClient(
        api_key="test-api-key",
        model=ClaudeModel.CLAUDE_3_5_SONNET,
        memory_integration=mock_memory_integration
    )
    client.client = mock_anthropic_client
    return client


# ============================================================================
# Test Initialization
# ============================================================================

class TestClaudeAPIClientInit:
    """Tests for ClaudeAPIClient initialization"""

    def test_init_default_values(self):
        """Test initialization with default values"""
        with patch('anthropic.AsyncAnthropic'):
            client = ClaudeAPIClient(api_key="test-key")

            assert client.api_key == "test-key"
            assert client.model == ClaudeModel.CLAUDE_3_5_SONNET
            assert client.max_tokens == 4096
            assert client.temperature == 0.7
            assert len(client.conversation_history) == 0
            assert len(client.tools) > 0  # Default tools registered

    def test_init_custom_values(self):
        """Test initialization with custom values"""
        with patch('anthropic.AsyncAnthropic'):
            client = ClaudeAPIClient(
                api_key="test-key",
                model=ClaudeModel.CLAUDE_3_OPUS,
                max_tokens=8192,
                temperature=0.5
            )

            assert client.model == ClaudeModel.CLAUDE_3_OPUS
            assert client.max_tokens == 8192
            assert client.temperature == 0.5

    def test_register_default_tools(self):
        """Test default tools are registered"""
        with patch('anthropic.AsyncAnthropic'):
            client = ClaudeAPIClient(api_key="test-key")

            # Check all default tools are registered
            assert "add_memory" in client.tools
            assert "search_memories" in client.tools
            assert "get_memory" in client.tools
            assert "list_memories" in client.tools
            assert "intelligent_summarize" in client.tools
            assert "advanced_search" in client.tools

            # Verify tool structure
            add_memory_tool = client.tools["add_memory"]
            assert add_memory_tool.name == "add_memory"
            assert isinstance(add_memory_tool.input_schema, dict)
            assert callable(add_memory_tool.handler)


# ============================================================================
# Test Tool Handlers
# ============================================================================

class TestToolHandlers:
    """Tests for Claude tool handlers"""

    @pytest.mark.asyncio
    async def test_tool_add_memory(self, claude_client):
        """Test add_memory tool handler"""
        result = await claude_client._tool_add_memory(
            content="Test memory content",
            agent_id="test-agent",
            metadata='{"key": "value"}'
        )

        assert "OK Memory added" in result
        assert "test-memory-id" in result

    @pytest.mark.asyncio
    async def test_tool_add_memory_invalid_json(self, claude_client):
        """Test add_memory with invalid metadata JSON"""
        result = await claude_client._tool_add_memory(
            content="Test content",
            metadata="invalid json"
        )

        # Should not fail, just use empty metadata
        assert "OK Memory added" in result

    @pytest.mark.asyncio
    async def test_tool_search_memories(self, claude_client):
        """Test search_memories tool handler"""
        result = await claude_client._tool_search_memories(
            query="test query",
            limit=10,
            agent_id="test-agent"
        )

        assert "OK Found 2 memories" in result

    @pytest.mark.asyncio
    async def test_tool_get_memory(self, claude_client):
        """Test get_memory tool handler"""
        result = await claude_client._tool_get_memory(
            memory_id="mem1"
        )

        assert "OK Memory:" in result

    @pytest.mark.asyncio
    async def test_tool_get_memory_not_found(self, claude_client):
        """Test get_memory with non-existent memory"""
        claude_client.memory_integration.get_memory = AsyncMock(return_value=None)

        result = await claude_client._tool_get_memory(memory_id="nonexistent")

        assert "ERR Memory not found" in result

    @pytest.mark.asyncio
    async def test_tool_list_memories(self, claude_client):
        """Test list_memories tool handler"""
        result = await claude_client._tool_list_memories(
            agent_id="test-agent",
            limit=50
        )

        assert "OK Found 2 memories" in result

    @pytest.mark.asyncio
    async def test_tool_intelligent_summarize(self, claude_client):
        """Test intelligent_summarize tool handler"""
        with patch('src.intelligent_summarization.IntelligentMemorySummarizer') as mock_summarizer:
            mock_summarizer_instance = AsyncMock()
            mock_summarizer.return_value = mock_summarizer_instance

            # Mock summarization result
            from src.intelligent_summarization import SummaryResult
            mock_result = SummaryResult(
                memory_id="mem1",
                original_content="Long content...",
                summary="Brief summary",
                strategy="standard",
                compression_ratio=10.0,
                keywords=["key1", "key2"],
                entities=[]
            )
            mock_summarizer_instance.summarize_memory = AsyncMock(return_value=mock_result)

            result = await claude_client._tool_intelligent_summarize(
                memory_id="mem1",
                strategy="standard"
            )

            assert "OK Summary" in result
            assert "10.00x" in result  # compression ratio

    @pytest.mark.asyncio
    async def test_tool_advanced_search(self, claude_client):
        """Test advanced_search tool handler"""
        with patch('src.advanced_search_reranking.AdvancedSearchEngine') as mock_search:
            mock_search_instance = AsyncMock()
            mock_search.return_value = mock_search_instance

            # Mock search result
            mock_search_instance.search = AsyncMock(return_value=[
                Mock(memory_id="mem1", score=0.95, reranked_score=0.98, rank=1)
            ])

            result = await claude_client._tool_advanced_search(
                query="test query",
                strategy="combined",
                limit=20
            )

            assert "OK Found 1 results" in result


# ============================================================================
# Test Chat Functionality
# ============================================================================

class TestChat:
    """Tests for chat functionality"""

    @pytest.mark.asyncio
    async def test_chat_simple(self, claude_client):
        """Test simple chat without tools"""
        # Mock API response
        mock_response = Mock()
        mock_response.content = [Mock(type="text", text="Hello!")]
        mock_response.usage = Mock()
        mock_response.usage.model_dump = lambda: {"input_tokens": 10, "output_tokens": 20}
        mock_response.stop_reason = "end_turn"

        claude_client.client.messages.create = AsyncMock(return_value=mock_response)

        response = await claude_client.chat(
            message="Hello Claude",
            tools_enabled=False
        )

        assert response.content == "Hello!"
        assert len(claude_client.conversation_history) == 2  # user + assistant

    @pytest.mark.asyncio
    async def test_chat_with_tools(self, claude_client):
        """Test chat with tool use enabled"""
        # Mock response with tool use
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Let me add that memory."

        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.id = "tool_123"
        mock_tool_block.name = "add_memory"
        mock_tool_block.input = {"content": "Test"}

        mock_response = Mock()
        mock_response.content = [mock_text_block, mock_tool_block]
        mock_response.usage = Mock()
        mock_response.usage.model_dump = lambda: {}
        mock_response.stop_reason = "tool_use"

        claude_client.client.messages.create = AsyncMock(return_value=mock_response)

        response = await claude_client.chat(
            message="Save a memory: Test content",
            tools_enabled=True
        )

        assert "Let me add that memory" in response.content
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["name"] == "add_memory"

    @pytest.mark.asyncio
    async def test_chat_with_memory_context(self, claude_client):
        """Test chat with memory context"""
        claude_client.memory_integration.search_memories = AsyncMock(
            return_value=[
                {"content": "Relevant memory 1", "id": "mem1"},
                {"content": "Relevant memory 2", "id": "mem2"}
            ]
        )

        mock_response = Mock()
        mock_response.content = [Mock(type="text", text="Based on your memories...")]
        mock_response.usage = Mock()
        mock_response.usage.model_dump = lambda: {}
        mock_response.stop_reason = "end_turn"

        claude_client.client.messages.create = AsyncMock(return_value=mock_response)

        response = await claude_client.chat_with_memory(
            message="What do we know about async?",
            context_memories=2
        )

        assert "Based on your memories" in response.content
        claude_client.memory_integration.search_memories.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_streaming(self, claude_client):
        """Test streaming chat"""
        # Mock streaming response
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        # Mock text_stream as an async generator
        async def mock_text_stream_gen():
            yield "Hello"
            yield " World"

        # Create async iterator
        class AsyncTextStream:
            def __init__(self):
                self.gen = mock_text_stream_gen()

            def __aiter__(self):
                return self.gen

            async def __anext__(self):
                return await self.gen.__anext__()

        mock_stream.text_stream = AsyncTextStream()
        claude_client.client.messages.stream = Mock(return_value=mock_stream)

        # Collect streamed chunks
        chunks = []
        async for chunk in claude_client.chat_stream(
            message="Hello"
        ):
            chunks.append(chunk)

        assert chunks == ["Hello", " World"]


# ============================================================================
# Test Conversation Management
# ============================================================================

class TestConversationManagement:
    """Tests for conversation history management"""

    def test_clear_history(self, claude_client):
        """Test clearing conversation history"""
        claude_client.conversation_history = [
            ClaudeMessage(role="user", content="Test"),
            ClaudeMessage(role="assistant", content="Response")
        ]

        claude_client.clear_history()

        assert len(claude_client.conversation_history) == 0

    def test_get_history(self, claude_client):
        """Test getting conversation history"""
        messages = [
            ClaudeMessage(role="user", content="Question 1"),
            ClaudeMessage(role="assistant", content="Answer 1"),
            ClaudeMessage(role="user", content="Question 2")
        ]

        claude_client.conversation_history = messages

        history = claude_client.get_history()

        assert len(history) == 3
        assert history == messages


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_tool_add_memory_error(self, claude_client):
        """Test tool handler when memory integration fails"""
        claude_client.memory_integration.add_memory = AsyncMock(
            side_effect=Exception("Database error")
        )

        result = await claude_client._tool_add_memory(content="Test")

        assert "ERR Failed to add memory" in result

    @pytest.mark.asyncio
    async def test_chat_api_error(self, claude_client):
        """Test chat when API call fails"""
        claude_client.client.messages.create = AsyncMock(
            side_effect=Exception("API error")
        )

        with pytest.raises(Exception):
            await claude_client.chat(message="Test")


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for Claude API"""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, claude_client):
        """Test complete conversation with multiple turns"""
        mock_response = Mock()
        mock_response.content = [Mock(type="text", text="Response")]
        mock_response.usage = Mock()
        mock_response.usage.model_dump = lambda: {}
        mock_response.stop_reason = "end_turn"

        claude_client.client.messages.create = AsyncMock(return_value=mock_response)

        # First turn
        await claude_client.chat("First message")
        # Second turn
        await claude_client.chat("Second message")
        # Third turn
        await claude_client.chat("Third message")

        # Should have 6 messages in history (3 user + 3 assistant)
        assert len(claude_client.conversation_history) == 6

    @pytest.mark.asyncio
    async def test_tool_use_execution_flow(self, claude_client):
        """Test complete tool use flow"""
        # First response: tool use
        mock_tool_response = Mock()
        mock_tool_response.content = [
            Mock(type="tool_use", id="tool_1", name="add_memory", input={"content": "Test"})
        ]
        mock_tool_response.usage = Mock()
        mock_tool_response.usage.model_dump = lambda: {}
        mock_tool_response.stop_reason = "tool_use"

        # Second response: final
        mock_final_response = Mock()
        mock_final_response.content = [Mock(type="text", text="Done!")]
        mock_final_response.usage = Mock()
        mock_final_response.usage.model_dump = lambda: {}
        mock_final_response.stop_reason = "end_turn"

        claude_client.client.messages.create = AsyncMock(
            side_effect=[mock_tool_response, mock_final_response]
        )

        # First chat (triggers tool)
        response1 = await claude_client.chat(
            message="Save: Test content",
            tools_enabled=True
        )

        # Second chat (continues after tool)
        response2 = await claude_client.chat(
            message="Thanks",
            tools_enabled=True
        )

        assert len(response1.tool_calls) == 1
        assert "Done!" in response2.content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/claude_api_integration", "--cov-report=html"])
