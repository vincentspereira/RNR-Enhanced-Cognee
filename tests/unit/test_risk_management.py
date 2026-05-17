"""
Unit tests for src/agents/ats/risk_management.py
Covers: assess_trade_risk, monitor_portfolio_risk, all private helpers, risk scoring
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.agents.ats.risk_management import RiskManagement, _SCORE_HIGH, _SCORE_MEDIUM


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_memory():
    return AsyncMock()


@pytest.fixture
def rm(mock_memory):
    return RiskManagement(memory_integration=mock_memory)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestRiskManagementInit:
    @pytest.mark.unit
    def test_agent_config(self, rm):
        assert rm.agent_config["agent_id"] == "risk-management"

    @pytest.mark.unit
    def test_risk_limits_initialized(self, rm):
        limits = rm.risk_limits
        assert "max_position_size" in limits
        assert "max_daily_loss" in limits
        assert "max_concentration" in limits
        assert "max_leverage" in limits
        assert "min_liquidity_ratio" in limits

    @pytest.mark.unit
    def test_memory_integration_stored(self, rm, mock_memory):
        assert rm.memory_integration is mock_memory


# ---------------------------------------------------------------------------
# assess_trade_risk
# ---------------------------------------------------------------------------

class TestAssessTradeRisk:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_low_risk_by_default(self, rm):
        result = await rm.assess_trade_risk({"symbol": "AAPL", "quantity": 100})
        assert result["risk_level"] == "low"
        assert result["risk_score"] == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_low_risk_has_auto_approved(self, rm):
        result = await rm.assess_trade_risk({"symbol": "MSFT", "quantity": 50})
        assert "auto-approved" in result["approvals"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_medium_risk_score_triggers_review(self, rm):
        with patch.object(rm, "_calculate_overall_risk_score", return_value=_SCORE_MEDIUM):
            result = await rm.assess_trade_risk({"symbol": "TSLA", "quantity": 1000})
        assert result["risk_level"] == "medium"
        assert "requires-review" in result["approvals"]
        assert len(result["recommendations"]) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_high_risk_score_triggers_reduction_recs(self, rm):
        with patch.object(rm, "_calculate_overall_risk_score", return_value=_SCORE_HIGH):
            result = await rm.assess_trade_risk({"symbol": "GME", "quantity": 100000})
        assert result["risk_level"] == "high"
        recs = result["recommendations"]
        assert any("position size" in r.lower() for r in recs)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_all_checks(self, rm):
        result = await rm.assess_trade_risk({})
        checks = result["checks"]
        assert "position_size" in checks
        assert "concentration" in checks
        assert "leverage" in checks
        assert "liquidity" in checks

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_assessed_at_timestamp(self, rm):
        result = await rm.assess_trade_risk({"symbol": "AAPL", "quantity": 1})
        assert "assessed_at" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self, rm):
        with patch.object(rm, "_check_position_size_risk", side_effect=RuntimeError("db down")):
            result = await rm.assess_trade_risk({"symbol": "AAPL", "quantity": 5})
        assert "error" in result
        assert result["risk_level"] == "unknown"
        assert result["risk_score"] == -1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_score_exactly_at_high_threshold(self, rm):
        with patch.object(rm, "_calculate_overall_risk_score", return_value=_SCORE_HIGH):
            result = await rm.assess_trade_risk({})
        assert result["risk_level"] == "high"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_score_exactly_at_medium_threshold(self, rm):
        with patch.object(rm, "_calculate_overall_risk_score", return_value=_SCORE_MEDIUM):
            result = await rm.assess_trade_risk({})
        assert result["risk_level"] == "medium"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_score_below_medium_is_low(self, rm):
        with patch.object(rm, "_calculate_overall_risk_score", return_value=_SCORE_MEDIUM - 1):
            result = await rm.assess_trade_risk({})
        assert result["risk_level"] == "low"


# ---------------------------------------------------------------------------
# monitor_portfolio_risk
# ---------------------------------------------------------------------------

class TestMonitorPortfolioRisk:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_compliant_when_no_breaches(self, rm):
        result = await rm.monitor_portfolio_risk()
        assert result["compliance_status"] == "compliant"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_non_compliant_when_breaches(self, rm):
        with patch.object(rm, "_identify_risk_breaches", return_value=["breach1"]):
            result = await rm.monitor_portfolio_risk()
        assert result["compliance_status"] == "non-compliant"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_portfolio_value_zero_with_no_positions(self, rm):
        result = await rm.monitor_portfolio_risk()
        assert result["portfolio_value"] == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_portfolio_value_sums_positions(self, rm):
        positions = {
            "AAPL": {"value": 10000},
            "MSFT": {"value": 20000},
        }
        with patch.object(rm, "_get_current_positions", return_value=positions):
            result = await rm.monitor_portfolio_risk()
        assert result["portfolio_value"] == 30000.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_risk_metrics(self, rm):
        result = await rm.monitor_portfolio_risk()
        assert "risk_metrics" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_monitored_at_timestamp(self, rm):
        result = await rm.monitor_portfolio_risk()
        assert "monitored_at" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_alerts_returned(self, rm):
        result = await rm.monitor_portfolio_risk()
        assert "alerts" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_error(self, rm):
        with patch.object(rm, "_get_current_positions", side_effect=Exception("connection lost")):
            result = await rm.monitor_portfolio_risk()
        assert "error" in result
        assert result["compliance_status"] == "unknown"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

class TestPrivateHelpers:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_position_size_risk(self, rm):
        result = await rm._check_position_size_risk({"symbol": "AAPL", "quantity": 100})
        assert "position_size_ok" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_concentration_risk(self, rm):
        result = await rm._check_concentration_risk({"symbol": "MSFT"})
        assert "concentration_ok" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_leverage_risk(self, rm):
        result = await rm._check_leverage_risk({"symbol": "TSLA"})
        assert "leverage_ok" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_liquidity_risk(self, rm):
        result = await rm._check_liquidity_risk({"symbol": "AMZN"})
        assert "liquidity_ok" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_overall_risk_score_returns_int(self, rm):
        score = await rm._calculate_overall_risk_score({}, {}, {}, {})
        assert isinstance(score, int)
        assert score == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_positions_returns_dict(self, rm):
        positions = await rm._get_current_positions()
        assert isinstance(positions, dict)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_portfolio_risk_metrics(self, rm):
        metrics = await rm._calculate_portfolio_risk_metrics({})
        assert "total_value" in metrics
        assert "var_95" in metrics

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_identify_risk_breaches_returns_list(self, rm):
        breaches = await rm._identify_risk_breaches({}, {})
        assert isinstance(breaches, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_risk_alerts_returns_list(self, rm):
        alerts = await rm._generate_risk_alerts([])
        assert isinstance(alerts, list)
