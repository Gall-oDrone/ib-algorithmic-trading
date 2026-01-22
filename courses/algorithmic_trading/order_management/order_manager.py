"""Order management for IB API."""

from typing import Optional, Dict, Any

import pandas as pd

from ibapi.order import Order
from ibapi.order_cancel import OrderCancel

from utils import get_logger
from exceptions import OrderError
from .consts.dataframes import get_open_order_dataframe

logger = get_logger(__name__)


class OrderManager:
    """Manages order creation and tracking."""
    
    def __init__(self):
        """Initialize order manager."""
        self._order: Optional[Order] = None
        self._next_valid_order_id: Optional[int] = None
        self._order_df: pd.DataFrame = get_open_order_dataframe()
        self._active_orders: Dict[int, Order] = {}
    
    @property
    def order(self) -> Optional[Order]:
        """Get current order."""
        return self._order
    
    @property
    def next_valid_order_id(self) -> Optional[int]:
        """Get next valid order ID."""
        return self._next_valid_order_id
    
    @property
    def order_dataframe(self) -> pd.DataFrame:
        """Get order tracking dataframe."""
        return self._order_df.copy()
    
    def set_order_id(self, order_id: int) -> None:
        """
        Set the next valid order ID.
        
        Args:
            order_id: Order ID
        """
        self._next_valid_order_id = order_id
        logger.debug(f"Set next valid order ID: {order_id}")
    
    def create_order(self) -> Order:
        """
        Create a new order object.
        
        Returns:
            New Order instance
        """
        self._order = Order()
        logger.debug("Created new order")
        return self._order
    
    def set_order_details(
        self,
        action: str,
        order_type: str,
        total_quantity: float,
        limit_price: Optional[float] = None,
        aux_price: Optional[float] = None,
        discretionary_amt: Optional[float] = None,
        trail_stop_price: Optional[float] = None,
    ) -> None:
        """
        Set order details.
        
        Args:
            action: BUY or SELL
            order_type: Order type (LMT, MKT, STP, TRAIL, etc.)
            total_quantity: Order quantity
            limit_price: Limit price (for limit orders)
            aux_price: Auxiliary price (for stop orders)
            discretionary_amt: Discretionary amount
            trail_stop_price: Trail stop price
        """
        if self._order is None:
            raise OrderError("Order must be created before setting details")
        
        self._order.action = action
        self._order.orderType = order_type
        self._order.totalQuantity = total_quantity
        
        if limit_price is not None:
            self._order.lmtPrice = limit_price
        if aux_price is not None:
            self._order.auxPrice = aux_price
        if discretionary_amt is not None:
            self._order.discretionaryAmt = discretionary_amt
        if trail_stop_price is not None:
            self._order.trailStopPrice = trail_stop_price
        
        logger.debug(f"Set order details: {action} {total_quantity} {order_type}")
    
    def set_order_details_from_dict(self, order_dict: Dict[str, Any]) -> None:
        """
        Set order details from dictionary.
        
        Args:
            order_dict: Dictionary with order details
        """
        self.set_order_details(
            action=order_dict.get("action", ""),
            order_type=order_dict.get("orderType", ""),
            total_quantity=order_dict.get("orderTotalQuantity", 0),
            limit_price=order_dict.get("orderLmtPrice"),
            aux_price=order_dict.get("orderAuxPrice"),
            discretionary_amt=order_dict.get("orderDiscretionaryAmt"),
            trail_stop_price=order_dict.get("orderTrailStopPrice"),
        )
    
    def create_order_cancel(self) -> OrderCancel:
        """
        Create an order cancellation object.
        
        Returns:
            OrderCancel instance
        """
        return OrderCancel()
    
    def track_order(
        self,
        order_id: int,
        contract_symbol: str,
        sec_type: str,
        exchange: str,
        action: str,
        order_type: str,
        total_qty: float,
        cash_qty: Optional[float] = None,
        last_price: Optional[float] = None,
        aux_price: Optional[float] = None,
        status: Optional[str] = None,
        perm_id: Optional[int] = None,
        client_id: Optional[int] = None,
        account: Optional[str] = None,
    ) -> None:
        """
        Track an order in the dataframe.
        
        Args:
            order_id: Order ID
            contract_symbol: Contract symbol
            sec_type: Security type
            exchange: Exchange
            action: BUY or SELL
            order_type: Order type
            total_qty: Total quantity
            cash_qty: Cash quantity
            last_price: Last price
            aux_price: Auxiliary price
            status: Order status
            perm_id: Permanent ID
            client_id: Client ID
            account: Account number
        """
        order_dict = {
            "PermId": perm_id,
            "ClientId": client_id,
            "OrderId": order_id,
            "Account": account,
            "Symbol": contract_symbol,
            "SecType": sec_type,
            "Exchange": exchange,
            "Action": action,
            "OrderType": order_type,
            "TotalQty": total_qty,
            "CashQty": cash_qty,
            "LastPrice": last_price,
            "AuxPrice": aux_price,
            "Status": status,
        }
        
        # Use concat instead of deprecated append
        self._order_df = pd.concat(
            [self._order_df, pd.DataFrame([order_dict])],
            ignore_index=True
        )
        logger.debug(f"Tracked order {order_id} for {contract_symbol}")
