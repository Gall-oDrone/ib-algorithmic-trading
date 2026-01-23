"""
Enhanced integration test for NDX Index with multiple indicators, timeframes, 
visualizations, and benchmark comparisons.

This test:
1. Fetches NDX data for multiple timeframes (daily, weekly, monthly)
2. Calculates multiple indicators (Bollinger Bands, ATR, MACD)
3. Generates visualizations/charts
4. Compares indicators with benchmarks (SMA, EMA)
5. Exports comprehensive results to CSV and charts to PNG files

Prerequisites:
- IB Trader Workstation or IB Gateway must be running
- Paper trading account must be connected
- API connections must be enabled

Run with: pytest tests/test_ndx_indicators_integration.py -v -s
"""

import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional

import pytest
import pandas as pd
import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import IB API only when needed (inside test functions)
# This allows the module to be imported even if ibapi is not available
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.common import BarData
    IBAPI_AVAILABLE = True
except ImportError:
    IBAPI_AVAILABLE = False

from handlers.historical_data_handler import HistoricalDataHandler, DEFAULT_OUTPUT_DIR
from handlers.contract_handler import ContractHandler
from config import get_config
from indicators.bollinger_bands import BollingerBandsIndicator
from indicators.atr import ATRIndicator
from indicators.macd import MACDIndicator


if IBAPI_AVAILABLE:
    class NDXMultiTimeframeApp(EWrapper, EClient):
        """App for fetching NDX data across multiple timeframes."""
        
        def __init__(self):
            EClient.__init__(self, self)
            self.data_handler = HistoricalDataHandler()
            self.contract_handler = ContractHandler()
            self.connected = False
            self.data_received: Dict[int, bool] = {}
            self.request_configs: Dict[int, Dict] = {}  # Store request configs
            
        def nextValidId(self, orderId):
            self.connected = True
            
        def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=''):
            if errorCode not in [2104, 2106, 2158]:
                print(f"   Error {reqId} {errorCode}: {errorString}")
        
        def historicalData(self, reqId, bar: BarData):
            self.data_handler.add_bar(reqId, bar)
        
        def historicalDataEnd(self, reqId, start, end):
            self.data_received[reqId] = True
            config = self.request_configs.get(reqId, {})
            timeframe = config.get('timeframe', 'unknown')
            print(f"   Historical data complete for NDX ({timeframe}): {start} to {end}")
else:
    # Dummy class when IBAPI is not available
    class NDXMultiTimeframeApp:
        pass


