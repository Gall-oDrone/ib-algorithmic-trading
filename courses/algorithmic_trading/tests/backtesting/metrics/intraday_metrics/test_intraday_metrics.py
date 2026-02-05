"""Tests for IntradayTradeMetrics.

Unit tests use generated/fixture data. Integration tests require TWS/Gateway
with paper account and API enabled (NDX intraday historical data).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

parent_dir = Path(__file__).parent.parent.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from backtesting.metrics.base_metric import BaseTradeMetric
from backtesting.metrics.intraday_metrics import (
    IntradayTradeMetrics,
    calculate_intraday_metrics,
)


# ---- Fixtures: generated trade returns ----


@pytest.fixture
def sample_trade_returns():
    """Sample trade returns: 5 trades, 3 wins, 2 losses."""
    return [0.02, -0.01, 0.015, -0.005, 0.01]


@pytest.fixture
def all_winning_trades():
    """All trades are winners."""
    return [0.01, 0.02, 0.015]


@pytest.fixture
def all_losing_trades():
    """All trades are losers."""
    return [-0.01, -0.02, -0.005]


@pytest.fixture
def consecutive_loss_series():
    """Returns with a run of 3 consecutive losses then a win."""
    return [0.01, -0.01, -0.02, -0.01, 0.02]


@pytest.fixture
def empty_returns():
    """No trades."""
    return []


@pytest.fixture
def single_trade():
    """Single trade return."""
    return [0.03]


# ---- Unit tests: convenience function and keys ----


def test_calculate_intraday_metrics_function(sample_trade_returns):
    """Test convenience function returns expected keys."""
    result = calculate_intraday_metrics(sample_trade_returns)
    assert "absolute_return" in result
    assert "win_rate" in result
    assert "mean_return_per_trade" in result
    assert "mean_return_winning_trades" in result
    assert "mean_return_losing_trades" in result
    assert "maximum_consecutive_loss" in result


def test_intraday_metrics_class(sample_trade_returns):
    """Test IntradayTradeMetrics.evaluate returns all six metrics."""
    calc = IntradayTradeMetrics()
    result = calc.evaluate(sample_trade_returns)
    assert len(result) == 6
    assert result["win_rate"] == 0.6  # 3 wins of 5
    assert result["maximum_consecutive_loss"] == 1  # no run of 2+ losses in [0.02, -0.01, 0.015, -0.005, 0.01]


# ---- Unit tests: absolute return (compounded) ----


def test_absolute_return_compounded(sample_trade_returns):
    """Absolute return = (1+r1)(1+r2)... - 1."""
    result = calculate_intraday_metrics(sample_trade_returns)
    expected = (
        (1 + 0.02) * (1 - 0.01) * (1 + 0.015) * (1 - 0.005) * (1 + 0.01)
    ) - 1
    assert abs(result["absolute_return"] - expected) < 1e-10


def test_absolute_return_single(single_trade):
    """Single trade: absolute return equals that return."""
    result = calculate_intraday_metrics(single_trade)
    assert abs(result["absolute_return"] - 0.03) < 1e-10


# ---- Unit tests: win rate ----


def test_win_rate_all_winning(all_winning_trades):
    """All winners -> win_rate 1.0."""
    result = calculate_intraday_metrics(all_winning_trades)
    assert result["win_rate"] == 1.0


def test_win_rate_all_losing(all_losing_trades):
    """All losers -> win_rate 0.0."""
    result = calculate_intraday_metrics(all_losing_trades)
    assert result["win_rate"] == 0.0


def test_win_rate_half():
    """Half wins, half losses -> 0.5."""
    result = calculate_intraday_metrics([0.01, -0.01, 0.02, -0.02])
    assert result["win_rate"] == 0.5


# ---- Unit tests: mean return per trade ----


def test_mean_return_per_trade(sample_trade_returns):
    """Mean return = mean of list."""
    result = calculate_intraday_metrics(sample_trade_returns)
    expected = np.mean(sample_trade_returns)
    assert abs(result["mean_return_per_trade"] - expected) < 1e-10


# ---- Unit tests: mean return winning / losing ----


def test_mean_return_winning_trades(all_winning_trades):
    """When all win, mean_return_winning_trades = mean of returns."""
    result = calculate_intraday_metrics(all_winning_trades)
    assert abs(result["mean_return_winning_trades"] - np.mean(all_winning_trades)) < 1e-10


def test_mean_return_losing_trades(all_losing_trades):
    """When all lose, mean_return_losing_trades = mean of returns."""
    result = calculate_intraday_metrics(all_losing_trades)
    assert abs(result["mean_return_losing_trades"] - np.mean(all_losing_trades)) < 1e-10


def test_mean_return_winning_nan_when_no_wins(all_losing_trades):
    """No winning trades -> mean_return_winning_trades is NaN."""
    result = calculate_intraday_metrics(all_losing_trades)
    assert np.isnan(result["mean_return_winning_trades"])


def test_mean_return_losing_nan_when_no_losses(all_winning_trades):
    """No losing trades -> mean_return_losing_trades is NaN."""
    result = calculate_intraday_metrics(all_winning_trades)
    assert np.isnan(result["mean_return_losing_trades"])


# ---- Unit tests: maximum consecutive loss ----


def test_maximum_consecutive_loss_series(consecutive_loss_series):
    """Run of 3 consecutive losses -> maximum_consecutive_loss = 3."""
    result = calculate_intraday_metrics(consecutive_loss_series)
    assert result["maximum_consecutive_loss"] == 3


def test_maximum_consecutive_loss_no_losses(all_winning_trades):
    """No losses -> 0."""
    result = calculate_intraday_metrics(all_winning_trades)
    assert result["maximum_consecutive_loss"] == 0


def test_maximum_consecutive_loss_two_runs():
    """Two separate runs of 2 and 3 -> max is 3."""
    # -1, -2, win, -1, -1, -1
    returns = [-0.01, -0.02, 0.01, -0.01, -0.01, -0.01]
    result = calculate_intraday_metrics(returns)
    assert result["maximum_consecutive_loss"] == 3


# ---- Unit tests: empty and single ----


def test_empty_returns(empty_returns):
    """Empty list -> NaN metrics, maximum_consecutive_loss 0."""
    result = calculate_intraday_metrics(empty_returns)
    assert np.isnan(result["absolute_return"])
    assert np.isnan(result["win_rate"])
    assert np.isnan(result["mean_return_per_trade"])
    assert result["maximum_consecutive_loss"] == 0


# ---- Unit tests: input types (Series, DataFrame, array) ----


def test_accepts_series(sample_trade_returns):
    """Accepts pandas Series."""
    ser = pd.Series(sample_trade_returns)
    result = calculate_intraday_metrics(ser)
    assert "win_rate" in result
    assert result["win_rate"] == 0.6


def test_accepts_dataframe_with_return_column(sample_trade_returns):
    """Accepts DataFrame with 'return' column."""
    df = pd.DataFrame({"return": sample_trade_returns})
    result = calculate_intraday_metrics(df)
    assert result["win_rate"] == 0.6


def test_accepts_dataframe_with_pnl_column(sample_trade_returns):
    """Accepts DataFrame with 'pnl' column (treated as decimal return)."""
    df = pd.DataFrame({"pnl": sample_trade_returns})
    result = calculate_intraday_metrics(df)
    assert result["win_rate"] == 0.6


def test_accepts_numpy_array(sample_trade_returns):
    """Accepts numpy array."""
    arr = np.array(sample_trade_returns)
    result = calculate_intraday_metrics(arr)
    assert result["win_rate"] == 0.6


# ---- Unit tests: inheritance and validation ----


def test_inherits_base():
    """IntradayTradeMetrics is a BaseTradeMetric."""
    calc = IntradayTradeMetrics()
    assert isinstance(calc, BaseTradeMetric)
    assert calc.name == "IntradayTradeMetrics"


def test_base_metric_invalid_name():
    """BaseTradeMetric rejects empty or invalid name via subclass __init__."""

    class BadMetric(BaseTradeMetric):
        def evaluate(self, trade_returns, **kwargs):
            return {}

    with pytest.raises(ValueError, match="name must be a non-empty string"):
        BadMetric("")
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        BadMetric(None)


def test_dataframe_missing_return_column_raises():
    """DataFrame without return/pnl column raises."""
    df = pd.DataFrame({"price": [1, 2, 3]})
    with pytest.raises(ValueError, match="DataFrame must have"):
        calculate_intraday_metrics(df)


def test_invalid_type_raises():
    """Invalid input type raises TypeError."""
    with pytest.raises(TypeError, match="data must be"):
        calculate_intraday_metrics("not a list or series")


# ---- Integration test: NDX intraday real data (TWS) ----


INTRADAY_BAR_SIZES = [
    ("5 mins", "5min"),
    ("15 mins", "15min"),
    ("1 hour", "1hour"),
]


@pytest.mark.parametrize("bar_size,bar_size_label", INTRADAY_BAR_SIZES)
def test_intraday_metrics_ndx_real_data(bar_size, bar_size_label):
    """
    Integration test: IntradayTradeMetrics on NDX intraday data from TWS.
    Fetches NDX bars, derives per-bar returns as synthetic 'trades', computes
    metrics, and writes CSV under data/backtesting/all_metrics/.../intraday/.
    """
    try:
        import time
        import threading
        from datetime import datetime
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.common import BarData
        from handlers.historical_data_handler import HistoricalDataHandler
        from handlers.contract_handler import ContractHandler
        from config import get_config
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")

    class NDXIntradayApp(EWrapper, EClient):
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
    app = NDXIntradayApp()
    try:
        app.connect(config.host, config.port, clientId=212)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)
        if not app.isConnected():
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
    except Exception as e:
        pytest.skip(f"Could not connect to IB TWS: {e}")

    try:
        print(f"\n[1/4] Requesting NDX intraday data ({bar_size_label})...")
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

        print("\n[2/4] Waiting for data...")
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

        print("\n[3/4] Deriving bar returns and computing intraday metrics...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip(f"No data for {bar_size_label}.")
        df = pd.DataFrame(data)
        if "Date" in df.columns:
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
        closes = df["Close"].dropna()
        if len(closes) < 2:
            pytest.skip(
                f"Insufficient NDX intraday data ({bar_size_label})."
            )
        # Per-bar returns as synthetic "trades"
        trade_returns = closes.pct_change().dropna().values

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
            Path(__file__).parent.parent.parent.parent.parent
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
            / f"ndx_intraday_metrics_{bar_size_label}_{current_date}.csv"
        )
        pd.DataFrame([result]).to_csv(out_path, index=False)
        print(f"   Exported intraday metrics to: {out_path}")

        assert out_path.exists()
        print(
            f"\nIntraday metrics ({bar_size_label}): win_rate={result.get('win_rate'):.2%}, "
            f"abs_return={result.get('absolute_return'):.4f}, "
            f"max_consecutive_loss={result.get('maximum_consecutive_loss')}"
        )
    finally:
        app.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
