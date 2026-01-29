"""Stochastic Oscillator indicator implementation."""

from typing import Dict

import pandas as pd
import numpy as np

from .base_indicator import BaseIndicator
from utils import get_logger

logger = get_logger(__name__)


class StochasticIndicator(BaseIndicator):
    """Stochastic Oscillator indicator implementation.

    The Stochastic Oscillator compares the closing price to the price range
    over a given period. It ranges from 0 to 100 and is used to identify:
    - Overbought conditions (typically %K or %D > 80)
    - Oversold conditions (typically %K or %D < 20)
    - Momentum and potential reversal points

    Calculation:
    1. %K = 100 * (Close - Lowest Low(k)) / (Highest High(k) - Lowest Low(k))
    2. %D = Simple Moving Average of %K over d periods

    When the price range is zero (Highest High = Lowest Low), %K is set to 0.
    """

    def __init__(self, k_period: int = 14, d_period: int = 3):
        """
        Initialize Stochastic Oscillator indicator.

        Args:
            k_period: Number of periods for %K (lookback for high/low range)
            d_period: Number of periods for %D (SMA of %K)
        """
        super().__init__("Stochastic")
        if k_period <= 0:
            raise ValueError("k_period must be greater than 0")
        if d_period <= 0:
            raise ValueError("d_period must be greater than 0")

        self.k_period = k_period
        self.d_period = d_period

    def calculate(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        **kwargs
    ) -> Dict[str, pd.Series]:
        """
        Calculate Stochastic Oscillator.

        Args:
            high: High price series
            low: Low price series
            close: Close price series
            **kwargs: Optional parameters (k_period, d_period)

        Returns:
            Dictionary with 'stoch_k' and 'stoch_d' keys
        """
        k_period = kwargs.get("k_period", self.k_period)
        d_period = kwargs.get("d_period", self.d_period)

        min_length = k_period + d_period - 1

        if not self._validate_price_data(high, low, close, min_length=min_length):
            if close is None:
                return {
                    "stoch_k": pd.Series(dtype=float),
                    "stoch_d": pd.Series(dtype=float),
                }
            return {
                "stoch_k": pd.Series(index=close.index, dtype=float),
                "stoch_d": pd.Series(index=close.index, dtype=float),
            }

        lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
        highest_high = high.rolling(window=k_period, min_periods=k_period).max()
        price_range = highest_high - lowest_low

        # %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
        raw_k = close - lowest_low
        stoch_k = pd.Series(index=close.index, dtype=float)
        valid = price_range > 0
        stoch_k[valid] = 100 * raw_k[valid] / price_range[valid]
        stoch_k[~valid & price_range.notna()] = 0

        # %D = SMA of %K over d_period
        stoch_d = stoch_k.rolling(window=d_period, min_periods=d_period).mean()

        logger.debug(
            f"Calculated Stochastic for {len(close)} data points "
            f"(k={k_period}, d={d_period})"
        )

        return {
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
        }

    def _validate_price_data(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        min_length: int = 1,
    ) -> bool:
        """
        Validate price data for Stochastic calculation.

        Args:
            high: High price series
            low: Low price series
            close: Close price series
            min_length: Minimum required length

        Returns:
            True if valid, False otherwise
        """
        if high is None or low is None or close is None:
            logger.warning(f"{self.name}: One or more price series are None")
            return False

        if len(high) < min_length or len(low) < min_length or len(close) < min_length:
            logger.warning(
                f"{self.name}: Insufficient data "
                f"(high: {len(high)}, low: {len(low)}, close: {len(close)}, "
                f"required: {min_length})"
            )
            return False

        if not (len(high) == len(low) == len(close)):
            logger.warning(
                f"{self.name}: Price series have different lengths "
                f"(high: {len(high)}, low: {len(low)}, close: {len(close)})"
            )
            return False

        if not (high >= low).all():
            logger.warning(
                f"{self.name}: High prices are not always >= Low prices"
            )
            return False

        return True

    def calculate_from_dataframe(
        self,
        data: pd.DataFrame,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        **kwargs
    ) -> Dict[str, pd.Series]:
        """
        Calculate Stochastic from a DataFrame with OHLC data.

        Args:
            data: DataFrame containing OHLC data
            high_col: Column name for high prices
            low_col: Column name for low prices
            close_col: Column name for close prices
            **kwargs: Optional parameters (k_period, d_period)

        Returns:
            Dictionary with 'stoch_k' and 'stoch_d' keys
        """
        if high_col not in data.columns:
            raise ValueError(f"Column '{high_col}' not found in DataFrame")
        if low_col not in data.columns:
            raise ValueError(f"Column '{low_col}' not found in DataFrame")
        if close_col not in data.columns:
            raise ValueError(f"Column '{close_col}' not found in DataFrame")

        return self.calculate(
            data[high_col],
            data[low_col],
            data[close_col],
            **kwargs
        )


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> Dict[str, pd.Series]:
    """
    Calculate Stochastic Oscillator (convenience function).

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        k_period: Lookback period for %K
        d_period: SMA period for %D

    Returns:
        Dictionary with 'stoch_k' and 'stoch_d' keys
    """
    indicator = StochasticIndicator(k_period=k_period, d_period=d_period)
    return indicator.calculate(high, low, close)
