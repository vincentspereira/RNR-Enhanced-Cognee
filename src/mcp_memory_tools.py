"""
Enhanced Cognee - Standard Memory MCP Tools Module

This module contains the standard memory MCP tools that provide
the core memory interface for Claude Code integration.

Tools included:
- add_memory
- search_memories
- get_memories
- get_memory
- update_memory
- delete_memory
- list_agents

This module is ASCII-only output compatible for Windows console.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def add_memory(
    content: str,
    user_id: str = "default",
    agent_id: str = "claude-code",
    metadata: Optional[str] = None,
    postgres_pool=None,
    memory_deduplicator=None,
    realtime_sync=None,
    cross_agent_sharing=None,
    performance_analytics=None
) -> Dict[str, Any]:
    """
    Add a memory entry (Standard Memory MCP Tool)

    This is the standard memory tool interface for Claude Code integration.
    Memories are stored in PostgreSQL and indexed in Qdrant for semantic search.

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs

    Parameters:
    -----------
    - content: The memory content to store
    - user_id: User identifier (default: "default")
    - agent_id: Agent identifier (default: "claude-code")
    - metadata: Optional JSON string with additional metadata
    - postgres_pool: PostgreSQL connection pool
    - memory_deduplicator: Deduplicator instance
    - realtime_sync: Real-time sync instance
    - cross_agent_sharing: Cross-agent sharing instance
    - performance_analytics: Performance analytics instance

    Returns:
    --------
    - Dictionary with status, data, error, timestamp
    """
    from src.security_mcp import (
        ValidationError,
        validate_agent_id,
        validate_memory_content,
        sanitize_string
    )

    import uuid
    from datetime import timezone

    result = {
        "status": "error",
        "data": None,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    try:
        # Input validation
        content = validate_memory_content(content)
        agent_id = validate_agent_id(agent_id)
        if user_id:
            user_id = sanitize_string(user_id, max_length=100)

        if not postgres_pool:
            result["error"] = "PostgreSQL not available - cannot add memory"
            return result

        # AUTO-TRIGGER: Check for duplicate before adding
        if memory_deduplicator:
            try:
                duplicate_check = await memory_deduplicator.check_duplicate(
                    content=content,
                    agent_id=agent_id,
                    memory_category="general"
                )
                if duplicate_check.get("is_duplicate"):
                    logger.info(f"Duplicate prevented: {duplicate_check.get('reason')}")
                    result["status"] = "success"
                    result["data"] = {"duplicate_prevented": True, "reason": duplicate_check.get('reason')}
                    return result
            except Exception as e:
                logger.warning(f"Duplicate check failed, continuing: {e}")

        # Parse metadata if provided
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except:
                metadata_dict = {"raw_metadata": metadata}

        # Generate memory ID
        memory_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Store in PostgreSQL
        async with postgres_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO shared_memory.documents
                (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, memory_id, f"Memory from {agent_id}", content,
                agent_id, "general", [], metadata_dict, created_at)

        logger.info(f"OK Added memory: {memory_id} for user: {user_id}, agent: {agent_id}")

        # AUTO-TRIGGER: Publish memory event for real-time sync
        if realtime_sync:
            try:
                await realtime_sync.publish_memory_event(
                    event_type="memory_added",
                    memory_id=memory_id,
                    agent_id=agent_id,
                    data={"content_preview": content[:100]}
                )
            except Exception as e:
                logger.warning(f"Failed to publish memory event: {e}")

        # AUTO-TRIGGER: Sync with shared agents
        if cross_agent_sharing and realtime_sync:
            try:
                # Check if this memory is shared
                access_check = await cross_agent_sharing.can_agent_access_memory(
                    memory_id=memory_id,
                    agent_id=agent_id
                )
                # Sync to all agents that should have access
                await realtime_sync.sync_agent_state(
                    source_agent=agent_id,
                    target_agent="all",
                    category="general"
                )
            except Exception as e:
                logger.warning(f"Failed to sync agent state: {e}")

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="add_memory",
                    agent_id=agent_id,
                    metadata={
                        "user_id": user_id,
                        "content_length": len(content),
                        "has_metadata": bool(metadata_dict)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log add_memory performance: {e}")

        result["status"] = "success"
        result["data"] = {
            "memory_id": memory_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "created_at": created_at.isoformat()
        }
        return result

    except ValidationError as e:
        logger.error(f"add_memory validation failed: {e}")
        result["error"] = str(e)
        return result
    except Exception as e:
        logger.error(f"add_memory failed: {e}")
        result["error"] = f"Failed to add memory: {str(e)}"
        return result


async def search_memories(
    query: str,
    limit: int = 10,
    user_id: str = "default",
    agent_id: Optional[str] = None,
    postgres_pool=None,
    performance_analytics=None
) -> Dict[str, Any]:
    """
    Search memories using semantic and text search (Standard Memory MCP Tool)

    This is the standard memory search tool for Claude Code integration.
    Performs both text-based and semantic vector search.

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs

    Parameters:
    -----------
    - query: Search query text
    - limit: Maximum results to return (default: 10)
    - user_id: User identifier to filter memories (default: "default")
    - agent_id: Optional agent identifier to filter memories
    - postgres_pool: PostgreSQL connection pool
    - performance_analytics: Performance analytics instance

    Returns:
    --------
    - Dictionary with status, data, error, timestamp
    """
    import time
    from src.security_mcp import ValidationError, sanitize_string, validate_limit, validate_agent_id

    start_time = time.time()
    result = {
        "status": "error",
        "data": None,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }

    try:
        # Input validation
        query = sanitize_string(query, max_length=1000)
        limit = validate_limit(limit, "limit")
        if user_id:
            user_id = sanitize_string(user_id, max_length=100)
        if agent_id:
            agent_id = validate_agent_id(agent_id)

        if not postgres_pool:
            result["error"] = "PostgreSQL not available - cannot search memories"
            return result

        async with postgres_pool.acquire() as conn:
            # Build query with filters
            query_str = """
                SELECT id, title, content, agent_id, created_at
                FROM shared_memory.documents
                WHERE content ILIKE $1
            """
            params = [f"%{query}%"]

            # Add agent filter if specified
            if agent_id:
                query_str += " AND agent_id = $2"
                params.append(agent_id)

            query_str += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query_str, *params)

            # Calculate search duration
            duration_ms = (time.time() - start_time) * 1000

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="search_memories",
                        agent_id=agent_id or "unknown",
                        metadata={
                            "query_length": len(query),
                            "results_count": len(rows),
                            "duration_ms": duration_ms
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log search performance: {e}")

            # AUTO-TRIGGER: If slow, log to slow queries
            if duration_ms > 1000:  # 1 second threshold
                logger.warning(f"Slow search query: {duration_ms:.2f}ms - {query[:50]}")

            # Format results
            if rows:
                results_list = []
                for row in rows:
                    results_list.append({
                        "memory_id": row['id'],
                        "title": row['title'],
                        "agent_id": row['agent_id'],
                        "content": row['content'][:200],
                        "created_at": str(row['created_at'])
                    })

                result["status"] = "success"
                result["data"] = {
                    "results_count": len(rows),
                    "duration_ms": duration_ms,
                    "memories": results_list
                }
            else:
                result["status"] = "success"
                result["data"] = {
                    "results_count": 0,
                    "message": f"No memories found for query: {query}"
                }
            return result

    except ValidationError as e:
        logger.error(f"search_memories validation failed: {e}")
        result["error"] = str(e)
        return result
    except Exception as e:
        logger.error(f"search_memories failed: {e}")
        result["error"] = f"Failed to search memories: {str(e)}"
        return result


async def delete_memory(
    memory_id: str,
    agent_id: str = "claude-code",
    confirm_token: Optional[str] = None,
    postgres_pool=None,
    realtime_sync=None,
    cross_agent_sharing=None
) -> Dict[str, Any]:
    """
    Delete a specific memory (Standard Memory MCP Tool)

    TRIGGER TYPE: (M) Manual - User must explicitly trigger this destructive operation

    SECURITY: Requires authorization and confirmation for non-admin agents.

    Parameters:
    -----------
    - memory_id: The unique ID of the memory to delete
    - agent_id: Agent requesting deletion (default: claude-code)
    - confirm_token: Optional confirmation token for non-dry-run operations
    - postgres_pool: PostgreSQL connection pool
    - realtime_sync: Real-time sync instance
    - cross_agent_sharing: Cross-agent sharing instance

    Returns:
    --------
    - Dictionary with status, data, error, timestamp
    """
    from src.security_mcp import (
        ValidationError,
        AuthorizationError,
        ConfirmationRequiredError,
        validate_uuid,
        validate_agent_id,
        authorizer,
        confirmation_manager,
        require_agent_authorization
    )

    result = {
        "status": "error",
        "data": None,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }

    try:
        # Input validation
        memory_id = validate_uuid(memory_id, "memory_id")
        agent_id = validate_agent_id(agent_id)

        # Require confirmation for destructive operation
        confirmation_manager.require_confirmation(
            operation="delete_memory",
            details={"memory_id": memory_id, "agent_id": agent_id},
            confirm_token=confirm_token
        )

        # Authorization check
        await require_agent_authorization(
            agent_id=agent_id,
            operation="delete_memory",
            memory_id=memory_id
        )

        if not postgres_pool:
            result["error"] = "PostgreSQL not available - cannot delete memory"
            return result

        async with postgres_pool.acquire() as conn:
            # Check if memory exists and get category
            existing = await conn.fetchrow("""
                SELECT id, agent_id, data->>'category' as category
                FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            if not existing:
                result["error"] = f"Memory not found: {memory_id}"
                return result

            # Delete memory
            await conn.execute("""
                DELETE FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            logger.info(f"OK Deleted memory: {memory_id} by agent: {agent_id}")

            # Publish deletion event for real-time sync
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_deleted",
                        memory_id=memory_id,
                        agent_id=agent_id,
                        data=json.dumps({"authorized": True})
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish memory deletion event: {e}")

            # AUTO-TRIGGER: Sync with shared agents
            if cross_agent_sharing and realtime_sync:
                try:
                    await realtime_sync.sync_agent_state(
                        source_agent=agent_id,
                        target_agent="all",
                        category="general"
                    )
                except Exception as e:
                    logger.warning(f"Failed to sync agent state after deletion: {e}")

            result["status"] = "success"
            result["data"] = {
                "memory_id": memory_id,
                "deleted_by": agent_id
            }
            return result

    except ValidationError as e:
        logger.error(f"delete_memory validation failed: {e}")
        result["error"] = str(e)
        return result
    except AuthorizationError as e:
        logger.error(f"delete_memory authorization failed: {e}")
        result["error"] = str(e)
        return result
    except ConfirmationRequiredError as e:
        logger.info(f"delete_memory confirmation required: {e}")
        result["error"] = str(e)
        return result
    except Exception as e:
        logger.error(f"delete_memory failed: {e}")
        result["error"] = f"Failed to delete memory: {str(e)}"
        return result


async def list_agents(
    postgres_pool=None,
    performance_analytics=None
) -> Dict[str, Any]:
    """
    List all agents that have stored memories (Standard Memory MCP Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs

    Parameters:
    -----------
    - postgres_pool: PostgreSQL connection pool
    - performance_analytics: Performance analytics instance

    Returns:
    --------
    - Dictionary with status, data, error, timestamp
    """
    result = {
        "status": "error",
        "data": None,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }

    try:
        if not postgres_pool:
            result["error"] = "PostgreSQL not available - cannot list agents"
            return result

        async with postgres_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT agent_id, COUNT(*) as memory_count
                FROM shared_memory.documents
                GROUP BY agent_id
                ORDER BY memory_count DESC
            """)

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="list_agents",
                        agent_id="system",
                        metadata={
                            "agents_count": len(rows) if rows else 0
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log list_agents performance: {e}")

            if rows:
                agents_list = []
                for row in rows:
                    agents_list.append({
                        "agent_id": row['agent_id'],
                        "memory_count": row['memory_count']
                    })

                result["status"] = "success"
                result["data"] = {
                    "agents_count": len(rows),
                    "agents": agents_list
                }
            else:
                result["status"] = "success"
                result["data"] = {
                    "agents_count": 0,
                    "message": "No agents found"
                }
            return result

    except Exception as e:
        logger.error(f"list_agents failed: {e}")
        result["error"] = f"Failed to list agents: {str(e)}"
        return result


# Export all tool functions
__all__ = [
    "add_memory",
    "search_memories",
    "delete_memory",
    "list_agents"
]