def fetch_ndx_data(
    app: NDXMultiTimeframeApp,
    timeframe: str,
    duration: str,
    bar_size: str,
    req_id: int,
    what_to_show: str = "ADJUSTED_LAST"
) -> bool:
    """
    Fetch NDX data for a specific timeframe.
    
    Args:
        app: NDXMultiTimeframeApp instance
        timeframe: Timeframe label (e.g., 'daily', 'weekly', 'monthly')
        duration: Duration string (e.g., '1 Y')
        bar_size: Bar size (e.g., '1 day', '1 week', '1 month')
        req_id: Request ID
        
    Returns:
        True if request was successful
    """
    try:
        contract = app.contract_handler.create_contract(
            "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
        )
        app.data_handler.register_request(req_id, f"NDX_{timeframe}")
        app.request_configs[req_id] = {
            'timeframe': timeframe,
            'duration': duration,
            'bar_size': bar_size
        }
        app.data_received[req_id] = False
        
        app.reqHistoricalData(
            reqId=req_id,
            contract=contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="ADJUSTED_LAST",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )
        return True
    except Exception as e:
        print(f"   Error requesting {timeframe} data: {e}")
        return False


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all indicators on a DataFrame.
    
    Args:
        df: DataFrame with OHLC data
        
    Returns:
        DataFrame with original data + all indicator columns
    """
    result_df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    
    # Bollinger Bands
    bb_indicator = BollingerBandsIndicator(period=20, num_std=2.0)
    bb_result = bb_indicator.calculate(close)
    result_df["BB_Middle"] = bb_result["middle"]
    result_df["BB_Upper"] = bb_result["upper"]
    result_df["BB_Lower"] = bb_result["lower"]
    result_df["BB_Bandwidth"] = bb_indicator.get_bandwidth(close)
    result_df["BB_PercentB"] = bb_indicator.get_percent_b(close)
    
    # ATR
    atr_indicator = ATRIndicator(period=14)
    atr_result = atr_indicator.calculate(high, low, close)
    result_df["ATR"] = atr_result["atr"]
    
    # MACD
    macd_indicator = MACDIndicator(fast_period=12, slow_period=26, signal_period=9)
    macd_result = macd_indicator.calculate(close)
    result_df["MACD"] = macd_result["macd"]
    result_df["MACD_Signal"] = macd_result["signal"]
    result_df["MACD_Histogram"] = macd_result["histogram"]
    
    # Benchmark indicators (SMA and EMA for comparison)
    result_df["SMA_20"] = close.rolling(window=20, min_periods=20).mean()
    result_df["SMA_50"] = close.rolling(window=50, min_periods=50).mean()
    result_df["EMA_12"] = close.ewm(span=12, adjust=False).mean()
    result_df["EMA_26"] = close.ewm(span=26, adjust=False).mean()
    
    # Additional comparison metrics
    result_df["BB_vs_SMA20"] = result_df["BB_Middle"] - result_df["SMA_20"]
    result_df["MACD_vs_Signal"] = result_df["MACD"] - result_df["MACD_Signal"]
    
    return result_df


def create_visualizations(
    df: pd.DataFrame,
    timeframe: str,
    output_dir: Path
) -> List[Path]:
    """
    Create visualization charts for the indicators.
    
    Args:
        df: DataFrame with price and indicator data
        timeframe: Timeframe label
        output_dir: Base output directory (charts will go in charts/ subfolder)
        
    Returns:
        List of paths to created chart files
    """
    if not MATPLOTLIB_AVAILABLE:
        print("   Matplotlib not available, skipping chart generation")
        return []
    
    # Create charts subdirectory
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    chart_files = []
    
    # Chart 1: Price with Bollinger Bands
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(df.index, df["Close"], label="Close Price", linewidth=1.5, color='black')
    ax.plot(df.index, df["BB_Upper"], label="BB Upper", linestyle='--', alpha=0.7, color='red')
    ax.plot(df.index, df["BB_Middle"], label="BB Middle", linestyle='--', alpha=0.7, color='blue')
    ax.plot(df.index, df["BB_Lower"], label="BB Lower", linestyle='--', alpha=0.7, color='red')
    ax.fill_between(df.index, df["BB_Upper"], df["BB_Lower"], alpha=0.1, color='gray')
    ax.set_title(f"NDX Index - Price with Bollinger Bands ({timeframe})", fontsize=14, fontweight='bold')
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart_file = charts_dir / f"NDX_BollingerBands_{timeframe}.png"
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    chart_files.append(chart_file)
    print(f"   Created chart: charts/{chart_file.name}")
    
    # Chart 2: MACD
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Price on top
    ax1.plot(df.index, df["Close"], label="Close Price", linewidth=1.5, color='black')
    ax1.set_title(f"NDX Index - Price and MACD ({timeframe})", fontsize=14, fontweight='bold')
    ax1.set_ylabel("Price")
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # MACD on bottom
    ax2.plot(df.index, df["MACD"], label="MACD", linewidth=1.5, color='blue')
    ax2.plot(df.index, df["MACD_Signal"], label="Signal", linewidth=1.5, color='red')
    ax2.bar(df.index, df["MACD_Histogram"], label="Histogram", alpha=0.6, color='green')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_xlabel("Date")
    ax2.set_ylabel("MACD")
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart_file = charts_dir / f"NDX_MACD_{timeframe}.png"
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    chart_files.append(chart_file)
    print(f"   Created chart: charts/{chart_file.name}")
    
    # Chart 3: ATR and Volatility
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Price on top
    ax1.plot(df.index, df["Close"], label="Close Price", linewidth=1.5, color='black')
    ax1.set_title(f"NDX Index - Price and ATR ({timeframe})", fontsize=14, fontweight='bold')
    ax1.set_ylabel("Price")
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # ATR on bottom
    ax2.plot(df.index, df["ATR"], label="ATR", linewidth=1.5, color='purple')
    ax2.set_xlabel("Date")
    ax2.set_ylabel("ATR")
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart_file = charts_dir / f"NDX_ATR_{timeframe}.png"
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    chart_files.append(chart_file)
    print(f"   Created chart: charts/{chart_file.name}")
    
    # Chart 4: Comprehensive comparison with benchmarks
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(df.index, df["Close"], label="Close Price", linewidth=2, color='black')
    ax.plot(df.index, df["BB_Middle"], label="BB Middle (SMA 20)", linestyle='--', alpha=0.7, color='blue')
    ax.plot(df.index, df["SMA_20"], label="SMA 20", linestyle=':', alpha=0.7, color='green')
    ax.plot(df.index, df["SMA_50"], label="SMA 50", linestyle=':', alpha=0.7, color='orange')
    ax.set_title(f"NDX Index - Price with Benchmark Indicators ({timeframe})", fontsize=14, fontweight='bold')
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart_file = charts_dir / f"NDX_BenchmarkComparison_{timeframe}.png"
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    chart_files.append(chart_file)
    print(f"   Created chart: charts/{chart_file.name}")
    
    return chart_files


def test_ndx_comprehensive_indicators_analysis():
    """
    Comprehensive integration test for NDX with multiple timeframes, indicators,
    visualizations, and benchmark comparisons.
    """
    if not IBAPI_AVAILABLE:
        pytest.skip("ibapi module not available. Install it to run integration tests.")
    
    config = get_config()
    app = NDXMultiTimeframeApp()
    
    # Timeframe configurations
    # Note: Weekly and monthly use "TRADES" instead of "ADJUSTED_LAST" 
    # because IB API doesn't support multi-day bars with adjusted data
    timeframes = [
        {"label": "daily", "duration": "1 Y", "bar_size": "1 day", "what_to_show": "ADJUSTED_LAST"},
        {"label": "weekly", "duration": "2 Y", "bar_size": "1 week", "what_to_show": "TRADES"},
        {"label": "monthly", "duration": "5 Y", "bar_size": "1 month", "what_to_show": "TRADES"},
    ]
    
    # Try to connect
    try:
        print("\n" + "=" * 70)
        print("COMPREHENSIVE NDX INDICATORS INTEGRATION TEST")
        print("=" * 70)
        print(f"Host: {config.host}, Port: {config.port}")
        print(f"Timeframes: {[tf['label'] for tf in timeframes]}")
        print("=" * 70)
        
        app.connect(config.host, config.port, clientId=300)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)
        
        if not app.isConnected():
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
        
        print("\n[1/6] Connected to IB TWS")
        
    except Exception as e:
        pytest.skip(f"Could not connect to IB TWS: {e}")
    
    try:
        # Step 1: Request data for all timeframes
        print("\n[2/6] Requesting NDX data for all timeframes...")
        for i, tf in enumerate(timeframes):
            success = fetch_ndx_data(
                app, tf["label"], tf["duration"], tf["bar_size"], req_id=i,
                what_to_show=tf.get("what_to_show", "ADJUSTED_LAST")
            )
            if success:
                print(f"   Requested {tf['label']} data (duration: {tf['duration']}, bar_size: {tf['bar_size']})")
            time.sleep(2)  # Delay between requests
        
        # Step 2: Wait for all data
        print("\n[3/6] Waiting for data to be received...")
        max_wait = 60  # Longer wait for multiple requests
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if all(app.data_received.get(i, False) for i in range(len(timeframes))):
                break
            time.sleep(2)
        
        received_count = sum(1 for i in range(len(timeframes)) if app.data_received.get(i, False))
        print(f"   Received data for {received_count}/{len(timeframes)} timeframes")
        
        if received_count == 0:
            pytest.skip("No data received from IB TWS. Skipping integration test.")
        
        # Step 3: Process data and calculate indicators
        print("\n[4/6] Processing data and calculating indicators...")
        output_dir = DEFAULT_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_results = {}
        all_chart_files = []
        
        for i, tf in enumerate(timeframes):
            if not app.data_received.get(i, False):
                print(f"   Skipping {tf['label']} - no data received")
                continue
            
            data = app.data_handler.get_data(i)
            if not data:
                print(f"   Skipping {tf['label']} - empty data")
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
            
            print(f"\n   Processing {tf['label']} data: {len(df)} bars")
            
            # Calculate all indicators
            result_df = calculate_all_indicators(df)
            all_results[tf["label"]] = result_df
            
            # Create organized folder structure
            bb_dir = output_dir / "bollinger_bands"
            macd_dir = output_dir / "macd"
            bb_dir.mkdir(parents=True, exist_ok=True)
            macd_dir.mkdir(parents=True, exist_ok=True)
            
            # Export Bollinger Bands data
            bb_columns = ["Open", "High", "Low", "Close", "Volume", 
                         "BB_Middle", "BB_Upper", "BB_Lower", "BB_Bandwidth", "BB_PercentB"]
            available_bb_cols = [col for col in bb_columns if col in result_df.columns]
            bb_df = result_df[available_bb_cols].copy()
            bb_df = bb_df.reset_index()  # Reset index to include Date as a column
            bb_csv = bb_dir / f"NDX_bollinger_bands_{tf['label']}.csv"
            bb_df.to_csv(bb_csv, index=False)
            print(f"   Exported Bollinger Bands CSV: bollinger_bands/{bb_csv.name} ({len(bb_df)} rows)")
            
            # Export MACD data
            macd_columns = ["Open", "High", "Low", "Close", "Volume",
                           "MACD", "MACD_Signal", "MACD_Histogram"]
            available_macd_cols = [col for col in macd_columns if col in result_df.columns]
            macd_df = result_df[available_macd_cols].copy()
            macd_df = macd_df.reset_index()  # Reset index to include Date as a column
            macd_csv = macd_dir / f"NDX_macd_{tf['label']}.csv"
            macd_df.to_csv(macd_csv, index=False)
            print(f"   Exported MACD CSV: macd/{macd_csv.name} ({len(macd_df)} rows)")
            
            # Export comprehensive CSV (all indicators)
            csv_file = output_dir / f"NDX_indicators_{tf['label']}.csv"
            result_df.to_csv(csv_file, index=True)
            print(f"   Exported comprehensive CSV: {csv_file.name} ({len(result_df)} rows, {len(result_df.columns)} columns)")
            
            # Create visualizations
            if MATPLOTLIB_AVAILABLE:
                print(f"   Creating visualizations for {tf['label']}...")
                chart_files = create_visualizations(result_df, tf["label"], output_dir)
                all_chart_files.extend(chart_files)
            else:
                print(f"   Skipping visualizations (matplotlib not available)")
        
        # Step 4: Create summary comparison
        print("\n[5/6] Creating summary comparison...")
        summary_data = []
        
        for timeframe, df in all_results.items():
            if df.empty:
                continue
            
            # Calculate summary statistics
            valid_bb = df["BB_Middle"].notna().sum()
            valid_atr = df["ATR"].notna().sum()
            valid_macd = df["MACD"].notna().sum()
            
            if valid_bb > 0:
                summary_data.append({
                    "Timeframe": timeframe,
                    "Total_Bars": len(df),
                    "BB_Valid_Points": valid_bb,
                    "ATR_Valid_Points": valid_atr,
                    "MACD_Valid_Points": valid_macd,
                    "BB_Avg_Bandwidth": df["BB_Bandwidth"].mean(),
                    "ATR_Mean": df["ATR"].mean(),
                    "ATR_Std": df["ATR"].std(),
                    "Price_Range": df["Close"].max() - df["Close"].min(),
                    "Price_Change_Pct": ((df["Close"].iloc[-1] / df["Close"].iloc[0]) - 1) * 100,
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_file = output_dir / "NDX_indicators_summary.csv"
            summary_df.to_csv(summary_file, index=False)
            print(f"   Created summary: {summary_file.name}")
            print("\n" + summary_df.to_string(index=False))
        
        # Update file listing to show organized structure
        print("\n" + "-" * 70)
        print("ORGANIZED FILE STRUCTURE")
        print("-" * 70)
        if (output_dir / "bollinger_bands").exists():
            bb_files = list((output_dir / "bollinger_bands").glob("*.csv"))
            if bb_files:
                print(f"\nbollinger_bands/ ({len(bb_files)} files):")
                for f in bb_files:
                    print(f"  - {f.name}")
        
        if (output_dir / "macd").exists():
            macd_files = list((output_dir / "macd").glob("*.csv"))
            if macd_files:
                print(f"\nmacd/ ({len(macd_files)} files):")
                for f in macd_files:
                    print(f"  - {f.name}")
        
        if (output_dir / "charts").exists():
            chart_files = list((output_dir / "charts").glob("*.png"))
            if chart_files:
                print(f"\ncharts/ ({len(chart_files)} files):")
                for f in chart_files:
                    print(f"  - {f.name}")
        
        # Step 5: Final report
        print("\n[6/6] Final Report")
        print("=" * 70)
        print("COMPREHENSIVE NDX INDICATORS ANALYSIS COMPLETED")
        print("=" * 70)
        print(f"Output directory: {output_dir}")
        print(f"Timeframes processed: {len(all_results)}")
        print(f"Bollinger Bands CSV files: {len([f for f in (output_dir / 'bollinger_bands').glob('*.csv') if (output_dir / 'bollinger_bands').exists()])}")
        print(f"MACD CSV files: {len([f for f in (output_dir / 'macd').glob('*.csv') if (output_dir / 'macd').exists()])}")
        print(f"Chart files: {len(all_chart_files)}")
        
        print("\nOrganized Structure:")
        print(f"  data/historical_output/")
        print(f"    ├── bollinger_bands/")
        print(f"    ├── macd/")
        print(f"    ├── charts/")
        print(f"    └── NDX_indicators_summary.csv")
        
        print("=" * 70)
        
        # Assertions
        assert len(all_results) > 0, "No data was processed"
        for timeframe, df in all_results.items():
            assert len(df) > 0, f"No data in {timeframe} DataFrame"
            assert "BB_Middle" in df.columns, f"Bollinger Bands not found in {timeframe}"
            assert "ATR" in df.columns, f"ATR not found in {timeframe}"
            assert "MACD" in df.columns, f"MACD not found in {timeframe}"
        
        # Verify files exist
        for timeframe in all_results.keys():
            csv_file = output_dir / f"NDX_indicators_{timeframe}.csv"
            assert csv_file.exists(), f"CSV file does not exist: {csv_file}"
        
    finally:
        app.disconnect()
        print("\nDisconnected from IB TWS")


def test_ndx_intraday_5min_indicators():
    """
    Integration test: Calculate indicators on NDX Index with 5-minute candles for current day.
    
    This test:
    1. Fetches NDX intraday data (5-minute bars) for the current trading day
    2. Calculates all indicators (Bollinger Bands, ATR, MACD)
    3. Generates visualizations/charts
    4. Exports results to organized folder structure
    
    Prerequisites:
    - IB Trader Workstation or IB Gateway must be running
    - Paper trading account must be connected
    - API connections must be enabled
    - Market must be open (or recent trading day data available)
    
    If IB connection is not available, the test will be skipped.
    """
    if not IBAPI_AVAILABLE:
        pytest.skip("ibapi module not available. Install it to run integration tests.")
    
    config = get_config()
    app = NDXMultiTimeframeApp()
    
    # Try to connect
    try:
        print("\n" + "=" * 70)
        print("NDX INTRADAY 5-MINUTE INDICATORS TEST")
        print("=" * 70)
        print(f"Host: {config.host}, Port: {config.port}")
        print("Timeframe: Current day, 5-minute candles")
        print("=" * 70)
        
        app.connect(config.host, config.port, clientId=301)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)
        
        if not app.isConnected():
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
        
        print("\n[1/5] Connected to IB TWS")
        
    except Exception as e:
        pytest.skip(f"Could not connect to IB TWS: {e}")
    
    try:
        # Request current day 5-minute data
        print("\n[2/5] Requesting NDX intraday data (5-minute candles, current day)...")
        contract = app.contract_handler.create_contract(
            "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
        )
        app.data_handler.register_request(0, "NDX_5min")
        app.request_configs[0] = {
            'timeframe': '5min_intraday',
            'duration': '1 D',
            'bar_size': '5 mins'
        }
        app.data_received[0] = False
        
        app.reqHistoricalData(
            reqId=0,
            contract=contract,
            endDateTime="",  # Current time
            durationStr="1 D",  # Current day
            barSizeSetting="5 mins",  # 5-minute bars
            whatToShow="TRADES",  # Use TRADES for intraday data
            useRTH=1,  # Regular trading hours only
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )
        print("   Requested NDX data (1 day, 5-minute bars, regular trading hours)")
        
        # Wait for data
        print("\n[3/5] Waiting for data to be received...")
        max_wait = 30
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if app.data_received.get(0, False):
                break
            time.sleep(1)
        
        if not app.data_received.get(0, False):
            pytest.skip("No data received from IB TWS. Skipping integration test.")
        
        # Get data as DataFrame
        print("\n[4/5] Processing data and calculating indicators...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip("No data available. Skipping integration test.")
        
        df = pd.DataFrame(data)
        if "Date" in df.columns:
            # Handle IB API date format: "20260122 09:30:00 US/Eastern"
            # Try to parse with different formats
            try:
                df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d %H:%M:%S %Z")
            except:
                try:
                    # Try parsing without timezone
                    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d %H:%M:%S")
                except:
                    # Fallback to pandas auto-parsing
                    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
            df.set_index("Date", inplace=True)
        
        print(f"   Received {len(df)} 5-minute bars")
        
        if len(df) == 0:
            pytest.skip("No data received. Market may be closed or no data available.")
        
        # Calculate all indicators
        result_df = calculate_all_indicators(df)
        
        # Create organized folder structure
        output_dir = DEFAULT_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        bb_dir = output_dir / "bollinger_bands"
        macd_dir = output_dir / "macd"
        bb_dir.mkdir(parents=True, exist_ok=True)
        macd_dir.mkdir(parents=True, exist_ok=True)
        
        # Export Bollinger Bands data
        bb_columns = ["Open", "High", "Low", "Close", "Volume", 
                     "BB_Middle", "BB_Upper", "BB_Lower", "BB_Bandwidth", "BB_PercentB"]
        available_bb_cols = [col for col in bb_columns if col in result_df.columns]
        bb_df = result_df[available_bb_cols].copy()
        bb_df = bb_df.reset_index()
        bb_csv = bb_dir / "NDX_bollinger_bands_5min_intraday.csv"
        bb_df.to_csv(bb_csv, index=False)
        print(f"   Exported Bollinger Bands CSV: bollinger_bands/{bb_csv.name} ({len(bb_df)} rows)")
        
        # Export MACD data
        macd_columns = ["Open", "High", "Low", "Close", "Volume",
                       "MACD", "MACD_Signal", "MACD_Histogram"]
        available_macd_cols = [col for col in macd_columns if col in result_df.columns]
        macd_df = result_df[available_macd_cols].copy()
        macd_df = macd_df.reset_index()
        macd_csv = macd_dir / "NDX_macd_5min_intraday.csv"
        macd_df.to_csv(macd_csv, index=False)
        print(f"   Exported MACD CSV: macd/{macd_csv.name} ({len(macd_df)} rows)")
        
        # Export comprehensive CSV
        csv_file = output_dir / "NDX_indicators_5min_intraday.csv"
        result_df.to_csv(csv_file, index=True)
        print(f"   Exported comprehensive CSV: {csv_file.name} ({len(result_df)} rows, {len(result_df.columns)} columns)")
        
        # Create visualizations
        if MATPLOTLIB_AVAILABLE:
            print("\n   Creating visualizations...")
            chart_files = create_visualizations(result_df, "5min_intraday", output_dir)
            print(f"   Created {len(chart_files)} chart(s)")
        else:
            print("   Skipping visualizations (matplotlib not available)")
        
        # Display summary
        print("\n[5/5] Final Report")
        print("=" * 70)
        print("NDX INTRADAY 5-MINUTE INDICATORS TEST COMPLETED")
        print("=" * 70)
        print(f"Output directory: {output_dir}")
        print(f"Data points: {len(result_df)}")
        print(f"Time range: {result_df.index[0]} to {result_df.index[-1]}")
        print(f"Valid BB values: {result_df['BB_Middle'].notna().sum()}")
        print(f"Valid ATR values: {result_df['ATR'].notna().sum()}")
        print(f"Valid MACD values: {result_df['MACD'].notna().sum()}")
        
        if result_df['ATR'].notna().any():
            print(f"ATR range: {result_df['ATR'].min():.2f} - {result_df['ATR'].max():.2f}")
        
        print("\nGenerated Files:")
        print(f"  - bollinger_bands/{bb_csv.name}")
        print(f"  - macd/{macd_csv.name}")
        print(f"  - {csv_file.name}")
        if MATPLOTLIB_AVAILABLE and chart_files:
            for chart_file in chart_files:
                print(f"  - charts/{chart_file.name}")
        
        print("=" * 70)
        
        # Assertions
        assert len(result_df) > 0, "No data in result DataFrame"
        assert "BB_Middle" in result_df.columns, "Bollinger Bands not found"
        assert "ATR" in result_df.columns, "ATR not found"
        assert "MACD" in result_df.columns, "MACD not found"
        
        # Verify files exist
        assert bb_csv.exists(), f"Bollinger Bands CSV file does not exist: {bb_csv}"
        assert macd_csv.exists(), f"MACD CSV file does not exist: {macd_csv}"
        assert csv_file.exists(), f"Comprehensive CSV file does not exist: {csv_file}"
        
    finally:
        app.disconnect()
        print("\nDisconnected from IB TWS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
