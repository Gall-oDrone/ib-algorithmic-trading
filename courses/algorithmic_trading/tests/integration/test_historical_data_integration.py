"""
Integration test for HistoricalDataHandler with real IB Trader Workstation connection.

This test requires:
1. IB Trader Workstation (TWS) or IB Gateway running
2. Paper trading account connected
3. API connections enabled in TWS/Gateway settings

Run with: pytest tests/test_historical_data_integration.py -v -s
"""

import sys
import time
import threading
from pathlib import Path

import pytest
import pandas as pd

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import BarData

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from handlers.historical_data_handler import HistoricalDataHandler, DEFAULT_OUTPUT_DIR
from handlers.contract_handler import ContractHandler
from config import get_config

# Same tickers as in trading_app.py fetch_stock_data method
DEFAULT_TICKERS = ["AMZN", "TSLA", "NVDA"]


class SimpleTestApp(EWrapper, EClient):
    """Simple test application for IB API integration testing."""
    
    def __init__(self):
        EClient.__init__(self, self)
        self.data_handler = HistoricalDataHandler()
        self.contract_handler = ContractHandler()
        self.connected = False
        self.data_received = {i: False for i in range(len(DEFAULT_TICKERS))}
        
    def nextValidId(self, orderId):
        """Called when connection is established."""
        self.connected = True
        print(f"   Connected! Next valid order ID: {orderId}")
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=''):
        """Handle errors."""
        # Filter out informational messages (2104, 2106, 2158 are connection confirmations)
        if errorCode not in [2104, 2106, 2158]:
            print(f"   Error {reqId} {errorCode}: {errorString}")
    
    def historicalData(self, reqId, bar: BarData):
        """Receive historical data bars."""
        self.data_handler.add_bar(reqId, bar)
    
    def historicalDataEnd(self, reqId, start, end):
        """Called when historical data request completes."""
        self.data_received[reqId] = True
        symbol = self.data_handler.get_symbol(reqId)
        print(f"   Historical data complete for {symbol} (req_id={reqId}): {start} to {end}")


