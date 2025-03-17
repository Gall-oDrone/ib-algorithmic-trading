from ibapi.client import EClient
from ibapi.wrapper import EWrapper

class TradingApp(EWrapper, EClient):
    def __init__(self, *args, **kwargs):
        EClient.__init__(self, self)
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        print("Error {} {} {}".format(reqId,errorCode,errorString))

app = TradingApp()
app.connect("127.0.0.1", 4002, clientId=0)
app.run()