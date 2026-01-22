import unittest
from unittest.mock import MagicMock
from ibapi.contract import Contract
from order_management.orders import OrderManagement


class TestOrderManagement(unittest.TestCase):
    def setUp(self):
        self.order_manager = OrderManagement()
        self.order_manager.nextValidOrderId = 1  # Simulate a valid order ID

    def test_set_order(self):
        """Test order creation."""
        self.order_manager.setOrder()
        self.assertIsNotNone(self.order_manager.order)

    def test_set_order_details(self):
        """Test setting order details."""
        self.order_manager.setOrder()
        self.order_manager.setOrderDetails("BUY", "LMT", 10, 150.00, 0.0, 0.0, 0.0)

        self.assertEqual(self.order_manager.order.action, "BUY")
        self.assertEqual(self.order_manager.order.orderType, "LMT")
        self.assertEqual(self.order_manager.order.totalQuantity, 10)
        self.assertEqual(self.order_manager.order.lmtPrice, 150.00)

    def test_set_order_id(self):
        """Test setting order ID."""
        self.order_manager.setOrderId(123)
        self.assertEqual(self.order_manager.nextValidOrderId, 123)

    def test_create_order_cancel(self):
        """Test order cancel creation."""
        order_cancel = self.order_manager.createOrderCancel()
        self.assertIsNotNone(order_cancel)


if __name__ == "__main__":
    unittest.main()
