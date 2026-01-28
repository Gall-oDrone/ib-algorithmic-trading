"""Tests for OrderManager."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from order_management.order_manager import OrderManager
from exceptions import OrderError

from tests.conftest import order_manager, sample_order


def test_create_order(order_manager):
    """Test order creation."""
    order = order_manager.create_order()
    
    assert order is not None
    assert order_manager.order == order


def test_set_order_id(order_manager):
    """Test setting order ID."""
    order_manager.set_order_id(123)
    
    assert order_manager.next_valid_order_id == 123


def test_set_order_details(order_manager):
    """Test setting order details."""
    order_manager.create_order()
    order_manager.set_order_details(
        action="BUY",
        order_type="LMT",
        total_quantity=10,
        limit_price=150.0,
    )
    
    assert order_manager.order.action == "BUY"
    assert order_manager.order.orderType == "LMT"
    assert order_manager.order.totalQuantity == 10
    assert order_manager.order.lmtPrice == 150.0


def test_set_order_details_without_order(order_manager):
    """Test setting order details without creating order first."""
    with pytest.raises(OrderError):
        order_manager.set_order_details(
            action="BUY",
            order_type="LMT",
            total_quantity=10,
        )


def test_create_order_cancel(order_manager):
    """Test order cancellation object creation."""
    order_cancel = order_manager.create_order_cancel()
    
    assert order_cancel is not None


def test_set_order_details_from_dict(order_manager):
    """Test setting order details from dictionary."""
    order_dict = {
        "action": "SELL",
        "orderType": "MKT",
        "orderTotalQuantity": 5,
    }
    
    order_manager.create_order()
    order_manager.set_order_details_from_dict(order_dict)
    
    assert order_manager.order.action == "SELL"
    assert order_manager.order.orderType == "MKT"
    assert order_manager.order.totalQuantity == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
