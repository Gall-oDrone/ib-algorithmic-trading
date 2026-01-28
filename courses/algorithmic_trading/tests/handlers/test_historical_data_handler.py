"""Tests for HistoricalDataHandler."""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pandas as pd

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from handlers.historical_data_handler import HistoricalDataHandler, DEFAULT_OUTPUT_DIR
from storage.dataframe_manager import DataFrameManager


# Same tickers as in trading_app.py fetch_stock_data method
DEFAULT_TICKERS = ["AMZN", "TSLA", "NVDA"]


@pytest.fixture
def historical_data_handler():
    """Fixture for HistoricalDataHandler."""
    return HistoricalDataHandler()


@pytest.fixture
def mock_bar_data():
    """Fixture for mock bar data."""
    def create_bar(date, open_, high, low, close, volume):
        bar = MagicMock()
        bar.date = date
        bar.open = open_
        bar.high = high
        bar.low = low
        bar.close = close
        bar.volume = volume
        return bar
    return create_bar


@pytest.fixture
def sample_bars(mock_bar_data):
    """Fixture for sample bar data for multiple tickers."""
    return {
        0: [  # AMZN (req_id=0)
            mock_bar_data("20260115 09:30:00", 185.50, 186.00, 185.25, 185.75, 10000),
            mock_bar_data("20260115 10:00:00", 185.75, 187.00, 185.50, 186.80, 12000),
            mock_bar_data("20260115 10:30:00", 186.80, 188.25, 186.50, 188.00, 15000),
            mock_bar_data("20260115 11:00:00", 188.00, 188.50, 187.00, 187.50, 11000),
            mock_bar_data("20260115 11:30:00", 187.50, 188.00, 186.75, 187.25, 9000),
        ],
        1: [  # TSLA (req_id=1)
            mock_bar_data("20260115 09:30:00", 250.00, 252.50, 249.50, 251.75, 50000),
            mock_bar_data("20260115 10:00:00", 251.75, 255.00, 251.00, 254.50, 65000),
            mock_bar_data("20260115 10:30:00", 254.50, 256.75, 253.25, 255.00, 72000),
            mock_bar_data("20260115 11:00:00", 255.00, 257.00, 254.00, 256.50, 58000),
            mock_bar_data("20260115 11:30:00", 256.50, 258.00, 255.50, 257.25, 45000),
        ],
        2: [  # NVDA (req_id=2)
            mock_bar_data("20260115 09:30:00", 145.00, 146.50, 144.50, 146.00, 80000),
            mock_bar_data("20260115 10:00:00", 146.00, 148.00, 145.75, 147.75, 95000),
            mock_bar_data("20260115 10:30:00", 147.75, 150.00, 147.00, 149.50, 110000),
            mock_bar_data("20260115 11:00:00", 149.50, 151.25, 148.75, 150.00, 100000),
            mock_bar_data("20260115 11:30:00", 150.00, 152.00, 149.25, 151.50, 85000),
        ],
    }


