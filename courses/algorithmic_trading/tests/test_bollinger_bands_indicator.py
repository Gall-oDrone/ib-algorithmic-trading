"""Tests for Bollinger Bands indicator."""

import sys
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from indicators.bollinger_bands import (
    calculate_bollinger_bands,
    BollingerBandsIndicator
)


@pytest.fixture
def sample_price_data():
    """Create sample price data."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    return pd.Series(prices, index=dates)


@pytest.fixture
def constant_price_data():
    """Create constant price data for edge case testing."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    prices = pd.Series([100.0] * 50, index=dates)
    return prices


def test_calculate_bollinger_bands_function(sample_price_data):
    """Test Bollinger Bands calculation function."""
    result = calculate_bollinger_bands(sample_price_data)
    
    assert "middle" in result
    assert "upper" in result
    assert "lower" in result
    assert len(result["middle"]) == len(sample_price_data)
    assert len(result["upper"]) == len(sample_price_data)
    assert len(result["lower"]) == len(sample_price_data)
    
    # Upper band should be >= middle band (excluding NaN values)
    valid_mask = result["upper"].notna() & result["middle"].notna()
    if valid_mask.any():
        assert (result["upper"][valid_mask] >= result["middle"][valid_mask]).all()
    # Lower band should be <= middle band (excluding NaN values)
    valid_mask = result["lower"].notna() & result["middle"].notna()
    if valid_mask.any():
        assert (result["lower"][valid_mask] <= result["middle"][valid_mask]).all()


def test_bollinger_bands_indicator_class(sample_price_data):
    """Test Bollinger Bands indicator class."""
    indicator = BollingerBandsIndicator(period=20, num_std=2.0)
    result = indicator.calculate(sample_price_data)
    
    assert "middle" in result
    assert "upper" in result
    assert "lower" in result
    assert len(result["middle"]) == len(sample_price_data)


def test_bollinger_bands_with_insufficient_data():
    """Test Bollinger Bands with insufficient data."""
    short_data = pd.Series([100, 101, 102, 103, 104])  # Less than period=20
    indicator = BollingerBandsIndicator(period=20)
    result = indicator.calculate(short_data)
    
    # Should return series with NaN values when data is insufficient
    assert len(result["middle"]) == len(short_data)
    # All values should be NaN when data is insufficient
    assert pd.isna(result["middle"]).all()


def test_bollinger_bands_custom_periods(sample_price_data):
    """Test Bollinger Bands with custom periods."""
    indicator = BollingerBandsIndicator(period=10, num_std=1.5)
    result = indicator.calculate(sample_price_data)
    
    assert "middle" in result
    assert "upper" in result
    assert "lower" in result
    # With period=10, first 9 values should be NaN
    assert pd.isna(result["middle"].iloc[:9]).all()
    # 10th value should be valid
    assert not pd.isna(result["middle"].iloc[9])


def test_bollinger_bands_custom_num_std(sample_price_data):
    """Test Bollinger Bands with custom number of standard deviations."""
    indicator = BollingerBandsIndicator(period=20, num_std=3.0)
    result = indicator.calculate(sample_price_data)
    
    # With num_std=3.0, bands should be wider than with num_std=2.0
    indicator_2 = BollingerBandsIndicator(period=20, num_std=2.0)
    result_2 = indicator_2.calculate(sample_price_data)
    
    # Compare band widths at a valid index
    valid_idx = 50
    width_3 = result["upper"].iloc[valid_idx] - result["lower"].iloc[valid_idx]
    width_2 = result_2["upper"].iloc[valid_idx] - result["lower"].iloc[valid_idx]
    
    assert width_3 > width_2


def test_bollinger_bands_constant_price(constant_price_data):
    """Test Bollinger Bands with constant price (zero volatility)."""
    indicator = BollingerBandsIndicator(period=20, num_std=2.0)
    result = indicator.calculate(constant_price_data)
    
    # With constant price, standard deviation should be 0
    # So all bands should be equal to the price
    valid_idx = 30
    assert abs(result["middle"].iloc[valid_idx] - 100.0) < 1e-10
    assert abs(result["upper"].iloc[valid_idx] - 100.0) < 1e-10
    assert abs(result["lower"].iloc[valid_idx] - 100.0) < 1e-10


def test_bollinger_bands_bandwidth(sample_price_data):
    """Test Bollinger Bandwidth calculation."""
    indicator = BollingerBandsIndicator(period=20, num_std=2.0)
    bandwidth = indicator.get_bandwidth(sample_price_data)
    
    assert len(bandwidth) == len(sample_price_data)
    assert bandwidth.notna().sum() > 0  # Should have some valid values
    
    # Bandwidth should be non-negative
    assert (bandwidth.dropna() >= 0).all()


