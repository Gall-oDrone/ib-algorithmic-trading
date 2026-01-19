"""DataFrame constants and utilities for order management."""

import pandas as pd


def get_open_order_dataframe() -> pd.DataFrame:
    """
    Create and return an empty dataframe for tracking open orders.
    
    Returns:
        Empty DataFrame with order tracking columns
    """
    return pd.DataFrame(columns=[
        "PermId",
        "ClientId",
        "OrderId",
        "Account",
        "Symbol",
        "SecType",
        "Exchange",
        "Action",
        "OrderType",
        "TotalQty",
        "CashQty",
        "LastPrice",
        "AuxPrice",
        "Status",
    ])