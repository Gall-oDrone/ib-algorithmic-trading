"""Tests for RSI (Relative Strength Index) indicator."""

import sys
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from indicators.rsi import calculate_rsi, RSIIndicator


@pytest.fixture
def sample_price_data():
    """Create sample price data."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    return pd.Series(prices, index=dates)


@pytest.fixture
def trending_up_data():
    """Create trending up price data."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    prices = 100 + np.arange(50) * 0.5  # Steady upward trend
    return pd.Series(prices, index=dates)


@pytest.fixture
def trending_down_data():
    """Create trending down price data."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    prices = 100 - np.arange(50) * 0.5  # Steady downward trend
    return pd.Series(prices, index=dates)


@pytest.fixture
def constant_price_data():
    """Create constant price data."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    prices = pd.Series([100.0] * 50, index=dates)
    return prices


def test_calculate_rsi_function(sample_price_data):
    """Test RSI calculation function."""
    result = calculate_rsi(sample_price_data)
    
    assert "rsi" in result
    assert len(result["rsi"]) == len(sample_price_data)
    # RSI should be between 0 and 100
    valid_rsi = result["rsi"].dropna()
    if len(valid_rsi) > 0:
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


def test_rsi_indicator_class(sample_price_data):
    """Test RSI indicator class."""
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(sample_price_data)
    
    assert "rsi" in result
    assert len(result["rsi"]) == len(sample_price_data)


def test_rsi_with_insufficient_data():
    """Test RSI with insufficient data."""
    short_data = pd.Series([100, 101, 102, 103, 104])
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(short_data)
    
    # Should return series with NaN values when data is insufficient
    assert len(result["rsi"]) == len(short_data)
    # All values should be NaN when data is insufficient
    assert pd.isna(result["rsi"]).all()


def test_rsi_custom_period(sample_price_data):
    """Test RSI with custom period."""
    indicator = RSIIndicator(period=10)
    result = indicator.calculate(sample_price_data)
    
    assert "rsi" in result
    # First 10 values should be NaN (need period+1 for first valid RSI)
    assert pd.isna(result["rsi"].iloc[:10]).all()
    # 11th value should be valid
    assert not pd.isna(result["rsi"].iloc[10])


def test_rsi_trending_up(trending_up_data):
    """Test RSI with trending up data."""
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(trending_up_data)
    
    valid_rsi = result["rsi"].dropna()
    if len(valid_rsi) > 0:
        # In an uptrend, RSI should generally be above 50
        # Check that most values are above 50
        above_50 = (valid_rsi > 50).sum()
        assert above_50 > len(valid_rsi) * 0.5


def test_rsi_trending_down(trending_down_data):
    """Test RSI with trending down data."""
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(trending_down_data)
    
    valid_rsi = result["rsi"].dropna()
    if len(valid_rsi) > 0:
        # In a downtrend, RSI should generally be below 50
        # Check that most values are below 50
        below_50 = (valid_rsi < 50).sum()
        assert below_50 > len(valid_rsi) * 0.5


def test_rsi_constant_price(constant_price_data):
    """Test RSI with constant price data."""
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(constant_price_data)
    
    # With constant prices, there are no gains or losses
    # RSI calculation should handle this (division by zero case)
    valid_rsi = result["rsi"].dropna()
    if len(valid_rsi) > 0:
        # When avg_loss is 0, RSI should be 100 (or NaN if handled differently)
        # Most implementations return NaN or 100
        assert (valid_rsi.isna() | (valid_rsi == 100)).all()


def test_rsi_invalid_period():
    """Test RSI with invalid period."""
    with pytest.raises(ValueError, match="Period must be greater than 0"):
        RSIIndicator(period=0)
    
    with pytest.raises(ValueError, match="Period must be greater than 0"):
        RSIIndicator(period=-1)


def test_rsi_none_input():
    """Test RSI with None input."""
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(None)
    
    # Should return empty series
    assert len(result["rsi"]) == 0


def test_rsi_calculate_from_dataframe(sample_price_data):
    """Test RSI calculation from DataFrame."""
    df = pd.DataFrame({
        "close": sample_price_data,
    })
    
    indicator = RSIIndicator(period=14)
    result = indicator.calculate_from_dataframe(df)
    
    assert "rsi" in result
    assert len(result["rsi"]) == len(df)


def test_rsi_calculate_from_dataframe_custom_column():
    """Test RSI calculation from DataFrame with custom column name."""
    df = pd.DataFrame({
        "C": [100, 101, 102, 103, 104, 105] * 10,
    })
    
    indicator = RSIIndicator(period=14)
    result = indicator.calculate_from_dataframe(df, close_col="C")
    
    assert "rsi" in result
    assert len(result["rsi"]) == len(df)


