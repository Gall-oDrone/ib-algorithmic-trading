from ibapi.order import Order
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.order_cancel import OrderCancel

class OrderManagement():
    def __init__(self):
        action = None
        orderType = None
        orderTotalQuantity = None
        orderLmtPrice = None
        orderAuxPrice = None
        orderDiscretionaryAmt = None
        orderTrailStopPrice = None
        order = None
        nextValidOrderId = None

    def setOrderId(self, oid):
        self.nextValidOrderId = oid
    def setOrder(self):
        self.order = Order()
        
    def setOrderDetails(self, action, orderType, orderTotalQuantity, orderLmtPrice, orderAuxPrice, orderDiscretionaryAmt, orderTrailStopPrice):
        self.order.action = action
        self.order.orderType = orderType
        self.order.totalQuantity = orderTotalQuantity
        self.order.lmtPrice = orderLmtPrice
        self.order.auxPrice = orderAuxPrice
        self.order.discretionaryAmt = orderDiscretionaryAmt
        self.order.trailStopPrice = orderTrailStopPrice

    def createOrderCancel(self):
        return OrderCancel()