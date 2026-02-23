"""Backtest runner: convert signal series + OHLC into trade returns and optional equity curve.

Convention: signal at bar t means position held at end of bar t (1=long, 0=flat).
- When signal goes 0 -> 1: we enter long at the next bar's open (open of bar t+1).
- When signal goes 1 -> 0: we exit at the next bar's open (open of bar t+1).
So we are long during bars where signal[t-1] was 1 (entered at open of bar t).
Per-trade return = (exit_price - entry_price) / entry_price (decimal).
Optional stop_price series: if bar's low <= stop_price, exit at stop_price that bar.
"""

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from utils import get_logger

logger = get_logger(__name__)

# Default OHLC column names
DEFAULT_OPEN_COL = "Open"
DEFAULT_CLOSE_COL = "Close"
DEFAULT_LOW_COL = "Low"


def run_backtest(
    data: pd.DataFrame,
    signal: pd.Series,
    *,
    open_col: str = DEFAULT_OPEN_COL,
    close_col: str = DEFAULT_CLOSE_COL,
    low_col: str = DEFAULT_LOW_COL,
    stop_price: Optional[pd.Series] = None,
) -> Tuple[List[float], pd.Series]:
    """
    Compute trade returns and equity curve from OHLC and a long/flat signal series.

    Convention: signal[t] = 1 means we are long at end of bar t. Entry/exit happen
    at the open of the bar after the signal change (so we enter at open of bar t+1
    when signal goes 0->1 at bar t, and exit at open of bar t+1 when signal goes 1->0
    at bar t). If stop_price is provided, within each long period we exit at stop_price
    when the bar's low <= stop_price (stop hit), and record that trade return.

    Args:
        data: DataFrame with Open, Close and same index as signal; Low required if stop_price given.
        signal: Series with same index as data; 1 = long, 0 = flat.
        open_col: Column name for open prices.
        close_col: Column name for close prices (used only for final bar if still long).
        low_col: Column name for low prices (used only when stop_price is provided).
        stop_price: Optional series, same index as data; when long, exit at this price if low <= stop_price.

    Returns:
        trade_returns: List of per-trade decimal returns (e.g. 0.02 = 2%).
        equity_curve: Series of cumulative equity (1.0 at start, then product of
            (1 + r) for each completed trade; same length as data, index aligned).
    """
    if open_col not in data.columns:
        raise ValueError(f"Column '{open_col}' not found in DataFrame")
    if close_col not in data.columns:
        raise ValueError(f"Column '{close_col}' not found in DataFrame")
    if not data.index.equals(signal.index):
        raise ValueError("data and signal must have the same index")
    if stop_price is not None:
        if not data.index.equals(stop_price.index):
            raise ValueError("data and stop_price must have the same index")
        if low_col not in data.columns:
            raise ValueError(f"Column '{low_col}' not found in DataFrame (required when stop_price is provided)")

    opens = data[open_col].values
    closes = data[close_col].values
    sig = np.asarray(signal, dtype=np.int64).ravel()
    n = len(data)
    lows = data[low_col].values if stop_price is not None else None
    stop_arr = stop_price.values if stop_price is not None else None

    trade_returns: List[float] = []
    equity = np.ones(n, dtype=float)
    current_equity = 1.0
    entry_price: Optional[float] = None

    for i in range(1, n):
        prev_sig = sig[i - 1]
        curr_sig = sig[i]

        # If we're long, check stop first (same bar: did low hit stop?)
        if entry_price is not None and stop_arr is not None and lows is not None:
            stop_val = stop_arr[i]
            if np.isfinite(stop_val) and float(lows[i]) <= stop_val:
                exit_price = stop_val
                r = (exit_price - entry_price) / entry_price
                trade_returns.append(r)
                current_equity *= 1.0 + r
                entry_price = None
                equity[i] = current_equity
                continue

        if prev_sig == 0 and curr_sig == 1:
            # Enter long at open of bar i
            entry_price = float(opens[i])
        elif prev_sig == 1 and curr_sig == 0:
            # Exit at open of bar i (signal exit)
            if entry_price is not None and entry_price != 0:
                exit_price = float(opens[i])
                r = (exit_price - entry_price) / entry_price
                trade_returns.append(r)
                current_equity *= 1.0 + r
            entry_price = None

        equity[i] = current_equity
    # If still long at end, close at last bar's close
    if entry_price is not None and n > 0:
        exit_price = float(closes[-1])
        r = (exit_price - entry_price) / entry_price
        trade_returns.append(r)
        current_equity *= 1.0 + r
        equity[-1] = current_equity

    equity_series = pd.Series(equity, index=data.index)
    return trade_returns, equity_series


def trade_returns_from_backtest(
    data: pd.DataFrame,
    signal: pd.Series,
    *,
    open_col: str = DEFAULT_OPEN_COL,
    close_col: str = DEFAULT_CLOSE_COL,
    low_col: str = DEFAULT_LOW_COL,
    stop_price: Optional[pd.Series] = None,
) -> List[float]:
    """
    Return only the list of per-trade decimal returns from the backtest.

    Same convention as run_backtest. Convenience when only trade returns are needed
    (e.g. for IntradayTradeMetrics).
    """
    returns, _ = run_backtest(
        data, signal,
        open_col=open_col,
        close_col=close_col,
        low_col=low_col,
        stop_price=stop_price,
    )
    return returns