def test_rsi_calculate_from_dataframe_missing_column():
    """Test RSI calculation from DataFrame with missing column."""
    df = pd.DataFrame({
        "high": [100, 101, 102],
        "low": [99, 100, 101],
        # Missing "close" column
    })
    
    indicator = RSIIndicator(period=14)
    
    with pytest.raises(ValueError, match="Column 'close' not found"):
        indicator.calculate_from_dataframe(df)


def test_rsi_kwargs_override(sample_price_data):
    """Test that kwargs can override default parameters."""
    indicator = RSIIndicator(period=14)
    result_default = indicator.calculate(sample_price_data)
    
    result_override = indicator.calculate(sample_price_data, period=10)
    
    # Results should be different
    assert not result_default["rsi"].equals(result_override["rsi"])


def test_rsi_range():
    """Test that RSI values are within valid range (0-100)."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    # Create more volatile data
    prices = 100 + np.cumsum(np.random.randn(100) * 2)
    data = pd.Series(prices, index=dates)
    
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(data)
    
    valid_rsi = result["rsi"].dropna()
    if len(valid_rsi) > 0:
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


def test_rsi_known_values():
    """Test RSI calculation with known values."""
    # Create simple data where we can verify RSI calculation
    # 14 periods of gains followed by 14 periods of losses
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    prices = [100]
    for i in range(1, 15):
        prices.append(prices[-1] + 1)  # Gains
    for i in range(15, 30):
        prices.append(prices[-1] - 1)  # Losses
    
    data = pd.Series(prices, index=dates)
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(data)
    
    # First valid RSI should be high (after 14 gains)
    valid_rsi = result["rsi"].dropna()
    if len(valid_rsi) > 0:
        # After gains, RSI should be high
        assert valid_rsi.iloc[0] > 50


def test_rsi_on_ndx_index():
    """
    Integration test: Calculate RSI on real NASDAQ Index (NDX) data.
    
    This test:
    1. Fetches historical NDX data from IB TWS (if available)
    2. Calculates RSI using Close prices
    3. Exports results to CSV file in data/rsi/ndx/YYYYMMDD/ folder structure
    
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
        app.connect(config.host, config.port, clientId=203)
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
        print("\n[3/4] Processing data and calculating RSI...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip("No data available. Skipping integration test.")
        
        df = pd.DataFrame(data)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
        
        # Calculate RSI
        close_prices = df["Close"]
        indicator = RSIIndicator(period=14)
        rsi_result = indicator.calculate(close_prices)
        
        # Combine original data with RSI values
        result_df = df.copy()
        result_df["RSI"] = rsi_result["rsi"]
        
        # Create folder structure: data/rsi/ndx/YYYYMMDD/
        current_date = datetime.now().strftime("%Y%m%d")
        base_dir = Path(__file__).parent.parent / "data" / "rsi" / "ndx" / current_date
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        print("\n[4/4] Exporting results to CSV...")
        output_file = base_dir / f"ndx_rsi_{current_date}.csv"
        
        # Reset index to include Date as a column for better CSV readability
        export_df = result_df.reset_index()
        export_df.to_csv(output_file, index=False)
        print(f"   Exported to: {output_file}")
        print(f"   Rows: {len(export_df)}, Columns: {list(export_df.columns)}")
        
        # Verify file exists and has data
        assert output_file.exists(), f"Export file does not exist: {output_file}"
        assert len(export_df) > 0, "No data in result DataFrame"
        assert "RSI" in export_df.columns, "RSI column not found"
        
        # Display summary
        print("\n" + "=" * 70)
        print("RSI INTEGRATION TEST COMPLETED")
        print("=" * 70)
        print(f"Output file: {output_file}")
        print(f"Folder structure: data/rsi/ndx/{current_date}/")
        print(f"Data points: {len(export_df)}")
        print(f"Valid RSI values: {export_df['RSI'].notna().sum()}")
        if export_df['RSI'].notna().any():
            valid_rsi = export_df['RSI'].dropna()
            print(f"RSI range: {valid_rsi.min():.2f} - {valid_rsi.max():.2f}")
            print(f"RSI mean: {valid_rsi.mean():.2f}")
            # Count overbought (>70) and oversold (<30) conditions
            overbought = (valid_rsi > 70).sum()
            oversold = (valid_rsi < 30).sum()
            print(f"Overbought conditions (RSI > 70): {overbought}")
            print(f"Oversold conditions (RSI < 30): {oversold}")
        print("=" * 70)
        
    finally:
        app.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
