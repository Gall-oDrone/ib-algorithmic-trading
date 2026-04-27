"""Tests for historical volatility indicator."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from indicators.historical_volatility import (
    HistoricalVolatilityIndicator,
    calculate_historical_volatility,
)


def test_calculate_historical_volatility_function():
    """Test convenience function output structure."""
    np.random.seed(1)
    returns = np.random.normal(0.0001, 0.01, 80)
    prices = 100 * np.exp(np.cumsum(returns))
    data = pd.Series(prices)

    result = calculate_historical_volatility(data, window=20)
    assert "historical_volatility" in result
    assert len(result["historical_volatility"]) == len(data)


def test_historical_volatility_indicator_class():
    """Test indicator class output and non-negative values."""
    np.random.seed(2)
    returns = np.random.normal(0.0002, 0.012, 120)
    prices = 120 * np.exp(np.cumsum(returns))
    data = pd.Series(prices)

    indicator = HistoricalVolatilityIndicator(window=30)
    result = indicator.calculate(data)
    hv = result["historical_volatility"].dropna()

    assert len(hv) > 0
    assert (hv >= 0).all()


def test_historical_volatility_insufficient_data():
    """Return aligned NaN series when data is insufficient."""
    data = pd.Series([100.0, 101.0, 102.0, 103.0])
    indicator = HistoricalVolatilityIndicator(window=10)
    result = indicator.calculate(data)

    assert len(result["historical_volatility"]) == len(data)
    assert result["historical_volatility"].isna().all()


@pytest.mark.parametrize(
    "window,annualization_periods,error_message",
    [
        (1, 252, "window must be greater than 1"),
        (30, 0, "annualization_periods must be greater than 0"),
    ],
)
def test_historical_volatility_invalid_init(
    window, annualization_periods, error_message
):
    """Validate constructor inputs."""
    with pytest.raises(ValueError, match=error_message):
        HistoricalVolatilityIndicator(
            window=window, annualization_periods=annualization_periods
        )


def test_historical_volatility_kwargs_override():
    """Allow overriding defaults at calculation time."""
    np.random.seed(3)
    returns = np.random.normal(0.0, 0.01, 100)
    prices = 95 * np.exp(np.cumsum(returns))
    data = pd.Series(prices)

    indicator = HistoricalVolatilityIndicator(window=30, annualization_periods=252)
    default_result = indicator.calculate(data)["historical_volatility"]
    override_result = indicator.calculate(
        data, window=20, annualization_periods=365
    )["historical_volatility"]

    assert not default_result.equals(override_result)
