#!/usr/bin/env python3
"""
Official Claude API Integration for Enhanced Cognee
Provides native Anthropic Claude API integration with streaming, tool use, and function calling
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable, AsyncIterator
from datetime import datetime, UTC
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ClaudeModel(Enum):
    """Available Claude models"""
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"


@dataclass
class ClaudeMessage:
    """Message for Claude API"""
    role: str  # "user" or "assistant"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaudeTool:
    """Tool definition for Claude function calling"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


@dataclass
class ClaudeResponse:
    """Response from Claude API"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    stop_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClaudeAPIClient:
    """
    Official Claude API Client for Enhanced Cognee

    Features:
    - Native Anthropic Claude API integration
    - Streaming and non-streaming responses
    - Tool use and function calling
    - Memory-aware conversations
    - Integration with Enhanced Cognee memory
    """

    def __init__(
        self,
        api_key: str,
        model: ClaudeModel = ClaudeModel.CLAUDE_3_5_SONNET,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        memory_integration=None
    ):
        """
        Initialize Claude API client

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-1)
            memory_integration: Enhanced Cognee memory integration
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.memory_integration = memory_integration

        # Conversation history
        self.conversation_history: List[ClaudeMessage] = []

        # Available tools
        self.tools: Dict[str, ClaudeTool] = {}

        # Initialize Anthropic client
        self._init_client()

        # Register default Enhanced Cognee tools
        self._register_default_tools()

    def _init_client(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=self.api_key)
            logger.info(f"OK Claude API client initialized with model: {self.model.value}")
        except ImportError:
            logger.error("Anthropic library not available")
            raise

    def _register_default_tools(self):
        """Register default Enhanced Cognee memory tools"""

        # Tool: add_memory
        self.tools["add_memory"] = ClaudeTool(
            name="add_memory",
            description="Add a memory entry to Enhanced Cognee",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory content to store"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent identifier (default: claude-code)"
                    },
                    "metadata": {
                        "type": "string",
                        "description": "Optional JSON metadata"
                    }
                },
                "required": ["content"]
            },
            handler=self._tool_add_memory
        )

        # Tool: search_memories
        self.tools["search_memories"] = ClaudeTool(
            name="search_memories",
            description="Search memories in Enhanced Cognee",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 10)"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Optional agent filter"
                    }
                },
                "required": ["query"]
            },
            handler=self._tool_search_memories
        )

        # Tool: get_memory
        self.tools["get_memory"] = ClaudeTool(
            name="get_memory",
            description="Get a specific memory by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory ID to retrieve"
                    }
                },
                "required": ["memory_id"]
            },
            handler=self._tool_get_memory
        )

        # Tool: list_memories
        self.tools["list_memories"] = ClaudeTool(
            name="list_memories",
            description="List all memories with optional filters",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Optional agent filter"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 50)"
                    }
                }
            },
            handler=self._tool_list_memories
        )

        # Tool: intelligent_summarize
        self.tools["intelligent_summarize"] = ClaudeTool(
            name="intelligent_summarize",
            description="Summarize a memory using LLM",
            input_schema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory ID to summarize"
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Strategy: concise, standard, detailed, extractive",
                        "enum": ["concise", "standard", "detailed", "extractive"]
                    }
                },
                "required": ["memory_id"]
            },
            handler=self._tool_intelligent_summarize
        )

        # Tool: advanced_search
        self.tools["advanced_search"] = ClaudeTool(
            name="advanced_search",
            description="Advanced search with query expansion and re-ranking",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Re-ranking strategy: relevance, recency, combined, personalized",
                        "enum": ["relevance", "recency", "combined", "personalized"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 20)"
                    }
                },
                "required": ["query"]
            },
            handler=self._tool_advanced_search
        )

        logger.info(f"OK Registered {len(self.tools)} Enhanced Cognee tools")

    async def _tool_add_memory(self, **kwargs) -> str:
        """Tool handler: add_memory"""
        if not self.memory_integration:
            return "ERR Memory integration not available"

        try:
            content = kwargs.get("content", "")
            agent_id = kwargs.get("agent_id", "claude-code")
            metadata_json = kwargs.get("metadata", "{}")

            # Parse metadata
            try:
                metadata = json.loads(metadata_json)
            except:
                metadata = {}

            # Add memory
            memory_id = await self.memory_integration.add_memory(
                content=content,
                agent_id=agent_id,
                metadata=metadata
            )

            return f"OK Memory added (ID: {memory_id})"

        except Exception as e:
            logger.error(f"Tool add_memory failed: {e}")
            return f"ERR Failed to add memory: {str(e)}"

    async def _tool_search_memories(self, **kwargs) -> str:
        """Tool handler: search_memories"""
        if not self.memory_integration:
            return "ERR Memory integration not available"

        try:
            query = kwargs.get("query", "")
            limit = kwargs.get("limit", 10)
            agent_id = kwargs.get("agent_id")

            results = await self.memory_integration.search_memories(
                query=query,
                limit=limit,
                agent_id=agent_id
            )

            return f"OK Found {len(results)} memories for query: {query}"

        except Exception as e:
            logger.error(f"Tool search_memories failed: {e}")
            return f"ERR Failed to search: {str(e)}"

    async def _tool_get_memory(self, **kwargs) -> str:
        """Tool handler: get_memory"""
        if not self.memory_integration:
            return "ERR Memory integration not available"

        try:
            memory_id = kwargs.get("memory_id", "")
            memory = await self.memory_integration.get_memory(memory_id)

            if not memory:
                return f"ERR Memory not found: {memory_id}"

            return f"OK Memory: {memory.get('content', '')[:200]}..."

        except Exception as e:
            logger.error(f"Tool get_memory failed: {e}")
            return f"ERR Failed to get memory: {str(e)}"

    async def _tool_list_memories(self, **kwargs) -> str:
        """Tool handler: list_memories"""
        if not self.memory_integration:
            return "ERR Memory integration not available"

        try:
            agent_id = kwargs.get("agent_id")
            limit = kwargs.get("limit", 50)

            memories = await self.memory_integration.get_memories(
                agent_id=agent_id,
                limit=limit
            )

            return f"OK Found {len(memories)} memories"

        except Exception as e:
            logger.error(f"Tool list_memories failed: {e}")
            return f"ERR Failed to list memories: {str(e)}"

    async def _tool_intelligent_summarize(self, **kwargs) -> str:
        """Tool handler: intelligent_summarize"""
        # Import here to avoid circular dependency
        try:
            from src.intelligent_summarization import IntelligentMemorySummarizer, SummaryStrategy

            if not self.memory_integration:
                return "ERR Memory integration not available"

            memory_id = kwargs.get("memory_id", "")
            strategy_str = kwargs.get("strategy", "standard")

            # Get memory
            memory = await self.memory_integration.get_memory(memory_id)
            if not memory:
                return f"ERR Memory not found: {memory_id}"

            # Initialize summarizer
            summarizer = IntelligentMemorySummarizer(
                postgres_pool=self.memory_integration.postgres_pool,
                llm_config={'provider': 'anthropic', 'api_key': self.api_key},
                redis_client=self.memory_integration.redis_client
            )

            # Parse strategy
            try:
                strategy = SummaryStrategy(strategy_str)
            except ValueError:
                strategy = SummaryStrategy.STANDARD

            # Summarize
            result = await summarizer.summarize_memory(memory, strategy)

            return f"OK Summary (compression: {result.compression_ratio:.2f}x): {result.summary}"

        except Exception as e:
            logger.error(f"Tool intelligent_summarize failed: {e}")
            return f"ERR Failed to summarize: {str(e)}"

    async def _tool_advanced_search(self, **kwargs) -> str:
        """Tool handler: advanced_search"""
        try:
            from src.advanced_search_reranking import AdvancedSearchEngine, ReRankingStrategy

            if not self.memory_integration:
                return "ERR Memory integration not available"

            query = kwargs.get("query", "")
            strategy_str = kwargs.get("strategy", "combined")
            limit = kwargs.get("limit", 20)

            # Initialize search engine
            search_engine = AdvancedSearchEngine(
                postgres_pool=self.memory_integration.postgres_pool,
                qdrant_client=self.memory_integration.qdrant_client,
                redis_client=self.memory_integration.redis_client,
                llm_config={'provider': 'anthropic', 'api_key': self.api_key}
            )

            # Parse strategy
            try:
                strategy = ReRankingStrategy(strategy_str)
            except ValueError:
                strategy = ReRankingStrategy.COMBINED

            # Search
            results = await search_engine.search(
                query=query,
                user_id="claude",
                limit=limit,
                rerank=True,
                strategy=strategy
            )

            return f"OK Found {len(results)} results with re-ranking"

        except Exception as e:
            logger.error(f"Tool advanced_search failed: {e}")
            return f"ERR Failed to search: {str(e)}"

    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        tools_enabled: bool = True,
        stream: bool = False
    ) -> ClaudeResponse:
        """
        Send chat message to Claude

        Args:
            message: User message
            system_prompt: Optional system prompt
            tools_enabled: Whether to enable tool use
            stream: Whether to stream response

        Returns:
            ClaudeResponse with content and metadata
        """
        try:
            # Add user message to history
            self.conversation_history.append(
                ClaudeMessage(role="user", content=message)
            )

            # Build messages for API
            messages = [
                {"role": m.role, "content": m.content}
                for m in self.conversation_history
            ]

            # Build tools config
            tools = None
            if tools_enabled and self.tools:
                tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema
                    }
                    for tool in self.tools.values()
                ]

            # Call Claude API
            if stream:
                return await self._chat_stream(messages, system_prompt, tools)
            else:
                return await self._chat_nonstream(messages, system_prompt, tools)

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise

    async def _chat_nonstream(
        self,
        messages: List[Dict],
        system_prompt: Optional[str],
        tools: Optional[List[Dict]]
    ) -> ClaudeResponse:
        """Non-streaming chat"""
        response = await self.client.messages.create(
            model=self.model.value,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=messages,
            tools=tools
        )

        # Process response
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        # Execute tool calls
        if tool_calls and self.tools:
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]

                if tool_name in self.tools:
                    tool = self.tools[tool_name]
                    result = await tool.handler(**tool_input)

                    # Add tool result to conversation
                    self.conversation_history.append(
                        ClaudeMessage(role="assistant", content=f"Tool: {tool_name}")
                    )
                    self.conversation_history.append(
                        ClaudeMessage(role="user", content=f"Result: {result}")
                    )

        # Add assistant response to history
        self.conversation_history.append(
            ClaudeMessage(role="assistant", content=content)
        )

        return ClaudeResponse(
            content=content,
            model=self.model.value,
            usage=response.usage.model_dump() if response.usage else {},
            tool_calls=tool_calls,
            stop_reason=response.stop_reason
        )

    async def _chat_stream(
        self,
        messages: List[Dict],
        system_prompt: Optional[str],
        tools: Optional[List[Dict]]
    ) -> AsyncIterator[str]:
        """Streaming chat - yields text chunks"""
        async with self.client.messages.stream(
            model=self.model.value,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=messages,
            tools=tools
        ) as stream:
            async for text in stream.text_stream:
                yield text

        # Collect full response for history
        full_response = ""
        async for text in stream.text_stream:
            full_response += text

        self.conversation_history.append(
            ClaudeMessage(role="assistant", content=full_response)
        )

    async def chat_with_memory(
        self,
        message: str,
        context_memories: int = 5,
        system_prompt: Optional[str] = None
    ) -> ClaudeResponse:
        """
        Chat with memory context from Enhanced Cognee

        Args:
            message: User message
            context_memories: Number of relevant memories to include
            system_prompt: Optional system prompt

        Returns:
            ClaudeResponse with memory-aware response
        """
        try:
            # Search for relevant memories
            if self.memory_integration:
                relevant_memories = await self.memory_integration.search_memories(
                    query=message,
                    limit=context_memories
                )

                # Build context from memories
                memory_context = "\n\n".join([
                    f"- {mem.get('content', '')[:200]}..."
                    for mem in relevant_memories
                ])

                # Add context to message
                enhanced_message = f"""Context from memory:
{memory_context}

User message: {message}"""
            else:
                enhanced_message = message

            # Default system prompt for Enhanced Cognee
            if not system_prompt:
                system_prompt = """You are Enhanced Cognee, an intelligent memory assistant with access to a knowledge graph and advanced search capabilities. You can store, retrieve, and analyze memories using the available tools. Be helpful, accurate, and concise."""

            # Chat with enhanced message
            return await self.chat(
                message=enhanced_message,
                system_prompt=system_prompt,
                tools_enabled=True
            )

        except Exception as e:
            logger.error(f"Chat with memory failed: {e}")
            raise

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("OK Conversation history cleared")

    def get_history(self) -> List[ClaudeMessage]:
        """Get conversation history"""
        return self.conversation_history


# Example usage
async def example_claude_api_usage():
    """Example usage of Claude API integration"""
    import os

    # Initialize client
    client = ClaudeAPIClient(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=ClaudeModel.CLAUDE_3_5_SONNET
    )

    # Example 1: Simple chat
    response = await client.chat(
        message="Hello! What can you help me with?",
        tools_enabled=False
    )
    print(f"Response: {response.content}")

    # Example 2: Chat with tools
    response = await client.chat(
        message="Save a memory about Python async programming best practices",
        tools_enabled=True
    )
    print(f"Response: {response.content}")
    print(f"Tool Calls: {response.tool_calls}")

    # Example 3: Chat with memory context
    response = await client.chat_with_memory(
        message="What did we discuss about async programming?",
        context_memories=3
    )
    print(f"Memory-aware Response: {response.content}")

    # Example 4: Streaming response
    async for chunk in client.chat(
        message="Tell me about Enhanced Cognee",
        stream=True
    ):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(example_claude_api_usage())
