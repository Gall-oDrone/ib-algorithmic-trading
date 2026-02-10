"""Tests for MACD + Stochastic long signal strategy and backtest runner."""

import sys
import time
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from signals import (
    MACDStochasticLongStrategy,
    generate_macd_stochastic_long_signal,
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

# Bar sizes for NDX integration test (same as intraday_metrics)
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
    # Trend up then down
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
    strategy = MACDStochasticLongStrategy()
    signal = strategy.generate(data)
    assert isinstance(signal, pd.Series)
    assert len(signal) == len(data)
    assert signal.index.equals(data.index)


def test_signal_values_are_zero_or_one(synthetic_ohlc_rising_falling):
    """Signal contains only 0 or 1."""
    data = synthetic_ohlc_rising_falling
    strategy = MACDStochasticLongStrategy()
    signal = strategy.generate(data)
    assert set(signal.dropna().unique()).issubset({0, 1})
    assert signal.notna().all()


def test_signal_no_nans_after_warmup(synthetic_ohlc_rising_falling):
    """No NaNs in signal (strategy outputs 0/1 for all bars)."""
    data = synthetic_ohlc_rising_falling
    strategy = MACDStochasticLongStrategy()
    signal = strategy.generate(data)
    assert signal.notna().all()


def test_insufficient_data_returns_all_flat(synthetic_ohlc_short):
    """With insufficient data, signal is all 0 (flat)."""
    data = synthetic_ohlc_short
    strategy = MACDStochasticLongStrategy()
    signal = strategy.generate(data)
    assert len(signal) == len(data)
    assert (signal == 0).all()


def test_include_components_returns_dataframe(synthetic_ohlc_rising_falling):
    """include_components=True returns DataFrame with signal and component columns."""
    data = synthetic_ohlc_rising_falling
    strategy = MACDStochasticLongStrategy()
    result = strategy.generate(data, include_components=True)
    assert isinstance(result, pd.DataFrame)
    assert "signal" in result.columns
    assert "macd_bullish" in result.columns
    assert "macd_bearish" in result.columns
    assert "stoch_bullish" in result.columns
    assert "stoch_bearish" in result.columns
    assert len(result) == len(data)


def test_convenience_function(synthetic_ohlc_rising_falling):
    """generate_macd_stochastic_long_signal produces same-length series."""
    data = synthetic_ohlc_rising_falling
    signal = generate_macd_stochastic_long_signal(data)
    assert isinstance(signal, pd.Series)
    assert len(signal) == len(data)
    signal_df = generate_macd_stochastic_long_signal(
        data, include_components=True
    )
    assert "signal" in signal_df.columns


def test_runner_produces_trade_returns_and_equity(synthetic_ohlc_rising_falling):
    """Backtest runner returns list of trade returns and equity series."""
    data = synthetic_ohlc_rising_falling
    strategy = MACDStochasticLongStrategy()
    signal = strategy.generate(data)
    trade_returns, equity_curve = run_backtest(data, signal)
    assert isinstance(trade_returns, list)
    assert isinstance(equity_curve, pd.Series)
    assert len(equity_curve) == len(data)
    assert equity_curve.index.equals(data.index)
    assert equity_curve.iloc[0] == 1.0
    for r in trade_returns:
        assert isinstance(r, (int, float))


def test_trade_returns_from_backtest(synthetic_ohlc_rising_falling):
    """trade_returns_from_backtest returns only list of returns."""
    data = synthetic_ohlc_rising_falling
    signal = generate_macd_stochastic_long_signal(data)
    returns = trade_returns_from_backtest(data, signal)
    assert isinstance(returns, list)


def test_runner_with_signal_feed_into_intraday_metrics(synthetic_ohlc_rising_falling):
    """Trade returns from runner can be passed to IntradayTradeMetrics."""
    data = synthetic_ohlc_rising_falling
    signal = generate_macd_stochastic_long_signal(data)
    returns = trade_returns_from_backtest(data, signal)
    metrics_calc = IntradayTradeMetrics()
    result = metrics_calc.evaluate(returns)
    assert "absolute_return" in result
    assert "win_rate" in result
    assert "mean_return_per_trade" in result
    assert "maximum_consecutive_loss" in result


def test_missing_ohlc_column_raises():
    """Missing OHLC column raises ValueError."""
    strategy = MACDStochasticLongStrategy()
    df = pd.DataFrame({"Open": [1], "High": [2], "Low": [0.5]})  # no Close
    with pytest.raises(ValueError, match="not found"):
        strategy.generate(df)


def test_custom_column_names():
    """Strategy accepts custom OHLC column names."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    df = pd.DataFrame(
        {
            "open": np.linspace(100, 110, 50),
            "high": np.linspace(101, 111, 50),
            "low": np.linspace(99, 109, 50),
            "close": np.linspace(100, 110, 50),
        },
        index=dates,
    )
    strategy = MACDStochasticLongStrategy()
    signal = strategy.generate(
        df,
        open_col="open",
        high_col="high",
        low_col="low",
        close_col="close",
    )
    assert len(signal) == 50
    assert signal.notna().all()


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
def test_macd_stochastic_long_ndx_real_data(bar_size, bar_size_label):
    """
    Integration test: MACD+Stochastic long strategy on NDX intraday data from TWS.
    Fetches NDX bars, generates signals, runs backtest, computes intraday metrics,
    and writes CSV under data/backtesting/all_metrics/ndx/<date>/intraday/<bar_size_label>/.
    """
    class NDXSignalApp(EWrapper, EClient):
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

    config = get_config()
    app = NDXSignalApp()
    try:
        app.connect(config.host, config.port, clientId=213)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)
        if not app.isConnected():
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
    except Exception as e:
        pytest.skip(f"Could not connect to IB TWS: {e}")

    try:
        print(f"\n[1/5] Requesting NDX intraday data ({bar_size_label})...")
        contract = app.contract_handler.create_contract(
            "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
        )
        app.data_handler.register_request(0, f"NDX_{bar_size_label}")
        app.reqHistoricalData(
            reqId=0,
            contract=contract,
            endDateTime="",
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
            pytest.skip(
                f"No data received from IB TWS for {bar_size_label}. Skipping."
            )

        print("\n[3/5] Building OHLC and running MACD+Stochastic long strategy...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip(f"No data for {bar_size_label}.")
        df = _build_ohlc_df_from_tws_data(data)
        if "Open" not in df.columns or "High" not in df.columns or "Low" not in df.columns or "Close" not in df.columns:
            pytest.skip(f"OHLC columns missing in NDX data ({bar_size_label}).")
        if len(df) < 50:
            pytest.skip(
                f"Insufficient NDX intraday data ({bar_size_label}): {len(df)} bars."
            )

        strategy = MACDStochasticLongStrategy()
        signal = strategy.generate(df)
        trade_returns, equity_curve = run_backtest(df, signal)

        print("\n[4/5] Computing intraday metrics from strategy trades...")
        metrics_calc = IntradayTradeMetrics()
        result = metrics_calc.evaluate(trade_returns)

        assert "absolute_return" in result
        assert "win_rate" in result
        assert "mean_return_per_trade" in result
        assert "mean_return_winning_trades" in result
        assert "mean_return_losing_trades" in result
        assert "maximum_consecutive_loss" in result

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
            / f"ndx_macd_stochastic_long_metrics_{bar_size_label}_{current_date}.csv"
        )
        # Add number of trades for context
        export = dict(result)
        export["num_trades"] = len(trade_returns)
        pd.DataFrame([export]).to_csv(out_path, index=False)
        print(f"   Exported MACD+Stochastic long metrics to: {out_path}")

        assert out_path.exists()
        print(
            f"\nMACD+Stochastic long on NDX ({bar_size_label}): "
            f"trades={len(trade_returns)}, win_rate={result.get('win_rate'):.2%}, "
            f"abs_return={result.get('absolute_return'):.4f}, "
            f"max_consecutive_loss={result.get('maximum_consecutive_loss')}"
        )
    finally:
        app.disconnect()
