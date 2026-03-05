"""Unit tests for cancel_all_open_orders and close_all_positions."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from core.trading_app import TradingApp
from exceptions import ConnectionError


@pytest.fixture
def app():
    """TradingApp with mocked config (connection not established)."""
    with patch("core.trading_app.get_config"):
        a = TradingApp()
    return a


class TestCancelAllOpenOrders:
    """Tests for cancel_all_open_orders."""

    def test_raises_when_not_connected(self, app):
        """cancel_all_open_orders raises ConnectionError when not connected."""
        app.connection_manager = MagicMock()
        app.connection_manager.is_connected = False
        with pytest.raises(ConnectionError, match="Not connected"):
            app.cancel_all_open_orders()

    def test_calls_req_open_orders_and_returns_list(self, app):
        """When connected, calls reqOpenOrders and returns list of cancelled order IDs."""
        app.connection_manager._connected = True
        app._active_orders = {101: MagicMock(), 102: MagicMock()}
        app._open_orders_event.set()  # Simulate openOrderEnd already received

        with patch.object(app.connection_manager.client, "isConnected", return_value=True):
            with patch.object(app, "reqOpenOrders") as mock_req:
                with patch.object(app, "cancel_order") as mock_cancel:
                    result = app.cancel_all_open_orders(timeout_sec=0.1)

        mock_req.assert_called_once()
        assert result == [101, 102]
        assert mock_cancel.call_count == 2

    def test_timeout_returns_whatever_orders_received(self, app):
        """If openOrderEnd never fires, still returns current _active_orders after timeout."""
        app.connection_manager._connected = True
        app._active_orders = {}
        app._open_orders_event.clear()

        with patch.object(app.connection_manager.client, "isConnected", return_value=True):
            with patch.object(app, "reqOpenOrders"):
                result = app.cancel_all_open_orders(timeout_sec=0.05)

        assert result == []


class TestCloseAllPositions:
    """Tests for close_all_positions."""

    def test_raises_when_not_connected(self, app):
        """close_all_positions raises ConnectionError when not connected."""
        app.connection_manager = MagicMock()
        app.connection_manager.is_connected = False
        with pytest.raises(ConnectionError, match="Not connected"):
            app.close_all_positions()

    def test_calls_req_positions_and_returns_list(self, app):
        """When connected, calls reqPositions and returns list of closed position info."""
        app.connection_manager._connected = True
        app.portfolio_manager.clear_positions()
        app._positions_event.set()

        with patch.object(app.connection_manager.client, "isConnected", return_value=True):
            with patch.object(app, "reqPositions") as mock_req:
                with patch.object(app, "place_market_order"):
                    result = app.close_all_positions(timeout_sec=0.1)

        mock_req.assert_called_once()
        assert isinstance(result, list)
        assert result == []

    def test_closes_position_when_get_positions_returns_one_row(self, app):
        """When get_positions returns one position, place_market_order is called and result has one entry."""
        app.connection_manager._connected = True
        app._positions_event.set()
        one_position = pd.DataFrame(
            [{"Account": "DU123", "Symbol": "AAPL", "SecType": "STK", "Currency": "USD", "Position": 10.0, "AvgCost": 150.0}]
        )

        with patch.object(app.connection_manager.client, "isConnected", return_value=True):
            with patch.object(app, "reqPositions"):
                with patch.object(app, "place_market_order") as mock_place:
                    with patch.object(app.portfolio_manager, "get_positions", return_value=one_position):
                        result = app.close_all_positions(timeout_sec=0.1)

        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["action"] == "SELL"
        assert result[0]["quantity"] == 10.0
        mock_place.assert_called_once()
