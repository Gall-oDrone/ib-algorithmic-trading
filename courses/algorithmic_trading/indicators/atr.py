"""ATR (Average True Range) indicator implementation."""

from typing import Dict, Optional

import pandas as pd
import numpy as np

from .base_indicator import BaseIndicator
from utils import get_logger

logger = get_logger(__name__)


class ATRIndicator(BaseIndicator):
    """ATR (Average True Range) indicator implementation.
    
    ATR measures market volatility by calculating the average of true ranges
    over a specified period. True Range is the maximum of:
    1. Current High - Current Low
    2. Absolute value of (Current High - Previous Close)
    3. Absolute value of (Current Low - Previous Close)
    
    ATR is useful for:
    - Setting stop-loss levels
    - Position sizing based on volatility
    - Identifying periods of high/low volatility
    """
    
    def __init__(self, period: int = 14):
        """
        Initialize ATR indicator.
        
        Args:
            period: Number of periods for averaging the true range
        """
        super().__init__("ATR")
        if period <= 0:
            raise ValueError("Period must be greater than 0")
        
        self.period = period
    
    def calculate(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        **kwargs
    ) -> Dict[str, pd.Series]:
        """
        Calculate ATR indicator.
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            **kwargs: Optional parameters (period)
            
        Returns:
            Dictionary with 'atr' key containing the ATR series
        """
        period = kwargs.get("period", self.period)
        
        # Validate all series have the same length
        if not self._validate_price_data(high, low, close, min_length=period + 1):
            # Handle None input case
            if close is None:
                return {
                    "atr": pd.Series(dtype=float),
                }
            return {
                "atr": pd.Series(index=close.index, dtype=float),
            }
        
        # Calculate True Range
        true_range = self._calculate_true_range(high, low, close)
        
        # Calculate ATR using Simple Moving Average of True Range
        # First ATR value is the simple average of first 'period' true ranges
        # Subsequent values use Wilder's smoothing method (exponential-like)
        atr = self._calculate_atr(true_range, period)
        
        logger.debug(
            f"Calculated ATR for {len(close)} data points (period={period})"
        )
        
        return {
            "atr": atr,
        }
    
    def _validate_price_data(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        min_length: int = 1
    ) -> bool:
        """
        Validate price data for ATR calculation.
        
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
        
        # Check if all series have the same length
        if not (len(high) == len(low) == len(close)):
            logger.warning(
                f"{self.name}: Price series have different lengths "
                f"(high: {len(high)}, low: {len(low)}, close: {len(close)})"
            )
            return False
        
        # Basic sanity check: high >= low, high >= close, low <= close
        if not (high >= low).all():
            logger.warning(f"{self.name}: High prices are not always >= Low prices")
            return False
        
        return True
    
    def _calculate_true_range(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> pd.Series:
        """
        Calculate True Range for each period.
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            
        Returns:
            True Range series
        """
        # Shift close to get previous close
        prev_close = close.shift(1)
        
        # Calculate the three components of True Range
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        # True Range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return true_range
    
    def _calculate_atr(self, true_range: pd.Series, period: int) -> pd.Series:
        """
        Calculate ATR from True Range using Wilder's smoothing method.
        
        The first ATR value is the simple average of the first 'period' true ranges.
        Subsequent values use Wilder's smoothing:
        ATR = ((Previous ATR * (period - 1)) + Current TR) / period
        
        This is equivalent to an exponential moving average with alpha = 1/period.
        
        Args:
            true_range: True Range series
            period: ATR period
            
        Returns:
            ATR series
        """
        atr = pd.Series(index=true_range.index, dtype=float)
        
        # First ATR value is the simple average of first 'period' true ranges
        if len(true_range) >= period:
            # Skip first value (no previous close)
            atr.iloc[period] = true_range.iloc[1:period+1].mean()
            
            # Calculate subsequent ATR values using Wilder's smoothing
            for i in range(period + 1, len(true_range)):
                atr.iloc[i] = ((atr.iloc[i-1] * (period - 1)) + true_range.iloc[i]) / period
        
        return atr
    
    def calculate_from_dataframe(
        self,
        data: pd.DataFrame,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        **kwargs
    ) -> Dict[str, pd.Series]:
        """
        Calculate ATR from a DataFrame with OHLC data.
        
        Args:
            data: DataFrame containing OHLC data
            high_col: Column name for high prices
            low_col: Column name for low prices
            close_col: Column name for close prices
            **kwargs: Optional parameters (period)
            
        Returns:
            Dictionary with 'atr' key containing the ATR series
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


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> Dict[str, pd.Series]:
    """
    Calculate ATR indicator (convenience function).
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: Number of periods for averaging the true range
        
    Returns:
        Dictionary with 'atr' key containing the ATR series
    """
    indicator = ATRIndicator(period=period)
    return indicator.calculate(high, low, close)
