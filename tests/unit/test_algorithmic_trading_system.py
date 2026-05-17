"""
Unit tests for src/agents/ats/algorithmic_trading_system.py
Covers: process_market_data, execute_trade, private helpers, error paths
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.ats.algorithmic_trading_system import AlgorithmicTradingSystem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_memory():
    return AsyncMock()


@pytest.fixture
def ats(mock_memory):
    return AlgorithmicTradingSystem(memory_integration=mock_memory)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestATSInit:
    @pytest.mark.unit
    def test_agent_config_has_required_keys(self, ats):
        cfg = ats.agent_config
        assert cfg["agent_id"] == "algorithmic-trading-system"
        assert "supported_symbols" in cfg
        assert "max_position_size" in cfg
        assert "order_types" in cfg

    @pytest.mark.unit
    def test_trading_state_initialized_empty(self, ats):
        st = ats.trading_state
        assert st["market_data_cache"] == {}
        assert st["current_signals"] == []
        assert st["open_positions"] == {}
        assert st["execution_history"] == []

    @pytest.mark.unit
    def test_memory_integration_stored(self, ats, mock_memory):
        assert ats.memory_integration is mock_memory


# ---------------------------------------------------------------------------
# process_market_data
# ---------------------------------------------------------------------------

class TestProcessMarketData:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stores_market_data_in_cache(self, ats):
        data = {"symbol": "AAPL", "price": 150.0}
        result = await ats.process_market_data(data)
        assert result is True
        assert ats.trading_state["market_data_cache"]["AAPL"] == data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_defaults_symbol_to_unknown(self, ats):
        data = {"price": 100.0}
        result = await ats.process_market_data(data)
        assert result is True
        assert "UNKNOWN" in ats.trading_state["market_data_cache"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, ats):
        result = await ats.process_market_data({"symbol": "MSFT", "price": 200.0})
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_signals_appended_when_returned(self, ats):
        signal = {"action": "buy", "symbol": "TSLA"}
        with patch.object(ats, "_generate_trading_signals", return_value=[signal]):
            await ats.process_market_data({"symbol": "TSLA", "price": 500.0})
        assert signal in ats.trading_state["current_signals"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_signals_does_not_change_list(self, ats):
        with patch.object(ats, "_generate_trading_signals", return_value=[]):
            await ats.process_market_data({"symbol": "AMZN", "price": 300.0})
        assert ats.trading_state["current_signals"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, ats):
        with patch.object(ats, "_generate_trading_signals", side_effect=RuntimeError("boom")):
            result = await ats.process_market_data({"symbol": "GOOG", "price": 1000.0})
        assert result is False


# ---------------------------------------------------------------------------
# execute_trade
# ---------------------------------------------------------------------------

class TestExecuteTrade:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_valid_trade_returns_completed_status(self, ats):
        request = {"symbol": "AAPL", "quantity": 10}
        result = await ats.execute_trade(request)
        assert result["status"] == "completed"
        assert result["symbol"] == "AAPL"
        assert result["quantity"] == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_order_result(self, ats):
        request = {"symbol": "MSFT", "quantity": 5}
        result = await ats.execute_trade(request)
        assert "order_result" in result
        assert "timestamp" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_trade_missing_symbol_returns_failed(self, ats):
        request = {"quantity": 10}
        result = await ats.execute_trade(request)
        assert result["status"] == "failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_trade_zero_quantity_returns_failed(self, ats):
        request = {"symbol": "AAPL", "quantity": 0}
        result = await ats.execute_trade(request)
        assert result["status"] == "failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_trade_negative_quantity_returns_failed(self, ats):
        request = {"symbol": "AAPL", "quantity": -5}
        result = await ats.execute_trade(request)
        assert result["status"] == "failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execution_error_returns_failed(self, ats):
        with patch.object(ats, "_execute_order", side_effect=Exception("network error")):
            result = await ats.execute_trade({"symbol": "AAPL", "quantity": 10})
        assert result["status"] == "failed"
        assert "network error" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_trade_appended_to_execution_history(self, ats):
        request = {"symbol": "TSLA", "quantity": 3}
        await ats.execute_trade(request)
        assert len(ats.trading_state["execution_history"]) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failed_validation_includes_symbol_and_quantity(self, ats):
        result = await ats.execute_trade({"symbol": "XYZ", "quantity": 0})
        assert result["symbol"] == "XYZ"
        assert result["quantity"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_trade_with_custom_order_result(self, ats):
        custom_result = {"status": "filled", "fill_price": 195.50}
        with patch.object(ats, "_execute_order", return_value=custom_result):
            result = await ats.execute_trade({"symbol": "AAPL", "quantity": 2})
        assert result["order_result"] == custom_result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

class TestPrivateHelpers:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_trading_signals_returns_empty(self, ats):
        signals = await ats._generate_trading_signals({"symbol": "AAPL"})
        assert signals == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_trade_request_valid(self, ats):
        result = await ats._validate_trade_request({"symbol": "AAPL", "quantity": 10})
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_trade_request_empty_symbol(self, ats):
        result = await ats._validate_trade_request({"symbol": "", "quantity": 5})
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_trade_request_no_symbol(self, ats):
        result = await ats._validate_trade_request({"quantity": 5})
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_order_returns_filled(self, ats):
        result = await ats._execute_order({"symbol": "AAPL", "quantity": 1})
        assert result["status"] == "filled"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_trading_state_appends_to_history(self, ats):
        req = {"symbol": "AAPL", "quantity": 1}
        order = {"status": "filled", "fill_price": 150.0}
        await ats._update_trading_state(req, order)
        assert len(ats.trading_state["execution_history"]) == 1
        entry = ats.trading_state["execution_history"][0]
        assert entry["request"] == req
        assert entry["result"] == order