class TestHistoricalDataHandler:
    """Test class for HistoricalDataHandler."""

    def test_add_bar(self, historical_data_handler, mock_bar_data):
        """Test adding a single bar."""
        bar = mock_bar_data("20260115 09:30:00", 185.50, 186.00, 185.25, 185.75, 10000)
        
        historical_data_handler.add_bar(0, bar)
        
        data = historical_data_handler.get_data(0)
        assert len(data) == 1
        assert data[0]["Date"] == "20260115 09:30:00"
        assert data[0]["Open"] == 185.50
        assert data[0]["High"] == 186.00
        assert data[0]["Low"] == 185.25
        assert data[0]["Close"] == 185.75
        assert data[0]["Volume"] == 10000

    def test_add_multiple_bars(self, historical_data_handler, sample_bars):
        """Test adding multiple bars for a single ticker."""
        # Add all AMZN bars
        for bar in sample_bars[0]:
            historical_data_handler.add_bar(0, bar)
        
        data = historical_data_handler.get_data(0)
        assert len(data) == 5
        
        # Verify first and last bars
        assert data[0]["Date"] == "20260115 09:30:00"
        assert data[-1]["Date"] == "20260115 11:30:00"

    def test_register_request(self, historical_data_handler):
        """Test request registration."""
        for i, ticker in enumerate(DEFAULT_TICKERS):
            historical_data_handler.register_request(i, ticker)
        
        assert historical_data_handler.get_symbol(0) == "AMZN"
        assert historical_data_handler.get_symbol(1) == "TSLA"
        assert historical_data_handler.get_symbol(2) == "NVDA"

    def test_get_all_data(self, historical_data_handler, sample_bars):
        """Test getting all historical data."""
        # Add bars for all tickers
        for req_id, bars in sample_bars.items():
            for bar in bars:
                historical_data_handler.add_bar(req_id, bar)
        
        all_data = historical_data_handler.get_all_data()
        
        assert len(all_data) == 3
        assert all(req_id in all_data for req_id in [0, 1, 2])
        assert all(len(bars) == 5 for bars in all_data.values())

    def test_clear_specific_data(self, historical_data_handler, sample_bars):
        """Test clearing data for a specific request ID."""
        # Add bars for all tickers
        for req_id, bars in sample_bars.items():
            historical_data_handler.register_request(req_id, DEFAULT_TICKERS[req_id])
            for bar in bars:
                historical_data_handler.add_bar(req_id, bar)
        
        # Clear only TSLA data
        historical_data_handler.clear_data(1)
        
        assert len(historical_data_handler.get_data(0)) == 5  # AMZN still there
        assert len(historical_data_handler.get_data(1)) == 0  # TSLA cleared
        assert len(historical_data_handler.get_data(2)) == 5  # NVDA still there
        assert historical_data_handler.get_symbol(1) is None  # Symbol mapping cleared

    def test_clear_all_data(self, historical_data_handler, sample_bars):
        """Test clearing all historical data."""
        # Add bars for all tickers
        for req_id, bars in sample_bars.items():
            historical_data_handler.register_request(req_id, DEFAULT_TICKERS[req_id])
            for bar in bars:
                historical_data_handler.add_bar(req_id, bar)
        
        historical_data_handler.clear_data()
        
        all_data = historical_data_handler.get_all_data()
        assert len(all_data) == 0

    def test_get_nonexistent_data(self, historical_data_handler):
        """Test getting data for non-existent request ID."""
        data = historical_data_handler.get_data(999)
        assert data == []

    def test_get_nonexistent_symbol(self, historical_data_handler):
        """Test getting symbol for non-existent request ID."""
        symbol = historical_data_handler.get_symbol(999)
        assert symbol is None


