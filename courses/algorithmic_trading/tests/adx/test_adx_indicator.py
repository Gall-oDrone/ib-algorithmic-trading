"""Tests for ADX (Average Directional Index) indicator."""

import sys
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from indicators.adx import calculate_adx, ADXIndicator


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
def trending_up_ohlc_data():
    """Create trending up OHLC data."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    
    # Steady upward trend
    base_prices = 100 + np.arange(50) * 0.5
    high = base_prices + 0.5
    low = base_prices - 0.5
    close = base_prices + np.random.randn(50) * 0.1
    
    # Ensure high >= low and high >= close >= low
    high = np.maximum(high, np.maximum(close, low))
    low = np.minimum(low, np.minimum(close, high))
    
    return {
        "high": pd.Series(high, index=dates),
        "low": pd.Series(low, index=dates),
        "close": pd.Series(close, index=dates),
    }


@pytest.fixture
def trending_down_ohlc_data():
    """Create trending down OHLC data."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    
    # Steady downward trend
    base_prices = 100 - np.arange(50) * 0.5
    high = base_prices + 0.5
    low = base_prices - 0.5
    close = base_prices + np.random.randn(50) * 0.1
    
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


def test_calculate_adx_function(sample_ohlc_data):
    """Test ADX calculation function."""
    result = calculate_adx(
        sample_ohlc_data["high"],
        sample_ohlc_data["low"],
        sample_ohlc_data["close"]
    )
    
    assert "adx" in result
    assert "+di" in result
    assert "-di" in result
    assert len(result["adx"]) == len(sample_ohlc_data["close"])
    # ADX should be between 0 and 100
    valid_adx = result["adx"].dropna()
    if len(valid_adx) > 0:
        assert (valid_adx >= 0).all() and (valid_adx <= 100).all()


def test_adx_indicator_class(sample_ohlc_data):
    """Test ADX indicator class."""
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(
        sample_ohlc_data["high"],
        sample_ohlc_data["low"],
        sample_ohlc_data["close"]
    )
    
    assert "adx" in result
    assert "+di" in result
    assert "-di" in result
    assert len(result["adx"]) == len(sample_ohlc_data["close"])


def test_adx_with_insufficient_data():
    """Test ADX with insufficient data."""
    short_high = pd.Series([100, 101, 102, 103, 104])
    short_low = pd.Series([99, 100, 101, 102, 103])
    short_close = pd.Series([99.5, 100.5, 101.5, 102.5, 103.5])
    
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(short_high, short_low, short_close)
    
    # Should return series with NaN values when data is insufficient
    assert len(result["adx"]) == len(short_close)
    # All values should be NaN when data is insufficient
    assert pd.isna(result["adx"]).all()


def test_adx_custom_period(sample_ohlc_data):
    """Test ADX with custom period."""
    indicator = ADXIndicator(period=10)
    result = indicator.calculate(
        sample_ohlc_data["high"],
        sample_ohlc_data["low"],
        sample_ohlc_data["close"]
    )
    
    assert "adx" in result
    # First values should be NaN (need period*2-1 for first valid ADX)
    # With period=10, first ADX value appears at index 19 (period * 2 - 1)
    assert pd.isna(result["adx"].iloc[:19]).all()
    # Value at index 19 should be valid (first ADX value)
    assert not pd.isna(result["adx"].iloc[19])


def test_adx_trending_up(trending_up_ohlc_data):
    """Test ADX with trending up data."""
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(
        trending_up_ohlc_data["high"],
        trending_up_ohlc_data["low"],
        trending_up_ohlc_data["close"]
    )
    
    valid_adx = result["adx"].dropna()
    valid_plus_di = result["+di"].dropna()
    valid_minus_di = result["-di"].dropna()
    
    if len(valid_adx) > 0:
        # In an uptrend, +DI should generally be greater than -DI
        if len(valid_plus_di) > 0 and len(valid_minus_di) > 0:
            # Check that +DI is generally higher than -DI
            plus_di_higher = (valid_plus_di > valid_minus_di).sum()
            assert plus_di_higher > len(valid_plus_di) * 0.5


