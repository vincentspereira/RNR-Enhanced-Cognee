"""Algorithmic Trading System (ATS) agents."""
from .algorithmic_trading_system import AlgorithmicTradingSystem
from .risk_management import RiskManagement

__all__ = ["AlgorithmicTradingSystem", "RiskManagement", "ATS_AGENTS", "create_ats_agent"]

# Agent registry entry so src/agents/__init__.py can discover this module
ATS_AGENTS: dict = {
    "algorithmic-trading-system": {
        "class": "AlgorithmicTradingSystem",
        "module": "src.agents.ats.algorithmic_trading_system",
        "category": "trading",
        "critical": False,
    },
    "risk-management": {
        "class": "RiskManagement",
        "module": "src.agents.ats.risk_management",
        "category": "trading",
        "critical": False,
    },
}


async def create_ats_agent(agent_id: str, memory_integration) -> object:
    """Factory function used by AgentRegistry."""
    _CLASS_MAP = {
        "algorithmic-trading-system": AlgorithmicTradingSystem,
        "risk-management": RiskManagement,
    }
    cls = _CLASS_MAP.get(agent_id)
    if cls is None:
        raise ValueError(f"Unknown ATS agent: {agent_id}")
    return cls(memory_integration)