class TestHistoricalDataToDataFrame:
    """Test class for converting historical data to DataFrames."""

    def test_create_dataframe_for_single_ticker(self, historical_data_handler, sample_bars):
        """Test creating DataFrame for a single ticker."""
        # Add AMZN bars
        for bar in sample_bars[0]:
            historical_data_handler.add_bar(0, bar)
        
        df_manager = DataFrameManager(historical_data_handler)
        df = df_manager.create_dataframe_from_data(historical_data_handler.get_data(0))
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
        
        print("\n=== AMZN DataFrame ===")
        print(df)

    def test_create_dataframes_for_all_tickers(self, historical_data_handler, sample_bars):
        """Test creating DataFrames for all tickers (AMZN, TSLA, NVDA)."""
        # Register and add bars for all tickers
        for req_id, bars in sample_bars.items():
            historical_data_handler.register_request(req_id, DEFAULT_TICKERS[req_id])
            for bar in bars:
                historical_data_handler.add_bar(req_id, bar)
        
        df_manager = DataFrameManager(historical_data_handler)
        dataframes = df_manager.create_dataframes(tickers=DEFAULT_TICKERS)
        
        assert len(dataframes) == 3
        assert all(ticker in dataframes for ticker in DEFAULT_TICKERS)
        
        print("\n" + "=" * 60)
        print("HISTORICAL DATA DATAFRAMES")
        print("=" * 60)
        
        for ticker in DEFAULT_TICKERS:
            df = dataframes[ticker]
            print(f"\n=== {ticker} Historical Data ===")
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print(df)
            print()
            
            # Verify DataFrame structure
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 5
            assert "Open" in df.columns
            assert "High" in df.columns
            assert "Low" in df.columns
            assert "Close" in df.columns
            assert "Volume" in df.columns

    def test_dataframe_data_integrity(self, historical_data_handler, sample_bars):
        """Test that DataFrame values match original bar data."""
        # Add NVDA bars with req_id=0 to match tickers list index
        for bar in sample_bars[2]:
            historical_data_handler.add_bar(0, bar)
        
        historical_data_handler.register_request(0, "NVDA")
        
        df_manager = DataFrameManager(historical_data_handler)
        dataframes = df_manager.create_dataframes(tickers=["NVDA"])
        
        df = dataframes["NVDA"]
        
        # Verify first bar values
        assert df.iloc[0]["Open"] == 145.00
        assert df.iloc[0]["High"] == 146.50
        assert df.iloc[0]["Low"] == 144.50
        assert df.iloc[0]["Close"] == 146.00
        assert df.iloc[0]["Volume"] == 80000
        
        # Verify last bar values
        assert df.iloc[-1]["Open"] == 150.00
        assert df.iloc[-1]["High"] == 152.00
        assert df.iloc[-1]["Low"] == 149.25
        assert df.iloc[-1]["Close"] == 151.50
        assert df.iloc[-1]["Volume"] == 85000

    def test_dataframe_statistics(self, historical_data_handler, sample_bars):
        """Test DataFrame statistics and display."""
        # Add all bars
        for req_id, bars in sample_bars.items():
            historical_data_handler.register_request(req_id, DEFAULT_TICKERS[req_id])
            for bar in bars:
                historical_data_handler.add_bar(req_id, bar)
        
        df_manager = DataFrameManager(historical_data_handler)
        dataframes = df_manager.create_dataframes(tickers=DEFAULT_TICKERS)
        
        print("\n" + "=" * 60)
        print("DATAFRAME STATISTICS")
        print("=" * 60)
        
        for ticker in DEFAULT_TICKERS:
            df = dataframes[ticker]
            print(f"\n=== {ticker} Statistics ===")
            print(df.describe())


class TestEmptyDataHandling:
    """Test edge cases with empty or missing data."""

    def test_empty_handler(self, historical_data_handler):
        """Test DataFrameManager with empty handler."""
        df_manager = DataFrameManager(historical_data_handler)
        dataframes = df_manager.create_dataframes(tickers=DEFAULT_TICKERS)
        
        # Should return empty dict or dfs for missing tickers
        assert isinstance(dataframes, dict)

    def test_partial_data(self, historical_data_handler, sample_bars):
        """Test with data for only some tickers."""
        # Only add AMZN data
        historical_data_handler.register_request(0, "AMZN")
        for bar in sample_bars[0]:
            historical_data_handler.add_bar(0, bar)
        
        df_manager = DataFrameManager(historical_data_handler)
        dataframes = df_manager.create_dataframes(tickers=DEFAULT_TICKERS)
        
        # Should have AMZN but not others
        assert "AMZN" in dataframes
        assert len(dataframes["AMZN"]) == 5


