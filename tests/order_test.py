import unittest
from unittest.mock import MagicMock
from ibapi.contract import Contract
from order_management.orders import OrderManagement

class TestOrderManagement(unittest.TestCase):
    def setUp(self):
        self.order_manager = OrderManagement()
        self.order_manager.nextValidOrderId = 1  # Simulate a valid order ID
        self.order_manager.placeOrder = MagicMock()  # Mock placeOrder method

    def test_place_order(self):
        # Define a contract
        contract = Contract()
        contract.symbol = "AAPL"
        contract.secType = "STK"
        contract.currency = "USD"
        contract.exchange = "SMART"

        # Set order details
        self.order_manager.setOrderDetails("BUY", "LMT", 10, 150.00, 0.0)

        # Place order
        self.order_manager.place_order(contract)

        # Assertions
        self.order_manager.placeOrder.assert_called_once_with(1, contract, self.order_manager.order)
        self.assertEqual(self.order_manager.nextValidOrderId, 2)

if __name__ == "__main__":
    unittest.main()
