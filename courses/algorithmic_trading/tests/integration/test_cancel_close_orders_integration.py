"""
Integration tests for cancel_all_open_orders and close_all_positions with real TWS.

Requires TWS (or IB Gateway) running in Paper/Test mode with API enabled.
Uses tickers: NDX, AAPL, AMZN, META, NVDA, TSLA, PLTR (from project conventions).

Run: pytest tests/integration/test_cancel_close_orders_integration.py -v -s
"""

import sys
import time
from pathlib import Path

import pytest

parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from core.trading_app import TradingApp
from config import get_config

# Tickers used across the project for tests (NDX index + stocks)
CANCEL_CLOSE_TICKERS = ["NDX", "AAPL", "AMZN", "META", "NVDA", "TSLA", "PLTR"]


@pytest.fixture(scope="module")
def config():
    return get_config()


def _connect_app(app: TradingApp, client_id: int = 60) -> bool:
    """Connect app to TWS; returns True if connected."""
    cfg = get_config()
    try:
        app.connect(
            host=cfg.host,
            port=cfg.port,
            client_id=client_id,
        )
        time.sleep(cfg.connection_timeout + 1)
        return app.connection_manager.is_connected
    except Exception:
        return False


@pytest.mark.integration
class TestCancelCloseOrdersIntegration:
    """Integration tests: cancel all open orders and close all positions against live TWS."""

    def test_cancel_all_open_orders_no_orders(self, config):
        """Connect to TWS, call cancel_all_open_orders with no open orders (returns [] or list of IDs)."""
        app = TradingApp()
        if not _connect_app(app, client_id=61):
            pytest.skip("TWS not available")
        try:
            result = app.cancel_all_open_orders(timeout_sec=10.0)
            assert isinstance(result, list)
            print(f"   cancel_all_open_orders returned {len(result)} order IDs: {result}")
        finally:
            app.disconnect()

    def test_close_all_positions_no_positions(self, config):
        """Connect to TWS, call close_all_positions with no positions (returns [] or list of closed)."""
        app = TradingApp()
        if not _connect_app(app, client_id=62):
            pytest.skip("TWS not available")
        try:
            result = app.close_all_positions(timeout_sec=10.0)
            assert isinstance(result, list)
            print(f"   close_all_positions returned {len(result)} closed positions: {result}")
        finally:
            app.disconnect()

    def test_place_orders_then_cancel_all(self, config):
        """
        Place one market BUY order per ticker (1 share each), then cancel all open orders.
        You should see orders appear in TWS, then get cancelled.
        """
        app = TradingApp()
        if not _connect_app(app, client_id=63):
            pytest.skip("TWS not available")
        try:
            # NDX is an index and cannot be traded; use stocks only for place-then-cancel test
            stock_tickers = [s for s in CANCEL_CLOSE_TICKERS if s != "NDX"]
            order_ids = []
            for symbol in stock_tickers:
                contract = app.contract_handler.create_contract(symbol, sec_type="STK", currency="USD", exchange="SMART")
                try:
                    oid = app.place_market_order(contract, "BUY", 1)
                    order_ids.append(oid)
                    print(f"   Placed BUY 1 {symbol} -> order_id {oid}")
                except Exception as e:
                    print(f"   Skip {symbol}: {e}")
                time.sleep(1.5)  # Allow TWS to send next valid order ID before next order
            if not order_ids:
                pytest.skip("No orders were placed")
            time.sleep(2.0)
            cancelled = app.cancel_all_open_orders(timeout_sec=10.0)
            print(f"   cancel_all_open_orders sent cancel for: {cancelled}")
            assert isinstance(cancelled, list)
        finally:
            app.disconnect()
