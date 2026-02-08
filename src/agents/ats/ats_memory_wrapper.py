#!/usr/bin/env python3
"""
ATS (Algorithmic Trading System) Memory Wrapper
Specialized memory interface for trading system agents
Integrates with Enhanced Cognee stack
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, UTC
from ...agent_memory_integration import (
    AgentMemoryIntegration, MemoryCategory, MemoryType, MemoryEntry,
    MemorySearchResult
)

logger = logging.getLogger(__name__)

class ATSMemoryWrapper:
    """Specialized memory wrapper for ATS category agents"""

    def __init__(self, integration: AgentMemoryIntegration):
        self.integration = integration
        self.ats_agents = [
            "algorithmic-trading-system",
            "risk-management",
            "portfolio-optimizer",
            "market-analyzer",
            "execution-engine",
            "signal-processor",
            "compliance-monitor"
        ]

    async def store_market_data(self, agent_id: str, market_data: Dict[str, Any],
                                metadata: Dict[str, Any] = None) -> str:
        """Store market data with specialized metadata"""
        content = self._format_market_data(market_data)

        enhanced_metadata = {
            **(metadata or {}),
            "data_type": "market_data",
            "timestamp": market_data.get("timestamp"),
            "symbols": market_data.get("symbols", []),
            "data_sources": market_data.get("sources", []),
            "priority": market_data.get("priority", "normal")
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.FACTUAL,
            metadata=enhanced_metadata,
            tags=["market_data", "trading", "real_time"]
        )

    async def store_trading_signal(self, agent_id: str, signal: Dict[str, Any],
                                    confidence: float = 1.0, metadata: Dict[str, Any] = None) -> str:
        """Store trading signal with confidence scoring"""
        content = self._format_trading_signal(signal)

        enhanced_metadata = {
            **(metadata or {}),
            "signal_type": signal.get("type"),
            "symbol": signal.get("symbol"),
            "direction": signal.get("direction"),
            "strength": signal.get("strength"),
            "timeframe": signal.get("timeframe"),
            "confidence": confidence
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.FACTUAL,
            metadata=enhanced_metadata,
            tags=["signal", "trading", "recommendation"]
        )

    async def store_risk_assessment(self, agent_id: str, risk_data: Dict[str, Any],
                                   metadata: Dict[str, Any] = None) -> str:
        """Store risk assessment with risk metrics"""
        content = self._format_risk_assessment(risk_data)

        enhanced_metadata = {
            **(metadata or {}),
            "risk_level": risk_data.get("risk_level"),
            "risk_score": risk_data.get("risk_score"),
            "portfolio_id": risk_data.get("portfolio_id"),
            "risk_factors": risk_data.get("factors", []),
            "mitigation_required": risk_data.get("mitigation_required", False)
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.PROCEDURAL,
            metadata=enhanced_metadata,
            tags=["risk", "assessment", "compliance"]
        )

    async def store_execution_result(self, agent_id: str, execution: Dict[str, Any],
                                    metadata: Dict[str, Any] = None) -> str:
        """Store trade execution result"""
        content = self._format_execution_result(execution)

        enhanced_metadata = {
            **(metadata or {}),
            "execution_id": execution.get("execution_id"),
            "order_id": execution.get("order_id"),
            "symbol": execution.get("symbol"),
            "quantity": execution.get("quantity"),
            "price": execution.get("price"),
            "status": execution.get("status"),
            "slippage": execution.get("slippage"),
            "execution_time": execution.get("execution_time")
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.EPISODIC,
            metadata=enhanced_metadata,
            tags=["execution", "trade", "result"]
        )

    async def store_compliance_event(self, agent_id: str, compliance_event: Dict[str, Any],
                                     metadata: Dict[str, Any] = None) -> str:
        """Store compliance monitoring event"""
        content = self._format_compliance_event(compliance_event)

        enhanced_metadata = {
            **(metadata or {}),
            "event_type": compliance_event.get("event_type"),
            "severity": compliance_event.get("severity"),
            "regulation": compliance_event.get("regulation"),
            "auto_resolved": compliance_event.get("auto_resolved", False),
            "action_required": compliance_event.get("action_required", False)
        }

        return await self.integration.add_memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType.FACTUAL,
            metadata=enhanced_metadata,
            tags=["compliance", "regulation", "monitoring"]
        )

    async def search_market_data(self, agent_id: str, symbol: str = None,
                                 timeframe: str = None, limit: int = 50) -> List[MemorySearchResult]:
        """Search for historical market data"""
        query = symbol or ""
        if timeframe:
            query += f" {timeframe}"

        return await self.integration.search_memory(
            agent_id=agent_id,
            query=query,
            memory_type=MemoryType.FACTUAL,
            category=MemoryCategory.ATS,
            limit=limit
        )

    async def search_trading_signals(self, agent_id: str, symbol: str = None,
                                    direction: str = None, min_confidence: float = 0.5,
                                    hours_back: int = 24) -> List[MemorySearchResult]:
        """Search for recent trading signals"""
        # This would need to be implemented with time-based filtering
        results = await self.integration.search_memory(
            agent_id=agent_id,
            query=f"{symbol or ''} {direction or ''}".strip(),
            memory_type=MemoryType.FACTUAL,
            category=MemoryCategory.ATS,
            limit=100
        )

        # Filter by confidence and recent time (simplified)
        filtered_results = []
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours_back)

        for result in results:
            # Check metadata for confidence and timestamp
            if (result.metadata.get("confidence", 1.0) >= min_confidence and
                result.created_at >= cutoff_time):
                filtered_results.append(result)

        return filtered_results[:50]

    async def get_agent_performance_summary(self, agent_id: str, days_back: int = 7) -> Dict[str, Any]:
        """Get performance summary for ATS agent"""
        try:
            # Get memory statistics
            stats = await self.integration.get_agent_memory_stats(agent_id)

            # Get recent memories for analysis
            recent_memories = await self.integration.search_memory(
                agent_id=agent_id,
                limit=1000
            )

            # Analyze memories by type
            memory_types = {}
            signal_count = 0
            execution_count = 0
            risk_count = 0

            for memory in recent_memories:
                if "signal" in memory.tags:
                    signal_count += 1
                elif "execution" in memory.tags:
                    execution_count += 1
                elif "risk" in memory.tags:
                    risk_count += 1

            return {
                "agent_id": agent_id,
                "period_days": days_back,
                "total_memories": len(recent_memories),
                "memory_stats": stats,
                "recent_activity": {
                    "signals_generated": signal_count,
                    "trades_executed": execution_count,
                    "risk_assessments": risk_count
                }
            }
        except Exception as e:
            logger.error(f"Failed to get performance summary for {agent_id}: {e}")
            return {"error": str(e)}

    async def get_cross_agent_insights(self, symbol: str = None) -> Dict[str, Any]:
        """Get insights across all ATS agents for a symbol"""
        insights = {
            "symbol": symbol,
            "analysis": {},
            "timeline": []
        }

        for agent_id in self.ats_agents:
            try:
                # Search for recent activity related to symbol
                memories = await self.search_market_data(agent_id, symbol)

                # Also search for signals and executions
                signals = await self.search_trading_signals(agent_id, symbol)
                executions = [m for m in memories if "execution" in m.tags]

                insights["analysis"][agent_id] = {
                    "total_memories": len(memories),
                    "signals": len(signals),
                    "executions": len(executions),
                    "last_activity": max([m.created_at for m in memories + signals + executions],
                                     default=None).isoformat() if (memories + signals + executions) else None
                }

                # Add to timeline
                for memory in memories + signals + executions[:5]:  # Limit timeline entries
                    insights["timeline"].append({
                        "agent_id": agent_id,
                        "content": memory.content[:100] + "..." if len(memory.content) > 100 else memory.content,
                        "type": list(set(memory.tags))[0] if memory.tags else "general",
                        "created_at": memory.created_at.isoformat()
                    })

            except Exception as e:
                logger.error(f"Failed to analyze {agent_id} for symbol {symbol}: {e}")
                insights["analysis"][agent_id] = {"error": str(e)}

        # Sort timeline by most recent
        insights["timeline"].sort(key=lambda x: x["created_at"], reverse=True)
        insights["timeline"] = insights["timeline"][:20]  # Limit to 20 timeline entries

        return insights

    def _format_market_data(self, market_data: Dict[str, Any]) -> str:
        """Format market data for storage"""
        return f"Market data update: {market_data.get('symbols', 'Unknown symbols')} " \
               f"at {market_data.get('timestamp', datetime.now(UTC).isoformat())}. " \
               f"Price: {market_data.get('price', 'N/A')}, " \
               f"Volume: {market_data.get('volume', 'N/A')}, " \
               f"Change: {market_data.get('change', 'N/A')}"

    def _format_trading_signal(self, signal: Dict[str, Any]) -> str:
        """Format trading signal for storage"""
        return f"Trading signal for {signal.get('symbol', 'Unknown')}: " \
               f"{signal.get('direction', 'Unknown')} with strength {signal.get('strength', 'N/A')}. " \
               f"Timeframe: {signal.get('timeframe', 'N/A')}, " \
               f"Reasoning: {signal.get('reasoning', 'No reasoning provided')}"

    def _format_risk_assessment(self, risk_data: Dict[str, Any]) -> str:
        """Format risk assessment for storage"""
        return f"Risk assessment: Risk level {risk_data.get('risk_level', 'Unknown')} " \
               f"with score {risk_data.get('risk_score', 'N/A')}. " \
               f"Portfolio: {risk_data.get('portfolio_id', 'N/A')}. " \
               f"Factors: {', '.join(risk_data.get('factors', []))}"

    def _format_execution_result(self, execution: Dict[str, Any]) -> str:
        """Format execution result for storage"""
        return f"Trade execution {execution.get('status', 'Unknown')}: " \
               f"{execution.get('symbol', 'N/A')} {execution.get('quantity', 'N/A')} shares " \
               f"at ${execution.get('price', 'N/A')}. " \
               f"Execution time: {execution.get('execution_time', 'N/A')}ms, " \
               f"Slippage: {execution.get('slippage', 'N/A')}bps"

    def _format_compliance_event(self, compliance_event: Dict[str, Any]) -> str:
        """Format compliance event for storage"""
        return f"Compliance event: {compliance_event.get('event_type', 'Unknown')} " \
               f"with severity {compliance_event.get('severity', 'Unknown')}. " \
               f"Regulation: {compliance_event.get('regulation', 'N/A')}. " \
               f"Details: {compliance_event.get('description', 'No description provided')}"

# Usage example
async def example_usage():
    """Example usage of ATS Memory Wrapper"""
    # Initialize integration
    integration = AgentMemoryIntegration()
    await integration.initialize()

    # Create ATS wrapper
    ats_wrapper = ATSMemoryWrapper(integration)

    # Example: Store market data
    market_data = {
        "symbols": ["AAPL", "GOOGL"],
        "timestamp": datetime.now(UTC).isoformat(),
        "price": {"AAPL": 150.25, "GOOGL": 2800.50},
        "volume": {"AAPL": 1000000, "GOOGL": 500000},
        "change": {"AAPL": 2.5, "GOOGL": -1.2},
        "sources": ["market_feed", "exchange_api"]
    }

    memory_id = await ats_wrapper.store_market_data(
        agent_id="algorithmic-trading-system",
        market_data=market_data,
        metadata={"priority": "high", "data_quality": "real_time"}
    )

    print(f"Stored market data with ID: {memory_id}")

    # Search for market data
    results = await ats_wrapper.search_market_data(
        agent_id="algorithmic-trading-system",
        symbol="AAPL",
        limit=10
    )

    print(f"Found {len(results)} market data entries")

    # Get cross-agent insights
    insights = await ats_wrapper.get_cross_agent_insights(symbol="AAPL")
    print(f"Cross-agent insights: {insights}")

    await integration.close()

if __name__ == "__main__":
    asyncio.run(example_usage())