class TestHistoricalDataIntegration:
    """Integration tests for fetching real historical data from IB TWS."""

    def test_fetch_real_historical_data_and_export(self):
        """
        Integration test: Connect to IB TWS, fetch historical data for AMZN, TSLA, NVDA,
        and export to CSV files in the historical_output folder.
        
        Prerequisites:
        - IB Trader Workstation or IB Gateway must be running
        - Paper trading account must be connected
        - API connections must be enabled (Edit > Global Configuration > API > Settings)
        """
        config = get_config()
        
        print("\n" + "=" * 70)
        print("INTEGRATION TEST: Fetching Real Historical Data from IB TWS")
        print("=" * 70)
        print(f"Host: {config.host}")
        print(f"Port: {config.port}")
        print(f"Tickers: {DEFAULT_TICKERS}")
        print("=" * 70)
        
        # Create test app
        app = SimpleTestApp()
        
        # Step 1: Connect to IB TWS
        print("\n[1/5] Connecting to IB Trader Workstation...")
        try:
            app.connect(config.host, config.port, clientId=200)
            
            # Start message processing thread
            api_thread = threading.Thread(target=app.run, daemon=True)
            api_thread.start()
            
            # Wait for connection
            time.sleep(3)
            
            if not app.isConnected():
                pytest.skip("Could not connect to IB TWS. Make sure TWS is running with API enabled.")
            
            print("   Connected successfully!")
            
        except Exception as e:
            pytest.skip(f"Could not connect to IB TWS: {e}")
        
        try:
            # Step 2: Request historical data for all tickers
            print(f"\n[2/5] Requesting historical data for {DEFAULT_TICKERS}...")
            
            for i, ticker in enumerate(DEFAULT_TICKERS):
                contract = app.contract_handler.create_contract(ticker)
                app.data_handler.register_request(i, ticker)
                
                app.reqHistoricalData(
                    reqId=i,
                    contract=contract,
                    endDateTime="",
                    durationStr="1 D",
                    barSizeSetting="30 mins",
                    whatToShow="ADJUSTED_LAST",
                    useRTH=1,
                    formatDate=1,
                    keepUpToDate=False,
                    chartOptions=[]
                )
                print(f"   Requested data for {ticker} (req_id={i})")
                time.sleep(1)  # Small delay between requests
            
            # Step 3: Wait for data to be received
            print("\n[3/5] Waiting for data to be received...")
            max_wait = 30  # seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if all(app.data_received.values()):
                    break
                time.sleep(1)
            
            # Step 4: Get the data as DataFrames
            print("\n[4/5] Processing received data...")
            
            all_data = app.data_handler.get_all_data()
            
            if not all_data:
                pytest.fail("No data received from IB TWS. Check if market data subscription is active.")
            
            print(f"   Received data for {len(all_data)} ticker(s)")
            
            # Display the data
            print("\n" + "-" * 70)
            print("RECEIVED HISTORICAL DATA")
            print("-" * 70)
            
            for req_id, data in all_data.items():
                symbol = app.data_handler.get_symbol(req_id)
                df = pd.DataFrame(data)
                if "Date" in df.columns:
                    df.set_index("Date", inplace=True)
                
                print(f"\n=== {symbol} ===")
                print(f"Shape: {df.shape}")
                if not df.empty:
                    print(f"Date Range: {df.index[0]} to {df.index[-1]}")
                    print(df.head(10))
                    print(f"... ({len(df)} total bars)")
                else:
                    print("   (No data received)")
            
            # Step 5: Export to CSV files
            print("\n[5/5] Exporting data to CSV files...")
            
            exported_files = app.data_handler.export_data(
                output_format="csv",
                output_path=DEFAULT_OUTPUT_DIR,
                keep_files=True
            )
            
            print(f"\n   Exported {len(exported_files)} file(s) to: {DEFAULT_OUTPUT_DIR}")
            
            # Verify and display exported files
            print("\n" + "-" * 70)
            print("EXPORTED FILES")
            print("-" * 70)
            
            for ticker, file_path in exported_files.items():
                assert file_path.exists(), f"Export file does not exist: {file_path}"
                
                # Read and verify the exported file
                df = pd.read_csv(file_path, index_col=0)
                print(f"\n{ticker}: {file_path}")
                print(f"   Rows: {len(df)}, Columns: {list(df.columns)}")
            
            # Final summary
            print("\n" + "=" * 70)
            print("INTEGRATION TEST COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print(f"Output directory: {DEFAULT_OUTPUT_DIR}")
            print(f"Files exported: {list(exported_files.keys())}")
            
            # Assertions
            assert len(exported_files) > 0, "No files were exported"
            for ticker, file_path in exported_files.items():
                assert file_path.exists(), f"File {file_path} does not exist"
                
        finally:
            # Cleanup
            print("\nDisconnecting...")
            app.disconnect()


class TestHistoricalDataIntegrationQuick:
    """Quick integration test with a single ticker."""

    def test_fetch_single_ticker(self):
        """
        Quick integration test: Fetch historical data for a single ticker (AAPL).
        """
        config = get_config()
        ticker = "AAPL"
        
        print("\n" + "=" * 70)
        print(f"QUICK INTEGRATION TEST: Fetching {ticker} from IB TWS")
        print("=" * 70)
        
        app = SimpleTestApp()
        
        # Connect
        print("\n[1/4] Connecting to IB TWS...")
        try:
            app.connect(config.host, config.port, clientId=201)
            
            api_thread = threading.Thread(target=app.run, daemon=True)
            api_thread.start()
            
            time.sleep(3)
            
            if not app.isConnected():
                pytest.skip("Could not connect to IB TWS.")
            
            print("   Connected!")
            
        except Exception as e:
            pytest.skip(f"Could not connect to IB TWS: {e}")
        
        try:
            # Fetch data
            print(f"\n[2/4] Requesting historical data for {ticker}...")
            contract = app.contract_handler.create_contract(ticker)
            app.data_handler.register_request(0, ticker)
            
            app.reqHistoricalData(
                reqId=0,
                contract=contract,
                endDateTime="",
                durationStr="1 D",
                barSizeSetting="5 mins",
                whatToShow="ADJUSTED_LAST",
                useRTH=1,
                formatDate=1,
                keepUpToDate=False,
                chartOptions=[]
            )
            
            # Wait
            print("\n[3/4] Waiting for data (15 seconds)...")
            time.sleep(15)
            
            # Export
            print("\n[4/4] Exporting data...")
            data = app.data_handler.get_data(0)
            
            if data:
                exported_files = app.data_handler.export_data(
                    req_id=0,
                    output_format="csv",
                    output_path=DEFAULT_OUTPUT_DIR,
                    keep_files=True
                )
                
                print(f"\n   Data received: {len(data)} bars")
                print(f"   Exported to: {exported_files.get(ticker, 'N/A')}")
                
                # Show sample data
                df = pd.DataFrame(data)
                print(f"\n=== {ticker} Historical Data ===")
                print(df.head(10))
            else:
                print("\n   No data received. Check market data subscription.")
            
            print("\n" + "=" * 70)
            print("QUICK TEST COMPLETED")
            print("=" * 70)
            
        finally:
            app.disconnect()


if __name__ == "__main__":
    # Run the integration test directly
    pytest.main([__file__, "-v", "-s", "-k", "test_fetch_real_historical_data_and_export"])
