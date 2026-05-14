"""
enhanced_cognee_client - Async Python client for the Enhanced Cognee MCP server.

Provides a thin HTTP wrapper around the MCP tool endpoints so non-MCP
applications can interact with Enhanced Cognee using plain async/await.

Quickstart::

    from enhanced_cognee_client import EnhancedCogneeClient

    async with EnhancedCogneeClient(host="localhost", port=37777) as client:
        await client.add_memory("Remember this fact", agent_id="my-agent")
        results = await client.search_memories("fact", agent_id="my-agent")

All output is ASCII-only (no Unicode symbols, no emojis).
"""

from .client import EnhancedCogneeClient
from .exceptions import AuthError, ConnectionError, EnhancedCogneeError, ToolError

__all__ = [
    "EnhancedCogneeClient",
    "EnhancedCogneeError",
    "ConnectionError",
    "AuthError",
    "ToolError",
]

__version__ = "1.0.0"
