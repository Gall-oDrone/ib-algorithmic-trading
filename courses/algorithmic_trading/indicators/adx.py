"""ADX (Average Directional Index) indicator implementation."""

from typing import Dict, Tuple, Optional

import pandas as pd
import numpy as np

from .base_indicator import BaseIndicator
from utils import get_logger

logger = get_logger(__name__)


class ADXIndicator(BaseIndicator):
    """ADX (Average Directional Index) indicator implementation.
    
    ADX is a trend strength indicator that measures the strength of a trend
    regardless of direction. It ranges from 0 to 100 and is used to identify:
    - Strong trends (typically ADX > 25)
    - Weak trends or sideways markets (typically ADX < 20)
    - Trend direction (via +DI and -DI components)
    
    ADX calculation involves:
    1. Calculate True Range (TR)
    2. Calculate +DM and -DM (Directional Movement)
    3. Calculate smoothed +DM and -DM using Wilder's smoothing
    4. Calculate +DI and -DI (Directional Indicators)
    5. Calculate DX (Directional Index) = |+DI - -DI| / (+DI + -DI) * 100
    6. Calculate ADX as smoothed average of DX using Wilder's smoothing
    """
    
    def __init__(self, period: int = 14):
        """
        Initialize ADX indicator.
        
        Args:
            period: Number of periods for calculating ADX
        """
        super().__init__("ADX")
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
        Calculate ADX indicator.
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            **kwargs: Optional parameters (period)
            
        Returns:
            Dictionary with 'adx', '+di', and '-di' keys
        """
        period = kwargs.get("period", self.period)
        
        # Validate all series have the same length
        if not self._validate_price_data(high, low, close, min_length=period * 2):
            # Handle None input case
            if close is None:
                return {
                    "adx": pd.Series(dtype=float),
                    "+di": pd.Series(dtype=float),
                    "-di": pd.Series(dtype=float),
                }
            return {
                "adx": pd.Series(index=close.index, dtype=float),
                "+di": pd.Series(index=close.index, dtype=float),
                "-di": pd.Series(index=close.index, dtype=float),
            }
        
        # Calculate True Range
        true_range = self._calculate_true_range(high, low, close)
        
        # Calculate Directional Movement
        plus_dm, minus_dm = self._calculate_directional_movement(high, low)
        
        # Calculate smoothed TR, +DM, and -DM using Wilder's smoothing
        smoothed_tr = self._calculate_wilders_smoothing(true_range, period)
        smoothed_plus_dm = self._calculate_wilders_smoothing(plus_dm, period)
        smoothed_minus_dm = self._calculate_wilders_smoothing(minus_dm, period)
        
        # Calculate Directional Indicators (+DI and -DI)
        plus_di = 100 * (smoothed_plus_dm / smoothed_tr)
        minus_di = 100 * (smoothed_minus_dm / smoothed_tr)
        
        # Calculate DX (Directional Index)
        di_sum = plus_di + minus_di
        di_diff = (plus_di - minus_di).abs()
        
        # Avoid division by zero
        dx = pd.Series(index=close.index, dtype=float)
        valid_mask = di_sum > 0
        dx[valid_mask] = 100 * (di_diff[valid_mask] / di_sum[valid_mask])
        
        # Calculate ADX as smoothed average of DX using Wilder's smoothing
        # ADX needs period DX values, and DX starts at index 'period',
        # so first ADX value is at index 'period * 2 - 1'
        adx = self._calculate_adx_from_dx(dx, period)
        
        logger.debug(
            f"Calculated ADX for {len(close)} data points (period={period})"
        )
        
        return {
            "adx": adx,
            "+di": plus_di,
            "-di": minus_di,
        }
    
    def _validate_price_data(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        min_length: int = 1
    ) -> bool:
        """
        Validate price data for ADX calculation.
        
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
        
        # Basic sanity check: high >= low
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
    
    def _calculate_directional_movement(
        self,
        high: pd.Series,
        low: pd.Series
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Plus DM and Minus DM (Directional Movement).
        
        +DM = Current High - Previous High (if > 0 and > |Current Low - Previous Low|)
        -DM = Previous Low - Current Low (if > 0 and > |Current High - Previous High|)
        
        Args:
            high: High price series
            low: Low price series
            
        Returns:
            Tuple of (plus_dm, minus_dm) series
        """
        # Calculate price changes
        high_diff = high.diff()
        low_diff = -low.diff()  # Negative because we want previous - current
        
        # Initialize DM series
        plus_dm = pd.Series(index=high.index, dtype=float)
        minus_dm = pd.Series(index=low.index, dtype=float)
        
        # Calculate DM for each period
        for i in range(1, len(high)):
            up_move = high_diff.iloc[i] if high_diff.iloc[i] > 0 else 0
            down_move = low_diff.iloc[i] if low_diff.iloc[i] > 0 else 0
            
            if up_move > down_move and up_move > 0:
                plus_dm.iloc[i] = up_move
                minus_dm.iloc[i] = 0
            elif down_move > up_move and down_move > 0:
                plus_dm.iloc[i] = 0
                minus_dm.iloc[i] = down_move
            else:
                plus_dm.iloc[i] = 0
                minus_dm.iloc[i] = 0
        
        return plus_dm, minus_dm
    
    def _calculate_wilders_smoothing(
        self,
        series: pd.Series,
        period: int
    ) -> pd.Series:
        """
        Calculate Wilder's smoothing (exponential-like moving average).
        
        The first smoothed value is the simple average of the first 'period' values.
        Subsequent values use Wilder's smoothing:
        Smoothed = ((Previous Smoothed * (period - 1)) + Current Value) / period
        
        Args:
            series: Series to smooth
            period: Period for smoothing
            
        Returns:
            Smoothed series
        """
        smoothed = pd.Series(index=series.index, dtype=float)
        
        if len(series) < period + 1:
            return smoothed
        
        # First smoothed value is the simple average of first 'period' values
        # Skip first value (no previous value for comparison)
        smoothed.iloc[period] = series.iloc[1:period+1].mean()
        
        # Calculate subsequent smoothed values using Wilder's smoothing
        for i in range(period + 1, len(series)):
            smoothed.iloc[i] = ((smoothed.iloc[i-1] * (period - 1)) + series.iloc[i]) / period
        
        return smoothed
    
    def _calculate_adx_from_dx(self, dx: pd.Series, period: int) -> pd.Series:
        """
        Calculate ADX by smoothing DX values.
        
        DX values start at index 'period' (because +DI and -DI start at 'period').
        ADX is the smoothed average of DX, so we need 'period' DX values.
        The first ADX value appears at index 'period * 2 - 1'.
        
        Args:
            dx: DX (Directional Index) series
            period: Period for smoothing
            
        Returns:
            ADX series
        """
        adx = pd.Series(index=dx.index, dtype=float)
        
        # DX values start at index 'period', so we need at least 'period * 2 - 1' 
        # data points to calculate the first ADX value
        if len(dx) < period * 2:
            return adx
        
        # First ADX value is the simple average of first 'period' DX values
        # DX values start at index 'period', so we average from 'period' to 'period * 2 - 1'
        first_dx_start = period
        first_dx_end = period * 2 - 1
        adx.iloc[first_dx_end] = dx.iloc[first_dx_start:first_dx_end+1].mean()
        
        # Calculate subsequent ADX values using Wilder's smoothing
        for i in range(period * 2, len(dx)):
            adx.iloc[i] = ((adx.iloc[i-1] * (period - 1)) + dx.iloc[i]) / period
        
        return adx
    
    def calculate_from_dataframe(
        self,
        data: pd.DataFrame,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        **kwargs
    ) -> Dict[str, pd.Series]:
        """
        Calculate ADX from a DataFrame with OHLC data.
        
        Args:
            data: DataFrame containing OHLC data
            high_col: Column name for high prices
            low_col: Column name for low prices
            close_col: Column name for close prices
            **kwargs: Optional parameters (period)
            
        Returns:
            Dictionary with 'adx', '+di', and '-di' keys
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


def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> Dict[str, pd.Series]:
    """
    Calculate ADX indicator (convenience function).
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: Number of periods for calculating ADX
        
    Returns:
        Dictionary with 'adx', '+di', and '-di' keys
    """
    indicator = ADXIndicator(period=period)
    return indicator.calculate(high, low, close)
