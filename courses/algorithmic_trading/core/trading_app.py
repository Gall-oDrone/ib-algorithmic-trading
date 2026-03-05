"""Main TradingApp class that integrates all components."""

import threading
import time
from typing import Dict, List, Optional, Any

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.common import BarData

from config import get_config
from core.connection_manager import ConnectionManager
from handlers.contract_handler import ContractHandler
from handlers.historical_data_handler import HistoricalDataHandler
from order_management.order_manager import OrderManager
from account_and_portfolio.account_manager import AccountManager
from account_and_portfolio.portfolio_manager import PortfolioManager
from storage.dataframe_manager import DataFrameManager
from exceptions import TradingAppError, ConnectionError, OrderError
from utils import get_logger

logger = get_logger(__name__)


class TradingApp(EWrapper, EClient):
    """Main trading application integrating IB API functionality."""
    
    def __init__(self):
        """Initialize trading application."""
        EClient.__init__(self, self)
        
        # Configuration
        self.config = get_config()
        
        # Core components
        self.connection_manager = ConnectionManager(self, self)
        self.contract_handler = ContractHandler()
        self.data_handler = HistoricalDataHandler()
        self.order_manager = OrderManager()
        self.account_manager = AccountManager()
        self.portfolio_manager = PortfolioManager()
        self.dataframe_manager = DataFrameManager(self.data_handler)
        
        # State
        self._next_valid_order_id: Optional[int] = None
        self._active_orders: Dict[int, Order] = {}
        self._debug = self.config.debug
        self._open_orders_event = threading.Event()
        self._positions_event = threading.Event()
        
    @property
    def debug(self) -> bool:
        """Get debug mode."""
        return self._debug
    
    @debug.setter
    def debug(self, value: bool) -> None:
        """Set debug mode."""
        self._debug = value
        logger.setLevel("DEBUG" if value else "INFO")
    
    def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[int] = None,
    ) -> None:
        """
        Connect to IB API.
        
        Args:
            host: Host address
            port: Port number
            client_id: Client ID
        """
        self.connection_manager.connect(host, port, client_id)
    
    def disconnect(self) -> None:
        """Disconnect from IB API."""
        self.connection_manager.disconnect()
    
    # EWrapper callbacks
    
    def error(
        self,
        req_id: int,
        error_code: int,
        error_string: str,
        advanced_order_reject_json: str = "",
    ) -> None:
        """
        Handle errors from IB API.
        
        Args:
            req_id: Request ID
            error_code: Error code
            error_string: Error message
            advanced_order_reject_json: Additional error info
        """
        error_msg = (
            f"Error {req_id} {error_code}: {error_string}"
            if not advanced_order_reject_json
            else f"Error {req_id} {error_code}: {error_string} {advanced_order_reject_json}"
        )
        logger.error(error_msg)
    
    def nextValidId(self, order_id: int) -> None:
        """
        Callback when next valid order ID is received.
        
        Args:
            order_id: Next valid order ID
        """
        super().nextValidId(order_id)
        self._next_valid_order_id = order_id
        self.order_manager.set_order_id(order_id)
        logger.info(f"Next valid order ID: {order_id}")
    
    def contractDetails(self, req_id: int, contract_details) -> None:
        """
        Callback for contract details.
        
        Args:
            req_id: Request ID
            contract_details: Contract details
        """
        logger.debug(f"Contract details for req_id {req_id}: {contract_details}")
    
    def historicalData(self, req_id: int, bar: BarData) -> None:
        """
        Callback for historical data bars.
        
        Args:
            req_id: Request ID
            bar: Bar data
        """
        self.data_handler.add_bar(req_id, bar)
        if self._debug:
            logger.debug(f"Received bar for req_id {req_id}: {bar.date}")
    
    def historicalDataEnd(self, req_id: int, start: str, end: str) -> None:
        """
        Callback when historical data request completes.
        
        Args:
            req_id: Request ID
            start: Start date
            end: End date
        """
        logger.info(f"Historical data request {req_id} completed: {start} to {end}")
    
    def openOrder(
        self,
        order_id: int,
        contract: Contract,
        order: Order,
        order_state: OrderState,
    ) -> None:
        """
        Callback for open orders.
        
        Args:
            order_id: Order ID
            contract: Contract
            order: Order object
            order_state: Order state
        """
        super().openOrder(order_id, contract, order, order_state)
        self._active_orders[order_id] = order
        
        self.order_manager.track_order(
            order_id=order_id,
            contract_symbol=contract.symbol,
            sec_type=contract.secType,
            exchange=contract.exchange or "",
            action=order.action,
            order_type=order.orderType,
            total_qty=order.totalQuantity,
            cash_qty=order.cashQty if hasattr(order, "cashQty") else None,
            last_price=order.lastPrice if hasattr(order, "lastPrice") else None,
            aux_price=order.auxPrice if hasattr(order, "auxPrice") else None,
            status=order_state.status,
            perm_id=order.permId if hasattr(order, "permId") else None,
            client_id=order.clientId if hasattr(order, "clientId") else None,
            account=order.account if hasattr(order, "account") else None,
        )
        logger.debug(f"Open order {order_id}: {contract.symbol} {order.action} {order.totalQuantity}")
    
    def position(
        self,
        account: str,
        contract: Contract,
        position: float,
        avg_cost: float,
    ) -> None:
        """
        Callback for position updates.
        
        Args:
            account: Account number
            contract: Contract
            position: Position size
            avg_cost: Average cost
        """
        super().position(account, contract, position, avg_cost)
        self.portfolio_manager.add_position(account, contract, position, avg_cost)
        logger.debug(f"Position update: {account} {contract.symbol} = {position}")

    def openOrderEnd(self) -> None:
        """Callback when all open orders have been delivered."""
        super().openOrderEnd()
        self._open_orders_event.set()
        logger.debug("Open orders list complete")

    def positionEnd(self) -> None:
        """Callback when all positions have been delivered."""
        super().positionEnd()
        self._positions_event.set()
        logger.debug("Positions list complete")

    # Historical data methods
    
    def request_historical_data(
        self,
        req_id: int,
        contract: Contract,
        duration: str = "1 D",
        bar_size: str = "30 mins",
        what_to_show: str = "ADJUSTED_LAST",
        use_rth: bool = True,
        keep_up_to_date: bool = False,
    ) -> None:
        """
        Request historical data.
        
        Args:
            req_id: Request ID
            contract: Contract to request data for
            duration: Duration string (e.g., "1 D")
            bar_size: Bar size (e.g., "30 mins")
            what_to_show: What to show (e.g., "ADJUSTED_LAST")
            use_rth: Use regular trading hours only
            keep_up_to_date: Keep data updated
        """
        if not self.connection_manager.is_connected:
            raise ConnectionError("Not connected to IB API")
        
        self.data_handler.register_request(req_id, contract.symbol)
        
        self.reqHistoricalData(
            reqId=req_id,
            contract=contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=1 if use_rth else 0,
            formatDate=1,
            keepUpToDate=keep_up_to_date,
            chartOptions=[],
        )
        logger.info(f"Requested historical data for {contract.symbol} (req_id: {req_id})")
    
    def fetch_stock_data(
        self,
        tickers: Optional[List[str]] = None,
        duration: str = "1 D",
        bar_size: str = "30 mins",
    ) -> None:
        """
        Fetch historical data for multiple stocks.
        
        Args:
            tickers: List of ticker symbols
            duration: Duration string
            bar_size: Bar size
        """
        tickers = tickers or ["AMZN", "TSLA", "NVDA"]
        
        for i, ticker in enumerate(tickers):
            contract = self.contract_handler.create_contract(ticker)
            self.request_historical_data(i, contract, duration, bar_size)
            time.sleep(2)  # Small delay between requests
    
    def fetch_index_data(
        self,
        indices: Optional[List[str]] = None,
        duration: str = "1 D",
        bar_size: str = "30 mins",
    ) -> None:
        """
        Fetch historical data for indices.
        
        Args:
            indices: List of index symbols
            duration: Duration string
            bar_size: Bar size
        """
        indices = indices or ["NDX"]
        
        for i, idx in enumerate(indices):
            if idx == "NDX":
                contract = self.contract_handler.create_contract(
                    "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
                )
                self.request_historical_data(i, contract, duration, bar_size)
                time.sleep(2)
    
    def get_historical_dataframes(
        self,
        tickers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get historical data as DataFrames.
        
        Args:
            tickers: List of tickers (optional)
            
        Returns:
            Dictionary mapping tickers to DataFrames
        """
        return self.dataframe_manager.create_dataframes(tickers=tickers)
    
    # Order methods
    
    def place_order(
        self,
        contract: Contract,
        order: Order,
        order_id: Optional[int] = None,
    ) -> int:
        """
        Place an order.
        
        Args:
            contract: Contract to trade
            order: Order object
            order_id: Optional order ID (uses next valid if not provided)
            
        Returns:
            Order ID
            
        Raises:
            OrderError: If order cannot be placed
        """
        if not self.connection_manager.is_connected:
            raise ConnectionError("Not connected to IB API")
        
        if order_id is None:
            if self._next_valid_order_id is None:
                raise OrderError("No valid order ID available")
            order_id = self._next_valid_order_id
        
        if not self.contract_handler.validate_contract(contract):
            raise OrderError(f"Invalid contract: {contract.symbol}")
        
        self.placeOrder(order_id, contract, order)
        logger.info(f"Placed order {order_id}: {contract.symbol} {order.action} {order.totalQuantity} {order.orderType}")
        
        return order_id
    
    def place_limit_order(
        self,
        contract: Contract,
        action: str,
        quantity: float,
        limit_price: float,
    ) -> int:
        """
        Place a limit order.
        
        Args:
            contract: Contract to trade
            action: BUY or SELL
            quantity: Order quantity
            limit_price: Limit price
            
        Returns:
            Order ID
        """
        self.order_manager.create_order()
        self.order_manager.set_order_details(
            action=action,
            order_type="LMT",
            total_quantity=quantity,
            limit_price=limit_price,
        )
        return self.place_order(contract, self.order_manager.order)
    
    def place_market_order(
        self,
        contract: Contract,
        action: str,
        quantity: float,
    ) -> int:
        """
        Place a market order.
        
        Args:
            contract: Contract to trade
            action: BUY or SELL
            quantity: Order quantity
            
        Returns:
            Order ID
        """
        self.order_manager.create_order()
        self.order_manager.set_order_details(
            action=action,
            order_type="MKT",
            total_quantity=quantity,
        )
        return self.place_order(contract, self.order_manager.order)
    
    def place_stop_order(
        self,
        contract: Contract,
        action: str,
        quantity: float,
        stop_price: float,
    ) -> int:
        """
        Place a stop order (STP). Trigger price is aux_price.
        
        Args:
            contract: Contract to trade
            action: BUY or SELL
            quantity: Order quantity
            stop_price: Stop trigger price (aux_price)
            
        Returns:
            Order ID
        """
        self.order_manager.create_order()
        self.order_manager.set_order_details(
            action=action,
            order_type="STP",
            total_quantity=quantity,
            aux_price=stop_price,
        )
        return self.place_order(contract, self.order_manager.order)
    
    def place_trailing_stop_order(
        self,
        contract: Contract,
        action: str,
        quantity: float,
        trail_stop_price: float,
        aux_price: Optional[float] = None,
    ) -> int:
        """
        Place a trailing stop order (TRAIL).
        
        Args:
            contract: Contract to trade
            action: BUY or SELL
            quantity: Order quantity
            trail_stop_price: Trailing stop price
            aux_price: Optional auxiliary price
            
        Returns:
            Order ID
        """
        self.order_manager.create_order()
        self.order_manager.set_order_details(
            action=action,
            order_type="TRAIL",
            total_quantity=quantity,
            aux_price=aux_price,
            trail_stop_price=trail_stop_price,
        )
        return self.place_order(contract, self.order_manager.order)
    
    def modify_order(
        self,
        order_id: int,
        contract: Contract,
        order: Order,
    ) -> None:
        """
        Modify an existing order by re-placing with the same order ID.
        
        Args:
            order_id: Existing order ID to modify
            contract: Contract
            order: Order with updated details
        """
        if not self.connection_manager.is_connected:
            raise ConnectionError("Not connected to IB API")
        if not self.contract_handler.validate_contract(contract):
            raise OrderError(f"Invalid contract: {contract.symbol}")
        self.placeOrder(order_id, contract, order)
        logger.info(f"Modified order {order_id}: {contract.symbol} {order.action} {order.totalQuantity} {order.orderType}")
    
    def cancel_order(self, order_id: int) -> None:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
        """
        if not self.connection_manager.is_connected:
            raise ConnectionError("Not connected to IB API")

        order_cancel = self.order_manager.create_order_cancel()
        self.cancelOrder(order_id, orderCancel=order_cancel)
        logger.info(f"Cancelled order {order_id}")

    def cancel_all_open_orders(self, timeout_sec: float = 10.0) -> List[int]:
        """
        Request open orders from TWS, then cancel each one.

        Args:
            timeout_sec: Max seconds to wait for open orders list.

        Returns:
            List of order IDs that were sent cancel requests.

        Raises:
            ConnectionError: If not connected.
        """
        if not self.connection_manager.is_connected:
            raise ConnectionError("Not connected to IB API")

        self._open_orders_event.clear()
        self.reqOpenOrders()
        if not self._open_orders_event.wait(timeout=timeout_sec):
            logger.warning("Timeout waiting for open orders list")
        order_ids = list(self._active_orders.keys())
        for oid in order_ids:
            try:
                self.cancel_order(oid)
            except Exception as e:
                logger.warning("Failed to cancel order %s: %s", oid, e)
        logger.info("Cancel-all sent for %d open orders", len(order_ids))
        return order_ids

    def close_all_positions(self, timeout_sec: float = 10.0) -> List[Dict[str, Any]]:
        """
        Request positions from TWS, then place market orders to flatten each.

        Args:
            timeout_sec: Max seconds to wait for positions list.

        Returns:
            List of dicts with symbol, position, action (BUY/SELL), quantity for each closed position.

        Raises:
            ConnectionError: If not connected.
        """
        if not self.connection_manager.is_connected:
            raise ConnectionError("Not connected to IB API")

        self.portfolio_manager.clear_positions()
        self._positions_event.clear()
        self.reqPositions()
        if not self._positions_event.wait(timeout=timeout_sec):
            logger.warning("Timeout waiting for positions list")
        positions_df = self.portfolio_manager.get_positions()
        closed = []
        for _, row in positions_df.iterrows():
            pos = float(row["Position"])
            if pos == 0:
                continue
            symbol = str(row["Symbol"])
            sec_type = str(row["SecType"])
            currency = str(row["Currency"])
            exchange = "NASDAQ" if sec_type == "IND" else "SMART"
            contract = self.contract_handler.create_contract(
                symbol=symbol, sec_type=sec_type, currency=currency, exchange=exchange
            )
            action = "SELL" if pos > 0 else "BUY"
            qty = abs(pos)
            try:
                self.place_market_order(contract, action, qty)
                closed.append({"symbol": symbol, "position": pos, "action": action, "quantity": qty})
                time.sleep(0.5)  # Allow TWS to send next valid order ID before next order
            except Exception as e:
                logger.warning("Failed to close position %s: %s", symbol, e)
        logger.info("Close-all sent for %d positions", len(closed))
        return closed

    # Account methods
    
    def request_account_summary(
        self,
        req_id: int,
        account: str = "All",
        tag: str = "$LEDGER:ALL",
    ) -> None:
        """
        Request account summary.
        
        Args:
            req_id: Request ID
            account: Account number or "All"
            tag: Summary tags
        """
        if not self.connection_manager.is_connected:
            raise ConnectionError("Not connected to IB API")
        
        self.reqAccountSummary(req_id, account, tag)
        logger.info(f"Requested account summary for {account}")
    
    def request_pnl(
        self,
        req_id: int,
        account: str,
    ) -> None:
        """
        Request P&L data.
        
        Args:
            req_id: Request ID
            account: Account number
        """
        if not self.connection_manager.is_connected:
            raise ConnectionError("Not connected to IB API")
        
        self.reqPnL(req_id, account, "")
        logger.info(f"Requested P&L for account {account}")
    
    def get_account_summary(self):
        """Get account summary DataFrame."""
        return self.account_manager.get_account_summary()
    
    def get_pnl(self):
        """Get P&L DataFrame."""
        return self.account_manager.get_pnl()
    
    def get_positions(self):
        """Get positions DataFrame."""
        return self.portfolio_manager.get_positions()