class TestExportData:
    """Test class for exporting historical data to various formats."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for test output."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_export_single_ticker_csv(self, historical_data_handler, sample_bars, temp_output_dir):
        """Test exporting a single ticker to CSV format."""
        # Add AMZN bars
        historical_data_handler.register_request(0, "AMZN")
        for bar in sample_bars[0]:
            historical_data_handler.add_bar(0, bar)
        
        # Export to CSV with keep_files=True
        exported_files = historical_data_handler.export_data(
            req_id=0,
            output_format="csv",
            output_path=temp_output_dir,
            keep_files=True
        )
        
        assert "AMZN" in exported_files
        assert exported_files["AMZN"].exists()
        assert exported_files["AMZN"].suffix == ".csv"
        
        # Verify content
        df = pd.read_csv(exported_files["AMZN"], index_col=0)
        assert len(df) == 5
        assert "Open" in df.columns
        
        print(f"\n=== Exported AMZN CSV ===")
        print(f"File: {exported_files['AMZN']}")
        print(df)

    def test_export_all_tickers_csv(self, historical_data_handler, sample_bars, temp_output_dir):
        """Test exporting all tickers (AMZN, TSLA, NVDA) to CSV format."""
        # Register and add bars for all tickers
        for req_id, bars in sample_bars.items():
            historical_data_handler.register_request(req_id, DEFAULT_TICKERS[req_id])
            for bar in bars:
                historical_data_handler.add_bar(req_id, bar)
        
        # Export all to CSV with keep_files=True
        exported_files = historical_data_handler.export_data(
            output_format="csv",
            output_path=temp_output_dir,
            keep_files=True
        )
        
        print("\n" + "=" * 60)
        print("EXPORTED CSV FILES")
        print("=" * 60)
        
        assert len(exported_files) == 3
        for ticker in DEFAULT_TICKERS:
            assert ticker in exported_files
            assert exported_files[ticker].exists()
            
            df = pd.read_csv(exported_files[ticker], index_col=0)
            print(f"\n=== {ticker} CSV Export ===")
            print(f"File: {exported_files[ticker]}")
            print(f"Shape: {df.shape}")
            print(df)

    def test_export_to_json(self, historical_data_handler, sample_bars, temp_output_dir):
        """Test exporting to JSON format."""
        historical_data_handler.register_request(0, "TSLA")
        for bar in sample_bars[1]:
            historical_data_handler.add_bar(0, bar)
        
        exported_files = historical_data_handler.export_data(
            req_id=0,
            output_format="json",
            output_path=temp_output_dir,
            keep_files=True
        )
        
        assert "TSLA" in exported_files
        assert exported_files["TSLA"].suffix == ".json"
        assert exported_files["TSLA"].exists()
        
        # Verify JSON content
        df = pd.read_json(exported_files["TSLA"], orient="index")
        assert len(df) == 5
        
        print(f"\n=== Exported TSLA JSON ===")
        print(f"File: {exported_files['TSLA']}")
        print(exported_files["TSLA"].read_text()[:500])

    def test_export_to_parquet(self, historical_data_handler, sample_bars, temp_output_dir):
        """Test exporting to Parquet format."""
        pytest.importorskip("pyarrow", reason="pyarrow required for parquet export")
        
        historical_data_handler.register_request(0, "NVDA")
        for bar in sample_bars[2]:
            historical_data_handler.add_bar(0, bar)
        
        exported_files = historical_data_handler.export_data(
            req_id=0,
            output_format="parquet",
            output_path=temp_output_dir,
            keep_files=True
        )
        
        assert "NVDA" in exported_files
        assert exported_files["NVDA"].suffix == ".parquet"
        assert exported_files["NVDA"].exists()
        
        # Verify Parquet content
        df = pd.read_parquet(exported_files["NVDA"])
        assert len(df) == 5
        
        print(f"\n=== Exported NVDA Parquet ===")
        print(f"File: {exported_files['NVDA']}")
        print(f"Shape: {df.shape}")
        print(df)

    def test_export_to_excel(self, historical_data_handler, sample_bars, temp_output_dir):
        """Test exporting to Excel format."""
        pytest.importorskip("openpyxl", reason="openpyxl required for excel export")
        
        historical_data_handler.register_request(0, "AMZN")
        for bar in sample_bars[0]:
            historical_data_handler.add_bar(0, bar)
        
        exported_files = historical_data_handler.export_data(
            req_id=0,
            output_format="excel",
            output_path=temp_output_dir,
            keep_files=True
        )
        
        assert "AMZN" in exported_files
        assert exported_files["AMZN"].suffix == ".xlsx"
        assert exported_files["AMZN"].exists()
        
        # Verify Excel content
        df = pd.read_excel(exported_files["AMZN"], index_col=0)
        assert len(df) == 5
        
        print(f"\n=== Exported AMZN Excel ===")
        print(f"File: {exported_files['AMZN']}")
        print(f"Shape: {df.shape}")
        print(df)

    def test_export_to_default_path(self, historical_data_handler, sample_bars):
        """Test exporting to the default output directory with keep_files=True."""
        # Register and add bars for all tickers
        for req_id, bars in sample_bars.items():
            historical_data_handler.register_request(req_id, DEFAULT_TICKERS[req_id])
            for bar in bars:
                historical_data_handler.add_bar(req_id, bar)
        
        # Export all tickers to default path with keep_files=True
        exported_files = historical_data_handler.export_data(
            output_format="csv",
            keep_files=True  # Keep files in the default output folder
        )
        
        print(f"\n=== Default Path Export (keep_files=True) ===")
        print(f"Default output directory: {DEFAULT_OUTPUT_DIR}")
        
        assert len(exported_files) == 3
        for ticker in DEFAULT_TICKERS:
            assert ticker in exported_files
            assert exported_files[ticker].exists()
            assert DEFAULT_OUTPUT_DIR in exported_files[ticker].parents or exported_files[ticker].parent == DEFAULT_OUTPUT_DIR
            
            # Read and display the file
            df = pd.read_csv(exported_files[ticker], index_col=0)
            print(f"\n=== {ticker} ===")
            print(f"File: {exported_files[ticker]}")
            print(df)

    def test_export_invalid_format(self, historical_data_handler, sample_bars, temp_output_dir):
        """Test that invalid format raises ValueError."""
        historical_data_handler.register_request(0, "AMZN")
        for bar in sample_bars[0]:
            historical_data_handler.add_bar(0, bar)
        
        with pytest.raises(ValueError, match="Invalid format"):
            historical_data_handler.export_data(
                req_id=0,
                output_format="invalid_format",
                output_path=temp_output_dir
            )

    def test_export_empty_data_raises_error(self, historical_data_handler, temp_output_dir):
        """Test that exporting empty data raises ValueError."""
        with pytest.raises(ValueError, match="No data available"):
            historical_data_handler.export_data(output_path=temp_output_dir)

    def test_export_nonexistent_req_id_raises_error(self, historical_data_handler, temp_output_dir):
        """Test that exporting non-existent req_id raises ValueError."""
        with pytest.raises(ValueError, match="No data found"):
            historical_data_handler.export_data(req_id=999, output_path=temp_output_dir)

    def test_export_with_custom_symbol(self, historical_data_handler, sample_bars, temp_output_dir):
        """Test exporting with a custom symbol name."""
        # Add data without registering symbol
        for bar in sample_bars[0]:
            historical_data_handler.add_bar(0, bar)
        
        # Export with custom symbol and keep_files=True
        exported_files = historical_data_handler.export_data(
            req_id=0,
            symbol="CUSTOM_TICKER",
            output_format="csv",
            output_path=temp_output_dir,
            keep_files=True
        )
        
        assert "CUSTOM_TICKER" in exported_files
        assert "CUSTOM_TICKER_historical.csv" in str(exported_files["CUSTOM_TICKER"])
        assert exported_files["CUSTOM_TICKER"].exists()
        
        print(f"\n=== Custom Symbol Export ===")
        print(f"File: {exported_files['CUSTOM_TICKER']}")

    def test_export_all_formats_for_all_tickers(self, historical_data_handler, sample_bars, temp_output_dir):
        """Comprehensive test: Export all tickers in CSV and JSON formats."""
        # Register and add bars for all tickers
        for req_id, bars in sample_bars.items():
            historical_data_handler.register_request(req_id, DEFAULT_TICKERS[req_id])
            for bar in bars:
                historical_data_handler.add_bar(req_id, bar)
        
        # Only test formats that don't require optional dependencies
        formats = ["csv", "json"]
        
        print("\n" + "=" * 60)
        print("COMPREHENSIVE EXPORT TEST - ALL TICKERS, MULTIPLE FORMATS")
        print("=" * 60)
        
        for fmt in formats:
            # Create subdirectory for each format
            format_dir = temp_output_dir / fmt
            format_dir.mkdir(exist_ok=True)
            
            exported_files = historical_data_handler.export_data(
                output_format=fmt,
                output_path=format_dir,
                keep_files=True
            )
            
            print(f"\n--- {fmt.upper()} Format ---")
            for ticker, file_path in exported_files.items():
                assert file_path.exists()
                print(f"  {ticker}: {file_path}")


if __name__ == "__main__":
    # Run tests with verbose output to see DataFrames
    pytest.main([__file__, "-v", "-s"])
