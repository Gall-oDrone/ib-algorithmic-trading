"""Tests for ATR (Average True Range) indicator."""

import sys
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from indicators.atr import calculate_atr, ATRIndicator


@pytest.fixture
def sample_ohlc_data():
    """Create sample OHLC data."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    
    # Generate realistic OHLC data
    base_price = 100
    prices = base_price + np.cumsum(np.random.randn(100) * 0.5)
    
    # Create OHLC with some volatility
    high = prices + np.abs(np.random.randn(100) * 0.3)
    low = prices - np.abs(np.random.randn(100) * 0.3)
    close = prices + np.random.randn(100) * 0.1
    
    # Ensure high >= low and high >= close >= low
    high = np.maximum(high, np.maximum(close, low))
    low = np.minimum(low, np.minimum(close, high))
    
    return {
        "high": pd.Series(high, index=dates),
        "low": pd.Series(low, index=dates),
        "close": pd.Series(close, index=dates),
    }


@pytest.fixture
def constant_ohlc_data():
    """Create constant OHLC data for edge case testing."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    high = pd.Series([101.0] * 50, index=dates)
    low = pd.Series([99.0] * 50, index=dates)
    close = pd.Series([100.0] * 50, index=dates)
    return {
        "high": high,
        "low": low,
        "close": close,
    }


def test_calculate_atr_function(sample_ohlc_data):
    """Test ATR calculation function."""
    result = calculate_atr(
        sample_ohlc_data["high"],
        sample_ohlc_data["low"],
        sample_ohlc_data["close"]
    )
    
    assert "atr" in result
    assert len(result["atr"]) == len(sample_ohlc_data["close"])
    # ATR should be non-negative
    assert (result["atr"].dropna() >= 0).all()


def test_atr_indicator_class(sample_ohlc_data):
    """Test ATR indicator class."""
    indicator = ATRIndicator(period=14)
    result = indicator.calculate(
        sample_ohlc_data["high"],
        sample_ohlc_data["low"],
        sample_ohlc_data["close"]
    )
    
    assert "atr" in result
    assert len(result["atr"]) == len(sample_ohlc_data["close"])


def test_atr_with_insufficient_data():
    """Test ATR with insufficient data."""
    short_high = pd.Series([100, 101, 102, 103, 104])
    short_low = pd.Series([99, 100, 101, 102, 103])
    short_close = pd.Series([99.5, 100.5, 101.5, 102.5, 103.5])
    
    indicator = ATRIndicator(period=14)
    result = indicator.calculate(short_high, short_low, short_close)
    
    # Should return series with NaN values when data is insufficient
    assert len(result["atr"]) == len(short_close)
    # All values should be NaN when data is insufficient
    assert pd.isna(result["atr"]).all()


def test_atr_custom_period(sample_ohlc_data):
    """Test ATR with custom period."""
    indicator = ATRIndicator(period=10)
    result = indicator.calculate(
        sample_ohlc_data["high"],
        sample_ohlc_data["low"],
        sample_ohlc_data["close"]
    )
    
    assert "atr" in result
    # First 10 values should be NaN (need period+1 for first valid ATR)
    assert pd.isna(result["atr"].iloc[:10]).all()
    # 11th value should be valid
    assert not pd.isna(result["atr"].iloc[10])


def test_atr_constant_volatility(constant_ohlc_data):
    """Test ATR with constant volatility."""
    indicator = ATRIndicator(period=14)
    result = indicator.calculate(
        constant_ohlc_data["high"],
        constant_ohlc_data["low"],
        constant_ohlc_data["close"]
    )
    
    # With constant OHLC, True Range should be constant (high - low = 2.0)
    # ATR should converge to this value
    valid_idx = 30
    atr_value = result["atr"].iloc[valid_idx]
    assert not pd.isna(atr_value)
    # Should be close to the constant true range (2.0)
    assert abs(atr_value - 2.0) < 0.1


def test_atr_invalid_period():
    """Test ATR with invalid period."""
    with pytest.raises(ValueError, match="Period must be greater than 0"):
        ATRIndicator(period=0)
    
    with pytest.raises(ValueError, match="Period must be greater than 0"):
        ATRIndicator(period=-1)


