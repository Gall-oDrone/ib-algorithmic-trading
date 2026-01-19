"""Order constants for testing and trading."""

from typing import Dict, Any


# Order definitions
ORDERS: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {
    "buy": {
        "limit": {
            "test_1": {
                "action": "BUY",
                "orderType": "LMT",
                "orderTotalQuantity": 1,
                "orderLmtPrice": 80,
                "orderDiscretionaryAmt": False,
            },
            "test_2": {
                "action": "BUY",
                "orderType": "LMT",
                "orderTotalQuantity": 2,
                "orderLmtPrice": 50,
                "orderDiscretionaryAmt": False,
            },
        },
        "market": {
            "test_1": {
                "action": "BUY",
                "orderType": "MKT",
                "orderTotalQuantity": 1,
                "orderDiscretionaryAmt": False,
            },
        },
        "stop": {
            "test_1": {
                "action": "BUY",
                "orderType": "STP",
                "orderTotalQuantity": 1,
                "orderAuxPrice": 40,
                "orderDiscretionaryAmt": False,
            },
        },
        "trailStop": {
            "test_1": {
                "action": "BUY",
                "orderType": "TRAIL",
                "orderTotalQuantity": 1,
                "orderAuxPrice": 40,
                "orderDiscretionaryAmt": False,
                "orderTrailStopPrice": 10,
                "orderTrailingStop": 1,
            },
        },
    },
    "sell": {
        "limit": {
            "test_1": {
                "action": "SELL",
                "orderType": "LMT",
                "orderTotalQuantity": 1,
                "orderLmtPrice": 80,
                "orderDiscretionaryAmt": False,
            },
        },
        "market": {
            "test_1": {
                "action": "SELL",
                "orderType": "MKT",
                "orderTotalQuantity": 1,
                "orderDiscretionaryAmt": False,
            },
        },
        "stop": {
            "test_1": {
                "action": "SELL",
                "orderType": "STP",
                "orderTotalQuantity": 1,
                "orderAuxPrice": 40,
                "orderDiscretionaryAmt": False,
            },
        },
    },
}


def get_orders() -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
    """
    Get all order definitions.
    
    Returns:
        Dictionary of order definitions
    """
    return ORDERS.copy()


def get_order(action: str, order_type: str, test_key: str) -> Dict[str, Any]:
    """
    Get a specific order by action, type, and test key.
    
    Args:
        action: Order action (buy/sell)
        order_type: Order type (limit/market/stop/trailStop)
        test_key: Test key (test_1, test_2, etc.)
        
    Returns:
        Order definition dictionary
    """
    return ORDERS.get(action, {}).get(order_type, {}).get(test_key, {})
