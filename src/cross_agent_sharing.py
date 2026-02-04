"""
Cross-Agent Memory Sharing Module for Enhanced Cognee
Enables controlled memory sharing between agents
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class SharePolicy(Enum):
    """Memory sharing policies"""
    PRIVATE = "private"  # Only owner can access
    SHARED = "shared"  # All agents can read
    CATEGORY_SHARED = "category_shared"  # Agents with same category can read
    CUSTOM = "custom"  # Custom access control list


class CrossAgentMemorySharing:
    """Manages memory sharing between agents"""

    def __init__(self, postgres_pool):
        self.postgres_pool = postgres_pool

    async def set_memory_sharing(
        self,
        memory_id: str,
        policy: SharePolicy,
        allowed_agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Set sharing policy for a memory

        Args:
            memory_id: ID of the memory
            policy: Sharing policy (private, shared, category_shared, custom)
            allowed_agents: List of agent IDs that can access (for custom policy)

        Returns:
            Dict with result
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                # Build sharing metadata
                sharing_data = {
                    "policy": policy.value,
                    "allowed_agents": allowed_agents or [],
                    "shared_at": datetime.utcnow().isoformat()
                }

                # Update memory with sharing policy
                result = await conn.execute("""
                    UPDATE shared_memory.documents
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{sharing}',
                        $1::jsonb
                    )
                    WHERE id = $2
                """, json.dumps(sharing_data), memory_id)

                if result == 0:
                    return {
                        "status": "not_found",
                        "memory_id": memory_id
                    }

                logger.info(f"Set sharing policy '{policy.value}' for memory {memory_id}")

                return {
                    "status": "success",
                    "memory_id": memory_id,
                    "policy": policy.value
                }

        except Exception as e:
            logger.error(f"Failed to set sharing policy: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def can_agent_access_memory(
        self,
        memory_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Check if an agent can access a memory

        Args:
            memory_id: ID of the memory
            agent_id: Agent requesting access

        Returns:
            Dict with access decision
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        id,
                        agent_id as owner_id,
                        metadata->'sharing'->>'policy' as policy,
                        metadata->'sharing'->>'allowed_agents' as allowed_agents
                    FROM shared_memory.documents
                    WHERE id = $1
                """, memory_id)

                if not row:
                    return {
                        "can_access": False,
                        "reason": "memory_not_found"
                    }

                # Owner can always access
                if row["owner_id"] == agent_id:
                    return {
                        "can_access": True,
                        "reason": "owner"
                    }

                policy = row["policy"] or "private"

                if policy == "private":
                    return {
                        "can_access": False,
                        "reason": "private_memory"
                    }

                elif policy == "shared":
                    return {
                        "can_access": True,
                        "reason": "public_memory"
                    }

                elif policy == "category_shared":
                    # Check if agent shares the same category
                    category = await conn.fetchval("""
                        SELECT memory_category FROM shared_memory.documents WHERE id = $1
                    """, memory_id)

                    # Check if agent has memories in this category
                    has_access = await conn.fetchval("""
                        SELECT COUNT(*) > 0
                        FROM shared_memory.documents
                        WHERE agent_id = $1
                        AND memory_category = $2
                    """, agent_id, category)

                    return {
                        "can_access": has_access,
                        "reason": f"category_shared:{category}"
                    }

                elif policy == "custom":
                    allowed = row["allowed_agents"] or []
                    return {
                        "can_access": agent_id in allowed,
                        "reason": "custom_whitelist"
                    }

                else:
                    return {
                        "can_access": False,
                        "reason": "unknown_policy"
                    }

        except Exception as e:
            logger.error(f"Failed to check access: {e}")
            return {
                "can_access": False,
                "error": str(e)
            }

    async def get_shared_memories(
        self,
        agent_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get all memories shared with this agent"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Get memories this agent can access
                memories = await conn.fetch("""
                    SELECT
                        id,
                        title,
                        content,
                        agent_id as owner_id,
                        memory_category,
                        created_at
                    FROM shared_memory.documents
                    WHERE
                        agent_id = $1
                        OR metadata->'sharing'->>'policy' = 'shared'
                        OR (metadata->'sharing'->>'policy' = 'category_shared'
                            AND memory_category IN (
                                SELECT memory_category
                                FROM shared_memory.documents
                                WHERE agent_id = $1
                            ))
                        OR $1 = ANY(JSONB_ARRAY_ELEMENTS_TEXT(
                            COALESCE(metadata->'sharing'->>'allowed_agents', '[]'::jsonb)
                        ))
                    ORDER BY created_at DESC
                    LIMIT $2
                """, agent_id, limit)

                return [dict(row) for row in memories]

        except Exception as e:
            logger.error(f"Failed to get shared memories: {e}")
            return []

    async def get_sharing_stats(self) -> Dict[str, Any]:
        """Get statistics about memory sharing"""
        try:
            async with self.postgres_pool.acquire() as conn:
                stats = await conn.fetch("""
                    SELECT
                        metadata->'sharing'->>'policy' as policy,
                        COUNT(*) as count
                    FROM shared_memory.documents
                    WHERE metadata->'sharing' IS NOT NULL
                    GROUP BY policy
                """)

                policy_stats = {row["policy"]: row["count"] for row in stats}

                # Total shared memories
                total_shared = sum(policy_stats.values())

                # Total private memories
                total_private = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM shared_memory.documents
                    WHERE metadata->'sharing' IS NULL
                    OR metadata->'sharing'->>'policy' = 'private'
                """)

                return {
                    "total_shared": total_shared,
                    "total_private": total_private,
                    "by_policy": policy_stats
                }

        except Exception as e:
            logger.error(f"Failed to get sharing stats: {e}")
            return {"error": str(e)}

    async def create_shared_space(
        self,
        space_name: str,
        member_agents: List[str]
    ) -> Dict[str, Any]:
        """
        Create a shared memory space for multiple agents

        Args:
            space_name: Name for the shared space
            member_agents: List of agent IDs that can access this space

        Returns:
            Dict with result
        """
        try:
            # In PostgreSQL, we'd use a separate table or schema
            # For now, we'll use metadata to track shared spaces

            # Store shared space configuration in a special memory
            async with self.postgres_pool.acquire() as conn:
                space_id = f"shared_space_{space_name}"

                await conn.execute("""
                    INSERT INTO shared_memory.documents
                    (id, title, content, agent_id, memory_category, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        metadata = EXCLUDED.metadata || $6
                """,
                    space_id,
                    f"Shared Space: {space_name}",
                    f"Shared space for agents: {', '.join(member_agents)}",
                    "system",
                    "system",
                    json.dumps({
                        "type": "shared_space",
                        "space_name": space_name,
                        "members": member_agents,
                        "created_at": datetime.utcnow().isoformat()
                    })
                )

                logger.info(f"Created shared space '{space_name}' for {len(member_agents)} agents")

                return {
                    "status": "success",
                    "space_name": space_name,
                    "member_count": len(member_agents),
                    "space_id": space_id
                }

        except Exception as e:
            logger.error(f"Failed to create shared space: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
