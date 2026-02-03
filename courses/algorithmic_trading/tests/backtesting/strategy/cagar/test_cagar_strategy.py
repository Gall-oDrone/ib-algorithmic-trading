"""Tests for CAGAR (Compound Annual Growth And Return) backtesting strategy.

Intraday time periods (TWS): 15 sec, 30 sec, 1 min, 2 min, 3 min, 4 min, 5 min,
10 min, 15 min, 20 min, 30 min, Hourly, 2 hour.

Financial/risk rationale for tested intraday bar sizes:
- 5 min: Industry standard for intraday; balances noise vs resolution; widely
  used for execution, algo trading, and intraday risk.
- 15 min: Less noisy; good for swing-intraday and risk monitoring.
- 1 hour: Higher-level view; fewer bars; useful for daily risk and position sizing.
"""

import sys
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add algorithmic_trading to path (tests/backtesting/strategy/cagar -> 5 levels up)
parent_dir = Path(__file__).parent.parent.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from backtesting.strategy.cagar import CAGARStrategy, calculate_cagar
from backtesting.strategy.base_strategy import BaseBacktestStrategy


@pytest.fixture
def sample_equity_series():
    """Create sample equity curve (1 year of daily data)."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=365, freq="D")
    # Start 100, end ~110 with some noise
    equity = 100 * (1 + np.cumsum(np.random.randn(365) * 0.005) / 10)
    equity = np.maximum(equity, 1.0)
    return pd.Series(equity, index=dates)


@pytest.fixture
def trending_up_equity():
    """Equity that doubles in 1 year (100% CAGR)."""
    dates = pd.date_range("2024-01-01", periods=366, freq="D")
    # Linear growth 100 -> 200
    equity = 100 + (np.arange(366) / 365) * 100
    return pd.Series(equity, index=dates)


@pytest.fixture
def multi_year_equity():
    """~3 years of equity for multi-period CAGAR."""
    dates = pd.date_range("2022-01-01", periods=365 * 3 + 1, freq="D")
    # Approx 10% annual growth: 100 -> 133.1 over 3 years
    t = np.arange(len(dates)) / (365.25 * 3)
    equity = 100 * (1.10 ** (t * 3))
    return pd.Series(equity, index=dates)


def test_calculate_cagar_function(sample_equity_series):
    """Test CAGAR calculation convenience function."""
    result = calculate_cagar(sample_equity_series)

    assert "cagar_1y" in result
    assert "cagar_full" in result
    assert len(sample_equity_series) >= 2
    assert isinstance(result["cagar_1y"], (float, np.floating))
    assert isinstance(result["cagar_full"], (float, np.floating))


def test_cagar_strategy_class(sample_equity_series):
    """Test CAGAR strategy class evaluate()."""
    strategy = CAGARStrategy(time_periods=[1, 3, 5])
    result = strategy.evaluate(sample_equity_series)

    assert "cagar_1y" in result
    assert "cagar_3y" in result
    assert "cagar_5y" in result
    assert "cagar_full" in result
    assert isinstance(strategy.time_periods, list)
    assert strategy.time_periods == [1.0, 3.0, 5.0]


def test_cagar_custom_time_periods(sample_equity_series):
    """Test CAGAR with custom time_periods."""
    strategy = CAGARStrategy(time_periods=[1, 2])
    result = strategy.evaluate(sample_equity_series)

    assert "cagar_1y" in result
    assert "cagar_2y" in result
    assert "cagar_3y" not in result
    assert "cagar_full" in result


def test_cagar_insufficient_data():
    """Test CAGAR with insufficient data returns NaN metrics."""
    short = pd.Series([100.0], index=pd.DatetimeIndex(["2024-01-01"]))
    strategy = CAGARStrategy(time_periods=[1])
    result = strategy.evaluate(short)

    assert "cagar_1y" in result
    assert np.isnan(result["cagar_1y"])
    assert np.isnan(result["cagar_full"])


def test_cagar_two_points():
    """Test CAGAR with exactly two points."""
    dates = pd.DatetimeIndex(["2024-01-01", "2025-01-01"])
    equity = pd.Series([100.0, 110.0], index=dates)
    strategy = CAGARStrategy(time_periods=[1], include_full_period=True)
    result = strategy.evaluate(equity)

    assert result["cagar_1y"] == pytest.approx(0.10, rel=1e-2)
    assert result["cagar_full"] == pytest.approx(0.10, rel=1e-2)


def test_cagar_invalid_time_periods():
    """Test CAGAR with invalid time_periods raises."""
    with pytest.raises(ValueError, match="positive number"):
        CAGARStrategy(time_periods=[0])
    with pytest.raises(ValueError, match="positive number"):
        CAGARStrategy(time_periods=[-1])
    with pytest.raises(ValueError, match="at least one period"):
        CAGARStrategy(time_periods=[])


def test_cagar_known_values_double_in_one_year(trending_up_equity):
    """Test CAGAR when equity doubles in 1 year -> 100% CAGR."""
    strategy = CAGARStrategy(time_periods=[1], include_full_period=True)
    result = strategy.evaluate(trending_up_equity)

    # 100 -> 200 in 1 year: CAGR = 1.0 (100%)
    assert result["cagar_1y"] == pytest.approx(1.0, rel=1e-2)
    assert result["cagar_full"] == pytest.approx(1.0, rel=1e-2)


def test_cagar_include_rolling(sample_equity_series):
    """Test CAGAR with include_rolling=True."""
    strategy = CAGARStrategy(
        time_periods=[1],
        include_full_period=True,
        include_rolling=True,
    )
    result = strategy.evaluate(sample_equity_series)

    assert "rolling_cagar_1y" in result
    assert isinstance(result["rolling_cagar_1y"], pd.Series)
    assert len(result["rolling_cagar_1y"]) == len(sample_equity_series)


def test_cagar_no_full_period(sample_equity_series):
    """Test CAGAR with include_full_period=False."""
    strategy = CAGARStrategy(
        time_periods=[1],
        include_full_period=False,
    )
    result = strategy.evaluate(sample_equity_series)

    assert "cagar_full" not in result
    assert "cagar_1y" in result


def test_cagar_evaluate_from_dataframe(sample_equity_series):
    """Test CAGAR evaluation from DataFrame."""
    df = sample_equity_series.to_frame("Close")
    strategy = CAGARStrategy(time_periods=[1])
    result = strategy.evaluate_from_dataframe(df, value_col="Close")

    assert "cagar_1y" in result
    assert "cagar_full" in result


def test_cagar_evaluate_from_dataframe_with_date_col():
    """Test CAGAR from DataFrame with explicit date column."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "Close": 100 + np.cumsum(np.random.randn(100) * 0.1),
    })
    strategy = CAGARStrategy(time_periods=[1])
    result = strategy.evaluate_from_dataframe(
        df, value_col="Close", date_col="date"
    )

    assert "cagar_1y" in result
    assert "cagar_full" in result


