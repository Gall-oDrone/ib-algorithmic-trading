"""Tests for NDX intraday signal strategy (MACD + Stochastic + ATR stop levels) and backtest with stops."""

import json
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# #region agent log
_DEBUG_LOG = "/Users/diegogallovalenzuela/interactive-brokers/.cursor/debug-875a36.log"
def _debug_log(hypothesis_id, location, message, data):
    try:
        with open(_DEBUG_LOG, "a") as f:
            f.write(json.dumps({"sessionId": "875a36", "hypothesisId": hypothesis_id, "location": location, "message": message, "data": data, "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception:
        pass
# #endregion

parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from signals import (
    NDXIntradayStrategy,
    generate_ndx_intraday_signal,
)
from backtesting.runner import run_backtest, trade_returns_from_backtest
from backtesting.metrics import IntradayTradeMetrics

try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.common import BarData
    from handlers.historical_data_handler import HistoricalDataHandler
    from handlers.contract_handler import ContractHandler
    from config import get_config
    IBAPI_AVAILABLE = True
except ImportError:
    IBAPI_AVAILABLE = False

INTRADAY_BAR_SIZES = [
    ("5 mins", "5min"),
    ("15 mins", "15min"),
    ("1 hour", "1hour"),
]


@pytest.fixture
def synthetic_ohlc_rising_falling():
    """Synthetic OHLC: rise then fall to trigger MACD/Stochastic crossovers."""
    n = 120
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    np.random.seed(42)
    trend = np.concatenate([
        np.linspace(0, 15, n // 2),
        np.linspace(15, -5, n - n // 2),
    ])
    close = 100 + np.cumsum(trend + np.random.randn(n) * 0.3)
    high = close + np.abs(np.random.randn(n)) * 0.5
    low = close - np.abs(np.random.randn(n)) * 0.5
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close},
        index=dates,
    )


@pytest.fixture
def synthetic_ohlc_short():
    """Short OHLC (insufficient for full indicator warm-up)."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.DataFrame(
        {
            "Open": [100, 101, 102, 103, 104],
            "High": [101, 102, 103, 104, 105],
            "Low": [99, 100, 101, 102, 103],
            "Close": [100.5, 101.5, 102.5, 103.5, 104.5],
        },
        index=dates,
    )


def test_signal_length_and_index_match(synthetic_ohlc_rising_falling):
    """Output length and index match input."""
    data = synthetic_ohlc_rising_falling
    strategy = NDXIntradayStrategy()
    signal = strategy.generate(data)
    assert isinstance(signal, pd.Series)
    assert len(signal) == len(data)
    assert signal.index.equals(data.index)


def test_signal_values_are_zero_or_one(synthetic_ohlc_rising_falling):
    """Signal contains only -1, 0, or 1 (long/short/flat)."""
    data = synthetic_ohlc_rising_falling
    strategy = NDXIntradayStrategy()
    signal = strategy.generate(data)
    assert set(signal.dropna().unique()).issubset({-1, 0, 1})
    assert signal.notna().all()


def test_signal_no_nans_after_warmup(synthetic_ohlc_rising_falling):
    """No NaNs in signal (strategy outputs 0/1 for all bars)."""
    data = synthetic_ohlc_rising_falling
    strategy = NDXIntradayStrategy()
    signal = strategy.generate(data)
    assert signal.notna().all()


def test_insufficient_data_returns_all_flat(synthetic_ohlc_short):
    """With insufficient data, signal is all 0 (flat)."""
    data = synthetic_ohlc_short
    strategy = NDXIntradayStrategy()
    signal = strategy.generate(data)
    assert len(signal) == len(data)
    assert (signal == 0).all()


def test_include_stop_levels_returns_dataframe_with_stop_level(synthetic_ohlc_rising_falling):
    """include_stop_levels=True returns DataFrame with signal and stop_level."""
    data = synthetic_ohlc_rising_falling
    strategy = NDXIntradayStrategy()
    result = strategy.generate(data, include_stop_levels=True)
    assert isinstance(result, pd.DataFrame)
    assert "signal" in result.columns
    assert "stop_level" in result.columns
    assert len(result) == len(data)
    # Long: stop_level below close; short: stop_level above close
    where_long = result["signal"] == 1
    where_short = result["signal"] == -1
    if where_long.any():
        assert (result.loc[where_long, "stop_level"] < data.loc[where_long, "Close"]).all()
    if where_short.any():
        assert (result.loc[where_short, "stop_level"] > data.loc[where_short, "Close"]).all()


def test_include_components_returns_dataframe(synthetic_ohlc_rising_falling):
    """include_components=True returns DataFrame with signal and component columns."""
    data = synthetic_ohlc_rising_falling
    strategy = NDXIntradayStrategy()
    result = strategy.generate(data, include_components=True)
    assert isinstance(result, pd.DataFrame)
    assert "signal" in result.columns
    assert len(result) == len(data)


def test_backtest_with_signal_only(synthetic_ohlc_rising_falling):
    """Backtest runs with NDX intraday signal and returns trade_returns, equity."""
    data = synthetic_ohlc_rising_falling
    strategy = NDXIntradayStrategy(allow_short=False)
    signal = strategy.generate(data)
    trade_returns, equity_curve = run_backtest(data, signal)
    assert isinstance(trade_returns, list)
    assert isinstance(equity_curve, pd.Series)
    assert len(equity_curve) == len(data)


def test_backtest_with_stop_price_series(synthetic_ohlc_rising_falling):
    """Backtest with optional stop_price series runs and can change outcomes."""
    data = synthetic_ohlc_rising_falling
    strategy = NDXIntradayStrategy(allow_short=False)
    result = strategy.generate(data, include_stop_levels=True)
    signal = result["signal"]
    stop_level = result["stop_level"]
    returns_no_stop, _ = run_backtest(data, signal)
    returns_with_stop, _ = run_backtest(
        data, signal, stop_price=stop_level, low_col="Low"
    )
    # Both should produce valid return lists; with stops we may have more/fewer/different trades
    assert isinstance(returns_no_stop, list)
    assert isinstance(returns_with_stop, list)


def _build_ohlc_df_from_tws_data(data):
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


@pytest.mark.skipif(not IBAPI_AVAILABLE, reason="ibapi not available")
@pytest.mark.parametrize("bar_size,bar_size_label", INTRADAY_BAR_SIZES)
def test_ndx_intraday_strategy_ndx_real_data(bar_size, bar_size_label):
    """
    Integrity test: NDX intraday strategy on NDX intraday data from TWS.
    Fetches NDX bars, generates signals and stop levels, runs backtest (with and without stops),
    computes intraday metrics, and writes CSV under data/backtesting/all_metrics/ndx/<date>/intraday/<bar_size_label>/.
    """
    class NDXIntradayTestApp(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)
            self.data_handler = HistoricalDataHandler()
            self.contract_handler = ContractHandler()
            self.connected = False
            self.data_received = False

        def nextValidId(self, orderId):
            self.connected = True

        def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
            if errorCode not in [2104, 2106, 2158]:
                print(f"   Error {reqId} {errorCode}: {errorString}")

        def historicalData(self, reqId, bar: BarData):
            self.data_handler.add_bar(reqId, bar)

        def historicalDataEnd(self, reqId, start, end):
            self.data_received = True
            print(
                f"   Historical data complete for NDX ({bar_size_label}): {start} to {end}"
            )

    # #region agent log
    _debug_log("H2", "test_ndx_intraday_strategy.py:test_start", "Test started", {"bar_size_label": bar_size_label})
    # #endregion
    config = get_config()
    app = NDXIntradayTestApp()
    try:
        app.connect(config.host, config.port, clientId=214)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)
        if not app.isConnected():
            _debug_log("H2", "test_ndx_intraday_strategy.py:skip", "Skip: not connected", {})
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
    except Exception as e:
        _debug_log("H2", "test_ndx_intraday_strategy.py:skip", "Skip: connection error", {"error": str(e)})
        pytest.skip(f"Could not connect to IB TWS: {e}")

    try:
        print(f"\n[1/5] Requesting NDX intraday data ({bar_size_label})...")
        contract = app.contract_handler.create_contract(
            "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
        )
        app.data_handler.register_request(0, f"NDX_{bar_size_label}")
        # Request up to "now" in US/Eastern so we get the latest bars (including today if during RTH)
        try:
            import pytz
            eastern = pytz.timezone("US/Eastern")
            end_dt = datetime.now(eastern).strftime("%Y%m%d %H:%M:%S") + " US/Eastern"
        except Exception:
            end_dt = datetime.now().strftime("%Y%m%d %H:%M:%S")
        app.reqHistoricalData(
            reqId=0,
            contract=contract,
            endDateTime=end_dt,
            durationStr="1 W",
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )

        print("\n[2/5] Waiting for data...")
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if app.data_received:
                break
            time.sleep(1)
        if not app.data_received:
            _debug_log("H2", "test_ndx_intraday_strategy.py:skip", "Skip: no data received", {"bar_size_label": bar_size_label})
            pytest.skip(
                f"No data received from IB TWS for {bar_size_label}. Skipping."
            )

        print("\n[3/5] Building OHLC and running NDX intraday strategy (signal + stop levels)...")
        data = app.data_handler.get_data(0)
        # #region agent log
        _debug_log("H2", "test_ndx_intraday_strategy.py:after_get_data", "Data after fetch", {"data_len": len(data) if data else 0, "bar_size_label": bar_size_label})
        # #endregion
        if not data:
            pytest.skip(f"No data for {bar_size_label}.")
        df = _build_ohlc_df_from_tws_data(data)
        has_ohlc = "Open" in df.columns and "High" in df.columns and "Low" in df.columns and "Close" in df.columns
        n_bars = len(df)
        # #region agent log
        _debug_log("H2", "test_ndx_intraday_strategy.py:after_build_df", "DataFrame after build", {"n_bars": n_bars, "has_ohlc": has_ohlc})
        # #endregion
        if not has_ohlc:
            pytest.skip(f"OHLC columns missing in NDX data ({bar_size_label}).")
        if n_bars < 50:
            pytest.skip(
                f"Insufficient NDX intraday data ({bar_size_label}): {len(df)} bars."
            )

        # Export historical data used for this integrity test (same structure as all_metrics/ndx)
        current_date = datetime.now().strftime("%Y%m%d")
        data_root = Path(__file__).parent.parent.parent / "data"
        historical_base = (
            data_root / "historical_output" / "ndx" / current_date / "intraday" / bar_size_label
        )
        historical_base.mkdir(parents=True, exist_ok=True)
        historical_csv = historical_base / f"ndx_ohlc_{bar_size_label}_{current_date}.csv"
        # First line: note request end time and actual bar range (so range ending before "today" is explained)
        data_start = df.index.min()
        data_end = df.index.max()
        with open(historical_csv, "w") as f:
            f.write(f"# Request end: {end_dt} (US/Eastern); bar range in file: {data_start} to {data_end}\n")
        df.to_csv(historical_csv, mode="a")
        print(f"   Exported historical OHLC to: {historical_csv} (bars {data_start} to {data_end})")

        # Use allow_short=False so backtest (long-only) gets 0/1 signal
        strategy = NDXIntradayStrategy(allow_short=False)
        result = strategy.generate(df, include_stop_levels=True)
        signal = result["signal"]
        stop_level = result["stop_level"]
        n = len(signal)
        prev_signal = int(signal.iloc[-2]) if n >= 2 else 0
        curr_signal = int(signal.iloc[-1])
        # #region agent log
        _debug_log("H1", "test_ndx_intraday_strategy.py:signals", "Signal state", {"prev_signal": prev_signal, "curr_signal": curr_signal, "n_bars": n, "signal_counts": signal.value_counts().astype(int).to_dict()})
        # #endregion
        trade_returns_no_stop, _ = run_backtest(df, signal)
        trade_returns_with_stop, _ = run_backtest(
            df, signal, stop_price=stop_level, low_col="Low"
        )

        print("\n[4/5] Computing intraday metrics from strategy trades...")
        metrics_calc = IntradayTradeMetrics()
        result_no_stop = metrics_calc.evaluate(trade_returns_no_stop)
        result_with_stop = metrics_calc.evaluate(trade_returns_with_stop)

        for res in (result_no_stop, result_with_stop):
            assert "absolute_return" in res
            assert "win_rate" in res
            assert "mean_return_per_trade" in res
            assert "mean_return_winning_trades" in res
            assert "mean_return_losing_trades" in res
            assert "maximum_consecutive_loss" in res

        current_date = datetime.now().strftime("%Y%m%d")
        data_root = (
            Path(__file__).parent.parent.parent
            / "data"
            / "backtesting"
        )
        base_all = (
            data_root
            / "all_metrics"
            / "ndx"
            / current_date
            / "intraday"
            / bar_size_label
        )
        base_all.mkdir(parents=True, exist_ok=True)
        out_path = (
            base_all
            / f"ndx_intraday_strategy_metrics_{bar_size_label}_{current_date}.csv"
        )
        export = dict(result_with_stop)
        export["num_trades"] = len(trade_returns_with_stop)
        export["num_trades_no_stop"] = len(trade_returns_no_stop)
        pd.DataFrame([export]).to_csv(out_path, index=False)
        print(f"   Exported NDX intraday strategy metrics to: {out_path}")

        assert out_path.exists()
        print(
            f"\nNDX intraday strategy on NDX ({bar_size_label}): "
            f"trades (with stop)={len(trade_returns_with_stop)}, "
            f"trades (no stop)={len(trade_returns_no_stop)}, "
            f"win_rate={result_with_stop.get('win_rate'):.2%}, "
            f"abs_return={result_with_stop.get('absolute_return'):.4f}"
        )
    finally:
        app.disconnect()
