#!/usr/bin/env python3
"""
Algorithmic Trading System Agent
ATS Category - Core trading engine with market analysis and signal generation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from ...agent_memory_integration import AgentMemoryIntegration
from .ats_memory_wrapper import ATSMemoryWrapper

logger = logging.getLogger(__name__)

class AlgorithmicTradingSystem:
    """
    Algorithmic Trading System Agent
    Core ATS agent responsible for market analysis, signal generation, and trade execution
    """

    def __init__(self, memory_integration: AgentMemoryIntegration):
        self.memory_integration = memory_integration
        self.ats_memory = ATSMemoryWrapper(memory_integration)

        # Agent configuration
        self.agent_config = {
            "agent_id": "algorithmic-trading-system",
            "category": "ATS",
            "prefix": "ats_",
            "description": "High-frequency trading and market analysis engine",
            "capabilities": [
                "market_analysis",
                "signal_generation",
                "order_execution",
                "portfolio_optimization",
                "risk_assessment"
            ],
            "max_concurrent_tasks": 5,
            "critical": True,
            "supported_symbols": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
            "strategies": [
                "momentum_trading",
                "mean_reversion",
                "arbitrage",
                "market_making"
            ]
        }

        # Trading state
        self.trading_state = {
            "active_positions": {},
            "pending_orders": {},
            "current_signals": [],
            "market_data_cache": {},
            "risk_metrics": {}
        }

    async def initialize(self):
        """Initialize the trading system agent"""
        try:
            logger.info(f"Initializing {self.agent_config['agent_id']}")

            # Load trading configuration from memory
            await self._load_trading_configuration()

            # Initialize market data connections
            await self._initialize_market_data_connections()

            # Restore any active trading state
            await self._restore_trading_state()

            logger.info(f"{self.agent_config['agent_id']} initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_config['agent_id']}: {e}")
            raise

    async def process_market_data(self, market_data: Dict[str, Any]) -> bool:
        """
        Process incoming market data and generate trading signals
        """
        try:
            # Store market data
            await self.ats_memory.store_market_data(
                agent_id=self.agent_config["agent_id"],
                market_data=market_data,
                metadata={"priority": "high", "data_quality": "real_time"}
            )

            # Update market data cache
            symbol = market_data.get("symbol")
            if symbol:
                self.trading_state["market_data_cache"][symbol] = {
                    "data": market_data,
                    "timestamp": datetime.now(UTC)
                }

            # Generate trading signals
            signals = await self._generate_trading_signals(market_data)

            # Store signals
            for signal in signals:
                await self.ats_memory.store_trading_signal(
                    agent_id=self.agent_config["agent_id"],
                    signal=signal,
                    confidence=signal.get("confidence", 0.8)
                )

            self.trading_state["current_signals"].extend(signals)

            # Log processing
            logger.info(f"Processed market data for {symbol}, generated {len(signals)} signals")

            return True

        except Exception as e:
            logger.error(f"Failed to process market data: {e}")
            return False

    async def execute_trade(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trade based on signal or manual request
        """
        execution = None  # Initialize to avoid UnboundLocalError
        try:
            # Validate trade request
            if not await self._validate_trade_request(trade_request):
                raise ValueError("Invalid trade request")

            # Create execution record
            execution = {
                "execution_id": f"exec_{datetime.now(UTC).timestamp()}",
                "symbol": trade_request["symbol"],
                "quantity": trade_request["quantity"],
                "order_type": trade_request.get("order_type", "market"),
                "direction": trade_request["direction"],
                "status": "pending",
                "created_at": datetime.now(UTC).isoformat()
            }

            # Store execution request
            await self.ats_memory.store_execution_result(
                agent_id=self.agent_config["agent_id"],
                execution=execution
            )

            # Execute the trade (simulated for now)
            execution_result = await self._execute_order(execution)

            # Update execution record
            execution.update(execution_result)
            execution["status"] = "completed"

            # Store final execution result
            await self.ats_memory.store_execution_result(
                agent_id=self.agent_config["agent_id"],
                execution=execution
            )

            # Update trading state
            await self._update_trading_state(execution)

            logger.info(f"Trade executed: {execution['execution_id']}")

            return execution

        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return {
                "error": str(e),
                "status": "failed",
                "execution_id": execution.get("execution_id", "unknown") if execution else "unknown"
            }

    async def assess_portfolio_risk(self) -> Dict[str, Any]:
        """
        Assess current portfolio risk metrics
        """
        try:
            risk_assessment = {
                "assessment_id": f"risk_{datetime.now(UTC).timestamp()}",
                "timestamp": datetime.now(UTC).isoformat(),
                "portfolio_value": self._calculate_portfolio_value(),
                "position_count": len(self.trading_state["active_positions"]),
                "risk_metrics": {
                    "var_95": self._calculate_var(0.95),
                    "var_99": self._calculate_var(0.99),
                    "beta": self._calculate_portfolio_beta(),
                    "volatility": self._calculate_portfolio_volatility(),
                    "max_drawdown": self._calculate_max_drawdown()
                },
                "concentration_risk": self._calculate_concentration_risk(),
                "liquidity_risk": self._calculate_liquidity_risk()
            }

            # Store risk assessment
            await self.ats_memory.store_risk_assessment(
                agent_id=self.agent_config["agent_id"],
                risk_data=risk_assessment
            )

            # Update risk metrics in state
            self.trading_state["risk_metrics"] = risk_assessment["risk_metrics"]

            return risk_assessment

        except Exception as e:
            logger.error(f"Failed to assess portfolio risk: {e}")
            return {"error": str(e)}

    async def get_trading_performance(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Get recent trading performance metrics
        """
        try:
            # Get performance summary from memory
            performance = await self.ats_memory.get_agent_performance_summary(
                agent_id=self.agent_config["agent_id"],
                days_back=days_back
            )

            # Add current state information
            performance.update({
                "active_positions": len(self.trading_state["active_positions"]),
                "pending_orders": len(self.trading_state["pending_orders"]),
                "current_signals": len(self.trading_state["current_signals"]),
                "last_updated": datetime.now(UTC).isoformat()
            })

            return performance

        except Exception as e:
            logger.error(f"Failed to get trading performance: {e}")
            return {"error": str(e)}

    async def _generate_trading_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals based on market data"""
        signals = []
        symbol = market_data.get("symbol")

        if not symbol or symbol not in self.agent_config["supported_symbols"]:
            return signals

        # Momentum strategy signal
        momentum_signal = await self._generate_momentum_signal(market_data)
        if momentum_signal:
            signals.append(momentum_signal)

        # Mean reversion strategy signal
        mean_reversion_signal = await self._generate_mean_reversion_signal(market_data)
        if mean_reversion_signal:
            signals.append(mean_reversion_signal)

        return signals

    async def _generate_momentum_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate momentum-based trading signal"""
        # Simplified momentum strategy
        price = market_data.get("price", 0)
        volume = market_data.get("volume", 0)

        # Get historical data for momentum calculation
        historical_data = self.trading_state["market_data_cache"].get(market_data.get("symbol"), {})

        if historical_data:
            prev_price = historical_data.get("data", {}).get("price", price)
            price_change = (price - prev_price) / prev_price if prev_price > 0 else 0

            # Generate signal based on momentum
            if abs(price_change) > 0.02:  # 2% threshold
                direction = "buy" if price_change > 0 else "sell"
                confidence = min(abs(price_change) * 10, 1.0)

                return {
                    "signal_id": f"momentum_{datetime.now(UTC).timestamp()}",
                    "type": "momentum",
                    "symbol": market_data["symbol"],
                    "direction": direction,
                    "strength": "high" if confidence > 0.7 else "medium",
                    "confidence": confidence,
                    "reasoning": f"{'Positive' if price_change > 0 else 'Negative'} momentum detected: {price_change:.2%} change",
                    "timestamp": datetime.now(UTC).isoformat()
                }

        return None

    async def _generate_mean_reversion_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate mean reversion trading signal"""
        # Simplified mean reversion strategy
        price = market_data.get("price", 0)

        # Calculate moving average (simplified)
        recent_prices = [price]  # In real implementation, would use historical data
        if len(recent_prices) < 10:
            return None

        moving_avg = sum(recent_prices[-10:]) / 10
        deviation = (price - moving_avg) / moving_avg

        # Generate signal based on deviation from mean
        if abs(deviation) > 0.05:  # 5% deviation threshold
            direction = "sell" if deviation > 0 else "buy"
            confidence = min(abs(deviation) * 5, 1.0)

            return {
                "signal_id": f"mean_rev_{datetime.now(UTC).timestamp()}",
                "type": "mean_reversion",
                "symbol": market_data["symbol"],
                "direction": direction,
                "strength": "medium",
                "confidence": confidence,
                "reasoning": f"Price {deviation:.2%} from {'above' if direction == 'sell' else 'below'} moving average",
                "timestamp": datetime.now(UTC).isoformat()
            }

        return None

    async def _validate_trade_request(self, trade_request: Dict[str, Any]) -> bool:
        """Validate trade request parameters"""
        required_fields = ["symbol", "quantity", "direction"]

        for field in required_fields:
            if field not in trade_request:
                logger.error(f"Missing required field: {field}")
                return False

        if trade_request["symbol"] not in self.agent_config["supported_symbols"]:
            logger.error(f"Unsupported symbol: {trade_request['symbol']}")
            return False

        if trade_request["direction"] not in ["buy", "sell"]:
            logger.error(f"Invalid direction: {trade_request['direction']}")
            return False

        return True

    async def _execute_order(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading order (simulated)"""
        # Simulate order execution
        execution_time = 50  # milliseconds
        slippage = 2  # basis points

        # Simulate execution price with slippage
        market_price = 150.25  # Would get from market data
        slippage_amount = market_price * (slippage / 10000)
        execution_price = market_price + slippage_amount if execution["direction"] == "buy" else market_price - slippage_amount

        return {
            "executed_price": execution_price,
            "executed_quantity": execution["quantity"],
            "execution_time": execution_time,
            "slippage": slippage,
            "status": "filled",
            "executed_at": datetime.now(UTC).isoformat()
        }

    async def _update_trading_state(self, execution: Dict[str, Any]):
        """Update trading state after execution"""
        symbol = execution["symbol"]
        direction = execution["direction"]
        quantity = execution["quantity"]

        if symbol not in self.trading_state["active_positions"]:
            self.trading_state["active_positions"][symbol] = {
                "quantity": 0,
                "avg_price": 0,
                "total_cost": 0
            }

        position = self.trading_state["active_positions"][symbol]

        if direction == "buy":
            # Update long position
            total_quantity = position["quantity"] + quantity
            position["avg_price"] = (position["total_cost"] + (execution["executed_price"] * quantity)) / total_quantity
            position["quantity"] = total_quantity
            position["total_cost"] += execution["executed_price"] * quantity
        else:
            # Reduce position
            position["quantity"] -= quantity
            if position["quantity"] <= 0:
                # Position closed
                del self.trading_state["active_positions"][symbol]

    def _calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        total_value = 0.0
        for symbol, position in self.trading_state["active_positions"].items():
            # Use last known price for valuation
            market_data = self.trading_state["market_data_cache"].get(symbol, {})
            current_price = market_data.get("data", {}).get("price", position.get("avg_price", 0))
            total_value += position["quantity"] * current_price

        return total_value

    def _calculate_var(self, confidence_level: float) -> float:
        """Calculate Value at Risk (simplified)"""
        # Simplified VAR calculation
        portfolio_value = self._calculate_portfolio_value()
        # In real implementation, would use historical returns and statistical methods
        if confidence_level == 0.95:
            return portfolio_value * 0.02  # 2% VAR
        elif confidence_level == 0.99:
            return portfolio_value * 0.03  # 3% VAR
        return 0.0

    def _calculate_portfolio_beta(self) -> float:
        """Calculate portfolio beta (simplified)"""
        # Simplified beta calculation
        # In real implementation, would calculate using regression against market
        return 1.2  # Example beta

    def _calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility (simplified)"""
        # Simplified volatility calculation
        return 0.15  # 15% annualized volatility

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown (simplified)"""
        # Simplified max drawdown calculation
        return 0.08  # 8% max drawdown

    def _calculate_concentration_risk(self) -> Dict[str, Any]:
        """Calculate concentration risk metrics"""
        portfolio_value = self._calculate_portfolio_value()
        concentration = {}

        for symbol, position in self.trading_state["active_positions"].items():
            market_data = self.trading_state["market_data_cache"].get(symbol, {})
            current_price = market_data.get("data", {}).get("price", position.get("avg_price", 0))
            position_value = position["quantity"] * current_price
            concentration[symbol] = (position_value / portfolio_value) * 100 if portfolio_value > 0 else 0

        return {
            "largest_position": max(concentration.values()) if concentration else 0,
            "position_concentrations": concentration,
            "hhi": sum(weight**2 for weight in concentration.values()) / 10000  # Herfindahl-Hirschman Index
        }

    def _calculate_liquidity_risk(self) -> Dict[str, Any]:
        """Calculate liquidity risk metrics"""
        # Simplified liquidity risk calculation
        return {
            "average_daily_volume": 1000000,  # Example value
            "position_to_volume_ratio": 0.1,  # Example ratio
            "liquidity_score": "high"
        }

    async def _load_trading_configuration(self):
        """Load trading configuration from memory"""
        # Load configuration from memory storage
        pass

    async def _initialize_market_data_connections(self):
        """Initialize connections to market data providers"""
        # Initialize market data connections
        pass

    async def _restore_trading_state(self):
        """Restore previous trading state from memory"""
        # Load active trading state from memory
        pass

# Factory function for agent creation
async def create_algorithmic_trading_system(memory_integration: AgentMemoryIntegration) -> AlgorithmicTradingSystem:
    """Create and initialize Algorithmic Trading System agent"""
    agent = AlgorithmicTradingSystem(memory_integration)
    await agent.initialize()
    return agent

if __name__ == "__main__":
    # Example usage
    async def example_usage():
        from ...agent_memory_integration import AgentMemoryIntegration

        integration = AgentMemoryIntegration()
        await integration.initialize()

        trading_system = await create_algorithmic_trading_system(integration)

        # Process market data
        market_data = {
            "symbol": "AAPL",
            "price": 150.25,
            "volume": 1000000,
            "timestamp": datetime.now(UTC).isoformat(),
            "sources": ["market_feed"]
        }

        await trading_system.process_market_data(market_data)

        # Execute trade
        trade_request = {
            "symbol": "AAPL",
            "quantity": 100,
            "direction": "buy",
            "order_type": "market"
        }

        result = await trading_system.execute_trade(trade_request)
        print(f"Trade result: {result}")

        # Assess risk
        risk_assessment = await trading_system.assess_portfolio_risk()
        print(f"Risk assessment: {risk_assessment}")

        await integration.close()

    asyncio.run(example_usage())