def test_cagar_evaluate_from_dataframe_missing_column():
    """Test CAGAR from DataFrame with missing value column raises."""
    df = pd.DataFrame({"open": [100, 101], "high": [102, 103]})
    strategy = CAGARStrategy(time_periods=[1])

    with pytest.raises(ValueError, match="Column 'Close' not found"):
        strategy.evaluate_from_dataframe(df, value_col="Close")


def test_cagar_kwargs_override(sample_equity_series):
    """Test that kwargs can override default time_periods in evaluate()."""
    strategy = CAGARStrategy(time_periods=[1, 3, 5])
    result = strategy.evaluate(
        sample_equity_series,
        time_periods=[1, 2],
    )

    assert "cagar_1y" in result
    assert "cagar_2y" in result
    assert "cagar_3y" not in result


def test_base_strategy_invalid_name():
    """Test BaseBacktestStrategy rejects empty name."""
    class BadStrategy(BaseBacktestStrategy):
        def evaluate(self, equity, **kwargs):
            return {}

    with pytest.raises(ValueError, match="non-empty string"):
        BadStrategy(name="")


def test_cagar_none_input():
    """Test CAGAR with None equity returns empty-like result."""
    strategy = CAGARStrategy(time_periods=[1])
    result = strategy.evaluate(None)

    assert "cagar_1y" in result
    assert np.isnan(result["cagar_1y"])


def test_cagar_inherits_base():
    """Test CAGARStrategy is a BaseBacktestStrategy."""
    strategy = CAGARStrategy(time_periods=[1])
    assert isinstance(strategy, BaseBacktestStrategy)
    assert strategy.name == "CAGAR"


