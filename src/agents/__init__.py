"""
RNR Enhanced Cognee Agents System
Dynamic agent registry - categories loaded from configuration.
Legacy ATS/OMA/SMC agent modules were archived in Phase 4.
"""
import logging
from ..agent_memory_integration import AgentMemoryIntegration

logger = logging.getLogger(__name__)

# Legacy agent modules are archived - graceful fallback
try:
    from . import ats as _ats_mod
    ATS_AGENTS = _ats_mod.ATS_AGENTS
except ImportError:
    ATS_AGENTS = {}

try:
    from . import oma as _oma_mod
    OMA_AGENTS = _oma_mod.OMA_AGENTS
except ImportError:
    OMA_AGENTS = {}

try:
    from . import smc as _smc_mod
    SMC_AGENTS = _smc_mod.SMC_AGENTS
except ImportError:
    SMC_AGENTS = {}

__all__ = [
    "AgentRegistry",
    "create_agent",
    "ALL_AGENTS",
]

# Merged agent registry (empty if all legacy modules are archived)
ALL_AGENTS = {**ATS_AGENTS, **OMA_AGENTS, **SMC_AGENTS}


class AgentRegistry:
    """
    Central registry for managing agents dynamically.
    Categories and agent configs are loaded from .enhanced-cognee-config.json.
    """

    def __init__(self, memory_integration: AgentMemoryIntegration):
        self.memory_integration = memory_integration
        self.agent_instances = {}
        # Factory functions loaded dynamically - no hardcoded categories
        self.category_factories = {}
        # Populate factories from available legacy modules
        try:
            from . import ats as _ats
            self.category_factories["trading"] = _ats.create_ats_agent
        except (ImportError, AttributeError):
            pass

    async def initialize_critical_agents(self):
        """Initialize all critical agents from the registry."""
        critical_agents = [
            agent_id for agent_id, info in ALL_AGENTS.items()
            if info.get("critical", False)
        ]
        initialized = []
        for agent_id in critical_agents:
            try:
                agent = await self.create_agent(agent_id)
                if agent:
                    self.agent_instances[agent_id] = agent
                    initialized.append(agent_id)
            except Exception as exc:
                logger.warning(f"Failed to initialize agent {agent_id}: {exc}")
        return initialized

    async def create_agent(self, agent_id: str):
        """Create an agent instance by ID."""
        agent_info = ALL_AGENTS.get(agent_id)
        if not agent_info:
            logger.error(f"Unknown agent: {agent_id}")
            return None
        category = agent_info.get("category", "general")
        factory = self.category_factories.get(category)
        if not factory:
            logger.warning(f"No factory registered for category '{category}', agent: {agent_id}")
            return None
        try:
            return await factory(agent_id=agent_id, memory_integration=self.memory_integration)
        except Exception as exc:
            logger.error(f"Failed to create agent {agent_id}: {exc}")
            return None

    def get_all_agents(self):
        """Return all registered agents."""
        return ALL_AGENTS.copy()

    def get_agent_info(self, agent_id: str):
        """Return info dict for a specific agent."""
        return ALL_AGENTS.get(agent_id)


async def create_agent(agent_id: str, memory_integration: AgentMemoryIntegration):
    """Convenience function to create a single agent."""
    registry = AgentRegistry(memory_integration)
    return await registry.create_agent(agent_id)
