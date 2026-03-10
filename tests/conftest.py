"""Pytest configuration and fixtures."""

import sys
import os
from pathlib import Path

import pytest
from unittest.mock import MagicMock, Mock

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Optional: ibapi and app components (skip if not installed, e.g. when only running streaming_market_data tests)
Contract = Order = ContractHandler = OrderManager = TradingApp = None
try:
    from ibapi.contract import Contract
    from ibapi.order import Order
    try:
        from handlers.contract_handler import ContractHandler
        from order_management.order_manager import OrderManager
        from core.trading_app import TradingApp
    except ImportError:
        from ..handlers.contract_handler import ContractHandler
        from ..order_management.order_manager import OrderManager
        from ..core.trading_app import TradingApp
except ImportError:
    pass


@pytest.fixture
def contract_handler():
    """Fixture for ContractHandler."""
    if ContractHandler is None:
        pytest.importorskip("handlers.contract_handler")
    return ContractHandler()


@pytest.fixture
def order_manager():
    """Fixture for OrderManager."""
    if OrderManager is None:
        pytest.importorskip("order_management.order_manager")
    return OrderManager()


@pytest.fixture
def sample_contract():
    """Fixture for a sample contract."""
    if Contract is None:
        pytest.importorskip("ibapi.contract")
    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    return contract


@pytest.fixture
def sample_order():
    """Fixture for a sample order."""
    if Order is None:
        pytest.importorskip("ibapi.order")
    order = Order()
    order.action = "BUY"
    order.orderType = "LMT"
    order.totalQuantity = 10
    order.lmtPrice = 150.0
    return order


@pytest.fixture
def mock_trading_app():
    """Fixture for a mocked TradingApp."""
    if TradingApp is None:
        pytest.importorskip("core.trading_app")
    app = TradingApp()
    app.connection_manager.client = MagicMock()
    app.connection_manager.client.isConnected = MagicMock(return_value=True)
    app._next_valid_order_id = 1
    return app
