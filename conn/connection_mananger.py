# connection_manager.py
class ConnectionManager:
    def __init__(self):
        self.event = threading.Event()
        
    def start_connection(self, host="127.0.0.1", port=7497, clientId=CLIENT_ID):
        # Connection logic here
        pass
        
    def run_websocket(self):
        # Websocket logic here
        pass

# historical_data_manager.py
class HistoricalDataManager:
    def __init__(self):
        self.data = {}
        
    def request_historical_data(self, req_num, contract, duration, candle_size):
        # Historical data request logic here
        pass
        
    def fetch_stock_data(self, tickers=None):
        # Stock data fetching logic here
        pass
        
    def fetch_index_data(self, indices=None):
        # Index data fetching logic here
        pass

# order_management.py
class OrderManagement:
    def __init__(self):
        self._order = None
        self._next_valid_order_id = None
        self._order_details = {}
        
    @property
    def order(self):
        return self._order
        
    def set_order(self):
        self._order = Order()
        
    def set_order_id(self, order_id):
        self._next_valid_order_id = order_id
        
    def set_order_details(self, action, order_type, quantity, limit_price, discretionary_amt):
        self._order_details = {
            'action': action,
            'orderType': order_type,
            'totalQuantity': quantity,
            'lmtPrice': limit_price,
            'discretionaryAmt': discretionary_amt
        }
        self._apply_order_details()
        
    def _apply_order_details(self):
        if self._order:
            for key, value in self._order_details.items():
                setattr(self._order, key, value)
                
    def create_order_cancel(self):
        return OrderCancel()

# Refactored main TradingApp
class TradingApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connection_manager = ConnectionManager()
        self.historical_data_manager = HistoricalDataManager()
        self.order_manager = OrderManagement()
        self.debug = False
        self.orders = []
        
    def place_limit_order(self, order, contract):
        self.order_manager.set_order()
        order_id = self.nextValidOrderId
        self.order_manager.set_order_id(order_id)
        
        self.order_manager.set_order_details(
            order.get("action"),
            order.get("orderType"),
            order.get("orderTotalQuantity"),
            order.get("orderLmtPrice"),
            order.get("orderDiscretionaryAmt")
        )
        
        contract = handleContract(
            contract.get("symbol"),
            contract.get("sec"),
            contract.get("currency"),
            contract.get("exchange")
        )
        
        if self.order_manager.order and order_id is not None:
            self.placeOrder(order_id, contract, self.order_manager.order)
            self.orders.append(order_id)
            self.nextValidId(order_id)
            return True
        return False