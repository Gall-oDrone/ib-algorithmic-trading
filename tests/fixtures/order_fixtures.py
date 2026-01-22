"""Order test fixtures."""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import after path setup
try:
    from consts.orders import get_order
except ImportError:
    # Fallback for relative import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from consts.orders import get_order


def get_buy_limit_order_test1():
    """Get buy limit order test 1."""
    return get_order("buy", "limit", "test_1")


def get_buy_limit_order_test2():
    """Get buy limit order test 2."""
    return get_order("buy", "limit", "test_2")


def get_buy_market_order_test1():
    """Get buy market order test 1."""
    return get_order("buy", "market", "test_1")


def get_buy_stop_order_test1():
    """Get buy stop order test 1."""
    return get_order("buy", "stop", "test_1")


def get_buy_trail_stop_order_test1():
    """Get buy trailing stop order test 1."""
    return get_order("buy", "trailStop", "test_1")


def get_sell_limit_order_test1():
    """Get sell limit order test 1."""
    return get_order("sell", "limit", "test_1")


def get_sell_market_order_test1():
    """Get sell market order test 1."""
    return get_order("sell", "market", "test_1")
