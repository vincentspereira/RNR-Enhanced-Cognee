#!/usr/bin/python3
"""
SMC (Shared Multi-Agent Components) Memory Wrapper
Specialized memory interface for shared and coordination agents
Integrates with Enhanced Cognee stack
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, UTC
from ...agent_memory_integration import (
    AgentMemoryIntegration, MemoryCategory, MemoryType, MemoryEntry,
    MemorySearchResult
)

logger = logging.getLogger(__name__)

class SMCMemoryWrapper:
    """Specialized memory wrapper for SMC category agents"""

    def __init__(self, integration: AgentMemoryIntegration):
        self.integration = integration
        self.smc_agents = [
            "context-manager",
            "knowledge-graph",
            "message-broker",
            "task-scheduler",
            "data-processor",
            "api-gateway"
        ]

    async def store_context(self, agent_id: str, context_data: Dict[str, Any],
                           ttl_hours: int = 1, metadata: Dict[str, Any] = None) -> str:
        """Store agent context with TTL"""
        content = self._format_context(context_data)

        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

        enhanced_metadata = {
            **(metadata or {}),
            "context_type": context_data.get("type"),
            "session_id": context_data.get("session_id"),
            "user_id": context_data.get("user_id"),
            "priority": context_data.get("priority", "normal"),
            "ttl_hours": ttl_hours
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.WORKING,
            metadata=enhanced_metadata,
            tags=["context", "working_memory", "session"],
            expires_at=expires_at
        )

    async def store_knowledge(self, agent_id: str, knowledge_data: Dict[str, Any],
                              confidence: float = 1.0, metadata: Dict[str, Any] = None) -> str:
        """Store knowledge graph information"""
        content = self._format_knowledge(knowledge_data)

        enhanced_metadata = {
            **(metadata or {}),
            "knowledge_type": knowledge_data.get("type"),
            "domain": knowledge_data.get("domain"),
            "entities": knowledge_data.get("entities", []),
            "relationships": knowledge_data.get("relationships", []),
            "confidence": confidence,
            "source_agents": knowledge_data.get("source_agents", [])
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            metadata=enhanced_metadata,
            tags=["knowledge", "graph", "semantic"]
        )

    async def store_message(self, agent_id: str, message_data: Dict[str, Any],
                            metadata: Dict[str, Any] = None) -> str:
        """Store inter-agent communication message"""
        content = self._format_message(message_data)

        enhanced_metadata = {
            **(metadata or {}),
            "message_type": message_data.get("type"),
            "from_agent": message_data.get("from_agent"),
            "to_agent": message_data.get("to_agent"),
            "message_id": message_data.get("message_id"),
            "priority": message_data.get("priority", "normal"),
            "encrypted": message_data.get("encrypted", False)
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.EPISODIC,
            metadata=enhanced_metadata,
            tags=["message", "communication", "inter_agent"]
        )

    async def store_task(self, agent_id: str, task_data: Dict[str, Any],
                        metadata: Dict[str, Any] = None) -> str:
        """Store task scheduling and execution information"""
        content = self._format_task(task_data)

        enhanced_metadata = {
            **(metadata or {}),
            "task_type": task_data.get("type"),
            "task_id": task_data.get("task_id"),
            "priority": task_data.get("priority", "normal"),
            "status": task_data.get("status"),
            "assigned_to": task_data.get("assigned_to"),
            "dependencies": task_data.get("dependencies", []),
            "estimated_duration": task_data.get("estimated_duration")
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.PROCEDURAL,
            metadata=enhanced_metadata,
            tags=["task", "scheduling", "execution"]
        )

    async def store_data_processing(self, agent_id: str, processing_data: Dict[str, Any],
                                     metadata: Dict[str, Any] = None) -> str:
        """Store data processing pipeline information"""
        content = self._format_data_processing(processing_data)

        enhanced_metadata = {
            **(metadata or {}),
            "pipeline_id": processing_data.get("pipeline_id"),
            "processing_type": processing_data.get("type"),
            "stage": processing_data.get("stage"),
            "input_format": processing_data.get("input_format"),
            "output_format": processing_data.get("output_format"),
            "records_processed": processing_data.get("records_processed", 0),
            "processing_time": processing_data.get("processing_time")
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.EPISODIC,
            metadata=enhanced_metadata,
            tags=["data_processing", "pipeline", "etl"]
        )

    async def store_api_event(self, agent_id: str, api_data: Dict[str, Any],
                             metadata: Dict[str, Any] = None) -> str:
        """Store API gateway event"""
        content = self._format_api_event(api_data)

        enhanced_metadata = {
            **(metadata or {}),
            "api_method": api_data.get("method"),
            "api_endpoint": api_data.get("endpoint"),
            "status_code": api_data.get("status_code"),
            "response_time": api_data.get("response_time"),
            "user_agent": api_data.get("user_agent"),
            "ip_address": api_data.get("ip_address"),
            "rate_limit_applied": api_data.get("rate_limit_applied", False)
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.EPISODIC,
            metadata=enhanced_metadata,
            tags=["api", "gateway", "event"]
        )

    async def get_context(self, agent_id: str, session_id: str = None,
                        user_id: str = None) -> List[MemorySearchResult]:
        """Retrieve current context for agent"""
        query_parts = ["context"]
        if session_id:
            query_parts.append(session_id)
        if user_id:
            query_parts.append(user_id)

        return await self.integration.search_memory(
            agent_id=agent_id,
            query=" ".join(query_parts),
            memory_type=MemoryType.WORKING,
            category=MemoryCategory.SMC,
            limit=20
        )

    async def get_knowledge(self, agent_id: str = None, domain: str = None,
                           entity: str = None, limit: int = 50) -> List[MemorySearchResult]:
        """Retrieve knowledge from knowledge graph"""
        query_parts = ["knowledge"]
        if domain:
            query_parts.append(domain)
        if entity:
            query_parts.append(entity)

        return await self.integration.search_memory(
            agent_id=agent_id,
            query=" ".join(query_parts),
            memory_type=MemoryType.SEMANTIC,
            category=MemoryCategory.SMC,
            limit=limit
        )

    async def get_message_history(self, agent_id: str = None, time_range_hours: int = 24,
                                   limit: int = 100) -> Dict[str, Any]:
        """Get message history for communication analysis"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=time_range_hours)

        all_messages = await self.integration.search_memory(
            agent_id=agent_id,
            query="message communication",
            memory_type=MemoryType.EPISODIC,
            category=MemoryCategory.SMC,
            limit=limit
        )

        # Filter by time range
        recent_messages = [
            msg for msg in all_messages if msg.created_at >= cutoff_time
        ]

        # Analyze communication patterns
        message_stats = {
            "total_messages": len(recent_messages),
            "time_range_hours": time_range_hours,
            "agent_messages": {},
            "communication_matrix": {},
            "busiest_hour": None,
            "busiest_count": 0
        }

        hourly_counts = {}
        for msg in recent_messages:
            # Agent-specific stats
            agent = msg.agent_id
            if agent not in message_stats["agent_messages"]:
                message_stats["agent_messages"][agent] = 0
            message_stats["agent_messages"][agent] += 1

            # Communication matrix
            if "from_agent" in msg.metadata:
                from_agent = msg.metadata["from_agent"]
                if from_agent not in message_stats["communication_matrix"]:
                    message_stats["communication_matrix"][from_agent] = {}
                if agent not in message_stats["communication_matrix"][from_agent]:
                    message_stats["communication_matrix"][from_agent][agent] = 0
                message_stats["communication_matrix"][from_agent][agent] += 1

            # Hourly activity
            hour = msg.created_at.hour
            if hour not in hourly_counts:
                hourly_counts[hour] = 0
            hourly_counts[hour] += 1

        # Find busiest hour
        if hourly_counts:
            busiest_hour = max(hourly_counts.items(), key=lambda x: x[1])
            message_stats["busiest_hour"] = busiest_hour[0]
            message_stats["busiest_count"] = busiest_hour[1]

        message_stats["hourly_distribution"] = hourly_counts

        return message_stats

    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status for SMC components"""
        status = {
            "timestamp": datetime.now(UTC).isoformat(),
            "agents": {},
            "summary": {}
        }

        total_memories = 0

        for agent_id in self.smc_agents:
            try:
                # Get agent memory stats
                stats = await self.integration.get_agent_memory_stats(agent_id)
                status["agents"][agent_id] = {
                    "status": "active" if stats else "inactive",
                    "memory_stats": stats.get("memory_stats", {})
                }

                # Count memories
                if "postgresql" in stats.get("memory_stats", {}):
                    total_memories += stats["memory_stats"]["postgresql"].get("total_memories", 0)

            except Exception as e:
                logger.error(f"Failed to get status for {agent_id}: {e}")
                status["agents"][agent_id] = {"status": "error", "error": str(e)}

        status["summary"] = {
            "total_agents": len(self.smc_agents),
            "active_agents": len([a for a in status["agents"].values() if a.get("status") == "active"]),
            "total_memories": total_memories,
            "memory_integration": "operational" if self.integration else "inactive"
        }

        return status

    async def analyze_cross_agent_communication(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Analyze communication patterns across agents"""
        message_stats = await self.get_message_history(time_range_hours=time_range_hours)

        # Identify communication patterns
        patterns = {
            "highly_connected_pairs": [],
            "isolated_agents": [],
            "communication_frequency": {},
            "message_volume": {}
        }

        # Communication matrix analysis
        matrix = message_stats["communication_matrix"]
        agent_list = list(matrix.keys())

        # Find highly connected agent pairs
        for from_agent in agent_list:
            for to_agent in agent_list:
                if from_agent != to_agent and matrix.get(from_agent, {}).get(to_agent, 0) > 10:
                    patterns["highly_connected_pairs"].append((from_agent, to_agent, matrix[from_agent][to_agent]))

        # Find isolated agents
        for agent in agent_list:
            incoming = sum(matrix.get(other, {}).get(agent, 0) for other in agent_list)
            outgoing = sum(matrix.get(agent, {}).values())
            total_communication = incoming + outgoing

            if total_communication < 5:  # Threshold for isolation
                patterns["isolated_agents"].append({
                    "agent": agent,
                    "total_messages": total_communication,
                    "incoming": incoming,
                    "outgoing": outgoing
                })

        return {
            "time_range_hours": time_range_hours,
            "patterns": patterns,
            "message_stats": message_stats
        }

    def _format_context(self, context_data: Dict[str, Any]) -> str:
        """Format context data for storage"""
        return f"Context session {context_data.get('session_id', 'Unknown')} " \
               f"for user {context_data.get('user_id', 'Unknown')}:\n" \
               f"Type: {context_data.get('type', 'General context')}\n" \
               f"Priority: {context_data.get('priority', 'normal')}\n" \
               f"Data: {context_data.get('data', 'No data provided')}\n" \
               f"Metadata: {json.dumps(context_data.get('metadata', {}), indent=2)}"

    def _format_knowledge(self, knowledge_data: Dict[str, Any]) -> str:
        """Format knowledge data for storage"""
        return f"Knowledge entry in domain {knowledge_data.get('domain', 'Unknown')}:\n" \
               f"Type: {knowledge_data.get('type', 'General knowledge')}\n" \
               f"Entities: {', '.join(knowledge_data.get('entities', []))}\n" \
               f"Relationships: {', '.join([f'{r[0]}-{r[1]} ({r[2]})' for r in knowledge_data.get('relationships', [])])}\n" \
               f"Confidence: {knowledge_data.get('confidence', 1.0)}\n" \
               f"Content: {knowledge_data.get('content', 'No content')}"

    def _format_message(self, message_data: Dict[str, Any]) -> str:
        """Format inter-agent message for storage"""
        return f"Message from {message_data.get('from_agent', 'Unknown')} " \
               f"to {message_data.get('to_agent', 'Unknown')}\n" \
               f"Type: {message_data.get('type', 'General message')}\n" \
               f"Priority: {message_data.get('priority', 'normal')}\n" \
               f"Content: {message_data.get('content', 'No content')}\n" \
               f"Message ID: {message_data.get('message_id', 'Unknown')}"

    def _format_task(self, task_data: Dict[str, Any]) -> str:
        """Format task information for storage"""
        return f"Task {task_data.get('task_id', 'Unknown')}:\n" \
               f"Type: {task_data.get('type', 'General task')}\n" \
               f"Status: {task_data.get('status', 'Unknown')}\n" \
               f"Priority: {task_data.get('priority', 'normal')}\n" \
               f"Assigned to: {task_data.get('assigned_to', 'Unassigned')}\n" \
               f"Dependencies: {', '.join(task_data.get('dependencies', []))}\n" \
               f"Description: {task_data.get('description', 'No description')}"

    def _format_data_processing(self, processing_data: Dict[str, Any]) -> str:
        """Format data processing information for storage"""
        return f"Data processing pipeline {processing_data.get('pipeline_id', 'Unknown')}:\n" \
               f"Type: {processing_data.get('type', 'Unknown processing')}\n" \
               f"Stage: {processing_data.get('stage', 'Unknown stage')}\n" \
               f"Records processed: {processing_data.get('records_processed', 0)}\n" \
               f"Processing time: {processing_data.get('processing_time', 'Unknown')}ms\n" \
               f"Input format: {processing_data.get('input_format', 'Unknown')}\n" \
               f"Output format: {processing_data.get('output_format', 'Unknown')}"

    def _format_api_event(self, api_data: Dict[str, Any]) -> str:
        """Format API event for storage"""
        return f"API event for endpoint {api_data.get('endpoint', 'Unknown')}:\n" \
               f"Method: {api_data.get('method', 'Unknown')}\n" \
               f"Status Code: {api_data.get('status_code', 'Unknown')}\n" \
               f"Response Time: {api_data.get('response_time', 'Unknown')}ms\n" \
               f"Rate Limited: {api_data.get('rate_limit_applied', False)}\n" \
               f"IP Address: {api_data.get('ip_address', 'Unknown')}\n" \
               f"User Agent: {api_data.get('user_agent', 'Unknown')}"

