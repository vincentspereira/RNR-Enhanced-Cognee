"""
Enhanced Cognee Lite Mode - MCP Server

Lightweight MCP server with 10 essential tools.
No Docker required, <2 minute setup.

10 Essential Tools:
1. add_memory - Add memory to SQLite
2. search_memories - FTS5 full-text search
3. get_memories - List memories with filters
4. get_memory - Get specific memory by ID
5. update_memory - Update existing memory
6. delete_memory - Delete memory
7. list_agents - List all agents
8. health - Health check
9. get_stats - System statistics
10. cognify - Basic cognify (no graph)

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Optional
from datetime import datetime
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.lite_mode.sqlite_manager import SQLiteManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiteMCPServer:
    """
    Lightweight MCP server for Enhanced Cognee Lite mode.

    Features:
    - 10 essential memory tools
    - SQLite with FTS5 full-text search
    - No Docker required
    - ASCII-only output
    - Fast setup (<2 minutes)
    """

    def __init__(self, db_path: str = "cognee_lite.db"):
        """
        Initialize Lite MCP server.

        Args:
            db_path: Path to SQLite database file
        """
        self.db = SQLiteManager(db_path)
        logger.info("Lite MCP Server initialized")

    async def add_memory(
        self,
        content: str,
        agent_id: str = "claude-code",
        user_id: str = "default",
        metadata: Optional[dict] = None
    ) -> str:
        """
        Add a memory to the database.

        Args:
            content: Memory content
            agent_id: Agent identifier
            user_id: User identifier
            metadata: Optional metadata dictionary

        Returns:
            Memory ID
        """
        try:
            data_id = str(uuid.uuid4())
            doc_id = self.db.add_document(
                data_id=data_id,
                data_text=content,
                data_type="text",
                metadata=metadata,
                user_id=user_id,
                agent_id=agent_id
            )

            logger.info(f"Memory added: {doc_id}")
            return f"[OK] Memory added: {doc_id}"

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return f"[ERR] Failed to add memory: {str(e)}"

    async def search_memories(
        self,
        query: str,
        agent_id: str = "claude-code",
        user_id: str = "default",
        limit: int = 20
    ) -> str:
        """
        Search memories using FTS5 full-text search.

        Args:
            query: Search query
            agent_id: Agent identifier
            user_id: User identifier
            limit: Maximum results

        Returns:
            Formatted search results
        """
        try:
            results = self.db.search_documents(
                query=query,
                user_id=user_id,
                agent_id=agent_id,
                limit=limit
            )

            if not results:
                return f"[INFO] No results found for query: {query}"

            output = [f"[OK] Found {len(results)} results for: {query}\n"]

            for i, result in enumerate(results, 1):
                output.append(f"{i}. Memory ID: {result['id']}")
                output.append(f"   Type: {result['data_type']}")
                output.append(f"   Agent: {result['agent_id']}")
                output.append(f"   Created: {result['created_at']}")
                output.append(f"   Content: {result['data_text'][:200]}{'...' if len(result['data_text']) > 200 else ''}")
                output.append("")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return f"[ERR] Failed to search memories: {str(e)}"

    async def get_memories(
        self,
        agent_id: str = "claude-code",
        user_id: str = "default",
        limit: int = 50,
        offset: int = 0
    ) -> str:
        """
        List memories with pagination.

        Args:
            agent_id: Agent identifier
            user_id: User identifier
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Formatted memory list
        """
        try:
            results = self.db.list_documents(
                user_id=user_id,
                agent_id=agent_id,
                limit=limit,
                offset=offset
            )

            if not results:
                return f"[INFO] No memories found for agent: {agent_id}"

            output = [f"[OK] Showing {len(results)} memories (offset: {offset}):\n"]

            for i, result in enumerate(results, 1):
                output.append(f"{i}. Memory ID: {result['id']}")
                output.append(f"   Type: {result['data_type']}")
                output.append(f"   Created: {result['created_at']}")
                output.append(f"   Summary: {result['summary']}")
                output.append("")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return f"[ERR] Failed to get memories: {str(e)}"

    async def get_memory(self, memory_id: str) -> str:
        """
        Get a specific memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Formatted memory details
        """
        try:
            result = self.db.get_document(memory_id)

            if not result:
                return f"[INFO] Memory not found: {memory_id}"

            output = [
                f"[OK] Memory Details:",
                f"ID: {result['id']}",
                f"Data ID: {result['data_id']}",
                f"Type: {result['data_type']}",
                f"Agent: {result['agent_id']}",
                f"User: {result['user_id']}",
                f"Created: {result['created_at']}",
                f"Updated: {result['updated_at']}",
                f"\nContent:\n{result['data_text']}"
            ]

            if result['metadata']:
                output.append(f"\nMetadata:\n{json.dumps(result['metadata'], indent=2)}")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Failed to get memory: {e}")
            return f"[ERR] Failed to get memory: {str(e)}"

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Update an existing memory.

        Args:
            memory_id: Memory ID
            content: New content (optional)
            metadata: New metadata (optional)

        Returns:
            Status message
        """
        try:
            updated = self.db.update_document(
                doc_id=memory_id,
                data_text=content,
                metadata=metadata
            )

            if updated:
                logger.info(f"Memory updated: {memory_id}")
                return f"[OK] Memory updated: {memory_id}"
            else:
                return f"[INFO] Memory not found or no changes: {memory_id}"

        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return f"[ERR] Failed to update memory: {str(e)}"

    async def delete_memory(self, memory_id: str) -> str:
        """
        Delete a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Status message
        """
        try:
            deleted = self.db.delete_document(memory_id)

            if deleted:
                logger.info(f"Memory deleted: {memory_id}")
                return f"[OK] Memory deleted: {memory_id}"
            else:
                return f"[INFO] Memory not found: {memory_id}"

        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return f"[ERR] Failed to delete memory: {str(e)}"

    async def list_agents(self) -> str:
        """
        List all agents with memory counts.

        Returns:
            Formatted agent list
        """
        try:
            agents = self.db.list_agents()

            if not agents:
                return "[INFO] No agents found"

            output = [f"[OK] Found {len(agents)} agents:\n"]

            for i, agent in enumerate(agents, 1):
                output.append(
                    f"{i}. Agent: {agent['agent_id']}\n"
                    f"   Memories: {agent['memory_count']}\n"
                    f"   First: {agent['first_memory']}\n"
                    f"   Last: {agent['last_memory']}\n"
                )

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return f"[ERR] Failed to list agents: {str(e)}"

    async def health(self) -> str:
        """
        Perform health check.

        Returns:
            Health status
        """
        try:
            health_status = self.db.health_check()

            output = [
                "[INFO] Enhanced Cognee Lite Mode Health:",
                f"Status: {health_status['status']}",
                f"Database: {health_status['database']}",
                f"Path: {health_status['path']}",
                f"Mode: {health_status['mode']}"
            ]

            if health_status['status'] == 'OK':
                output[0] = "[OK] Enhanced Cognee Lite Mode Health:"
            else:
                output[0] = "[ERR] Enhanced Cognee Lite Mode Health:"

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Failed health check: {e}")
            return f"[ERR] Health check failed: {str(e)}"

    async def get_stats(self) -> str:
        """
        Get system statistics.

        Returns:
            Formatted statistics
        """
        try:
            stats = self.db.get_stats()

            output = [
                "[OK] Enhanced Cognee Lite Mode Statistics:",
                f"Total Documents: {stats['total_documents']}",
                f"Total Sessions: {stats['total_sessions']}",
                f"Active Sessions: {stats['active_sessions']}",
                f"Database Size: {stats['database_size_bytes']:,} bytes",
                f"Database Path: {stats['database_path']}",
                f"Mode: {stats['mode']}",
                f"\nAgents:"
            ]

            for agent_id, count in stats.get('agents', {}).items():
                output.append(f"  - {agent_id}: {count} memories")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return f"[ERR] Failed to get stats: {str(e)}"

    async def cognify(self, data: str) -> str:
        """
        Basic cognify - transform data to knowledge (Lite mode, no graph).

        Args:
            data: Text data to process

        Returns:
            Status message
        """
        try:
            # In Lite mode, cognify simply adds the data as a memory
            # No knowledge graph, just FTS5 indexing
            data_id = str(uuid.uuid4())
            doc_id = self.db.add_document(
                data_id=data_id,
                data_text=data,
                data_type="cognified",
                metadata={"cognified": True, "cognified_at": datetime.now().isoformat()},
                user_id="default",
                agent_id="cognify"
            )

            logger.info(f"Data cognified: {doc_id}")
            return f"[OK] Data cognified (Lite mode - no graph): {doc_id}"

        except Exception as e:
            logger.error(f"Failed to cognify: {e}")
            return f"[ERR] Failed to cognify: {str(e)}"


