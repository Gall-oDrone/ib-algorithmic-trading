"""
IBAPI - Getting historical data intro

@author: Diego Gallo
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from handlers.ibapi import handleContract
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

    def place_limit_order(self):
        order_mgmt = OrderManagement()
        order_mgmt.setOrder()
        orderId = self.nextValidOrderId
        order_mgmt.setOrderId(orderId)
        order_mgmt.setOrderDetails("BUY","LMT",1,80,False)
        contract = handleContract("AAPL","STK","USD","SMART")
        if order_mgmt.order and orderId is not None:
            self.placeOrder(orderId, contract, order_mgmt.order)
            print(f"Placing order ID {orderId} for {contract.symbol}\n")
            print(f"Order ID: {orderId} was placed sucessfully\n")
            self.nextValidId(orderId)
        else:
            print("Order or next valid ID is not set!")
        nextValidOrderId = order_mgmt.place_order(self.nextValidId, contract)

    def cancelOrder(self, orderId):
        self.cancelOrder(orderId)
        
    def timeout(self, startTime, maxLimit=60*5):
        return startTime + maxLimit

def main():
    app = TradingApp()
    app.start_connection()
    start_time = time.time()
    fetch_data_test = False
    place_order_test = True
    app.event.set()
    while time.time() <= app.timeout(start_time):
        if fetch_data_test:
            app.fetch_index_data()
            app.store_data('idx')
        elif place_order_test:
            app.place_limit_order()
        time.sleep(30 - ((time.time()-start_time)%30))

if __name__ == "__main__":
    main()