# Usage example
async def example_usage():
    """Example usage of SMC Memory Wrapper"""
    # Initialize integration
    integration = AgentMemoryIntegration()
    await integration.initialize()

    # Create SMC wrapper
    smc_wrapper = SMCMemoryWrapper(integration)

    # Example: Store context
    context_data = {
        "session_id": "session_123",
        "user_id": "user_456",
        "type": "trading_session",
        "priority": "high",
        "data": {
            "active_symbols": ["AAPL", "GOOGL"],
            "position_size": 10000,
            "risk_tolerance": 0.02
        },
        "metadata": {"session_start": datetime.now(UTC).isoformat()}
    }

    memory_id = await smc_wrapper.store_context(
        agent_id="context-manager",
        context_data=context_data,
        ttl_hours=2
    )

    print(f"Stored context with ID: {memory_id}")

    # Store inter-agent message
    message_data = {
        "from_agent": "algorithmic-trading-system",
        "to_agent": "risk-management",
        "type": "alert",
        "message_id": "msg_789",
        "priority": "high",
        "content": "High volatility detected in AAPL stock price",
        "encrypted": False
    }

    await smc_wrapper.store_message(
        agent_id="message-broker",
        message_data=message_data
    )

    # Get cross-agent communication analysis
    communication_analysis = await smc_wrapper.analyze_cross_agent_communication(time_range_hours=1)
    print(f"Communication analysis: {communication_analysis}")

    # Get system status
    system_status = await smc_wrapper.get_system_status()
    print(f"System status: {system_status}")

    await integration.close()

if __name__ == "__main__":
    asyncio.run(example_usage())