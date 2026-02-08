#!/usr/bin/env python3
"""
Context Manager Agent
SMC Category - Context sharing and session management across agents
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from ...agent_memory_integration import AgentMemoryIntegration
from .smc_memory_wrapper import SMCMemoryWrapper

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Context Manager Agent
    SMC agent responsible for managing shared context across multiple agents
    """

    def __init__(self, memory_integration: AgentMemoryIntegration):
        self.memory_integration = memory_integration
        self.smc_memory = SMCMemoryWrapper(memory_integration)

        # Agent configuration
        self.agent_config = {
            "agent_id": "context-manager",
            "category": "SMC",
            "prefix": "smc_",
            "description": "Context management and sharing across agents",
            "capabilities": [
                "context_sharing",
                "session_management",
                "state_tracking",
                "context_synchronization",
                "memory_coordination"
            ],
            "max_concurrent_tasks": 8,
            "critical": True
        }

        # Context management settings
        self.context_settings = {
            "session_timeout_hours": 24,
            "max_context_size_mb": 50,
            "context_retention_days": 7,
            "auto_sync_interval_seconds": 300,  # 5 minutes
            "context_compression_threshold": 0.8
        }

        # Current context state
        self.context_state = {
            "active_sessions": {},
            "shared_contexts": {},
            "agent_contexts": {},
            "context_snapshots": {},
            "sync_queue": []
        }

    async def initialize(self):
        """Initialize the context manager agent"""
        try:
            logger.info(f"Initializing {self.agent_config['agent_id']}")

            # Load context configuration from memory
            await self._load_context_configuration()

            # Restore active sessions
            await self._restore_active_sessions()

            # Start background context synchronization
            asyncio.create_task(self._background_context_sync())

            logger.info(f"{self.agent_config['agent_id']} initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_config['agent_id']}: {e}")
            raise

    async def create_session(self, session_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new context session
        """
        try:
            session_id = session_request.get("session_id") or f"session_{datetime.now(UTC).timestamp()}"
            user_id = session_request.get("user_id")
            agent_id = session_request.get("agent_id")

            # Validate session request
            if not user_id:
                raise ValueError("User ID is required for session creation")

            session_context = {
                "session_id": session_id,
                "user_id": user_id,
                "agent_id": agent_id,
                "created_at": datetime.now(UTC),
                "last_accessed": datetime.now(UTC),
                "expires_at": datetime.now(UTC) + timedelta(hours=self.context_settings["session_timeout_hours"]),
                "status": "active",
                "context_data": session_request.get("initial_context", {}),
                "participants": [agent_id] if agent_id else [],
                "metadata": session_request.get("metadata", {})
            }

            # Store session context
            await self.smc_memory.store_context(
                agent_id=self.agent_config["agent_id"],
                context_data={
                    "type": "session_creation",
                    "session_id": session_id,
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "context": session_context
                },
                ttl_hours=self.context_settings["session_timeout_hours"],
                metadata={"category": "session_management"}
            )

            # Update internal state
            self.context_state["active_sessions"][session_id] = session_context

            logger.info(f"Created session: {session_id} for user {user_id}")

            return {
                "session_id": session_id,
                "status": "created",
                "expires_at": session_context["expires_at"].isoformat(),
                "participants": session_context["participants"]
            }

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return {"error": str(e), "status": "failed"}

    async def update_context(self, context_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update context for a session or agent
        """
        try:
            session_id = context_request.get("session_id")
            agent_id = context_request.get("agent_id")
            context_data = context_request.get("context_data", {})
            context_type = context_request.get("context_type", "general")

            if not session_id:
                raise ValueError("Session ID is required")

            # Validate session exists and is active
            session = self.context_state["active_sessions"].get(session_id)
            if not session or session["status"] != "active":
                raise ValueError(f"Invalid or inactive session: {session_id}")

            # Update session context
            session["context_data"].update(context_data)
            session["last_accessed"] = datetime.now(UTC)

            # Update agent-specific context if provided
            if agent_id:
                if session_id not in self.context_state["agent_contexts"]:
                    self.context_state["agent_contexts"][session_id] = {}

                if agent_id not in self.context_state["agent_contexts"][session_id]:
                    self.context_state["agent_contexts"][session_id][agent_id] = {}

                self.context_state["agent_contexts"][session_id][agent_id].update(context_data)

            # Store updated context
            await self.smc_memory.store_context(
                agent_id=self.agent_config["agent_id"],
                context_data={
                    "type": "context_update",
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "context_type": context_type,
                    "updates": context_data
                },
                ttl_hours=self.context_settings["session_timeout_hours"],
                metadata={"category": "context_management"}
            )

            # Queue for synchronization
            self._queue_context_sync(session_id, agent_id, context_data)

            logger.info(f"Updated context for session {session_id}")

            return {
                "session_id": session_id,
                "status": "updated",
                "context_size": len(str(session["context_data"])),
                "participants": session["participants"]
            }

        except Exception as e:
            logger.error(f"Failed to update context: {e}")
            return {"error": str(e), "status": "failed"}

    async def get_context(self, context_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve context for a session or agent
        """
        try:
            session_id = context_request.get("session_id")
            agent_id = context_request.get("agent_id")
            context_type = context_request.get("context_type", "all")

            if not session_id:
                raise ValueError("Session ID is required")

            # Get session context
            session = self.context_state["active_sessions"].get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            result = {
                "session_id": session_id,
                "status": "found",
                "session_context": session["context_data"],
                "last_accessed": session["last_accessed"].isoformat()
            }

            # Add agent-specific context if requested
            if agent_id and session_id in self.context_state["agent_contexts"]:
                agent_context = self.context_state["agent_contexts"][session_id].get(agent_id, {})
                result["agent_context"] = agent_context

            # Add shared context if available
            if session_id in self.context_state["shared_contexts"]:
                result["shared_context"] = self.context_state["shared_contexts"][session_id]

            # Update last accessed time
            session["last_accessed"] = datetime.now(UTC)

            logger.info(f"Retrieved context for session {session_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return {"error": str(e), "status": "failed"}

    async def share_context(self, share_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Share context between agents
        """
        try:
            session_id = share_request.get("session_id")
            from_agent = share_request.get("from_agent")
            to_agents = share_request.get("to_agents", [])
            context_data = share_request.get("context_data", {})
            share_type = share_request.get("share_type", "context_update")

            if not session_id or not from_agent or not to_agents:
                raise ValueError("Session ID, from_agent, and to_agents are required")

            # Validate session
            session = self.context_state["active_sessions"].get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # Create shared context entry
            shared_context = {
                "session_id": session_id,
                "from_agent": from_agent,
                "to_agents": to_agents,
                "share_type": share_type,
                "context_data": context_data,
                "timestamp": datetime.now(UTC),
                "shared": False
            }

            # Store shared context
            await self.smc_memory.store_context(
                agent_id=self.agent_config["agent_id"],
                context_data={
                    "type": "context_sharing",
                    "session_id": session_id,
                    "from_agent": from_agent,
                    "to_agents": to_agents,
                    "share_type": share_type,
                    "shared_context": context_data
                },
                ttl_hours=self.context_settings["session_timeout_hours"],
                metadata={"category": "context_sharing"}
            )

            # Update shared context state
            if session_id not in self.context_state["shared_contexts"]:
                self.context_state["shared_contexts"][session_id] = {}

            self.context_state["shared_contexts"][session_id][f"{from_agent}_{datetime.now(UTC).timestamp()}"] = shared_context

            # Notify target agents
            await self._notify_agents_of_shared_context(shared_context)

            logger.info(f"Shared context from {from_agent} to {to_agents} in session {session_id}")

            return {
                "session_id": session_id,
                "from_agent": from_agent,
                "to_agents": to_agents,
                "status": "shared",
                "shared_at": shared_context["timestamp"].isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to share context: {e}")
            return {"error": str(e), "status": "failed"}

    async def create_context_snapshot(self, snapshot_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a snapshot of current context state
        """
        try:
            session_id = snapshot_request.get("session_id")
            snapshot_name = snapshot_request.get("snapshot_name")
            description = snapshot_request.get("description", "")

            if not session_id or not snapshot_name:
                raise ValueError("Session ID and snapshot name are required")

            # Get current context state
            session = self.context_state["active_sessions"].get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # Create snapshot
            snapshot = {
                "snapshot_id": f"snapshot_{datetime.now(UTC).timestamp()}",
                "session_id": session_id,
                "name": snapshot_name,
                "description": description,
                "created_at": datetime.now(UTC),
                "session_context": session["context_data"].copy(),
                "agent_contexts": self.context_state["agent_contexts"].get(session_id, {}).copy(),
                "shared_contexts": self.context_state["shared_contexts"].get(session_id, {}).copy(),
                "participants": session["participants"].copy()
            }

            # Store snapshot
            await self.smc_memory.store_context(
                agent_id=self.agent_config["agent_id"],
                context_data={
                    "type": "context_snapshot",
                    "snapshot_id": snapshot["snapshot_id"],
                    "session_id": session_id,
                    "name": snapshot_name,
                    "description": description,
                    "snapshot_data": snapshot
                },
                ttl_hours=self.context_settings["context_retention_days"] * 24,
                metadata={"category": "context_snapshot"}
            )

            # Update internal state
            if session_id not in self.context_state["context_snapshots"]:
                self.context_state["context_snapshots"][session_id] = {}

            self.context_state["context_snapshots"][session_id][snapshot["snapshot_id"]] = snapshot

            logger.info(f"Created context snapshot: {snapshot_name} for session {session_id}")

            return {
                "snapshot_id": snapshot["snapshot_id"],
                "session_id": session_id,
                "name": snapshot_name,
                "status": "created",
                "created_at": snapshot["created_at"].isoformat(),
                "size_estimate": len(str(snapshot))
            }

        except Exception as e:
            logger.error(f"Failed to create context snapshot: {e}")
            return {"error": str(e), "status": "failed"}

    async def restore_context_snapshot(self, restore_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore context from a snapshot
        """
        try:
            session_id = restore_request.get("session_id")
            snapshot_id = restore_request.get("snapshot_id")

            if not session_id or not snapshot_id:
                raise ValueError("Session ID and snapshot ID are required")

            # Get snapshot
            session_snapshots = self.context_state["context_snapshots"].get(session_id, {})
            snapshot = session_snapshots.get(snapshot_id)

            if not snapshot:
                raise ValueError(f"Snapshot not found: {snapshot_id}")

            # Restore session context
            session = self.context_state["active_sessions"].get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # Backup current state before restore
            backup_snapshot_id = await self.create_context_snapshot({
                "session_id": session_id,
                "snapshot_name": f"backup_before_restore_{datetime.now(UTC).timestamp()}",
                "description": "Automatic backup before context restore"
            })

            # Restore context
            session["context_data"] = snapshot["session_context"].copy()
            session["last_accessed"] = datetime.now(UTC)

            # Restore agent contexts
            self.context_state["agent_contexts"][session_id] = snapshot["agent_contexts"].copy()

            # Restore shared contexts
            self.context_state["shared_contexts"][session_id] = snapshot["shared_contexts"].copy()

            # Store restoration
            await self.smc_memory.store_context(
                agent_id=self.agent_config["agent_id"],
                context_data={
                    "type": "context_restore",
                    "session_id": session_id,
                    "snapshot_id": snapshot_id,
                    "backup_snapshot_id": backup_snapshot_id.get("snapshot_id"),
                    "restored_at": datetime.now(UTC).isoformat()
                },
                ttl_hours=self.context_settings["context_retention_days"] * 24,
                metadata={"category": "context_restore"}
            )

            logger.info(f"Restored context from snapshot {snapshot_id} to session {session_id}")

            return {
                "session_id": session_id,
                "snapshot_id": snapshot_id,
                "backup_snapshot_id": backup_snapshot_id.get("snapshot_id"),
                "status": "restored",
                "restored_at": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to restore context snapshot: {e}")
            return {"error": str(e), "status": "failed"}

    async def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """
        Clean up expired sessions and contexts
        """
        try:
            current_time = datetime.now(UTC)
            expired_sessions = []
            cleaned_contexts = 0

            # Find expired sessions
            for session_id, session in self.context_state["active_sessions"].items():
                if current_time > session["expires_at"]:
                    expired_sessions.append(session_id)

            # Clean up expired sessions
            for session_id in expired_sessions:
                # Store cleanup record
                await self.smc_memory.store_context(
                    agent_id=self.agent_config["agent_id"],
                    context_data={
                        "type": "session_cleanup",
                        "session_id": session_id,
                        "reason": "expired",
                        "cleaned_at": current_time.isoformat()
                    },
                    ttl_hours=24,
                    metadata={"category": "maintenance"}
                )

                # Remove from internal state
                self.context_state["active_sessions"].pop(session_id, None)
                self.context_state["agent_contexts"].pop(session_id, None)
                self.context_state["shared_contexts"].pop(session_id, None)

                cleaned_contexts += 1

            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

            return {
                "cleaned_sessions": len(expired_sessions),
                "cleaned_contexts": cleaned_contexts,
                "active_sessions_remaining": len(self.context_state["active_sessions"]),
                "cleanup_time": current_time.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return {"error": str(e), "status": "failed"}

    async def get_context_statistics(self) -> Dict[str, Any]:
        """
        Get context management statistics
        """
        try:
            current_time = datetime.now(UTC)

            # Calculate statistics
            active_sessions = len(self.context_state["active_sessions"])
            total_contexts = sum(
                len(contexts) for contexts in self.context_state["agent_contexts"].values()
            )
            shared_contexts = sum(
                len(contexts) for contexts in self.context_state["shared_contexts"].values()
            )
            total_snapshots = sum(
                len(snapshots) for snapshots in self.context_state["context_snapshots"].values()
            )

            # Calculate session ages
            session_ages = []
            for session in self.context_state["active_sessions"].values():
                age = (current_time - session["created_at"]).total_seconds() / 3600  # hours
                session_ages.append(age)

            avg_session_age = sum(session_ages) / len(session_ages) if session_ages else 0

            # Calculate context sizes (simplified)
            total_context_size = 0
            for session in self.context_state["active_sessions"].values():
                total_context_size += len(str(session["context_data"]))

            statistics = {
                "timestamp": current_time.isoformat(),
                "active_sessions": active_sessions,
                "total_agent_contexts": total_contexts,
                "total_shared_contexts": shared_contexts,
                "total_snapshots": total_snapshots,
                "average_session_age_hours": avg_session_age,
                "estimated_context_size_mb": total_context_size / (1024 * 1024),
                "sync_queue_size": len(self.context_state["sync_queue"]),
                "memory_utilization": self._calculate_memory_utilization()
            }

            return statistics

        except Exception as e:
            logger.error(f"Failed to get context statistics: {e}")
            return {"error": str(e)}

    def _queue_context_sync(self, session_id: str, agent_id: str, context_data: Dict[str, Any]):
        """Queue context for synchronization"""
        sync_item = {
            "session_id": session_id,
            "agent_id": agent_id,
            "context_data": context_data,
            "timestamp": datetime.now(UTC)
        }
        self.context_state["sync_queue"].append(sync_item)

    async def _background_context_sync(self):
        """Background task for context synchronization"""
        while True:
            try:
                if self.context_state["sync_queue"]:
                    # Process sync queue
                    sync_item = self.context_state["sync_queue"].pop(0)
                    await self._process_context_sync(sync_item)

                await asyncio.sleep(self.context_settings["auto_sync_interval_seconds"])

            except Exception as e:
                logger.error(f"Error in background context sync: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _process_context_sync(self, sync_item: Dict[str, Any]):
        """Process individual context synchronization"""
        # Implementation for context synchronization
        pass

    async def _notify_agents_of_shared_context(self, shared_context: Dict[str, Any]):
        """Notify agents about shared context"""
        from ..coordination.sub_agent_coordinator import MessageType, AgentMessage

        for to_agent in shared_context["to_agents"]:
            notification = AgentMessage(
                message_id=f"ctx_notify_{datetime.now(UTC).timestamp()}",
                from_agent=self.agent_config["agent_id"],
                to_agent=to_agent,
                message_type=MessageType.NOTIFICATION,
                subject="Context Shared",
                content={
                    "session_id": shared_context["session_id"],
                    "from_agent": shared_context["from_agent"],
                    "share_type": shared_context["share_type"]
                }
            )

            # Send notification through coordination system
            # In real implementation, would use the coordinator to send messages

    def _calculate_memory_utilization(self) -> float:
        """Calculate memory utilization percentage"""
        # Simplified calculation
        total_size = 0
        for session in self.context_state["active_sessions"].values():
            total_size += len(str(session["context_data"]))

        max_size_mb = self.context_settings["max_context_size_mb"]
        current_size_mb = total_size / (1024 * 1024)

        return min((current_size_mb / max_size_mb) * 100, 100) if max_size_mb > 0 else 0

    async def _load_context_configuration(self):
        """Load context management configuration from memory"""
        pass

    async def _restore_active_sessions(self):
        """Restore active sessions from memory"""
        # Load active sessions from memory storage
        pass

# Factory function for agent creation
async def create_context_manager(memory_integration: AgentMemoryIntegration) -> ContextManager:
    """Create and initialize Context Manager agent"""
    agent = ContextManager(memory_integration)
    await agent.initialize()
    return agent

if __name__ == "__main__":
    # Example usage
    async def example_usage():
        from ...agent_memory_integration import AgentMemoryIntegration

        integration = AgentMemoryIntegration()
        await integration.initialize()

        context_manager = await create_context_manager(integration)

        # Create session
        session_result = await context_manager.create_session({
            "session_id": "session_001",
            "user_id": "user_123",
            "agent_id": "algorithmic-trading-system",
            "initial_context": {"theme": "trading", "symbols": ["AAPL", "GOOGL"]}
        })
        print(f"Session created: {session_result}")

        # Update context
        update_result = await context_manager.update_context({
            "session_id": "session_001",
            "agent_id": "algorithmic-trading-system",
            "context_data": {"current_position": 1000, "strategy": "momentum"}
        })
        print(f"Context updated: {update_result}")

        # Share context
        share_result = await context_manager.share_context({
            "session_id": "session_001",
            "from_agent": "algorithmic-trading-system",
            "to_agents": ["risk-management"],
            "context_data": {"position_size": 1000}
        })
        print(f"Context shared: {share_result}")

        # Get statistics
        stats = await context_manager.get_context_statistics()
        print(f"Context statistics: {stats}")

        await integration.close()

    asyncio.run(example_usage())