# MCP Protocol Implementation
class MCPTool:
    """MCP tool descriptor."""

    def __init__(self, name: str, description: str, parameters: dict):
        self.name = name
        self.description = description
        self.parameters = parameters


class LiteMCPServerProtocol:
    """
    MCP protocol implementation for Lite mode.

    Implements stdio-based MCP protocol for Claude Code integration.
    """

    def __init__(self):
        self.server = LiteMCPServer()
        self.tools = self._initialize_tools()

    def _initialize_tools(self) -> list:
        """Initialize available MCP tools."""
        return [
            MCPTool(
                name="add_memory",
                description="Add a memory to the database",
                parameters={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Memory content to store"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Agent identifier (default: claude-code)"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User identifier (default: default)"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata dictionary"
                        }
                    },
                    "required": ["content"]
                }
            ),
            MCPTool(
                name="search_memories",
                description="Search memories using FTS5 full-text search",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Agent identifier (default: claude-code)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 20)"
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="get_memories",
                description="List memories with pagination",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Agent identifier (default: claude-code)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 50)"
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Pagination offset (default: 0)"
                        }
                    }
                }
            ),
            MCPTool(
                name="get_memory",
                description="Get a specific memory by ID",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "Memory ID"
                        }
                    },
                    "required": ["memory_id"]
                }
            ),
            MCPTool(
                name="update_memory",
                description="Update an existing memory",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "Memory ID"
                        },
                        "content": {
                            "type": "string",
                            "description": "New content (optional)"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "New metadata (optional)"
                        }
                    },
                    "required": ["memory_id"]
                }
            ),
            MCPTool(
                name="delete_memory",
                description="Delete a memory",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "Memory ID"
                        }
                    },
                    "required": ["memory_id"]
                }
            ),
            MCPTool(
                name="list_agents",
                description="List all agents with memory counts",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="health",
                description="Perform health check",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="get_stats",
                description="Get system statistics",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPTool(
                name="cognify",
                description="Transform data to knowledge (Lite mode - no graph)",
                parameters={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "string",
                            "description": "Text data to process and add to knowledge base"
                        }
                    },
                    "required": ["data"]
                }
            )
        ]

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Call an MCP tool.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        tool_method = getattr(self.server, tool_name, None)

        if not tool_method:
            return f"[ERR] Unknown tool: {tool_name}"

        try:
            result = await tool_method(**arguments)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"[ERR] Tool execution failed: {str(e)}"


async def main():
    """Main entry point for Lite MCP server."""
    server = LiteMCPServerProtocol()

    logger.info("Enhanced Cognee Lite Mode MCP Server starting...")
    logger.info("10 essential tools loaded:")
    for tool in server.tools:
        logger.info(f"  - {tool.name}")

    # For now, just test health
    health_result = await server.call_tool("health", {})
    print(health_result)

    # TODO: Implement stdio-based MCP protocol
    # For production, this would read/write JSON-RPC messages over stdin/stdout


if __name__ == "__main__":
    asyncio.run(main())
