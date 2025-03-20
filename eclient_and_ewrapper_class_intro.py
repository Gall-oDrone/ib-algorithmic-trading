"""
IBAPI - Getting historical data intro

@author: Diego Gallo
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time

class TradingApp(EWrapper, EClient):
    def __init__(self, *args, **kwargs):
        EClient.__init__(self, self)
        self.data = {}

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        if advancedOrderRejectJson:
            print("Error {} {} {} {}".format(reqId,errorCode,errorString,advancedOrderRejectJson))
        else:
            print("Error {} {} {}".format(reqId,errorCode,errorString))

    def contractDetails(self, reqId, contractDetails):
        print("reqID:{}, contract:{}".format(reqId,contractDetails))

    def historicalData(self, reqId, bar):
        if reqId not in self.data:
            self.data[reqId] = [{"Date":bar.date,"Open":bar.open,"High":bar.high,"Low":bar.low,"Close":bar.close,"Volume":bar.volume}]
        if reqId in self.data:
            self.data[reqId].append({"Date":bar.date,"Open":bar.open,"High":bar.high,"Low":bar.low,"Close":bar.close,"Volume":bar.volume})
        
        print(f"reqId:{reqId}, date{bar.date}, open:{bar.open}, high:{bar.high}, low:{bar.low}, close:{bar.close}, volume:{bar.volume}")

def websocket_conn():
    app.run()
    event.wait()
    if event.is_set():
        app.close()

event = threading.Event()
app = TradingApp()
app.connect("127.0.0.1", 4002, clientId=0)

conn_thread = threading.Thread(target=websocket_conn)
conn_thread.start()
time.sleep(1)

def handleContract(symbol, sec_type="STK",currency="USD", exchange="ISLAND"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.currency = currency
    contract.exchange = exchange
    return contract

def handleHistData(req_num,contract,duration,candle_size):
    app.reqHistoricalData(
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

idx_contract = handleContract("NDX","IND","USD","NASDAQ")
tickers = ["AMZN", "TSLA", "NVDA"]

for ticker in tickers:
    handleHistData(tickers.index(ticker),handleContract(ticker),"1 D","30 mins")    
    time.sleep(5)
event.set()