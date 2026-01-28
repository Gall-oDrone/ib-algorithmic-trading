"""Tests for MACD indicator."""

import sys
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from indicators.macd import calculate_macd, MACDIndicator


@pytest.fixture
def sample_price_data():
    """Create sample price data."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    return pd.Series(prices, index=dates)


def test_calculate_macd_function(sample_price_data):
    """Test MACD calculation function."""
    result = calculate_macd(sample_price_data)
    
    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result
    assert len(result["macd"]) == len(sample_price_data)
    assert len(result["signal"]) == len(sample_price_data)
    assert len(result["histogram"]) == len(sample_price_data)


def test_macd_indicator_class(sample_price_data):
    """Test MACD indicator class."""
    indicator = MACDIndicator(fast_period=12, slow_period=26, signal_period=9)
    result = indicator.calculate(sample_price_data)
    
    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result


def test_macd_with_insufficient_data():
    """Test MACD with insufficient data."""
    short_data = pd.Series([100, 101, 102])
    indicator = MACDIndicator()
    result = indicator.calculate(short_data)
    
    # Should return empty series when data is insufficient
    assert len(result["macd"]) == 0 or len(result["macd"]) == len(short_data)


def test_macd_custom_periods(sample_price_data):
    """Test MACD with custom periods."""
    indicator = MACDIndicator(fast_period=5, slow_period=10, signal_period=3)
    result = indicator.calculate(sample_price_data)
    
    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
