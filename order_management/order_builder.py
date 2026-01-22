"""Order builder for creating orders with a fluent interface."""

from typing import Optional

from ibapi.order import Order

from ..utils import get_logger

logger = get_logger(__name__)


class OrderBuilder:
    """Builder pattern for creating orders."""
    
    def __init__(self):
        """Initialize order builder."""
        self._order = Order()
    
    def with_action(self, action: str) -> "OrderBuilder":
        """Set order action (BUY/SELL)."""
        self._order.action = action
        return self
    
    def with_type(self, order_type: str) -> "OrderBuilder":
        """Set order type (LMT, MKT, STP, TRAIL, etc.)."""
        self._order.orderType = order_type
        return self
    
    def with_quantity(self, quantity: float) -> "OrderBuilder":
        """Set order quantity."""
        self._order.totalQuantity = quantity
        return self
    
    def with_limit_price(self, price: float) -> "OrderBuilder":
        """Set limit price."""
        self._order.lmtPrice = price
        return self
    
    def with_aux_price(self, price: float) -> "OrderBuilder":
        """Set auxiliary price."""
        self._order.auxPrice = price
        return self
    
    def with_discretionary_amt(self, amt: float) -> "OrderBuilder":
        """Set discretionary amount."""
        self._order.discretionaryAmt = amt
        return self
    
    def with_trail_stop_price(self, price: float) -> "OrderBuilder":
        """Set trail stop price."""
        self._order.trailStopPrice = price
        return self
    
    def build(self) -> Order:
        """Build and return the order."""
        logger.debug(f"Built order: {self._order.action} {self._order.totalQuantity} {self._order.orderType}")
        return self._order
