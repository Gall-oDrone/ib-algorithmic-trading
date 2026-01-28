from consts import orders

def get_buy_limit_order_test1():
    return orders.orders.get("buy").get("limit").get("test_1")

def get_buy_limit_order_test2():
    return orders.orders.get("buy").get("limit").get("test_2")

def get_buy_market_order_test1():
    return orders.orders.get("buy").get("market").get("test_1")

def get_buy_stop_order_test1():
    return orders.orders.get("buy").get("stop").get("test_1")

def get_sell_limit_order_test1():
    return orders.orders.get("sell").get("limit").get("test_1")

def get_sell_market_order_test1():
    return orders.orders.get("sell").get("market").get("test_1")

def get_buy_trail_stop_order_test1():
    return orders.orders.get("buy").get("trailStop").get("test_1")

