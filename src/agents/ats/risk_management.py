#!/usr/bin/env python3
"""
Risk Management Agent
ATS Category - Risk assessment and monitoring for trading activities
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from ...agent_memory_integration import AgentMemoryIntegration
from .ats_memory_wrapper import ATSMemoryWrapper

logger = logging.getLogger(__name__)

class RiskManagement:
    """
    Risk Management Agent
    ATS agent responsible for risk assessment, position monitoring, and compliance checks
    """

    def __init__(self, memory_integration: AgentMemoryIntegration):
        self.memory_integration = memory_integration
        self.ats_memory = ATSMemoryWrapper(memory_integration)

        # Agent configuration
        self.agent_config = {
            "agent_id": "risk-management",
            "category": "ATS",
            "prefix": "ats_",
            "description": "Risk assessment and position monitoring system",
            "capabilities": [
                "risk_assessment",
                "position_monitoring",
                "compliance_check",
                "var_calculation",
                "stress_testing"
            ],
            "max_concurrent_tasks": 3,
            "critical": True
        }

        # Risk thresholds and limits
        self.risk_limits = {
            "max_position_size": 1000000,  # $1M per position
            "max_portfolio_exposure": 5000000,  # $5M total exposure
            "max_var_95": 100000,  # $100K 95% VaR limit
            "max_var_99": 200000,  # $200K 99% VaR limit
            "max_drawdown": 0.15,  # 15% max drawdown
            "min_liquidity_ratio": 0.1,  # 10% minimum liquidity
            "max_leverage": 3.0,  # 3x maximum leverage
            "concentration_limit": 0.25  # 25% max concentration in single position
        }

        # Current risk state
        self.risk_state = {
            "current_positions": {},
            "portfolio_metrics": {},
            "risk_breaches": [],
            "compliance_status": "compliant",
            "last_assessment": None
        }

    async def initialize(self):
        """Initialize the risk management agent"""
        try:
            logger.info(f"Initializing {self.agent_config['agent_id']}")

            # Load risk configuration from memory
            await self._load_risk_configuration()

            # Initialize risk models
            await self._initialize_risk_models()

            # Restore previous risk state
            await self._restore_risk_state()

            logger.info(f"{self.agent_config['agent_id']} initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_config['agent_id']}: {e}")
            raise

    async def assess_trade_risk(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk for a proposed trade
        """
        try:
            risk_assessment = {
                "trade_id": trade_request.get("trade_id", f"risk_{datetime.now(UTC).timestamp()}"),
                "symbol": trade_request["symbol"],
                "action": trade_request["direction"],
                "quantity": trade_request["quantity"],
                "timestamp": datetime.now(UTC).isoformat(),
                "risk_level": "low",
                "approvals": [],
                "restrictions": [],
                "recommendations": []
            }

            # Check position size limits
            position_risk = await self._check_position_size_risk(trade_request)
            risk_assessment.update(position_risk)

            # Check portfolio concentration
            concentration_risk = await self._check_concentration_risk(trade_request)
            risk_assessment.update(concentration_risk)

            # Check leverage limits
            leverage_risk = await self._check_leverage_risk(trade_request)
            risk_assessment.update(leverage_risk)

            # Check liquidity impact
            liquidity_risk = await self._check_liquidity_risk(trade_request)
            risk_assessment.update(liquidity_risk)

            # Calculate overall risk score
            risk_score = await self._calculate_overall_risk_score(risk_assessment)
            risk_assessment["risk_score"] = risk_score

            # Determine final risk level
            if risk_score >= 80:
                risk_assessment["risk_level"] = "high"
                risk_assessment["recommendations"].append("Trade rejected - excessive risk")
            elif risk_score >= 60:
                risk_assessment["risk_level"] = "medium"
                risk_assessment["recommendations"].append("Consider reducing position size")
            else:
                risk_assessment["risk_level"] = "low"
                risk_assessment["approvals"].append("Trade approved within risk limits")

            # Store risk assessment
            await self.ats_memory.store_risk_assessment(
                agent_id=self.agent_config["agent_id"],
                risk_data=risk_assessment
            )

            return risk_assessment

        except Exception as e:
            logger.error(f"Failed to assess trade risk: {e}")
            return {"error": str(e), "risk_level": "error"}

    async def monitor_portfolio_risk(self) -> Dict[str, Any]:
        """
        Monitor current portfolio risk metrics
        """
        try:
            current_time = datetime.now(UTC)

            # Get current positions from memory
            current_positions = await self._get_current_positions()

            # Calculate portfolio risk metrics
            portfolio_metrics = await self._calculate_portfolio_risk_metrics(current_positions)

            # Check for risk breaches
            risk_breaches = await self._identify_risk_breaches(portfolio_metrics)

            # Update risk state
            self.risk_state.update({
                "current_positions": current_positions,
                "portfolio_metrics": portfolio_metrics,
                "risk_breaches": risk_breaches,
                "last_assessment": current_time
            })

            # Create comprehensive risk report
            risk_report = {
                "assessment_id": f"portfolio_risk_{current_time.timestamp()}",
                "timestamp": current_time.isoformat(),
                "portfolio_value": portfolio_metrics.get("total_value", 0),
                "risk_metrics": portfolio_metrics,
                "risk_breaches": risk_breaches,
                "compliance_status": "compliant" if not risk_breaches else "breached",
                "risk_alerts": await self._generate_risk_alerts(portfolio_metrics, risk_breaches)
            }

            # Store risk monitoring report
            await self.ats_memory.store_risk_assessment(
                agent_id=self.agent_config["agent_id"],
                risk_data=risk_report
            )

            # Handle critical risk breaches
            if risk_breaches:
                await self._handle_critical_risk_breaches(risk_breaches)

            return risk_report

        except Exception as e:
            logger.error(f"Failed to monitor portfolio risk: {e}")
            return {"error": str(e)}

    async def run_stress_test(self, stress_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run stress test scenarios on portfolio
        """
        try:
            stress_test_results = {
                "scenario_id": f"stress_{datetime.now(UTC).timestamp()}",
                "scenario_name": stress_scenario.get("name", "Custom Scenario"),
                "scenario_parameters": stress_scenario,
                "timestamp": datetime.now(UTC).isoformat(),
                "portfolio_impact": {},
                "position_impacts": [],
                "risk_breaches": [],
                "recommendations": []
            }

            # Get current positions
            current_positions = await self._get_current_positions()

            # Apply stress scenario to each position
            position_impacts = []
            total_portfolio_loss = 0

            for symbol, position in current_positions.items():
                position_impact = await self._calculate_position_stress_impact(
                    symbol, position, stress_scenario
                )
                position_impacts.append(position_impact)
                total_portfolio_loss += position_impact.get("loss_amount", 0)

            # Calculate portfolio-level impacts
            portfolio_impact = {
                "total_loss": total_portfolio_loss,
                "loss_percentage": (total_portfolio_loss / stress_test_results.get("portfolio_value", 1)) * 100,
                "var_breaches": await self._check_var_breaches_under_stress(total_portfolio_loss),
                "liquidity_impact": await self._calculate_liquidity_impact_under_stress(stress_scenario)
            }

            stress_test_results.update({
                "portfolio_impact": portfolio_impact,
                "position_impacts": position_impacts
            })

            # Generate recommendations based on stress test results
            recommendations = await self._generate_stress_test_recommendations(stress_test_results)
            stress_test_results["recommendations"] = recommendations

            # Store stress test results
            await self.ats_memory.store_risk_assessment(
                agent_id=self.agent_config["agent_id"],
                risk_data={
                    "type": "stress_test",
                    **stress_test_results
                }
            )

            logger.info(f"Stress test completed: {stress_test_results['scenario_id']}")

            return stress_test_results

        except Exception as e:
            logger.error(f"Failed to run stress test: {e}")
            return {"error": str(e)}

    async def check_compliance(self, compliance_check: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform compliance checks for trading activities
        """
        try:
            compliance_result = {
                "check_id": f"compliance_{datetime.now(UTC).timestamp()}",
                "check_type": compliance_check.get("type", "general"),
                "timestamp": datetime.now(UTC).isoformat(),
                "status": "compliant",
                "violations": [],
                "warnings": [],
                "required_actions": []
            }

            # Check position limits
            position_violations = await self._check_position_limit_compliance()
            compliance_result["violations"].extend(position_violations)

            # Check trading hours compliance
            trading_hours_violations = await self._check_trading_hours_compliance(compliance_check)
            compliance_result["violations"].extend(trading_hours_violations)

            # Check concentration limits
            concentration_violations = await self._check_concentration_limit_compliance()
            compliance_result["violations"].extend(concentration_violations)

            # Check reporting requirements
            reporting_violations = await self._check_reporting_compliance()
            compliance_result["violations"].extend(reporting_violations)

            # Update compliance status
            if compliance_result["violations"]:
                compliance_result["status"] = "non_compliant"
                self.risk_state["compliance_status"] = "non_compliant"
            else:
                self.risk_state["compliance_status"] = "compliant"

            # Store compliance check results
            await self.ats_memory.store_compliance_event(
                agent_id=self.agent_config["agent_id"],
                compliance_event={
                    "event_type": "compliance_check",
                    "severity": "high" if compliance_result["violations"] else "low",
                    "check_results": compliance_result,
                    "auto_resolved": not compliance_result["violations"]
                }
            )

            return compliance_result

        except Exception as e:
            logger.error(f"Failed to perform compliance check: {e}")
            return {"error": str(e), "status": "error"}

    async def _check_position_size_risk(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Check if trade position size exceeds limits"""
        position_value = trade_request["quantity"] * trade_request.get("price", 1)
        max_position_size = self.risk_limits["max_position_size"]

        if position_value > max_position_size:
            return {
                "position_size_risk": "high",
                "position_value": position_value,
                "limit": max_position_size,
                "excess": position_value - max_position_size,
                "restrictions": ["Position size exceeds maximum limit"],
                "recommendations": [f"Reduce position size to at most ${max_position_size:,.2f}"]
            }

        return {"position_size_risk": "low"}

    async def _check_concentration_risk(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Check concentration risk for the trade"""
        current_positions = await self._get_current_positions()
        symbol = trade_request["symbol"]

        # Calculate current and proposed position values
        current_position_value = current_positions.get(symbol, {}).get("value", 0)
        trade_value = trade_request["quantity"] * trade_request.get("price", 1)
        new_position_value = current_position_value + trade_value

        total_portfolio_value = sum(pos.get("value", 0) for pos in current_positions.values()) + trade_value
        concentration_ratio = (new_position_value / total_portfolio_value) if total_portfolio_value > 0 else 0

        concentration_limit = self.risk_limits["concentration_limit"]

        if concentration_ratio > concentration_limit:
            return {
                "concentration_risk": "high",
                "concentration_ratio": concentration_ratio,
                "limit": concentration_limit,
                "excess": concentration_ratio - concentration_limit,
                "restrictions": ["Concentration exceeds maximum limit"],
                "recommendations": [f"Reduce position to keep concentration below {concentration_limit:.1%}"]
            }

        return {"concentration_risk": "low"}

    async def _check_leverage_risk(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Check leverage requirements for the trade"""
        current_positions = await self._get_current_positions()

        # Calculate total exposure (including margin requirements)
        total_exposure = sum(pos.get("value", 0) for pos in current_positions.values())
        trade_exposure = trade_request["quantity"] * trade_request.get("price", 1)
        new_total_exposure = total_exposure + trade_exposure

        # Calculate portfolio value (simplified)
        portfolio_value = total_exposure  # Simplified calculation

        if portfolio_value > 0:
            leverage = new_total_exposure / portfolio_value
            max_leverage = self.risk_limits["max_leverage"]

            if leverage > max_leverage:
                return {
                    "leverage_risk": "high",
                    "current_leverage": leverage,
                    "limit": max_leverage,
                    "excess": leverage - max_leverage,
                    "restrictions": ["Leverage exceeds maximum limit"],
                    "recommendations": [f"Reduce leverage to at most {max_leverage:.1f}x"]
                }

        return {"leverage_risk": "low"}

    async def _check_liquidity_risk(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Check liquidity risk for the trade"""
        symbol = trade_request["symbol"]
        quantity = trade_request["quantity"]

        # Get average daily volume (simplified)
        avg_daily_volume = 1000000  # Would get from market data

        # Calculate position to volume ratio
        position_to_volume_ratio = quantity / avg_daily_volume if avg_daily_volume > 0 else 0

        if position_to_volume_ratio > 0.1:  # More than 10% of daily volume
            return {
                "liquidity_risk": "high",
                "position_to_volume_ratio": position_to_volume_ratio,
                "avg_daily_volume": avg_daily_volume,
                "restrictions": ["Large position relative to daily volume"],
                "recommendations": ["Consider executing order in smaller tranches"]
            }

        return {"liquidity_risk": "low"}

    def _calculate_overall_risk_score(self, risk_assessment: Dict[str, Any]) -> float:
        """Calculate overall risk score from individual risk components"""
        score = 0
        factors = []

        # Position size risk
        if risk_assessment.get("position_size_risk") == "high":
            score += 25
            factors.append("position_size")

        # Concentration risk
        if risk_assessment.get("concentration_risk") == "high":
            score += 20
            factors.append("concentration")

        # Leverage risk
        if risk_assessment.get("leverage_risk") == "high":
            score += 30
            factors.append("leverage")

        # Liquidity risk
        if risk_assessment.get("liquidity_risk") == "high":
            score += 25
            factors.append("liquidity")

        risk_assessment["risk_factors"] = factors
        return min(score, 100)

    async def _get_current_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get current trading positions from memory"""
        # This would retrieve current positions from the trading system
        # For now, return example data
        return {
            "AAPL": {
                "quantity": 1000,
                "avg_price": 150.25,
                "current_price": 152.30,
                "value": 152300,
                "unrealized_pnl": 2050
            },
            "GOOGL": {
                "quantity": 500,
                "avg_price": 2800.50,
                "current_price": 2850.00,
                "value": 1425000,
                "unrealized_pnl": 24750
            }
        }

    async def _calculate_portfolio_risk_metrics(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio risk metrics"""
        total_value = sum(pos["value"] for pos in positions.values())
        total_pnl = sum(pos.get("unrealized_pnl", 0) for pos in positions.values())

        # Simplified VaR calculation
        var_95 = total_value * 0.02  # 2% daily VaR
        var_99 = total_value * 0.03  # 3% daily VaR

        return {
            "total_value": total_value,
            "total_pnl": total_pnl,
            "var_95": var_95,
            "var_99": var_99,
            "max_drawdown": 0.05,  # 5% current drawdown
            "beta": 1.1,
            "volatility": 0.18,
            "sharpe_ratio": 1.2
        }

    async def _identify_risk_breaches(self, portfolio_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify any risk limit breaches"""
        breaches = []

        # Check VaR limits
        if portfolio_metrics.get("var_95", 0) > self.risk_limits["max_var_95"]:
            breaches.append({
                "type": "var_breach",
                "metric": "var_95",
                "current": portfolio_metrics["var_95"],
                "limit": self.risk_limits["max_var_95"],
                "severity": "high"
            })

        # Check drawdown limit
        if portfolio_metrics.get("max_drawdown", 0) > self.risk_limits["max_drawdown"]:
            breaches.append({
                "type": "drawdown_breach",
                "metric": "max_drawdown",
                "current": portfolio_metrics["max_drawdown"],
                "limit": self.risk_limits["max_drawdown"],
                "severity": "high"
            })

        return breaches

    async def _generate_risk_alerts(self, portfolio_metrics: Dict[str, Any], breaches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate risk alerts based on metrics and breaches"""
        alerts = []

        # Generate breach alerts
        for breach in breaches:
            alerts.append({
                "type": "breach_alert",
                "severity": breach["severity"],
                "message": f"Risk limit breach: {breach['metric']} ({breach['current']:.2f}) exceeds limit ({breach['limit']:.2f})",
                "timestamp": datetime.now(UTC).isoformat(),
                "requires_action": True
            })

        # Generate warning alerts for metrics approaching limits
        if portfolio_metrics.get("var_95", 0) > self.risk_limits["max_var_95"] * 0.8:
            alerts.append({
                "type": "warning_alert",
                "severity": "medium",
                "message": "VaR approaching limit - monitor closely",
                "timestamp": datetime.now(UTC).isoformat(),
                "requires_action": False
            })

        return alerts

    async def _handle_critical_risk_breaches(self, breaches: List[Dict[str, Any]]):
        """Handle critical risk breaches with automated responses"""
        for breach in breaches:
            if breach.get("severity") == "high":
                # Store critical compliance event
                await self.ats_memory.store_compliance_event(
                    agent_id=self.agent_config["agent_id"],
                    compliance_event={
                        "event_type": "risk_breach",
                        "severity": "critical",
                        "breach_details": breach,
                        "auto_resolved": False,
                        "action_required": True
                    }
                )

                # In real implementation, would trigger alerts and risk mitigation actions
                logger.critical(f"Critical risk breach detected: {breach}")

    async def _calculate_position_stress_impact(self, symbol: str, position: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate stress impact on a specific position"""
        # Get scenario parameters for this symbol
        symbol_scenario = scenario.get("symbol_scenarios", {}).get(symbol, {})
        price_shock = symbol_scenario.get("price_shock", -0.2)  # Default 20% price decline

        current_price = position.get("current_price", position.get("avg_price", 1))
        stress_price = current_price * (1 + price_shock)

        loss_amount = (current_price - stress_price) * position.get("quantity", 0)
        loss_percentage = (current_price - stress_price) / current_price

        return {
            "symbol": symbol,
            "current_price": current_price,
            "stress_price": stress_price,
            "loss_amount": loss_amount,
            "loss_percentage": loss_percentage,
            "position_value": position.get("value", 0)
        }

    async def _check_var_breaches_under_stress(self, total_loss: float) -> Dict[str, bool]:
        """Check VaR breaches under stress scenario"""
        return {
            "var_95_breached": total_loss > self.risk_limits["max_var_95"],
            "var_99_breached": total_loss > self.risk_limits["max_var_99"]
        }

    async def _calculate_liquidity_impact_under_stress(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate liquidity impact under stress scenario"""
        # Simplified liquidity impact calculation
        market_depth_reduction = scenario.get("market_depth_reduction", 0.5)  # 50% reduction
        return {
            "liquidity_reduction": market_depth_reduction,
            "impact_severity": "high" if market_depth_reduction > 0.7 else "medium"
        }

    async def _generate_stress_test_recommendations(self, stress_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on stress test results"""
        recommendations = []

        total_loss = stress_results.get("portfolio_impact", {}).get("total_loss", 0)
        loss_percentage = stress_results.get("portfolio_impact", {}).get("loss_percentage", 0)

        if loss_percentage > 15:
            recommendations.append("Portfolio shows excessive vulnerability to stress scenarios - consider reducing overall exposure")
        elif loss_percentage > 10:
            recommendations.append("Portfolio stress losses significant - review position sizing and diversification")

        if total_loss > self.risk_limits["max_var_99"]:
            recommendations.append("Stress test losses exceed VaR limits - implement additional risk controls")

        return recommendations

    async def _check_position_limit_compliance(self) -> List[Dict[str, Any]]:
        """Check compliance with position limits"""
        violations = []
        current_positions = await self._get_current_positions()

        for symbol, position in current_positions.items():
            position_value = position.get("value", 0)
            if position_value > self.risk_limits["max_position_size"]:
                violations.append({
                    "type": "position_limit_violation",
                    "symbol": symbol,
                    "position_value": position_value,
                    "limit": self.risk_limits["max_position_size"]
                })

        return violations

    async def _check_trading_hours_compliance(self, compliance_check: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check compliance with trading hours"""
        violations = []
        current_time = datetime.now(UTC)

        # Check if outside trading hours (simplified)
        if current_time.hour < 9 or current_time.hour > 16:
            violations.append({
                "type": "trading_hours_violation",
                "current_time": current_time.isoformat(),
                "trading_hours": "09:00 - 16:00"
            })

        return violations

    async def _check_concentration_limit_compliance(self) -> List[Dict[str, Any]]:
        """Check compliance with concentration limits"""
        violations = []
        current_positions = await self._get_current_positions()

        total_value = sum(pos.get("value", 0) for pos in current_positions.values())

        for symbol, position in current_positions.items():
            position_value = position.get("value", 0)
            concentration = (position_value / total_value) if total_value > 0 else 0

            if concentration > self.risk_limits["concentration_limit"]:
                violations.append({
                    "type": "concentration_limit_violation",
                    "symbol": symbol,
                    "concentration_ratio": concentration,
                    "limit": self.risk_limits["concentration_limit"]
                })

        return violations

    async def _check_reporting_compliance(self) -> List[Dict[str, Any]]:
        """Check compliance with reporting requirements"""
        violations = []

        # Check if required reports have been filed
        last_assessment = self.risk_state.get("last_assessment")

        if last_assessment:
            days_since_assessment = (datetime.now(UTC) - last_assessment).days
            if days_since_assessment > 1:  # Daily assessment required
                violations.append({
                    "type": "reporting_violation",
                    "report_type": "daily_risk_assessment",
                    "days_overdue": days_since_assessment - 1
                })

        return violations

    async def _load_risk_configuration(self):
        """Load risk management configuration from memory"""
        # Load configuration from memory storage
        pass

    async def _initialize_risk_models(self):
        """Initialize risk calculation models"""
        # Initialize VaR models, stress testing models, etc.
        pass

    async def _restore_risk_state(self):
        """Restore previous risk state from memory"""
        # Load previous risk state from memory
        pass

# Factory function for agent creation
async def create_risk_management(memory_integration: AgentMemoryIntegration) -> RiskManagement:
    """Create and initialize Risk Management agent"""
    agent = RiskManagement(memory_integration)
    await agent.initialize()
    return agent

if __name__ == "__main__":
    # Example usage
    async def example_usage():
        from ...agent_memory_integration import AgentMemoryIntegration

        integration = AgentMemoryIntegration()
        await integration.initialize()

        risk_manager = await create_risk_management(integration)

        # Assess trade risk
        trade_request = {
            "trade_id": "trade_001",
            "symbol": "AAPL",
            "quantity": 5000,
            "direction": "buy",
            "price": 150.25
        }

        risk_assessment = await risk_manager.assess_trade_risk(trade_request)
        print(f"Trade risk assessment: {risk_assessment}")

        # Monitor portfolio risk
        portfolio_risk = await risk_manager.monitor_portfolio_risk()
        print(f"Portfolio risk: {portfolio_risk}")

        # Run stress test
        stress_scenario = {
            "name": "Market Crash Scenario",
            "description": "20% market decline with liquidity reduction",
            "symbol_scenarios": {
                "AAPL": {"price_shock": -0.25},
                "GOOGL": {"price_shock": -0.20}
            },
            "market_depth_reduction": 0.7
        }

        stress_results = await risk_manager.run_stress_test(stress_scenario)
        print(f"Stress test results: {stress_results}")

        await integration.close()

    asyncio.run(example_usage())