def test_adx_trending_down(trending_down_ohlc_data):
    """Test ADX with trending down data."""
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(
        trending_down_ohlc_data["high"],
        trending_down_ohlc_data["low"],
        trending_down_ohlc_data["close"]
    )
    
    valid_adx = result["adx"].dropna()
    valid_plus_di = result["+di"].dropna()
    valid_minus_di = result["-di"].dropna()
    
    if len(valid_adx) > 0:
        # In a downtrend, -DI should generally be greater than +DI
        if len(valid_plus_di) > 0 and len(valid_minus_di) > 0:
            # Check that -DI is generally higher than +DI
            minus_di_higher = (valid_minus_di > valid_plus_di).sum()
            assert minus_di_higher > len(valid_minus_di) * 0.5


def test_adx_invalid_period():
    """Test ADX with invalid period."""
    with pytest.raises(ValueError, match="Period must be greater than 0"):
        ADXIndicator(period=0)
    
    with pytest.raises(ValueError, match="Period must be greater than 0"):
        ADXIndicator(period=-1)


def test_adx_mismatched_lengths():
    """Test ADX with mismatched series lengths."""
    high = pd.Series([100, 101, 102, 103, 104])
    low = pd.Series([99, 100, 101, 102])
    close = pd.Series([99.5, 100.5, 101.5, 102.5, 103.5])
    
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(high, low, close)
    
    # Should return series with NaN values due to validation failure
    assert len(result["adx"]) == len(close)
    assert pd.isna(result["adx"]).all()


def test_adx_none_input():
    """Test ADX with None input."""
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(None, None, None)
    
    # Should return empty series
    assert len(result["adx"]) == 0
    assert len(result["+di"]) == 0
    assert len(result["-di"]) == 0


def test_adx_calculate_from_dataframe(sample_ohlc_data):
    """Test ADX calculation from DataFrame."""
    df = pd.DataFrame({
        "high": sample_ohlc_data["high"],
        "low": sample_ohlc_data["low"],
        "close": sample_ohlc_data["close"],
    })
    
    indicator = ADXIndicator(period=14)
    result = indicator.calculate_from_dataframe(df)
    
    assert "adx" in result
    assert "+di" in result
    assert "-di" in result
    assert len(result["adx"]) == len(df)


def test_adx_calculate_from_dataframe_custom_columns():
    """Test ADX calculation from DataFrame with custom column names."""
    df = pd.DataFrame({
        "H": [100, 101, 102, 103, 104, 105] * 20,
        "L": [99, 100, 101, 102, 103, 104] * 20,
        "C": [99.5, 100.5, 101.5, 102.5, 103.5, 104.5] * 20,
    })
    
    indicator = ADXIndicator(period=14)
    result = indicator.calculate_from_dataframe(
        df, high_col="H", low_col="L", close_col="C"
    )
    
    assert "adx" in result
    assert "+di" in result
    assert "-di" in result
    assert len(result["adx"]) == len(df)


def test_adx_calculate_from_dataframe_missing_column():
    """Test ADX calculation from DataFrame with missing column."""
    df = pd.DataFrame({
        "high": [100, 101, 102],
        "low": [99, 100, 101],
        # Missing "close" column
    })
    
    indicator = ADXIndicator(period=14)
    
    with pytest.raises(ValueError, match="Column 'close' not found"):
        indicator.calculate_from_dataframe(df)


def test_adx_kwargs_override(sample_ohlc_data):
    """Test that kwargs can override default parameters."""
    indicator = ADXIndicator(period=14)
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
    assert not result_default["adx"].equals(result_override["adx"])


def test_adx_range():
    """Test that ADX values are within valid range (0-100)."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    
    base_price = 100
    prices = base_price + np.cumsum(np.random.randn(100) * 2)
    
    high = prices + np.abs(np.random.randn(100) * 0.5)
    low = prices - np.abs(np.random.randn(100) * 0.5)
    close = prices + np.random.randn(100) * 0.2
    
    high = np.maximum(high, np.maximum(close, low))
    low = np.minimum(low, np.minimum(close, high))
    
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(
        pd.Series(high, index=dates),
        pd.Series(low, index=dates),
        pd.Series(close, index=dates)
    )
    
    valid_adx = result["adx"].dropna()
    if len(valid_adx) > 0:
        assert (valid_adx >= 0).all() and (valid_adx <= 100).all()
    
    # +DI and -DI should also be between 0 and 100
    valid_plus_di = result["+di"].dropna()
    valid_minus_di = result["-di"].dropna()
    
    if len(valid_plus_di) > 0:
        assert (valid_plus_di >= 0).all() and (valid_plus_di <= 100).all()
    if len(valid_minus_di) > 0:
        assert (valid_minus_di >= 0).all() and (valid_minus_di <= 100).all()


def test_adx_di_relationship():
    """Test that +DI and -DI have correct relationship."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    
    # Create data with clear upward movement
    base_prices = 100 + np.arange(50) * 0.3
    high = base_prices + 0.3
    low = base_prices - 0.2
    close = base_prices + np.random.randn(50) * 0.05
    
    high = np.maximum(high, np.maximum(close, low))
    low = np.minimum(low, np.minimum(close, high))
    
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(
        pd.Series(high, index=dates),
        pd.Series(low, index=dates),
        pd.Series(close, index=dates)
    )
    
    valid_plus_di = result["+di"].dropna()
    valid_minus_di = result["-di"].dropna()
    
    if len(valid_plus_di) > 0 and len(valid_minus_di) > 0:
        # In an uptrend, +DI should generally be higher
        assert (valid_plus_di > valid_minus_di).sum() > len(valid_plus_di) * 0.4


