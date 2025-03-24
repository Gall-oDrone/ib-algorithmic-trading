from ibapi.order import Oder
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

class OrderManagement(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        action = None
        orderType = None
        orderTotalQuantity = None
        orderLmtPrice = None
        orderDiscretionaryAmt = None
        order = self.Order()


    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        print("NextValidId:", orderId)

    def setOrderDetails(action,orderType,orderTotalQuantity,orderLmtPrice,orderDiscretionaryAmt):
        self.action = action
        self.orderType = orderType
        self.orderTotalQuantity = orderTotalQuantity
        self.orderLmtPrice = orderLmtPrice
        self.orderDiscretionaryAmt = orderDiscretionaryAmt
