"""
Enhanced Cognee Coordination System
Comprehensive coordination layer for sub-agents with dynamic category configuration.
"""

from .sub_agent_coordinator import SubAgentCoordinator
from .task_orchestration import TaskOrchestrationEngine
from .distributed_decision import DistributedDecisionMaker
from .coordination_api import app

__version__ = "1.0.0"
__author__ = "Enhanced Cognee Team"

# Coordination system components
__all__ = [
    "SubAgentCoordinator",
    "TaskOrchestrationEngine",
    "DistributedDecisionMaker",
    "app"
]

# System metadata
COORDINATION_SYSTEM_INFO = {
    "name": "Enhanced Cognee Coordination System",
    "version": __version__,
    "description": "Comprehensive coordination layer for multi-agent system",
    "components": {
        "coordinator": "Manages sub-agents with dynamic category configuration",
        "orchestrator": "Handles complex workflows and task dependencies",
        "decision_maker": "Enables distributed decision-making with consensus mechanisms",
        "api": "RESTful interface for external system integration"
    },
    "categories": "dynamic (loaded from .enhanced-cognee-config.json)",
    "total_agents": "dynamic (loaded from configuration)"
}

async def initialize_coordination_system(memory_integration):
    """
    Initialize the complete coordination system

    Args:
        memory_integration: AgentMemoryIntegration instance

    Returns:
        Dict containing all coordination components
    """
    from .sub_agent_coordinator import SubAgentCoordinator
    from .task_orchestration import TaskOrchestrationEngine
    from .distributed_decision import DistributedDecisionMaker

    # Initialize coordinator first
    coordinator = SubAgentCoordinator(memory_integration)

    # Initialize orchestrator with coordinator
    orchestrator = TaskOrchestrationEngine(coordinator)

    # Initialize decision maker with coordinator
    decision_maker = DistributedDecisionMaker(coordinator)

    # Warm up the coordination system
    await _warm_up_coordination_system(coordinator, orchestrator, decision_maker)

    return {
        "coordinator": coordinator,
        "orchestrator": orchestrator,
        "decision_maker": decision_maker
    }

async def _warm_up_coordination_system(coordinator, orchestrator, decision_maker):
    """
    Warm up coordination system with default configurations
    """
    try:
        # Initialize agent capabilities (can be expanded)
        await _register_default_capabilities(coordinator)

        # Load coordination settings from memory if available
        await _load_coordination_settings(coordinator)

        print("Coordination system warmed up successfully")

    except Exception as e:
        print(f"Warning: Coordination system warm-up failed: {e}")

async def _register_default_capabilities(coordinator):
    """Register default capabilities for all agents"""
    from .sub_agent_coordinator import AgentCapability

    # Register some default capabilities for critical agents
    default_capabilities = [
        AgentCapability(
            agent_id="context-manager",
            capability_name="context_sharing",
            description="Share context across multiple agents",
            input_types=["session_data", "user_context"],
            output_types=["shared_context", "session_state"],
            max_concurrent_tasks=8
        ),
        AgentCapability(
            agent_id="task-scheduler",
            capability_name="task_scheduling",
            description="Schedule and distribute tasks across agents",
            input_types=["task_request", "agent_load"],
            output_types=["task_assignment", "schedule_plan"],
            max_concurrent_tasks=6
        ),
        AgentCapability(
            agent_id="message-broker",
            capability_name="message_routing",
            description="Route messages between agents efficiently",
            input_types=["message", "routing_rules"],
            output_types=["delivered_message", "routing_log"],
            max_concurrent_tasks=10
        )
    ]

    for capability in default_capabilities:
        try:
            await coordinator.register_agent_capability(capability)
        except Exception as e:
            print(f"Warning: Failed to register capability {capability.capability_name}: {e}")

async def _load_coordination_settings(coordinator):
    """Load coordination settings from memory storage"""
    try:
        # This would load previously saved coordination settings
        # For now, use default settings
        pass
    except Exception as e:  # pragma: no cover
        print(f"Warning: Failed to load coordination settings: {e}")

def get_coordination_system_info():
    """Get comprehensive information about the coordination system"""
    return COORDINATION_SYSTEM_INFO