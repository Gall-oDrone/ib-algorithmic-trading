from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class TradingApp(EWrapper, EClient):
    def __init__(self, *args, **kwargs):
        EClient.__init__(self, self)
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        if advancedOrderRejectJson:
            print("Error {} {} {} {}".format(reqId,errorCode,errorString,advancedOrderRejectJson))
        else:
            print("Error {} {} {}".format(reqId,errorCode,errorString))

    def contractDetails(self, reqId, contractDetails):
        print(f"reqID:{reqId}, contract:{contractDetails}")

app = TradingApp()
app.connect("127.0.0.1", 4002, clientId=0)

contract = Contract()
contract.symbol = "NVDA"
contract.secType = "STK"
contract.currency = "USD"
contract.exchange = "SMART"

app.reqContractDetails(100, contract)
app.run()