# NDX Indicators Integration Tests

## Overview

This document describes the enhanced integration tests for calculating technical indicators on the NASDAQ Index (NDX) with real data from Interactive Brokers TWS.

## Test Files

### 1. `test_ndx_indicators_integration.py` (NEW - Comprehensive Test)
**Main comprehensive integration test** with all advanced features:
- ✅ Multiple timeframes (daily, weekly, monthly)
- ✅ Combined indicators (Bollinger Bands + ATR + MACD)
- ✅ Chart/visualization generation (4 charts per timeframe)
- ✅ Benchmark comparisons (SMA, EMA)
- ✅ Summary statistics export

### 2. `test_bollinger_bands_indicator.py`
Contains `test_bollinger_bands_on_ndx_index()` - Simple test for Bollinger Bands only.

### 3. `test_atr_indicator.py`
Contains `test_atr_on_ndx_index()` - Simple test for ATR only.

## Features

### Multiple Timeframes
The comprehensive test fetches NDX data for three timeframes:
- **Daily**: 1 year of daily bars
- **Weekly**: 2 years of weekly bars  
- **Monthly**: 5 years of monthly bars

### Combined Indicators
Each timeframe includes calculations for:
- **Bollinger Bands**: Middle, Upper, Lower bands, Bandwidth, %B
- **ATR**: Average True Range (14-period)
- **MACD**: MACD line, Signal line, Histogram
- **Benchmarks**: SMA 20, SMA 50, EMA 12, EMA 26

### Visualizations
For each timeframe, 4 charts are generated:
1. **Price with Bollinger Bands** - Shows price action with BB bands
2. **Price and MACD** - Price chart with MACD indicator below
3. **Price and ATR** - Price chart with ATR volatility indicator
4. **Benchmark Comparison** - Price with SMA/EMA comparisons

### Output Files

#### CSV Files
- `NDX_indicators_daily.csv` - Daily data with all indicators
- `NDX_indicators_weekly.csv` - Weekly data with all indicators
- `NDX_indicators_monthly.csv` - Monthly data with all indicators
- `NDX_indicators_summary.csv` - Summary statistics across timeframes

#### Chart Files (PNG)
For each timeframe:
- `NDX_BollingerBands_{timeframe}.png`
- `NDX_MACD_{timeframe}.png`
- `NDX_ATR_{timeframe}.png`
- `NDX_BenchmarkComparison_{timeframe}.png`

## Prerequisites

1. **IB Trader Workstation (TWS) or IB Gateway** must be running
2. **Paper trading account** must be connected
3. **API connections** must be enabled in TWS/Gateway settings:
   - Edit > Global Configuration > API > Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Set Socket port (default: 7497 for paper, 7496 for live)

4. **Python packages**:
   ```bash
   pip install ibapi pandas numpy matplotlib pytest
   ```

## Running the Tests

### Comprehensive Test (Recommended)
```bash
# Run the full comprehensive test
pytest tests/test_ndx_indicators_integration.py::test_ndx_comprehensive_indicators_analysis -v -s
```

### Individual Indicator Tests
```bash
# Bollinger Bands only
pytest tests/test_bollinger_bands_indicator.py::test_bollinger_bands_on_ndx_index -v -s

# ATR only
pytest tests/test_atr_indicator.py::test_atr_on_ndx_index -v -s
```

### All NDX Integration Tests
```bash
pytest tests/test_ndx_indicators_integration.py tests/test_bollinger_bands_indicator.py::test_bollinger_bands_on_ndx_index tests/test_atr_indicator.py::test_atr_on_ndx_index -v -s
```

## Output Location

All files are exported to:
```
courses/algorithmic_trading/data/historical_output/
```

The directory is created automatically if it doesn't exist.

## Test Behavior

- **If IB TWS is not connected**: Tests will skip gracefully with a message
- **If data is not received**: Tests will skip with appropriate message
- **If matplotlib is not available**: Charts will be skipped, CSV exports will still work

## Expected Runtime

- **Comprehensive test**: ~60-90 seconds (depends on data fetch time)
- **Individual tests**: ~30-45 seconds each

## CSV File Structure

Each CSV file contains:
- Original OHLC data: `Date`, `Open`, `High`, `Low`, `Close`, `Volume`
- Bollinger Bands: `BB_Middle`, `BB_Upper`, `BB_Lower`, `BB_Bandwidth`, `BB_PercentB`
- ATR: `ATR`
- MACD: `MACD`, `MACD_Signal`, `MACD_Histogram`
- Benchmarks: `SMA_20`, `SMA_50`, `EMA_12`, `EMA_26`
- Comparisons: `BB_vs_SMA20`, `MACD_vs_Signal`

## Troubleshooting

### "Could not connect to IB TWS"
- Ensure TWS/Gateway is running
- Check API settings are enabled
- Verify port number matches config (default: 7497 for paper)
- Check firewall settings

### "No data received"
- Verify market data subscription is active
- Check if NDX index data is available for requested timeframes
- Try reducing duration (e.g., "6 M" instead of "1 Y")

### "Matplotlib not available"
- Install matplotlib: `pip install matplotlib`
- Charts will be skipped but CSV exports will work

### Import errors
- Ensure you're in the correct Python environment
- Install all requirements: `pip install -r requirements.txt`

## Example Output

```
======================================================================
COMPREHENSIVE NDX INDICATORS INTEGRATION TEST
======================================================================
Host: 127.0.0.1, Port: 7497
Timeframes: ['daily', 'weekly', 'monthly']
======================================================================

[1/6] Connected to IB TWS
[2/6] Requesting NDX data for all timeframes...
   Requested daily data (duration: 1 Y, bar_size: 1 day)
   Requested weekly data (duration: 2 Y, bar_size: 1 week)
   Requested monthly data (duration: 5 Y, bar_size: 1 month)
[3/6] Waiting for data to be received...
   Received data for 3/3 timeframes
[4/6] Processing data and calculating indicators...
   Processing daily data: 252 bars
   Exported CSV: NDX_indicators_daily.csv (252 rows, 20 columns)
   Creating visualizations for daily...
   Created chart: NDX_BollingerBands_daily.png
   ...
[5/6] Creating summary comparison...
[6/6] Final Report
======================================================================
COMPREHENSIVE NDX INDICATORS ANALYSIS COMPLETED
======================================================================
```

## Notes

- The comprehensive test uses client ID 300 to avoid conflicts
- Individual tests use client IDs 201 and 202
- All tests clean up connections automatically
- Files are saved with descriptive names including timeframe
- Charts use high resolution (150 DPI) for quality output