def test_atr_mismatched_lengths():
    """Test ATR with mismatched series lengths."""
    high = pd.Series([100, 101, 102, 103, 104])
    low = pd.Series([99, 100, 101, 102])
    close = pd.Series([99.5, 100.5, 101.5, 102.5, 103.5])
    
    indicator = ATRIndicator(period=14)
    result = indicator.calculate(high, low, close)
    
    # Should return series with NaN values due to validation failure
    assert len(result["atr"]) == len(close)
    assert pd.isna(result["atr"]).all()


def test_atr_none_input():
    """Test ATR with None input."""
    indicator = ATRIndicator(period=14)
    result = indicator.calculate(None, None, None)
    
    # Should return empty series
    assert len(result["atr"]) == 0


def test_atr_calculate_from_dataframe(sample_ohlc_data):
    """Test ATR calculation from DataFrame."""
    df = pd.DataFrame({
        "high": sample_ohlc_data["high"],
        "low": sample_ohlc_data["low"],
        "close": sample_ohlc_data["close"],
    })
    
    indicator = ATRIndicator(period=14)
    result = indicator.calculate_from_dataframe(df)
    
    assert "atr" in result
    assert len(result["atr"]) == len(df)


def test_atr_calculate_from_dataframe_custom_columns():
    """Test ATR calculation from DataFrame with custom column names."""
    df = pd.DataFrame({
        "H": [100, 101, 102, 103, 104, 105] * 10,
        "L": [99, 100, 101, 102, 103, 104] * 10,
        "C": [99.5, 100.5, 101.5, 102.5, 103.5, 104.5] * 10,
    })
    
    indicator = ATRIndicator(period=14)
    result = indicator.calculate_from_dataframe(
        df, high_col="H", low_col="L", close_col="C"
    )
    
    assert "atr" in result
    assert len(result["atr"]) == len(df)


def test_atr_calculate_from_dataframe_missing_column():
    """Test ATR calculation from DataFrame with missing column."""
    df = pd.DataFrame({
        "high": [100, 101, 102],
        "low": [99, 100, 101],
        # Missing "close" column
    })
    
    indicator = ATRIndicator(period=14)
    
    with pytest.raises(ValueError, match="Column 'close' not found"):
        indicator.calculate_from_dataframe(df)


def test_atr_kwargs_override(sample_ohlc_data):
    """Test that kwargs can override default parameters."""
    indicator = ATRIndicator(period=14)
    result_default = indicator.calculate(
        sample_ohlc_data["high"],
        sample_ohlc_data["low"],
        sample_ohlc_data["close"]
    )
    
    result_override = indicator.calculate(
        sample_ohlc_data["high"],
        sample_ohlc_data["low"],
        sample_ohlc_data["close"],
        period=10
    )
    
    # Results should be different
    assert not result_default["atr"].equals(result_override["atr"])


def test_atr_true_range_calculation():
    """Test True Range calculation logic."""
    # Create data where True Range should be predictable
    high = pd.Series([100, 105, 102, 108, 110])
    low = pd.Series([98, 100, 99, 100, 105])
    close = pd.Series([99, 104, 101, 107, 108])
    
    indicator = ATRIndicator(period=2)
    result = indicator.calculate(high, low, close)
    
    # First True Range: max(100-98, |100-99|, |98-99|) = max(2, 1, 1) = 2
    # Second True Range: max(105-100, |105-99|, |100-99|) = max(5, 6, 1) = 6
    # Third True Range: max(102-99, |102-104|, |99-104|) = max(3, 2, 5) = 5
    
    # ATR at index 2 (first valid): (2 + 6) / 2 = 4
    # ATR at index 3: ((4 * 1) + 5) / 2 = 4.5
    # ATR at index 4: ((4.5 * 1) + max(108-100, |108-101|, |100-101|)) / 2
    
    # Check that ATR values are reasonable
    assert not pd.isna(result["atr"].iloc[2])
    assert result["atr"].iloc[2] > 0


def test_atr_invalid_price_data():
    """Test ATR with invalid price data (high < low)."""
    high = pd.Series([100, 99, 102])  # Second value: high < low
    low = pd.Series([98, 100, 101])
    close = pd.Series([99, 99.5, 101.5])
    
    indicator = ATRIndicator(period=2)
    result = indicator.calculate(high, low, close)
    
    # Should return series with NaN values due to validation failure
    assert len(result["atr"]) == len(close)
    assert pd.isna(result["atr"]).all()


