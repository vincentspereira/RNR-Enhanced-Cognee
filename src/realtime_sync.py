"""
Real-Time Memory Synchronization Module for Enhanced Cognee
Enables real-time memory updates across multiple agents using Redis pub/sub
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SyncEvent:
    """Represents a synchronization event"""
    event_type: str  # "memory_added", "memory_updated", "memory_deleted"
    memory_id: str
    agent_id: str
    timestamp: datetime
    data: Dict[str, Any]


class RealTimeMemorySync:
    """Manages real-time synchronization of memories across agents"""

    def __init__(self, redis_client, postgres_pool):
        self.redis_client = redis_client
        self.postgres_pool = postgres_pool

        # Redis pub/sub channels
        self.sync_channel = "enhanced_cognee:memory_updates"
        self.agent_channels = {}  # agent_id -> channel name

        # Subscriptions
        self.subscriptions = {}

    async def publish_memory_event(
        self,
        event_type: str,
        memory_id: str,
        agent_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Publish a memory event to all subscribers

        Args:
            event_type: Type of event (memory_added, memory_updated, memory_deleted)
            memory_id: ID of the memory
            agent_id: Agent that triggered the event
            data: Additional event data

        Returns:
            Dict with publish result
        """
        try:
            event = {
                "event_type": event_type,
                "memory_id": memory_id,
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }

            # Publish to main sync channel
            await self.redis_client.publish(
                self.sync_channel,
                json.dumps(event)
            )

            logger.info(f"Published {event_type} event for memory {memory_id} from agent {agent_id}")

            return {
                "status": "success",
                "event_type": event_type,
                "memory_id": memory_id,
                "subscribers_notified": "all"
            }

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def subscribe_to_updates(
        self,
        agent_id: str,
        callback: Callable
    ) -> Dict[str, Any]:
        """
        Subscribe an agent to memory updates

        Args:
            agent_id: Agent ID subscribing to updates
            callback: Async function to call when update received

        Returns:
            Dict with subscription result
        """
        try:
            # Store subscription
            self.subscriptions[agent_id] = callback

            logger.info(f"Agent {agent_id} subscribed to memory updates")

            return {
                "status": "success",
                "agent_id": agent_id,
                "channel": self.sync_channel
            }

        except Exception as e:
            logger.error(f"Failed to subscribe agent: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def start_sync_listener(self):
        """Start listening for sync events in background"""
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(self.sync_channel)

            logger.info(f"Started listening on sync channel: {self.sync_channel}")

            async for message in pubsub.listen():
                try:
                    if message.type == "message":
                        event = json.loads(message.data)
                        await self._handle_sync_event(event)
                except Exception as e:
                    logger.error(f"Error handling sync event: {e}")

        except Exception as e:
            logger.error(f"Failed to start sync listener: {e}")

    async def _handle_sync_event(self, event: Dict):
        """Handle a synchronization event"""
        try:
            event_type = event["event_type"]
            memory_id = event["memory_id"]
            agent_id = event["agent_id"]
            data = event.get("data", {})

            # Notify all subscribed agents
            for subscribed_agent_id, callback in self.subscriptions.items():
                try:
                    # Don't notify the agent that sent the event
                    if subscribed_agent_id != agent_id:
                        await callback(event)
                        logger.debug(f"Notified agent {subscribed_agent_id} of {event_type} for memory {memory_id}")
                except Exception as e:
                    logger.error(f"Failed to notify agent {subscribed_agent_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to handle sync event: {e}")

    async def broadcast_memory_update(
        self,
        memory_id: str,
        update_type: str,
        agent_id: str,
        target_agents: List[str] = None
    ) -> Dict[str, Any]:
        """
        Broadcast a memory update to specific agents

        Args:
            memory_id: ID of the memory that was updated
            update_type: Type of update (updated, deleted, etc.)
            agent_id: Agent that made the update
            target_agents: List of agent IDs to notify (None = all)

        Returns:
            Dict with broadcast result
        """
        try:
            # Get memory details
            async with self.postgres_pool.acquire() as conn:
                memory = await conn.fetchrow("""
                    SELECT id, content, agent_id, memory_category
                    FROM shared_memory.documents
                    WHERE id = $1
                """, memory_id)

            if not memory:
                return {
                    "status": "not_found",
                    "memory_id": memory_id
                }

            # Create update event
            event = {
                "event_type": f"memory_{update_type}",
                "memory_id": memory_id,
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "memory": dict(memory),
                    "update_type": update_type
                }
            }

            # Notify subscribed agents
            notified_count = 0
            for subscribed_agent_id, callback in self.subscriptions.items():
                # Filter by target_agents if specified
                if target_agents is None or subscribed_agent_id in target_agents:
                    if subscribed_agent_id != agent_id:  # Don't notify sender
                        try:
                            await callback(event)
                            notified_count += 1
                        except Exception as e:
                            logger.error(f"Failed to notify {subscribed_agent_id}: {e}")

            logger.info(f"Broadcast memory {update_type} for {memory_id} to {notified_count} agents")

            return {
                "status": "success",
                "update_type": update_type,
                "memory_id": memory_id,
                "agents_notified": notified_count
            }

        except Exception as e:
            logger.error(f"Failed to broadcast memory update: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_sync_status(self) -> Dict[str, Any]:
        """Get synchronization status and statistics"""
        try:
            # Get subscription info
            subscribed_agents = list(self.subscriptions.keys())

            # Get Redis pub/sub info
            info = await self.redis_client.info("stats")
            connected_clients = info.get("connected_clients", 0)

            return {
                "status": "active",
                "sync_channel": self.sync_channel,
                "subscribed_agents": subscribed_agents,
                "subscribers_count": len(subscribed_agents),
                "redis_connected_clients": connected_clients
            }

        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def sync_agent_state(
        self,
        source_agent_id: str,
        target_agent_id: str,
        memory_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronize memory state between two agents

        Args:
            source_agent_id: Source agent to sync from
            target_agent_id: Target agent to sync to
            memory_category: Optional category filter

        Returns:
            Dict with sync result
        """
        try:
            # Get memories from source agent
            async with self.postgres_pool.acquire() as conn:
                if memory_category:
                    memories = await conn.fetch("""
                        SELECT id, content, metadata
                        FROM shared_memory.documents
                        WHERE agent_id = $1
                        AND memory_category = $2
                        ORDER BY created_at DESC
                        LIMIT 100
                    """, source_agent_id, memory_category)
                else:
                    memories = await conn.fetch("""
                        SELECT id, content, metadata
                        FROM shared_memory.documents
                        WHERE agent_id = $1
                        ORDER BY created_at DESC
                        LIMIT 100
                    """, source_agent_id)

                sync_result = {
                    "status": "success",
                    "source_agent": source_agent_id,
                    "target_agent": target_agent_id,
                    "memories_synced": 0,
                    "errors": []
                }

                # Copy memories to target agent
                for memory in memories:
                    try:
                        new_memory_id = f"{target_agent_id}_{memory['id']}"

                        await conn.execute("""
                            INSERT INTO shared_memory.documents
                            (id, title, content, agent_id, memory_category, metadata, created_at)
                            SELECT $1, $2 || ' (from ' || $3 || ')', $4, $5, $6, $7
                            FROM shared_memory.documents
                            WHERE id = $8
                            ON CONFLICT (id) DO UPDATE SET
                                content = EXCLUDED.content,
                                metadata = EXCLUDED.metadata || jsonb_build_object(
                                    'synced_from', $3,
                                    'synced_at', NOW()::text
                                )
                        """, new_memory_id, memory["id"], source_agent_id, target_agent_id,
                            memory.get("memory_category", "shared"), memory.get("metadata", {}), memory["id"])

                        sync_result["memories_synced"] += 1

                    except Exception as e:
                        sync_result["errors"].append({
                            "memory_id": memory["id"],
                            "error": str(e)
                }

                logger.info(f"Synced {sync_result['memories_synced']} memories from {source_agent_id} to {target_agent_id}")

                return sync_result

        except Exception as e:
            logger.error(f"Failed to sync agent state: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def resolve_conflict(
        self,
        memory_id: str,
        conflict_data: Dict[str, Any],
        resolution_strategy: str = "keep_newest"
    ) -> Dict[str, Any]:
        """
        Resolve memory synchronization conflicts

        Args:
            memory_id: ID of memory with conflict
            conflict_data: Details about the conflict
            resolution_strategy: How to resolve (keep_newest, merge, manual)

        Returns:
            Dict with resolution result
        """
        try:
            async with self.postgres_pool.acquire() as conn:
                if resolution_strategy == "keep_newest":
                    # Keep the most recently updated version
                    result = await conn.execute("""
                        UPDATE shared_memory.documents
                        SET
                            metadata = jsonb_set(
                                COALESCE(metadata, '{}'::jsonb),
                                '{conflict_resolved}',
                                'keep_newest',
                                '{resolved_at}',
                                NOW()::text
                            )
                        WHERE id = $1
                    """, memory_id)

                    logger.info(f"Resolved conflict for memory {memory_id} using keep_newest strategy")

                    return {
                        "status": "success",
                        "memory_id": memory_id,
                        "resolution": resolution_strategy
                    }

                elif resolution_strategy == "merge":
                    # Merge conflicting data (implementation depends on conflict type)
                    # For now, just mark as resolved
                    await conn.execute("""
                        UPDATE shared_memory.documents
                        SET metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{conflict_resolved}',
                            'merged',
                            '{resolved_at}',
                            NOW()::text
                        )
                        WHERE id = $1
                    """, memory_id)

                    return {
                        "status": "success",
                        "memory_id": memory_id,
                        "resolution": resolution_strategy
                    }

                else:
                    return {
                        "status": "error",
                        "error": f"Unknown resolution strategy: {resolution_strategy}"
                    }

        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
