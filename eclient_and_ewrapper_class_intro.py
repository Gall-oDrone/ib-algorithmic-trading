"""
IBAPI - Getting historical data intro

@author: Diego Gallo
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from tests.test_const_contracts import get_test_contract1, get_test_contract2, get_test_contract3, get_test_contract_facebook
from tests.test_const_orders import get_buy_limit_order_test1, get_buy_limit_order_test2, get_buy_market_order_test1, get_buy_stop_order_test1, get_buy_trail_stop_order_test1
from handlers.contract_handler import handleContract
from storage.dataframe import dataDataFrame
from order_management.orders import OrderManagement

import threading
import time

PAPER_TRADING_GATEWAY = 4002
PAPER_TRADING_TWS = 7497
CLIENT_ID = 1
CURRENT_PORT = PAPER_TRADING_TWS

class TradingApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = {}
        self.event = threading.Event()
        self.debug = False
        self.action = None
        self.orders = []
    
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        error_msg = f"Error {reqId} {errorCode} {errorString} {advancedOrderRejectJson}" if advancedOrderRejectJson else f"Error {reqId} {errorCode} {errorString}"
        print(error_msg)
    
    def contractDetails(self, reqId, contractDetails):
        print(f"reqID: {reqId}, contract: {contractDetails}")
    
    def historicalData(self, reqId, bar):
        bar_data = {"Date": bar.date, "Open": bar.open, "High": bar.high, "Low": bar.low, "Close": bar.close, "Volume": bar.volume}
        self.data.setdefault(reqId, []).append(bar_data)
        if self.debug: print(f"reqId: {reqId}, {bar_data}")
    
    def run_websocket(self):
        self.run()
        self.event.wait()
        if self.event.is_set():
            self.disconnect()

    def start_connection(self, host="127.0.0.1", port=7497, clientId=CLIENT_ID):
        self.connect(host, port, clientId)
        threading.Thread(target=self.run_websocket, daemon=True).start()
        time.sleep(5)
    
    def request_historical_data(self, req_num, contract, duration, candle_size):
        self.reqHistoricalData(
            reqId=req_num,
            contract=contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=candle_size,
            whatToShow="ADJUSTED_LAST",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )
    
    def fetch_stock_data(self, tickers=None):
        tickers = tickers or ["AMZN", "TSLA", "NVDA"]
        for i, ticker in enumerate(tickers):
            self.request_historical_data(i, handleContract(ticker), "1 D", "30 mins")    
            time.sleep(5)
    
    def fetch_index_data(self, indices=None):
        indices = indices or ["NDX"]
        for i, idx in enumerate(indices):
            if idx == "NDX":
                self.request_historical_data(i, handleContract("NDX", "IND", "USD", "NASDAQ"), "1 D", "30 mins")    
            time.sleep(5)
    
    def store_data(self, sec_type):
        print("Storing Data")
        if sec_type == 'idx':
            df = dataDataFrame(self, ["NDX"])
            if df:
                print(df)

    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        print("NextValidId:", orderId)

    def place_limitOrder(self, order, contract):
        order_mgmt = OrderManagement()
        order_mgmt.setOrder()
        orderId = self.nextValidOrderId
        order_mgmt.setOrderId(orderId)
        order_mgmt.setOrderDetails(order.get("action"),order.get("orderType"),order.get("orderTotalQuantity"),order.get("orderLmtPrice"),order.get("orderDiscretionaryAmt"))
        contract = handleContract(contract.get("symbol"),contract.get("sec"),contract.get("currency"),contract.get("exchange"))
        if order_mgmt.order and orderId is not None:
            self.placeOrder(orderId, contract, order_mgmt.order)
            print(f"Placing order ID {orderId} for {contract.symbol}\n")
            print(f"Order ID: {orderId} was placed sucessfully\n")
            self.orders.append(orderId)
            self.nextValidId(orderId)
        else:
            print("Order or next valid ID is not set!")

    def place_marketOrder(self, order, contract):
        order_mgmt = OrderManagement()
        order_mgmt.setOrder()
        orderId = self.nextValidOrderId
        order_mgmt.setOrderId(orderId)
        order_mgmt.setOrderDetails(order.get("action"),order.get("orderType"),order.get("orderTotalQuantity"),"","",order.get("orderDiscretionaryAmt"))
        contract_obj = handleContract(contract.get("symbol"),contract.get("sec"),contract.get("currency"),contract.get("exchange"))
        if order_mgmt.order and contract_obj and orderId is not None:
            self.placeOrder(orderId, contract_obj, order_mgmt.order)
            print(f"Placing order ID {orderId} for {contract_obj.symbol}\n")
            print(f"Order ID: {orderId} was placed sucessfully\n")
            self.orders.append(orderId)
            self.nextValidId(orderId)
        else:
            print("Order or next valid ID is not set!")
    
    def place_stopOrder(self, order, contract):
        order_mgmt = OrderManagement()
        order_mgmt.setOrder()
        orderId = self.nextValidOrderId
        order_mgmt.setOrderId(orderId)
        order_mgmt.setOrderDetails(order.get("action"),order.get("orderType"),order.get("orderTotalQuantity"),None,order.get("orderAuxPrice"),order.get("orderDiscretionaryAmt"))
        contract_obj = handleContract(contract.get("symbol"),contract.get("sec"),contract.get("currency"),contract.get("exchange"))
        if order_mgmt.order and contract_obj and orderId is not None:
            self.placeOrder(orderId, contract_obj, order_mgmt.order)
            print(f"Placing order ID {orderId} for {contract_obj.symbol}\n")
            print(f"Order ID: {orderId} was placed sucessfully\n")
            self.orders.append(orderId)
            self.nextValidId(orderId)
        else:
            print("Order or next valid ID is not set!")

    def cancelOrder(self, orderId, reason="Testing cancellation"):
        order_mgmt = OrderManagement()
        orderCancel = order_mgmt.createOrderCancel()
        self.cancelOrder(orderId=orderId, orderCancel=orderCancel)

    def place_trailStopOrder(self, order, contract):
        order_mgmt = OrderManagement()
        order_mgmt.setOrder()
        orderId = self.nextValidOrderId
        order_mgmt.setOrderId(orderId)
        order_mgmt.setOrderDetails(order.get("action"),order.get("orderType"),order.get("orderTotalQuantity"),None,order.get("orderTrailingStopPrice"),order.get("orderTrailingStop"),order.get("orderDiscretionaryAmt"))
        contract_obj = handleContract(contract.get("symbol"),contract.get("sec"),contract.get("currency"),contract.get("exchange"))
        if order_mgmt.order and contract_obj and orderId is not None:
            self.placeOrder(orderId, contract_obj, order_mgmt.order)
            print(f"Placing order ID {orderId} for {contract_obj.symbol}\n")
            print(f"Order ID: {orderId} was placed sucessfully\n")
            self.orders.append(orderId)
            self.nextValidId(orderId)
        else:
            print("Order or next valid ID is not set!")
        
    def timeout(self, startTime, maxLimit=60*5):
        return startTime + maxLimit

def main():
    app = TradingApp()
    app.start_connection()
    start_time = time.time()
    set_req_id = True
    fetch_data_test = False
    place_limit_order_test = False
    place_market_order_test = False
    place_stop_order_test = True
    cancel_order_test = False
    modify_order_test = False
    place_trail_stop_order_test = True
    app.event.set()
    while time.time() <= app.timeout(start_time):
        if fetch_data_test:
            app.fetch_index_data()
            app.store_data('idx')
        elif place_limit_order_test:
            order = get_buy_limit_order_test1()
            contract = get_test_contract1()
            app.place_limitOrder(order,contract)
        elif place_market_order_test:
            order = get_buy_market_order_test1()
            contract = get_test_contract2()
            app.place_marketOrder(order,contract)
        elif place_stop_order_test:
            order = get_buy_stop_order_test1()
            contract = get_test_contract3()
            app.place_stopOrder(order,contract)
        elif cancel_order_test:
            app.cancelOrder(app.orders[-1])
        elif modify_order_test:
                if set_req_id:
                    app.reqIds(-1)
                    time.sleep(3)
                orderId = app.nextValidOrderId
                order = get_buy_limit_order_test2()
                contract = get_test_contract2()
                app.place_limitrder(order,contract)
                app.cancelOrder(orderId)
        elif place_trail_stop_order_test:
            order = get_buy_trail_stop_order_test1()
            contract = get_test_contract_facebook()
            app.place_trailStopOrder(order,contract)
        time.sleep(30 - ((time.time()-start_time)%30))

if __name__ == "__main__":
    main()