def test_atr_on_ndx_index():
    """
    Integration test: Calculate ATR on real NASDAQ Index (NDX) data.
    
    This test:
    1. Fetches historical NDX data from IB TWS (if available)
    2. Calculates ATR using High, Low, and Close prices
    3. Exports results to CSV file in data/historical_output/
    
    Prerequisites:
    - IB Trader Workstation or IB Gateway must be running
    - Paper trading account must be connected
    - API connections must be enabled
    
    If IB connection is not available, the test will be skipped.
    """
    try:
        import time
        import threading
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.contract import Contract
        from ibapi.common import BarData
        from handlers.historical_data_handler import HistoricalDataHandler, DEFAULT_OUTPUT_DIR
        from handlers.contract_handler import ContractHandler
        from config import get_config
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")
    
    class NDXTestApp(EWrapper, EClient):
        """Simple app for fetching NDX data."""
        
        def __init__(self):
            EClient.__init__(self, self)
            self.data_handler = HistoricalDataHandler()
            self.contract_handler = ContractHandler()
            self.connected = False
            self.data_received = False
            
        def nextValidId(self, orderId):
            self.connected = True
            
        def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=''):
            if errorCode not in [2104, 2106, 2158]:
                print(f"   Error {reqId} {errorCode}: {errorString}")
        
        def historicalData(self, reqId, bar: BarData):
            self.data_handler.add_bar(reqId, bar)
        
        def historicalDataEnd(self, reqId, start, end):
            self.data_received = True
            print(f"   Historical data complete for NDX: {start} to {end}")
    
    config = get_config()
    app = NDXTestApp()
    
    # Try to connect
    try:
        app.connect(config.host, config.port, clientId=202)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)
        
        if not app.isConnected():
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
    except Exception as e:
        pytest.skip(f"Could not connect to IB TWS: {e}")
    
    try:
        # Request NDX historical data
        print("\n[1/4] Requesting NDX historical data...")
        contract = app.contract_handler.create_contract(
            "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
        )
        app.data_handler.register_request(0, "NDX")
        
        app.reqHistoricalData(
            reqId=0,
            contract=contract,
            endDateTime="",
            durationStr="1 Y",  # 1 year of data for better indicator calculation
            barSizeSetting="1 day",  # Daily bars
            whatToShow="ADJUSTED_LAST",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )
        print("   Requested NDX data (1 year, daily bars)")
        
        # Wait for data
        print("\n[2/4] Waiting for data...")
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if app.data_received:
                break
            time.sleep(1)
        
        if not app.data_received:
            pytest.skip("No data received from IB TWS. Skipping integration test.")
        
        # Get data as DataFrame
        print("\n[3/4] Processing data and calculating ATR...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip("No data available. Skipping integration test.")
        
        df = pd.DataFrame(data)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
        
        # Calculate ATR
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        
        indicator = ATRIndicator(period=14)
        atr_result = indicator.calculate(high, low, close)
        
        # Combine original data with ATR values
        result_df = df.copy()
        result_df["ATR"] = atr_result["atr"]
        
        # Export to CSV
        print("\n[4/4] Exporting results to CSV...")
        output_dir = DEFAULT_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "NDX_atr.csv"
        
        result_df.to_csv(output_file, index=True)
        print(f"   Exported to: {output_file}")
        print(f"   Rows: {len(result_df)}, Columns: {list(result_df.columns)}")
        
        # Verify file exists and has data
        assert output_file.exists(), f"Export file does not exist: {output_file}"
        assert len(result_df) > 0, "No data in result DataFrame"
        assert "ATR" in result_df.columns, "ATR column not found"
        
        # Display summary
        print("\n" + "=" * 70)
        print("ATR INTEGRATION TEST COMPLETED")
        print("=" * 70)
        print(f"Output file: {output_file}")
        print(f"Data points: {len(result_df)}")
        print(f"Valid ATR values: {result_df['ATR'].notna().sum()}")
        if result_df['ATR'].notna().any():
            print(f"ATR range: {result_df['ATR'].min():.2f} - {result_df['ATR'].max():.2f}")
        print("=" * 70)
        
    finally:
        app.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
