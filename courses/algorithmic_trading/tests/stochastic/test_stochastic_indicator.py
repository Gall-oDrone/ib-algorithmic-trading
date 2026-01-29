"""Tests for Stochastic Oscillator indicator."""

import sys
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from indicators.stochastic import calculate_stochastic, StochasticIndicator


@pytest.fixture
def sample_ohlc_data():
    """Create sample OHLC data."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    close = 100 + np.cumsum(np.random.randn(100) * 0.5)
    high = close + np.abs(np.random.randn(100) * 0.5)
    low = close - np.abs(np.random.randn(100) * 0.5)
    return pd.DataFrame({
        "High": high,
        "Low": low,
        "Close": close,
    }, index=dates)


@pytest.fixture
def trending_up_ohlc():
    """Create trending up OHLC data."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    close = 100 + np.arange(50) * 0.5
    high = close + 0.3
    low = close - 0.3
    return pd.DataFrame({
        "High": high,
        "Low": low,
        "Close": close,
    }, index=dates)


@pytest.fixture
def constant_range_ohlc():
    """Create OHLC where high-low range is constant (edge case)."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    close = pd.Series([100.0, 101.0, 99.0] * 10, index=dates[:30])
    high = close + 2.0
    low = close - 2.0
    return pd.DataFrame({
        "High": high,
        "Low": low,
        "Close": close,
    }, index=dates[:30])


def test_calculate_stochastic_function(sample_ohlc_data):
    """Test Stochastic calculation function."""
    result = calculate_stochastic(
        sample_ohlc_data["High"],
        sample_ohlc_data["Low"],
        sample_ohlc_data["Close"],
    )

    assert "stoch_k" in result
    assert "stoch_d" in result
    assert len(result["stoch_k"]) == len(sample_ohlc_data)
    assert len(result["stoch_d"]) == len(sample_ohlc_data)

    valid_k = result["stoch_k"].dropna()
    if len(valid_k) > 0:
        assert (valid_k >= 0).all() and (valid_k <= 100).all()

    valid_d = result["stoch_d"].dropna()
    if len(valid_d) > 0:
        assert (valid_d >= 0).all() and (valid_d <= 100).all()


def test_stochastic_indicator_class(sample_ohlc_data):
    """Test Stochastic indicator class."""
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate(
        sample_ohlc_data["High"],
        sample_ohlc_data["Low"],
        sample_ohlc_data["Close"],
    )

    assert "stoch_k" in result
    assert "stoch_d" in result
    assert len(result["stoch_k"]) == len(sample_ohlc_data)
    assert len(result["stoch_d"]) == len(sample_ohlc_data)


def test_stochastic_with_insufficient_data():
    """Test Stochastic with insufficient data."""
    high = pd.Series([101, 102, 103, 104, 105])
    low = pd.Series([99, 100, 101, 102, 103])
    close = pd.Series([100, 101, 102, 103, 104])
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate(high, low, close)

    assert len(result["stoch_k"]) == len(close)
    assert len(result["stoch_d"]) == len(close)
    # All values should be NaN when data is insufficient
    assert pd.isna(result["stoch_k"]).all()
    assert pd.isna(result["stoch_d"]).all()


def test_stochastic_custom_periods(sample_ohlc_data):
    """Test Stochastic with custom k_period and d_period."""
    indicator = StochasticIndicator(k_period=10, d_period=5)
    result = indicator.calculate(
        sample_ohlc_data["High"],
        sample_ohlc_data["Low"],
        sample_ohlc_data["Close"],
    )

    assert "stoch_k" in result
    assert "stoch_d" in result
    # First valid %K at index k_period-1, first valid %D at k_period + d_period - 2
    assert pd.isna(result["stoch_k"].iloc[:9]).all()
    assert not pd.isna(result["stoch_k"].iloc[9])
    assert pd.isna(result["stoch_d"].iloc[:13]).all()
    assert not pd.isna(result["stoch_d"].iloc[13])


def test_stochastic_invalid_k_period():
    """Test Stochastic with invalid k_period."""
    with pytest.raises(ValueError, match="k_period must be greater than 0"):
        StochasticIndicator(k_period=0, d_period=3)

    with pytest.raises(ValueError, match="k_period must be greater than 0"):
        StochasticIndicator(k_period=-1, d_period=3)


def test_stochastic_invalid_d_period():
    """Test Stochastic with invalid d_period."""
    with pytest.raises(ValueError, match="d_period must be greater than 0"):
        StochasticIndicator(k_period=14, d_period=0)

    with pytest.raises(ValueError, match="d_period must be greater than 0"):
        StochasticIndicator(k_period=14, d_period=-1)


def test_stochastic_none_input():
    """Test Stochastic with None input."""
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate(None, None, None)

    assert len(result["stoch_k"]) == 0
    assert len(result["stoch_d"]) == 0


def test_stochastic_calculate_from_dataframe(sample_ohlc_data):
    """Test Stochastic calculation from DataFrame."""
    df = sample_ohlc_data.copy()
    df.columns = ["high", "low", "close"]
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate_from_dataframe(df)

    assert "stoch_k" in result
    assert "stoch_d" in result
    assert len(result["stoch_k"]) == len(df)


def test_stochastic_calculate_from_dataframe_custom_columns(sample_ohlc_data):
    """Test Stochastic from DataFrame with custom column names."""
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate_from_dataframe(
        sample_ohlc_data,
        high_col="High",
        low_col="Low",
        close_col="Close",
    )

    assert "stoch_k" in result
    assert "stoch_d" in result
    assert len(result["stoch_k"]) == len(sample_ohlc_data)


def test_stochastic_calculate_from_dataframe_missing_column():
    """Test Stochastic from DataFrame with missing column."""
    df = pd.DataFrame({
        "high": [101, 102, 103],
        "low": [99, 100, 101],
        # Missing "close" column
    })
    indicator = StochasticIndicator(k_period=14, d_period=3)

    with pytest.raises(ValueError, match="Column 'close' not found"):
        indicator.calculate_from_dataframe(df)


def test_stochastic_kwargs_override(sample_ohlc_data):
    """Test that kwargs can override default parameters."""
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result_default = indicator.calculate(
        sample_ohlc_data["High"],
        sample_ohlc_data["Low"],
        sample_ohlc_data["Close"],
    )
    result_override = indicator.calculate(
        sample_ohlc_data["High"],
        sample_ohlc_data["Low"],
        sample_ohlc_data["Close"],
        k_period=10,
        d_period=5,
    )

    assert not result_default["stoch_k"].equals(result_override["stoch_k"])
    assert not result_default["stoch_d"].equals(result_override["stoch_d"])


def test_stochastic_range_0_to_100(sample_ohlc_data):
    """Test that %K and %D values are within 0-100."""
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate(
        sample_ohlc_data["High"],
        sample_ohlc_data["Low"],
        sample_ohlc_data["Close"],
    )

    valid_k = result["stoch_k"].dropna()
    valid_d = result["stoch_d"].dropna()
    if len(valid_k) > 0:
        assert (valid_k >= 0).all() and (valid_k <= 100).all()
    if len(valid_d) > 0:
        assert (valid_d >= 0).all() and (valid_d <= 100).all()


def test_stochastic_d_is_smoother_than_k(sample_ohlc_data):
    """Test that %D is a smoothed version of %K (less volatile)."""
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate(
        sample_ohlc_data["High"],
        sample_ohlc_data["Low"],
        sample_ohlc_data["Close"],
    )

    valid_idx = result["stoch_k"].notna() & result["stoch_d"].notna()
    if valid_idx.sum() > 3:
        k_series = result["stoch_k"][valid_idx]
        d_series = result["stoch_d"][valid_idx]
        # %D is SMA of %K, so std of %D should be <= std of %K (typically)
        assert d_series.std() <= k_series.std() + 1e-6  # small tolerance


def test_stochastic_known_values():
    """Test Stochastic with known values: close at high gives %K=100, at low gives %K=0."""
    # One bar: high=110, low=100, close=110 -> %K = 100*(110-100)/(110-100) = 100
    # One bar: high=110, low=100, close=100 -> %K = 100*(100-100)/(110-100) = 0
    dates = pd.date_range("2024-01-01", periods=20, freq="D")
    high = pd.Series([110.0] * 20, index=dates)
    low = pd.Series([100.0] * 20, index=dates)
    close = pd.Series([105.0] * 20, index=dates)  # mid
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate(high, low, close)

    valid_k = result["stoch_k"].dropna()
    if len(valid_k) > 0:
        # Close at mid -> %K = 50
        assert abs(valid_k.iloc[-1] - 50.0) < 1.0


def test_stochastic_zero_range():
    """Test Stochastic when high equals low (zero range) -> %K should be 0."""
    dates = pd.date_range("2024-01-01", periods=20, freq="D")
    high = pd.Series([100.0] * 20, index=dates)
    low = pd.Series([100.0] * 20, index=dates)
    close = pd.Series([100.0] * 20, index=dates)
    indicator = StochasticIndicator(k_period=14, d_period=3)
    result = indicator.calculate(high, low, close)

    valid_k = result["stoch_k"].dropna()
    if len(valid_k) > 0:
        assert (valid_k == 0).all()


def test_stochastic_on_ndx_index():
    """
    Integration test: Calculate Stochastic Oscillator on NDX Index data.

    This test:
    1. Fetches historical NDX data from IB TWS (if available)
    2. Calculates Stochastic using High, Low, Close
    3. Exports results to CSV in data/stochastic/ndx/YYYYMMDD/

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

    class NDXStochasticTestApp(EWrapper, EClient):
        """Simple app for fetching NDX data."""

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
    app = NDXStochasticTestApp()

    try:
        app.connect(config.host, config.port, clientId=205)
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
            durationStr="1 Y",
            barSizeSetting="1 day",
            whatToShow="ADJUSTED_LAST",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )
        print("   Requested NDX data (1 year, daily bars)")

        print("\n[2/4] Waiting for data...")
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if app.data_received:
                break
            time.sleep(1)

        if not app.data_received:
            pytest.skip("No data received from IB TWS. Skipping integration test.")

        print("\n[3/4] Processing data and calculating Stochastic...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip("No data available. Skipping integration test.")

        df = pd.DataFrame(data)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)

        indicator = StochasticIndicator(k_period=14, d_period=3)
        stoch_result = indicator.calculate_from_dataframe(
            df, high_col="High", low_col="Low", close_col="Close"
        )

        result_df = df.copy()
        result_df["Stoch_K"] = stoch_result["stoch_k"]
        result_df["Stoch_D"] = stoch_result["stoch_d"]

        current_date = datetime.now().strftime("%Y%m%d")
        base_dir = (
            Path(__file__).parent.parent.parent
            / "data"
            / "stochastic"
            / "ndx"
            / current_date
        )
        base_dir.mkdir(parents=True, exist_ok=True)

        print("\n[4/4] Exporting results to CSV...")
        output_file = base_dir / f"ndx_stochastic_{current_date}.csv"
        export_df = result_df.reset_index()
        export_df.to_csv(output_file, index=False)
        print(f"   Exported to: {output_file}")

        assert output_file.exists(), f"Export file does not exist: {output_file}"
        assert len(export_df) > 0, "No data in result DataFrame"
        assert "Stoch_K" in export_df.columns
        assert "Stoch_D" in export_df.columns

        valid_k = export_df["Stoch_K"].dropna()
        if len(valid_k) > 0:
            assert (valid_k >= 0).all() and (valid_k <= 100).all()
            print(f"\nStochastic %K range: {valid_k.min():.2f} - {valid_k.max():.2f}")
            overbought = (valid_k > 80).sum()
            oversold = (valid_k < 20).sum()
            print(f"Overbought (%%K > 80): {overbought}, Oversold (%%K < 20): {oversold}")

    finally:
        app.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
