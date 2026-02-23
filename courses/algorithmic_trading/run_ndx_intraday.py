"""NDX intraday strategy runner: fetch bars, run strategy, place/cancel orders based on signals."""

import json
import time
from typing import Any, Dict, Optional

import pandas as pd

from ibapi.contract import Contract

from utils import get_logger
from handlers.contract_handler import ContractHandler
from signals.ndx_intraday import NDXIntradayStrategy

logger = get_logger(__name__)

# #region agent log
_DEBUG_LOG = "/Users/diegogallovalenzuela/interactive-brokers/.cursor/debug-875a36.log"
def _debug_log(hypothesis_id: str, location: str, message: str, data: Dict[str, Any]) -> None:
    try:
        with open(_DEBUG_LOG, "a") as f:
            f.write(json.dumps({"sessionId": "875a36", "hypothesisId": hypothesis_id, "location": location, "message": message, "data": data, "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception:
        pass
# #endregion

# Default request ID for NDX intraday data
NDX_REQ_ID = 0

# Minimum bars required to run strategy
MIN_BARS = 50


def _build_ohlc_df_from_tws_data(data: list) -> pd.DataFrame:
    """Build OHLC DataFrame with Date index from TWS historical data list."""
    df = pd.DataFrame(data)
    if not df.empty and "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(
                df["Date"], format="%Y%m%d %H:%M:%S %Z"
            )
        except Exception:
            try:
                df["Date"] = pd.to_datetime(
                    df["Date"], format="%Y%m%d %H:%M:%S"
                )
            except Exception:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date").reset_index(drop=True)
        df = df.set_index("Date")
    return df


def run_ndx_intraday_iteration(
    app: Any,
    contract: Contract,
    state: Dict[str, Any],
    quantity: float = 1.0,
    bar_size: str = "5 mins",
    duration: str = "1 W",
) -> bool:
    """
    Run one iteration: fetch NDX intraday data, run strategy, act on signal changes.

    State dict: last_signal in {-1, 0, 1}, stop_order_id (protective stop when long or short).

    Long: 0->1 place market BUY, place stop SELL; 1->0 cancel stop, place market SELL.
    Short: 0->-1 place market SELL (open short), place stop BUY (cover stop); -1->0 cancel stop, place market BUY (cover).
    """
    data_handler = app.data_handler
    data_handler.clear_data(NDX_REQ_ID)
    data_handler.register_request(NDX_REQ_ID, "NDX")
    app.request_historical_data(
        NDX_REQ_ID,
        contract,
        duration=duration,
        bar_size=bar_size,
        what_to_show="TRADES",
        use_rth=True,
    )
    time.sleep(12)
    data = data_handler.get_data(NDX_REQ_ID)
    # #region agent log
    _debug_log("H2", "run_ndx_intraday.py:data_after_fetch", "Data after fetch", {"data_len": len(data) if data else 0, "contract": getattr(contract, "symbol", "")})
    # #endregion
    if not data:
        logger.warning("No NDX data received")
        return False
    df = _build_ohlc_df_from_tws_data(data)
    has_ohlc = "Open" in df.columns and "Close" in df.columns
    n_bars = len(df)
    # #region agent log
    _debug_log("H2", "run_ndx_intraday.py:df_after_build", "DataFrame after build", {"n_bars": n_bars, "has_ohlc": has_ohlc, "columns": list(df.columns) if not df.empty else []})
    # #endregion
    if not has_ohlc:
        logger.warning("OHLC columns missing in NDX data")
        return False
    if n_bars < MIN_BARS:
        logger.warning(f"Insufficient NDX data: {n_bars} bars (need {MIN_BARS})")
        return False

    strategy = NDXIntradayStrategy()
    result = strategy.generate(df, include_stop_levels=True)
    signal = result["signal"]
    stop_level = result["stop_level"]
    n = len(signal)
    prev_signal = int(signal.iloc[-2]) if n >= 2 else 0
    curr_signal = int(signal.iloc[-1])
    last_signal = state.get("last_signal")
    stop_order_id = state.get("stop_order_id")
    # #region agent log
    _debug_log("H1", "run_ndx_intraday.py:signals", "Signal state", {"prev_signal": prev_signal, "curr_signal": curr_signal, "last_signal": last_signal, "n_bars": n})
    _debug_log("H3", "run_ndx_intraday.py:first_run", "First run check", {"last_signal_is_none": last_signal is None})
    # #endregion

    # First run: sync state or act on transition from prev_signal -> curr_signal
    if last_signal is None:
        state["last_signal"] = curr_signal
        if curr_signal == 1 and prev_signal == 0:
            # #region agent log
            _debug_log("H4", "run_ndx_intraday.py:branch", "Order branch entered", {"branch": "first_0_to_1_long", "action": "BUY+stop"})
            # #endregion
            logger.info("NDX intraday: 0->1 LONG, placing BUY and protective stop SELL")
            app.place_market_order(contract, "BUY", quantity)
            stop_price = float(stop_level.iloc[-1])
            if pd.notna(stop_price) and stop_price > 0:
                oid = app.place_stop_order(contract, "SELL", quantity, stop_price)
                state["stop_order_id"] = oid
            else:
                state["stop_order_id"] = None
        elif curr_signal == -1 and prev_signal == 0:
            # #region agent log
            _debug_log("H4", "run_ndx_intraday.py:branch", "Order branch entered", {"branch": "first_0_to_minus1_short", "action": "SELL+stop"})
            # #endregion
            logger.info("NDX intraday: 0->-1 SHORT, placing SELL (open short) and protective stop BUY")
            app.place_market_order(contract, "SELL", quantity)
            stop_price = float(stop_level.iloc[-1])
            if pd.notna(stop_price) and stop_price > 0:
                oid = app.place_stop_order(contract, "BUY", quantity, stop_price)
                state["stop_order_id"] = oid
            else:
                state["stop_order_id"] = None
        elif curr_signal == 0 and prev_signal == 1:
            logger.info("NDX intraday: 1->0 exit long, placing SELL")
            app.place_market_order(contract, "SELL", quantity)
            state["stop_order_id"] = None
        elif curr_signal == 0 and prev_signal == -1:
            logger.info("NDX intraday: -1->0 exit short, placing BUY (cover)")
            app.place_market_order(contract, "BUY", quantity)
            state["stop_order_id"] = None
        return True

    # Long: 0->1 enter, 1->0 exit
    if curr_signal == 1 and last_signal == 0:
        # #region agent log
        _debug_log("H4", "run_ndx_intraday.py:branch", "Order branch entered", {"branch": "0_to_1_long", "action": "BUY+stop"})
        # #endregion
        logger.info("NDX intraday: BUY signal, placing market BUY and protective stop SELL")
        app.place_market_order(contract, "BUY", quantity)
        stop_price = float(stop_level.iloc[-1])
        if pd.notna(stop_price) and stop_price > 0:
            oid = app.place_stop_order(contract, "SELL", quantity, stop_price)
            state["stop_order_id"] = oid
        else:
            state["stop_order_id"] = None
    elif curr_signal == 0 and last_signal == 1:
        logger.info("NDX intraday: exit long, cancelling stop and placing market SELL")
        if stop_order_id is not None:
            try:
                app.cancel_order(stop_order_id)
            except Exception as e:
                logger.warning(f"Cancel stop order {stop_order_id} failed: {e}")
            state["stop_order_id"] = None
        app.place_market_order(contract, "SELL", quantity)

    # Short: 0->-1 enter, -1->0 exit
    elif curr_signal == -1 and last_signal == 0:
        # #region agent log
        _debug_log("H4", "run_ndx_intraday.py:branch", "Order branch entered", {"branch": "0_to_minus1_short", "action": "SELL+stop"})
        # #endregion
        logger.info("NDX intraday: SHORT signal, placing market SELL (open short) and protective stop BUY")
        app.place_market_order(contract, "SELL", quantity)
        stop_price = float(stop_level.iloc[-1])
        if pd.notna(stop_price) and stop_price > 0:
            oid = app.place_stop_order(contract, "BUY", quantity, stop_price)
            state["stop_order_id"] = oid
        else:
            state["stop_order_id"] = None
    elif curr_signal == 0 and last_signal == -1:
        logger.info("NDX intraday: exit short, cancelling stop and placing market BUY (cover)")
        if stop_order_id is not None:
            try:
                app.cancel_order(stop_order_id)
            except Exception as e:
                logger.warning(f"Cancel stop order {stop_order_id} failed: {e}")
            state["stop_order_id"] = None
        app.place_market_order(contract, "BUY", quantity)

    state["last_signal"] = curr_signal
    return True


def run_ndx_intraday_loop(
    app: Any,
    contract_handler: ContractHandler,
    quantity: float = 1.0,
    bar_size: str = "5 mins",
    duration: str = "1 W",
    poll_seconds: int = 300,
    timeout_seconds: Optional[int] = None,
) -> None:
    """
    Run NDX intraday strategy in a loop: fetch data, run strategy, place/cancel orders, sleep, repeat.

    Args:
        app: TradingApp instance (connected).
        contract_handler: ContractHandler to create NDX contract.
        quantity: Order quantity.
        bar_size: Bar size (e.g. "5 mins", "15 mins").
        duration: Historical data duration (e.g. "1 W").
        poll_seconds: Seconds to wait between iterations.
        timeout_seconds: If set, stop after this many seconds; otherwise run until interrupted.
    """
    contract = contract_handler.create_contract(
        "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
    )
    # #region agent log
    _debug_log("H5", "run_ndx_intraday.py:loop_start", "Loop contract", {"symbol": getattr(contract, "symbol", ""), "secType": getattr(contract, "secType", "")})
    # #endregion
    state = {"last_signal": None, "stop_order_id": None}
    start = time.time()
    iteration = 0
    while True:
        iteration += 1
        if timeout_seconds is not None and (time.time() - start) >= timeout_seconds:
            logger.info("NDX intraday loop: timeout reached, stopping")
            break
        logger.info(f"NDX intraday iteration {iteration}")
        run_ndx_intraday_iteration(
            app, contract, state,
            quantity=quantity,
            bar_size=bar_size,
            duration=duration,
        )
        time.sleep(poll_seconds)