def test_adx_constant_price(constant_ohlc_data):
    """Test ADX with constant price data."""
    indicator = ADXIndicator(period=14)
    result = indicator.calculate(
        constant_ohlc_data["high"],
        constant_ohlc_data["low"],
        constant_ohlc_data["close"]
    )
    
    # With constant prices, there should be minimal directional movement
    # ADX should be low (indicating weak/no trend)
    valid_adx = result["adx"].dropna()
    if len(valid_adx) > 0:
        # ADX should be relatively low for constant prices
        assert valid_adx.mean() < 30


def test_adx_on_ndx_index():
    """
    Integration test: Calculate ADX on real NASDAQ Index (NDX) data.
    
    This test:
    1. Fetches historical NDX data from IB TWS (if available)
    2. Calculates ADX using High, Low, and Close prices
    3. Exports results to CSV file in data/adx/ndx/YYYYMMDD/ folder structure
    
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
        from ibapi.contract import Contract
        from ibapi.common import BarData
        from handlers.historical_data_handler import HistoricalDataHandler
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
        app.connect(config.host, config.port, clientId=205)
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
        print("\n[3/4] Processing data and calculating ADX...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip("No data available. Skipping integration test.")
        
        df = pd.DataFrame(data)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
        
        # Calculate ADX
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        
        indicator = ADXIndicator(period=14)
        adx_result = indicator.calculate(high, low, close)
        
        # Combine original data with ADX values
        result_df = df.copy()
        result_df["ADX"] = adx_result["adx"]
        result_df["+DI"] = adx_result["+di"]
        result_df["-DI"] = adx_result["-di"]
        
        # Create folder structure: data/adx/ndx/YYYYMMDD/
        current_date = datetime.now().strftime("%Y%m%d")
        base_dir = Path(__file__).parent.parent.parent / "data" / "adx" / "ndx" / current_date
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        print("\n[4/4] Exporting results to CSV...")
        output_file = base_dir / f"ndx_adx_{current_date}.csv"
        
        # Reset index to include Date as a column for better CSV readability
        export_df = result_df.reset_index()
        export_df.to_csv(output_file, index=False)
        print(f"   Exported to: {output_file}")
        print(f"   Rows: {len(export_df)}, Columns: {list(export_df.columns)}")
        
        # Verify file exists and has data
        assert output_file.exists(), f"Export file does not exist: {output_file}"
        assert len(export_df) > 0, "No data in result DataFrame"
        assert "ADX" in export_df.columns, "ADX column not found"
        
        # Display summary
        print("\n" + "=" * 70)
        print("ADX INTEGRATION TEST COMPLETED")
        print("=" * 70)
        print(f"Output file: {output_file}")
        print(f"Folder structure: data/adx/ndx/{current_date}/")
        print(f"Data points: {len(export_df)}")
        print(f"Valid ADX values: {export_df['ADX'].notna().sum()}")
        if export_df['ADX'].notna().any():
            valid_adx = export_df['ADX'].dropna()
            print(f"ADX range: {valid_adx.min():.2f} - {valid_adx.max():.2f}")
            print(f"ADX mean: {valid_adx.mean():.2f}")
            # Count strong trends (>25) and weak trends (<20)
            strong_trends = (valid_adx > 25).sum()
            weak_trends = (valid_adx < 20).sum()
            print(f"Strong trends (ADX > 25): {strong_trends}")
            print(f"Weak trends (ADX < 20): {weak_trends}")
        print("=" * 70)
        
    finally:
        app.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
