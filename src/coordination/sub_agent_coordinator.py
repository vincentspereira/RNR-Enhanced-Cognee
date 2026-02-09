#!/usr/bin/env python3
"""
Sub-Agent Coordination System
Coordinates communication and task orchestration across 21 sub-agents
Uses Enhanced Cognee memory stack as coordination backbone
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from ..agent_memory_integration import AgentMemoryIntegration, MemoryCategory, MemoryType
from ..agents.ats.ats_memory_wrapper import ATSMemoryWrapper
from ..agents.oma.oma_memory_wrapper import OMAMemoryWrapper
from ..agents.smc.smc_memory_wrapper import SMCMemoryWrapper

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent operational status"""
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    SUSPENDED = "suspended"
    ERROR = "error"

class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

class MessageType(Enum):
    """Message types for agent communication"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    TASK_ASSIGNMENT = "task_assignment"
    TASK_COMPLETION = "task_completion"
    ERROR_REPORT = "error_report"
    HEARTBEAT = "heartbeat"

@dataclass
class AgentTask:
    """Task definition for agent coordination"""
    task_id: str
    title: str
    description: str
    assigned_to: List[str]
    created_by: str
    priority: TaskPriority
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

@dataclass
class AgentMessage:
    """Message for inter-agent communication"""
    message_id: str
    from_agent: str
    to_agent: str
    message_type: MessageType
    subject: str
    content: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reply_to: Optional[str] = None
    requires_response: bool = False
    responded_at: Optional[datetime] = None

@dataclass
class AgentCapability:
    """Agent capability definition"""
    agent_id: str
    capability_name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    max_concurrent_tasks: int = 1
    avg_processing_time: Optional[float] = None  # in seconds
    success_rate: float = 1.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

class SubAgentCoordinator:
    """
    Coordinates 21 sub-agents across ATS/OMA/SMC categories
    Manages task distribution, communication, and resource allocation
    """

    def __init__(self, integration: AgentMemoryIntegration):
        self.integration = integration

        # Initialize specialized memory wrappers
        self.ats_wrapper = ATSMemoryWrapper(integration)
        self.oma_wrapper = OMAMemoryWrapper(integration)
        self.smc_wrapper = SMCMemoryWrapper(integration)

        # Agent registry with capabilities
        self.agent_registry = self._initialize_agent_registry()

        # Active tasks and messages
        self.active_tasks: Dict[str, AgentTask] = {}
        self.message_queue: List[AgentMessage] = []
        self.agent_capabilities: Dict[str, AgentCapability] = {}

        # Coordination settings
        self.coordination_settings = {
            "max_task_retries": 3,
            "task_timeout_minutes": 60,
            "message_retention_hours": 168,  # 7 days
            "heartbeat_interval_seconds": 30,
            "load_balancing_strategy": "least_loaded"
        }

    def _initialize_agent_registry(self) -> Dict[str, Dict[str, Any]]:
        """Initialize registry of all 21 sub-agents with their properties"""
        return {
            # ATS agents (7)
            "algorithmic-trading-system": {
                "category": MemoryCategory.ATS,
                "type": "trading_engine",
                "capabilities": ["market_analysis", "signal_generation", "order_execution"],
                "max_concurrent_tasks": 5,
                "critical": True
            },
            "risk-management": {
                "category": MemoryCategory.ATS,
                "type": "risk_controller",
                "capabilities": ["risk_assessment", "position_monitoring", "compliance_check"],
                "max_concurrent_tasks": 3,
                "critical": True
            },
            "portfolio-optimizer": {
                "category": MemoryCategory.ATS,
                "type": "portfolio_manager",
                "capabilities": ["portfolio_optimization", "allocation_analysis", "performance_tracking"],
                "max_concurrent_tasks": 2,
                "critical": False
            },
            "market-analyzer": {
                "category": MemoryCategory.ATS,
                "type": "data_analyzer",
                "capabilities": ["market_data_analysis", "trend_detection", "sentiment_analysis"],
                "max_concurrent_tasks": 4,
                "critical": False
            },
            "execution-engine": {
                "category": MemoryCategory.ATS,
                "type": "execution_handler",
                "capabilities": ["order_execution", "trade_confirmation", "settlement"],
                "max_concurrent_tasks": 10,
                "critical": True
            },
            "signal-processor": {
                "category": MemoryCategory.ATS,
                "type": "signal_processor",
                "capabilities": ["signal_validation", "signal_enrichment", "signal_routing"],
                "max_concurrent_tasks": 6,
                "critical": False
            },
            "compliance-monitor": {
                "category": MemoryCategory.ATS,
                "type": "compliance_checker",
                "capabilities": ["regulatory_monitoring", "compliance_reporting", "audit_trail"],
                "max_concurrent_tasks": 2,
                "critical": True
            },

            # OMA agents (10)
            "code-reviewer": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["code_analysis", "quality_check", "security_audit"],
                "max_concurrent_tasks": 3,
                "critical": False
            },
            "data-engineer": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["data_pipeline", "etl_process", "data_quality"],
                "max_concurrent_tasks": 4,
                "critical": False
            },
            "debug-specialist": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["bug_analysis", "error_resolution", "performance_debugging"],
                "max_concurrent_tasks": 2,
                "critical": False
            },
            "frontend-developer": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["ui_development", "frontend_optimization", "user_experience"],
                "max_concurrent_tasks": 3,
                "critical": False
            },
            "backend-developer": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["api_development", "backend_optimization", "database_design"],
                "max_concurrent_tasks": 3,
                "critical": False
            },
            "security-specialist": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["security_analysis", "vulnerability_assessment", "penetration_testing"],
                "max_concurrent_tasks": 2,
                "critical": False
            },
            "test-engineer": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["test_automation", "quality_assurance", "performance_testing"],
                "max_concurrent_tasks": 3,
                "critical": False
            },
            "technical-writer": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["documentation", "api_docs", "user_guides"],
                "max_concurrent_tasks": 2,
                "critical": False
            },
            "devops-engineer": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["deployment", "infrastructure", "monitoring"],
                "max_concurrent_tasks": 2,
                "critical": False
            },
            "ui-ux-designer": {
                "category": MemoryCategory.OMA,
                "type": "development_tool",
                "capabilities": ["design_system", "user_research", "prototyping"],
                "max_concurrent_tasks": 2,
                "critical": False
            },

            # SMC agents (6)
            "context-manager": {
                "category": MemoryCategory.SMC,
                "type": "coordination_tool",
                "capabilities": ["context_sharing", "session_management", "state_tracking"],
                "max_concurrent_tasks": 8,
                "critical": True
            },
            "knowledge-graph": {
                "category": MemoryCategory.SMC,
                "type": "coordination_tool",
                "capabilities": ["knowledge_management", "semantic_search", "relationship_mapping"],
                "max_concurrent_tasks": 4,
                "critical": True
            },
            "message-broker": {
                "category": MemoryCategory.SMC,
                "type": "coordination_tool",
                "capabilities": ["message_routing", "communication_protocol", "queue_management"],
                "max_concurrent_tasks": 10,
                "critical": True
            },
            "task-scheduler": {
                "category": MemoryCategory.SMC,
                "type": "coordination_tool",
                "capabilities": ["task_scheduling", "resource_allocation", "workflow_management"],
                "max_concurrent_tasks": 6,
                "critical": True
            },
            "data-processor": {
                "category": MemoryCategory.SMC,
                "type": "coordination_tool",
                "capabilities": ["data_transformation", "batch_processing", "stream_processing"],
                "max_concurrent_tasks": 5,
                "critical": False
            },
            "api-gateway": {
                "category": MemoryCategory.SMC,
                "type": "coordination_tool",
                "capabilities": ["api_management", "rate_limiting", "request_routing"],
                "max_concurrent_tasks": 12,
                "critical": True
            }
        }

    async def assign_task(self, task: AgentTask) -> bool:
        """
        Assign task to appropriate agents based on capabilities and current load
        """
        try:
            # Store task in coordination memory
            await self._store_coordination_task(task)

            # Determine best agents for this task
            suitable_agents = await self._find_suitable_agents(task)

            if not suitable_agents:
                logger.warning(f"No suitable agents found for task {task.task_id}")
                task.status = "failed"
                task.error_message = "No suitable agents available"
                return False

            # Assign to agents with lowest load
            assigned_agents = await self._assign_to_least_loaded_agents(
                suitable_agents, task, max_assignments=min(3, len(suitable_agents))
            )

            task.assigned_to = assigned_agents
            task.status = "assigned"

            # Send task assignment messages
            for agent_id in assigned_agents:
                message = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    from_agent="coordinator",
                    to_agent=agent_id,
                    message_type=MessageType.TASK_ASSIGNMENT,
                    subject=f"Task Assignment: {task.title}",
                    content={
                        "task_id": task.task_id,
                        "task": task.__dict__,
                        "assignment_reason": "capability_match"
                    },
                    priority=task.priority,
                    requires_response=True
                )
                await self._send_message(message)

            logger.info(f"Task {task.task_id} assigned to agents: {assigned_agents}")
            self.active_tasks[task.task_id] = task
            return True

        except Exception as e:
            logger.error(f"Failed to assign task {task.task_id}: {e}")
            task.status = "failed"
            task.error_message = str(e)
            return False

    async def register_agent_capability(self, capability: AgentCapability) -> bool:
        """Register or update agent capability"""
        try:
            self.agent_capabilities[f"{capability.agent_id}_{capability.capability_name}"] = capability

            # Store in memory for persistence
            await self.smc_wrapper.store_context(
                agent_id="coordinator",
                context_data={
                    "type": "capability_registration",
                    "agent_id": capability.agent_id,
                    "capability": capability.__dict__
                },
                ttl_hours=24 * 7,  # 1 week
                metadata={"category": "coordination"}
            )

            logger.info(f"Registered capability {capability.capability_name} for agent {capability.agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to register capability: {e}")
            return False

    async def route_message(self, message: AgentMessage) -> bool:
        """
        Route message between agents with appropriate handling
        """
        try:
            # Store message in coordination memory
            await self._store_coordination_message(message)

            # Validate recipient
            if message.to_agent not in self.agent_registry:
                logger.error(f"Unknown recipient agent: {message.to_agent}")
                return False

            # Route message based on type
            if message.message_type == MessageType.BROADCAST:
                return await self._broadcast_message(message)
            elif message.to_agent == "all":
                return await self._broadcast_to_all(message)
            else:
                return await self._send_direct_message(message)

        except Exception as e:
            logger.error(f"Failed to route message {message.message_id}: {e}")
            return False

    async def get_agent_load(self, agent_id: str) -> Dict[str, Any]:
        """Get current load statistics for an agent"""
        try:
            # Count active tasks for this agent
            active_tasks = sum(
                1 for task in self.active_tasks.values()
                if agent_id in task.assigned_to and task.status in ["assigned", "in_progress"]
            )

            # Get agent info
            agent_info = self.agent_registry.get(agent_id, {})
            max_tasks = agent_info.get("max_concurrent_tasks", 1)

            # Calculate load percentage
            load_percentage = (active_tasks / max_tasks) * 100 if max_tasks > 0 else 0

            return {
                "agent_id": agent_id,
                "active_tasks": active_tasks,
                "max_concurrent_tasks": max_tasks,
                "load_percentage": min(load_percentage, 100),
                "status": "busy" if load_percentage >= 80 else "available",
                "agent_type": agent_info.get("type", "unknown"),
                "critical": agent_info.get("critical", False)
            }

        except Exception as e:
            logger.error(f"Failed to get load for agent {agent_id}: {e}")
            return {
                "agent_id": agent_id,
                "error": str(e),
                "load_percentage": 100,
                "status": "error"
            }

    async def get_coordination_overview(self) -> Dict[str, Any]:
        """Get comprehensive overview of coordination system"""
        try:
            # Task statistics
            total_tasks = len(self.active_tasks)
            task_status_counts = {}
            for task in self.active_tasks.values():
                task_status_counts[task.status] = task_status_counts.get(task.status, 0) + 1

            # Agent load statistics
            agent_loads = {}
            total_load = 0
            active_agents = 0

            for agent_id in self.agent_registry.keys():
                load = await self.get_agent_load(agent_id)
                agent_loads[agent_id] = load
                if load.get("status") != "error":
                    total_load += load.get("load_percentage", 0)
                    active_agents += 1

            avg_load = total_load / active_agents if active_agents > 0 else 0

            # Category-wise statistics
            category_stats = {}
            for agent_id, agent_info in self.agent_registry.items():
                category = agent_info["category"].value
                if category not in category_stats:
                    category_stats[category] = {"total_agents": 0, "active_agents": 0, "avg_load": 0}

                category_stats[category]["total_agents"] += 1
                if agent_loads[agent_id].get("status") != "error":
                    category_stats[category]["active_agents"] += 1
                    category_stats[category]["avg_load"] += agent_loads[agent_id].get("load_percentage", 0)

            # Calculate category averages
            for category in category_stats:
                if category_stats[category]["active_agents"] > 0:
                    category_stats[category]["avg_load"] /= category_stats[category]["active_agents"]

            # Recent message activity
            recent_messages = await self._get_recent_message_activity(hours=1)

            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "total_agents": len(self.agent_registry),
                "active_agents": active_agents,
                "system_avg_load": avg_load,
                "task_statistics": {
                    "total_tasks": total_tasks,
                    "status_breakdown": task_status_counts,
                    "completion_rate": (task_status_counts.get("completed", 0) / total_tasks * 100) if total_tasks > 0 else 0
                },
                "agent_loads": agent_loads,
                "category_statistics": category_stats,
                "message_activity": {
                    "messages_last_hour": len(recent_messages),
                    "most_active_agents": self._get_most_active_agents(recent_messages)
                },
                "coordination_health": {
                    "message_broker_status": "healthy" if agent_loads.get("message-broker", {}).get("status") != "error" else "unhealthy",
                    "task_scheduler_status": "healthy" if agent_loads.get("task-scheduler", {}).get("status") != "error" else "unhealthy",
                    "context_manager_status": "healthy" if agent_loads.get("context-manager", {}).get("status") != "error" else "unhealthy"
                }
            }

        except Exception as e:
            logger.error(f"Failed to get coordination overview: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }

    async def _find_suitable_agents(self, task: AgentTask) -> List[str]:
        """Find agents suitable for a given task"""
        suitable_agents = []

        # Simple capability matching (can be enhanced with ML)
        task_keywords = task.title.lower().split() + task.description.lower().split()

        for agent_id, agent_info in self.agent_registry.items():
            capabilities = [cap.lower() for cap in agent_info.get("capabilities", [])]

            # Check if any capability matches task keywords
            capability_match = any(
                any(keyword in capability for keyword in task_keywords)
                for capability in capabilities
            )

            if capability_match:
                suitable_agents.append(agent_id)

        return suitable_agents

    async def _assign_to_least_loaded_agents(self, agents: List[str], task: AgentTask, max_assignments: int = 1) -> List[str]:
        """Assign task to agents with lowest current load"""
        agent_loads = []

        for agent_id in agents:
            load_info = await self.get_agent_load(agent_id)
            agent_loads.append((agent_id, load_info.get("load_percentage", 100)))

        # Sort by load (ascending) and take top agents
        agent_loads.sort(key=lambda x: x[1])
        return [agent for agent, _ in agent_loads[:max_assignments]]

    async def _send_message(self, message: AgentMessage) -> bool:
        """Send message to specific agent"""
        try:
            # Store in appropriate memory wrapper based on recipient category
            recipient_info = self.agent_registry.get(message.to_agent, {})
            recipient_category = recipient_info.get("category", MemoryCategory.SMC)

            message_data = {
                "message_id": message.message_id,
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "type": message.message_type.value,
                "subject": message.subject,
                "content": message.content,
                "priority": message.priority.value,
                "requires_response": message.requires_response
            }

            if recipient_category == MemoryCategory.ATS:
                await self.ats_wrapper.store_execution_result(
                    agent_id=message.to_agent,
                    execution={
                        "execution_id": message.message_id,
                        "type": "message_received",
                        "status": "pending_response" if message.requires_response else "delivered",
                        "message_data": message_data
                    }
                )
            elif recipient_category == MemoryCategory.OMA:
                await self.oma_wrapper.store_analysis_report(
                    agent_id=message.to_agent,
                    report={
                        "type": "message_received",
                        "title": message.subject,
                        "content": message_data,
                        "severity": "info"
                    }
                )
            else:  # SMC
                await self.smc_wrapper.store_message(
                    agent_id=message.to_agent,
                    message_data=message_data
                )

            # Add to message queue for processing
            self.message_queue.append(message)

            logger.debug(f"Message {message.message_id} sent to {message.to_agent}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message {message.message_id}: {e}")
            return False

    async def _store_coordination_task(self, task: AgentTask):
        """Store coordination task in memory"""
        await self.smc_wrapper.store_task(
            agent_id="coordinator",
            task_data={
                "task_id": task.task_id,
                "type": "coordination_task",
                "title": task.title,
                "description": task.description,
                "assigned_to": task.assigned_to,
                "created_by": task.created_by,
                "priority": task.priority.value,
                "status": task.status,
                "metadata": task.metadata
            }
        )

    async def _store_coordination_message(self, message: AgentMessage):
        """Store coordination message in memory"""
        await self.smc_wrapper.store_message(
            agent_id="coordinator",
            message_data={
                "message_id": message.message_id,
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "type": message.message_type.value,
                "subject": message.subject,
                "content": message.content,
                "priority": message.priority.value,
                "requires_response": message.requires_response
            }
        )

    async def _get_recent_message_activity(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent message activity from memory"""
        try:
            # This would query the message history from memory
            # For now, return message queue activity
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

            recent_messages = [
                {
                    "message_id": msg.message_id,
                    "from_agent": msg.from_agent,
                    "to_agent": msg.to_agent,
                    "type": msg.message_type.value,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in self.message_queue
                if msg.created_at >= cutoff_time
            ]

            return recent_messages

        except Exception as e:
            logger.error(f"Failed to get recent message activity: {e}")
            return []

    def _get_most_active_agents(self, messages: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Get most active agents from message activity"""
        agent_activity = {}

        for message in messages:
            agent = message.get("from_agent")
            if agent:
                agent_activity[agent] = agent_activity.get(agent, 0) + 1

            agent = message.get("to_agent")
            if agent and agent != "all":
                agent_activity[agent] = agent_activity.get(agent, 0) + 1

        # Sort and return top agents
        sorted_agents = sorted(agent_activity.items(), key=lambda x: x[1], reverse=True)
        return [{"agent": agent, "message_count": count} for agent, count in sorted_agents[:limit]]

    async def _broadcast_message(self, message: AgentMessage) -> bool:
        """Broadcast message to multiple agents"""
        # Implementation for broadcasting to specific agent groups
        pass

    async def _broadcast_to_all(self, message: AgentMessage) -> bool:
        """Broadcast message to all agents"""
        success_count = 0
        total_agents = len(self.agent_registry)

        for agent_id in self.agent_registry.keys():
            broadcast_message = AgentMessage(
                message_id=str(uuid.uuid4()),
                from_agent=message.from_agent,
                to_agent=agent_id,
                message_type=message.message_type,
                subject=message.subject,
                content=message.content,
                priority=message.priority
            )

            if await self._send_direct_message(broadcast_message):
                success_count += 1

        return success_count == total_agents

    async def _send_direct_message(self, message: AgentMessage) -> bool:
        """Send direct message to specific agent"""
        return await self._send_message(message)

# Example usage and coordination scenarios
async def example_coordination_scenarios():
    """Example usage of the Sub-Agent Coordinator"""
    # Initialize integration
    integration = AgentMemoryIntegration()
    await integration.initialize()

    # Create coordinator
    coordinator = SubAgentCoordinator(integration)

    # Example 1: Assign trading analysis task
    trading_task = AgentTask(
        task_id="task_001",
        title="Analyze AAPL market volatility",
        description="Perform comprehensive volatility analysis for AAPL stock",
        assigned_to=[],
        created_by="trading_manager",
        priority=TaskPriority.HIGH,
        deadline=datetime.now(UTC) + timedelta(hours=2)
    )

    success = await coordinator.assign_task(trading_task)
    print(f"Trading task assignment: {success}")

    # Example 2: Register agent capability
    capability = AgentCapability(
        agent_id="market-analyzer",
        capability_name="volatility_analysis",
        description="Advanced volatility analysis using multiple models",
        input_types=["market_data", "price_history"],
        output_types=["volatility_metrics", "risk_assessment"],
        max_concurrent_tasks=3,
        avg_processing_time=45.0,
        success_rate=0.95
    )

    await coordinator.register_agent_capability(capability)

    # Example 3: Send inter-agent message
    message = AgentMessage(
        message_id="msg_001",
        from_agent="algorithmic-trading-system",
        to_agent="risk-management",
        message_type=MessageType.REQUEST,
        subject="Risk assessment for new position",
        content={
            "symbol": "AAPL",
            "quantity": 1000,
            "strategy": "momentum",
            "requested_analysis": ["var", "stress_test", "scenario_analysis"]
        },
        priority=TaskPriority.HIGH,
        requires_response=True
    )

    message_sent = await coordinator.route_message(message)
    print(f"Message sent: {message_sent}")

    # Example 4: Get coordination overview
    overview = await coordinator.get_coordination_overview()
    print(f"Coordination overview: {overview}")

    await integration.close()

if __name__ == "__main__":
    asyncio.run(example_coordination_scenarios())