"""Pytest configuration and fixtures."""

import sys
import os
from pathlib import Path

import pytest
from unittest.mock import MagicMock, Mock

from ibapi.contract import Contract
from ibapi.order import Order

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from handlers.contract_handler import ContractHandler
    from order_management.order_manager import OrderManager
    from core.trading_app import TradingApp
except ImportError:
    # Fallback for relative imports
    from ..handlers.contract_handler import ContractHandler
    from ..order_management.order_manager import OrderManager
    from ..core.trading_app import TradingApp


@pytest.fixture
def contract_handler():
    """Fixture for ContractHandler."""
    return ContractHandler()


@pytest.fixture
def order_manager():
    """Fixture for OrderManager."""
    return OrderManager()


@pytest.fixture
def sample_contract():
    """Fixture for a sample contract."""
    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    return contract


@pytest.fixture
def sample_order():
    """Fixture for a sample order."""
    order = Order()
    order.action = "BUY"
    order.orderType = "LMT"
    order.totalQuantity = 10
    order.lmtPrice = 150.0
    return order


@pytest.fixture
def mock_trading_app():
    """Fixture for a mocked TradingApp."""
    app = TradingApp()
    app.connection_manager.client = MagicMock()
    app.connection_manager.client.isConnected = MagicMock(return_value=True)
    app._next_valid_order_id = 1
    return app
