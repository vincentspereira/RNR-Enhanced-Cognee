"""
client.py - Async HTTP client for the Enhanced Cognee MCP server.

Wraps every MCP tool exposed at POST /tools/{tool_name} so that
non-MCP applications can call them with plain Python async/await.

All output strings are ASCII-only (no Unicode symbols, no emojis).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from .exceptions import AuthError, ConnectionError, EnhancedCogneeError, ToolError


class EnhancedCogneeClient:
    """Async HTTP client for the Enhanced Cognee MCP server.

    Usage as a context manager (recommended)::

        async with EnhancedCogneeClient(host="localhost", port=37777) as client:
            result = await client.add_memory("Remember this fact")

    Usage without a context manager::

        client = EnhancedCogneeClient()
        result = await client.health()
        await client.close()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 37777,
        timeout: float = 30.0,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialise the client.

        Args:
            host:    Hostname or IP of the Enhanced Cognee MCP server.
            port:    Port number the server is listening on.
            timeout: Request timeout in seconds for all HTTP calls.
            api_key: Optional Bearer token sent in the Authorization header.
                     Pass None to skip authentication.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.api_key = api_key
        self._base_url = f"http://{host}:{port}"

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Lifecycle / context manager
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()

    async def __aenter__(self) -> "EnhancedCogneeClient":
        """Enter the async context manager.

        Returns:
            self, ready to use.
        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager, closing the HTTP client.

        Args:
            exc_type: Exception type if an exception was raised, else None.
            exc_val:  Exception instance if an exception was raised, else None.
            exc_tb:   Traceback if an exception was raised, else None.
        """
        await self.close()

    # ------------------------------------------------------------------
    # Internal dispatcher
    # ------------------------------------------------------------------

    async def _call(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """POST to /tools/{tool_name} with the supplied keyword arguments.

        Never raises on network errors; returns an error dict instead so
        callers can handle failures gracefully without try/except.

        Args:
            tool_name: The name of the MCP tool to invoke.
            **kwargs:  Arbitrary keyword arguments forwarded as the
                       ``arguments`` payload to the server.

        Returns:
            Parsed JSON response dict from the server, or a dict of the
            form ``{"error": "<message>"}`` when the call fails.
        """
        payload: Dict[str, Any] = {"arguments": kwargs}
        try:
            response = await self._client.post(
                f"/tools/{tool_name}",
                content=json.dumps(payload),
            )
            if response.status_code in (401, 403):
                return {"error": f"ERR Auth failed (HTTP {response.status_code})"}
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            return {"error": f"ERR Request timed out: {exc}"}
        except httpx.ConnectError as exc:
            return {"error": f"ERR Cannot connect to server at {self._base_url}: {exc}"}
        except httpx.HTTPStatusError as exc:
            return {
                "error": (
                    f"ERR HTTP {exc.response.status_code} from server: "
                    f"{exc.response.text[:200]}"
                )
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": f"ERR Unexpected error: {exc}"}

    # ------------------------------------------------------------------
    # Core memory methods
    # ------------------------------------------------------------------

    async def add_memory(
        self,
        content: str,
        user_id: str = "default",
        agent_id: str = "claude-code",
        metadata: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store a new memory entry in the Enhanced Cognee server.

        Args:
            content:  The text content to store as a memory.
            user_id:  User identifier used to segregate memories.
            agent_id: Agent identifier used to segregate memories.
            metadata: Optional JSON string with extra key/value pairs
                      (e.g. '{"category": "trading", "priority": "high"}').

        Returns:
            Dict containing the server response, typically with the new
            memory ID, or ``{"error": "..."}`` on failure.
        """
        return await self._call(
            "add_memory",
            content=content,
            user_id=user_id,
            agent_id=agent_id,
            metadata=metadata,
        )

    async def search_memories(
        self,
        query: str,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search stored memories using semantic and text search.

        Args:
            query:    Natural-language search query.
            user_id:  User scope for the search.
            agent_id: Optional agent scope; pass None to search all agents.
            limit:    Maximum number of results to return.

        Returns:
            List of matching memory dicts, or a list containing a single
            ``{"error": "..."}`` dict on failure.
        """
        result = await self._call(
            "search_memories",
            query=query,
            user_id=user_id,
            agent_id=agent_id,
            limit=limit,
        )
        if isinstance(result, list):
            return result
        return [result]

    async def get_memories(
        self,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve all memories matching the given filters.

        Args:
            user_id:  User scope for the retrieval.
            agent_id: Optional agent scope; pass None to retrieve from all agents.
            limit:    Maximum number of memories to return.

        Returns:
            List of memory dicts, or a list containing a single
            ``{"error": "..."}`` dict on failure.
        """
        result = await self._call(
            "get_memories",
            user_id=user_id,
            agent_id=agent_id,
            limit=limit,
        )
        if isinstance(result, list):
            return result
        return [result]

    async def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """Fetch a single memory by its unique identifier.

        Args:
            memory_id: The UUID of the memory to fetch.

        Returns:
            Dict with the memory content and metadata, or
            ``{"error": "..."}`` on failure.
        """
        return await self._call("get_memory", memory_id=memory_id)

    async def update_memory(self, memory_id: str, content: str) -> Dict[str, Any]:
        """Replace the content of an existing memory.

        Args:
            memory_id: The UUID of the memory to update.
            content:   New text content for the memory.

        Returns:
            Dict with the server status response, or ``{"error": "..."}``
            on failure.
        """
        return await self._call(
            "update_memory",
            memory_id=memory_id,
            content=content,
        )

    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory by its unique identifier.

        Args:
            memory_id: The UUID of the memory to delete.

        Returns:
            Dict with the server status response, or ``{"error": "..."}``
            on failure.
        """
        return await self._call("delete_memory", memory_id=memory_id)

    # ------------------------------------------------------------------
    # Session methods
    # ------------------------------------------------------------------

    async def remember(
        self,
        content: str,
        agent_id: str = "claude-code",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store a memory in the context of an active session.

        Convenience wrapper around the ``remember`` MCP tool. Intended
        for use during an agent session where session continuity matters.

        Args:
            content:    The text content to remember.
            agent_id:   Agent identifier for memory ownership.
            session_id: Optional session identifier; if None the server
                        assigns or reuses a session automatically.

        Returns:
            Dict with the server response including the memory ID, or
            ``{"error": "..."}`` on failure.
        """
        return await self._call(
            "remember",
            content=content,
            agent_id=agent_id,
            session_id=session_id,
        )

    async def recall(
        self,
        query: str,
        agent_id: str = "claude-code",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Recall memories relevant to a query within an agent session.

        Convenience wrapper around the ``recall`` MCP tool.

        Args:
            query:    Natural-language query describing what to recall.
            agent_id: Agent scope for the recall operation.
            limit:    Maximum number of results to return.

        Returns:
            List of relevant memory dicts, or a list containing a single
            ``{"error": "..."}`` dict on failure.
        """
        result = await self._call("recall", query=query, agent_id=agent_id, limit=limit)
        if isinstance(result, list):
            return result
        return [result]

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    async def get_memory_history(
        self,
        memory_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Fetch the version history of a memory.

        Args:
            memory_id: The UUID of the memory whose history to retrieve.
            limit:     Maximum number of history entries to return.

        Returns:
            List of version dicts ordered from newest to oldest, or a
            list containing a single ``{"error": "..."}`` dict on failure.
        """
        result = await self._call(
            "get_memory_history",
            memory_id=memory_id,
            limit=limit,
        )
        if isinstance(result, list):
            return result
        return [result]

    async def revert_memory(
        self,
        memory_id: str,
        version_number: int,
    ) -> Dict[str, Any]:
        """Revert a memory to a specific historical version.

        Args:
            memory_id:      The UUID of the memory to revert.
            version_number: The version number to restore (from history).

        Returns:
            Dict with the server status response, or ``{"error": "..."}``
            on failure.
        """
        return await self._call(
            "revert_memory",
            memory_id=memory_id,
            version_number=version_number,
        )

    async def set_memory_confidence(
        self,
        memory_id: str,
        score: float,
    ) -> Dict[str, Any]:
        """Assign a confidence score to a memory.

        Args:
            memory_id: The UUID of the memory to score.
            score:     Confidence score in the range [0.0, 1.0].

        Returns:
            Dict with the server status response, or ``{"error": "..."}``
            on failure.
        """
        return await self._call(
            "set_memory_confidence",
            memory_id=memory_id,
            score=score,
        )

    async def get_confidence_report(
        self,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve a confidence report across memories.

        Args:
            agent_id: Optional agent scope; pass None for a global report.

        Returns:
            Dict containing the confidence distribution report, or
            ``{"error": "..."}`` on failure.
        """
        return await self._call("get_confidence_report", agent_id=agent_id)

    async def promote_memory_tier(self, memory_id: str) -> Dict[str, Any]:
        """Promote a memory to a higher storage tier (e.g. long-term).

        Args:
            memory_id: The UUID of the memory to promote.

        Returns:
            Dict with the server status response, or ``{"error": "..."}``
            on failure.
        """
        return await self._call("promote_memory_tier", memory_id=memory_id)

    # ------------------------------------------------------------------
    # GDPR methods
    # ------------------------------------------------------------------

    async def gdpr_delete_user_data(
        self,
        user_id: str,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Delete all data associated with a user (GDPR right to erasure).

        When ``dry_run=True`` (the default) no data is removed; the server
        returns a count of what would be deleted so you can confirm before
        committing.

        Args:
            user_id:  The user whose data should be erased.
            dry_run:  If True, perform a simulated deletion only. Set to
                      False to permanently delete all user data.

        Returns:
            Dict describing the deletion result or preview, or
            ``{"error": "..."}`` on failure.
        """
        return await self._call(
            "gdpr_delete_user_data",
            user_id=user_id,
            dry_run=dry_run,
        )

    async def gdpr_export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export all data associated with a user (GDPR right to portability).

        Args:
            user_id: The user whose data should be exported.

        Returns:
            Dict containing the exported data payload, or
            ``{"error": "..."}`` on failure.
        """
        return await self._call("gdpr_export_user_data", user_id=user_id)

    # ------------------------------------------------------------------
    # System methods
    # ------------------------------------------------------------------

    async def health(self) -> Dict[str, Any]:
        """Check the health of all backend services.

        Returns:
            Dict with connection status for PostgreSQL, Qdrant, Neo4j and
            Redis, or ``{"error": "..."}`` if the server itself is
            unreachable.
        """
        return await self._call("health")

    async def get_stats(self) -> Dict[str, Any]:
        """Retrieve system statistics and document counts.

        Returns:
            Dict with database statistics (document counts, collection
            sizes, etc.), or ``{"error": "..."}`` on failure.
        """
        return await self._call("get_stats")
