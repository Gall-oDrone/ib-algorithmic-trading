from ibapi.order import Order
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

class OrderManagement():
    def __init__(self):
        action = None
        orderType = None
        orderTotalQuantity = None
        orderLmtPrice = None
        orderDiscretionaryAmt = None
        order = None
        nextValidOrderId = None

    def setOrder(self):
        self.order = Order()
        
    def setOrderDetails(self, action, orderType, orderTotalQuantity, orderLmtPrice, orderDiscretionaryAmt):
        self.order.action = action
        self.order.orderType = orderType
        self.order.totalQuantity = orderTotalQuantity
        self.order.lmtPrice = orderLmtPrice
        self.order.discretionaryAmt = orderDiscretionaryAmt