def test_cagar_on_ndx_real_data():
    """
    Integration test: Compute CAGAR on NDX Index data from IB TWS.

    Prerequisites:
    - IB Trader Workstation or IB Gateway must be running
    - Paper trading account must be connected
    - API connections must be enabled

    If IB connection is not available, the test will be skipped.
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

    class NDXCAGARTestApp(EWrapper, EClient):
        """Simple app for fetching NDX data for CAGAR."""

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
            print(f"   Historical data complete for NDX: {start} to {end}")

    config = get_config()
    app = NDXCAGARTestApp()

    try:
        app.connect(config.host, config.port, clientId=206)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)

        if not app.isConnected():
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
    except Exception as e:
        pytest.skip(f"Could not connect to IB TWS: {e}")

    try:
        print("\n[1/4] Requesting NDX historical data...")
        contract = app.contract_handler.create_contract(
            "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
        )
        app.data_handler.register_request(0, "NDX")

        app.reqHistoricalData(
            reqId=0,
            contract=contract,
            endDateTime="",
            durationStr="3 Y",
            barSizeSetting="1 day",
            whatToShow="ADJUSTED_LAST",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )
        print("   Requested NDX data (3 years, daily bars)")

        print("\n[2/4] Waiting for data...")
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if app.data_received:
                break
            time.sleep(1)

        if not app.data_received:
            pytest.skip("No data received from IB TWS. Skipping integration test.")

        print("\n[3/4] Computing CAGAR on NDX close prices...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip("No data available. Skipping integration test.")

        df = pd.DataFrame(data)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)

        close = df["Close"].dropna()
        if len(close) < 2:
            pytest.skip("Insufficient NDX data for CAGAR.")

        strategy = CAGARStrategy(
            time_periods=[1, 3],
            include_full_period=True,
            include_rolling=False,
        )
        result = strategy.evaluate(close)

        current_date = datetime.now().strftime("%Y%m%d")
        base_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "data"
            / "backtesting"
            / "cagar"
            / "ndx"
            / current_date
        )
        base_dir.mkdir(parents=True, exist_ok=True)

        print("\n[4/4] Exporting CAGAR results to CSV...")
        out_path = base_dir / f"ndx_cagar_{current_date}.csv"
        metrics_df = pd.DataFrame([result])
        metrics_df.to_csv(out_path, index=False)
        print(f"   Exported to: {out_path}")

        assert out_path.exists(), f"Export file does not exist: {out_path}"
        assert "cagar_1y" in result
        assert "cagar_full" in result
        # At least one trailing period or full-period CAGR should be numeric
        cagar_values = [v for k, v in result.items() if k.startswith("cagar_") and isinstance(v, (int, float, np.floating)) and not np.isnan(v)]
        assert len(cagar_values) >= 1, "At least one CAGAR metric should be non-NaN with 3Y data"
        print(f"\nCAGAR 1Y: {result.get('cagar_1y', 'N/A')}")
        print(f"CAGAR 3Y: {result.get('cagar_3y', 'N/A')}")
        print(f"CAGAR full: {result.get('cagar_full', 'N/A')}")

    finally:
        app.disconnect()


# Intraday bar sizes chosen for financial/risk relevance (see module docstring).
INTRADAY_BAR_SIZES = [
    ("5 mins", "5min"),   # Industry standard; execution and intraday risk
    ("15 mins", "15min"), # Less noise; swing-intraday and monitoring
    ("1 hour", "1hour"),  # Strategic; daily risk and position sizing
]


@pytest.mark.parametrize("bar_size,bar_size_label", INTRADAY_BAR_SIZES)
def test_cagar_ndx_intraday_timeperiods(bar_size, bar_size_label):
    """
    Integration test: CAGAR on NDX intraday data for different TWS time periods.

    Uses 1 week of data to get enough bars for CAGAR. Bar sizes follow
    financial/risk best practice: 5 min (standard), 15 min (less noise), 1 hour
    (strategic). TWS intraday options include 15 sec–2 hour; we test the
    most relevant for backtesting and risk.

    Prerequisites: TWS/Gateway running, paper account, API enabled.
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

    class NDXCAGARIntradayTestApp(EWrapper, EClient):
        """App for fetching NDX intraday data for CAGAR."""

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
            print(f"   Historical data complete for NDX ({bar_size_label}): {start} to {end}")

    config = get_config()
    app = NDXCAGARIntradayTestApp()

    try:
        app.connect(config.host, config.port, clientId=207)
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
        print(f"   Requested NDX data (1 W, {bar_size} bars, regular trading hours)")

        print("\n[2/4] Waiting for data...")
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if app.data_received:
                break
            time.sleep(1)

        if not app.data_received:
            pytest.skip(
                f"No data received from IB TWS for {bar_size_label}. Skipping integration test."
            )

        print("\n[3/4] Computing CAGAR on NDX intraday close prices...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip(f"No data available for {bar_size_label}. Skipping integration test.")

        df = pd.DataFrame(data)
        if "Date" in df.columns:
            try:
                df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d %H:%M:%S %Z")
            except Exception:
                try:
                    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d %H:%M:%S")
                except Exception:
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df.set_index("Date", inplace=True)

        close = df["Close"].dropna()
        if len(close) < 2:
            pytest.skip(
                f"Insufficient NDX intraday data for CAGAR ({bar_size_label}: {len(close)} bars)."
            )

        strategy = CAGARStrategy(
            time_periods=[1],
            include_full_period=True,
            include_rolling=False,
        )
        result = strategy.evaluate(close)

        current_date = datetime.now().strftime("%Y%m%d")
        base_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "data"
            / "backtesting"
            / "cagar"
            / "ndx"
            / current_date
            / "intraday"
            / bar_size_label
        )
        base_dir.mkdir(parents=True, exist_ok=True)

        print("\n[4/4] Exporting CAGAR intraday results to CSV...")
        out_path = base_dir / f"ndx_cagar_intraday_{bar_size_label}_{current_date}.csv"
        metrics_df = pd.DataFrame([result])
        metrics_df.to_csv(out_path, index=False)
        print(f"   Exported to: {out_path}")

        assert out_path.exists(), f"Export file does not exist: {out_path}"
        assert "cagar_full" in result
        cagar_full = result["cagar_full"]
        assert isinstance(cagar_full, (int, float, np.floating)) or (
            hasattr(cagar_full, "item") and isinstance(cagar_full.item(), (int, float))
        )
        print(f"\nCAGAR full ({bar_size_label}): {cagar_full}")
    finally:
        app.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