def test_bollinger_bands_percent_b(sample_price_data):
    """Test %B (Percent B) calculation."""
    indicator = BollingerBandsIndicator(period=20, num_std=2.0)
    percent_b = indicator.get_percent_b(sample_price_data)
    
    assert len(percent_b) == len(sample_price_data)
    assert percent_b.notna().sum() > 0  # Should have some valid values
    
    # %B can be outside [0, 1] range (above upper band or below lower band)
    # But should be a reasonable value
    valid_values = percent_b.dropna()
    assert len(valid_values) > 0


def test_bollinger_bands_invalid_period():
    """Test Bollinger Bands with invalid period."""
    with pytest.raises(ValueError, match="Period must be greater than 0"):
        BollingerBandsIndicator(period=0)
    
    with pytest.raises(ValueError, match="Period must be greater than 0"):
        BollingerBandsIndicator(period=-1)


def test_bollinger_bands_invalid_num_std():
    """Test Bollinger Bands with invalid num_std."""
    with pytest.raises(ValueError, match="Number of standard deviations must be greater than 0"):
        BollingerBandsIndicator(num_std=0)
    
    with pytest.raises(ValueError, match="Number of standard deviations must be greater than 0"):
        BollingerBandsIndicator(num_std=-1)


def test_bollinger_bands_kwargs_override(sample_price_data):
    """Test that kwargs can override default parameters."""
    indicator = BollingerBandsIndicator(period=20, num_std=2.0)
    result_default = indicator.calculate(sample_price_data)
    
    result_override = indicator.calculate(sample_price_data, period=10, num_std=1.5)
    
    # Results should be different
    assert not result_default["middle"].equals(result_override["middle"])


def test_bollinger_bands_middle_is_sma(sample_price_data):
    """Test that middle band is indeed a Simple Moving Average."""
    indicator = BollingerBandsIndicator(period=20, num_std=2.0)
    result = indicator.calculate(sample_price_data)
    
    # Calculate SMA manually
    sma = sample_price_data.rolling(window=20, min_periods=20).mean()
    
    # Compare middle band with SMA
    valid_idx = 50
    assert abs(result["middle"].iloc[valid_idx] - sma.iloc[valid_idx]) < 1e-10


def test_bollinger_bands_on_ndx_index():
    """
    Integration test: Calculate Bollinger Bands on real NASDAQ Index (NDX) data.
    
    This test:
    1. Fetches historical NDX data from IB TWS (if available)
    2. Calculates Bollinger Bands on the close prices
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
        app.connect(config.host, config.port, clientId=201)
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
        print("\n[3/4] Processing data and calculating Bollinger Bands...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip("No data available. Skipping integration test.")
        
        df = pd.DataFrame(data)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
        
        # Calculate Bollinger Bands
        close_prices = df["Close"]
        indicator = BollingerBandsIndicator(period=20, num_std=2.0)
        bands = indicator.calculate(close_prices)
        
        # Combine original data with indicator values
        result_df = df.copy()
        result_df["BB_Middle"] = bands["middle"]
        result_df["BB_Upper"] = bands["upper"]
        result_df["BB_Lower"] = bands["lower"]
        result_df["BB_Bandwidth"] = indicator.get_bandwidth(close_prices)
        result_df["BB_PercentB"] = indicator.get_percent_b(close_prices)
        
        # Export to CSV
        print("\n[4/4] Exporting results to CSV...")
        output_dir = DEFAULT_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "NDX_bollinger_bands.csv"
        
        result_df.to_csv(output_file, index=True)
        print(f"   Exported to: {output_file}")
        print(f"   Rows: {len(result_df)}, Columns: {list(result_df.columns)}")
        
        # Verify file exists and has data
        assert output_file.exists(), f"Export file does not exist: {output_file}"
        assert len(result_df) > 0, "No data in result DataFrame"
        assert "BB_Middle" in result_df.columns, "Bollinger Bands columns not found"
        
        # Display summary
        print("\n" + "=" * 70)
        print("BOLLINGER BANDS INTEGRATION TEST COMPLETED")
        print("=" * 70)
        print(f"Output file: bollinger_bands/{output_file.name}")
        print(f"Data points: {len(result_df)}")
        print(f"Valid BB values: {result_df['BB_Middle'].notna().sum()}")
        print("=" * 70)
        
    finally:
        app.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
