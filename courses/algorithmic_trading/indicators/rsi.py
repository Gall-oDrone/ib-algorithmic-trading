"""RSI (Relative Strength Index) indicator implementation."""

from typing import Dict, Tuple

import pandas as pd
import numpy as np

from .base_indicator import BaseIndicator
from utils import get_logger

logger = get_logger(__name__)


class RSIIndicator(BaseIndicator):
    """RSI (Relative Strength Index) indicator implementation.
    
    RSI is a momentum oscillator that measures the speed and magnitude of price changes.
    It ranges from 0 to 100 and is used to identify:
    - Overbought conditions (typically RSI > 70)
    - Oversold conditions (typically RSI < 30)
    - Potential trend reversals
    
    RSI is calculated using Wilder's smoothing method:
    1. Calculate price changes (gains and losses)
    2. Calculate average gain and average loss over a period
    3. RSI = 100 - (100 / (1 + RS)) where RS = Average Gain / Average Loss
    """
    
    def __init__(self, period: int = 14):
        """
        Initialize RSI indicator.
        
        Args:
            period: Number of periods for calculating average gain/loss
        """
        super().__init__("RSI")
        if period <= 0:
            raise ValueError("Period must be greater than 0")
        
        self.period = period
    
    def calculate(self, data: pd.Series, **kwargs) -> Dict[str, pd.Series]:
        """
        Calculate RSI indicator.
        
        Args:
            data: Close price series
            **kwargs: Optional parameters (period)
            
        Returns:
            Dictionary with 'rsi' key containing the RSI series
        """
        period = kwargs.get("period", self.period)
        
        if not self.validate_data(data, min_length=period + 1):
            if data is None:
                return {
                    "rsi": pd.Series(dtype=float),
                }
            return {
                "rsi": pd.Series(index=data.index, dtype=float),
            }
        
        # Calculate price changes
        price_changes = data.diff()
        
        # Separate gains and losses
        gains = price_changes.where(price_changes > 0, 0)
        losses = -price_changes.where(price_changes < 0, 0)
        
        # Calculate average gain and average loss using Wilder's smoothing
        avg_gain, avg_loss = self._calculate_wilders_averages(gains, losses, period)
        
        # Calculate RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        logger.debug(
            f"Calculated RSI for {len(data)} data points (period={period})"
        )
        
        return {
            "rsi": rsi,
        }
    
    def _calculate_wilders_averages(
        self,
        gains: pd.Series,
        losses: pd.Series,
        period: int
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate average gain and average loss using Wilder's smoothing method.
        
        The first average is the simple average of the first 'period' values.
        Subsequent values use Wilder's smoothing:
        Average = ((Previous Average * (period - 1)) + Current Value) / period
        
        Args:
            gains: Series of gains (positive price changes)
            losses: Series of losses (positive values for negative price changes)
            period: Period for averaging
            
        Returns:
            Tuple of (average_gain, average_loss) series
        """
        avg_gain = pd.Series(index=gains.index, dtype=float)
        avg_loss = pd.Series(index=losses.index, dtype=float)
        
        if len(gains) < period + 1:
            return avg_gain, avg_loss
        
        # First average is the simple average of first 'period' values
        # Skip first value (no price change)
        avg_gain.iloc[period] = gains.iloc[1:period+1].mean()
        avg_loss.iloc[period] = losses.iloc[1:period+1].mean()
        
        # Calculate subsequent averages using Wilder's smoothing
        for i in range(period + 1, len(gains)):
            avg_gain.iloc[i] = ((avg_gain.iloc[i-1] * (period - 1)) + gains.iloc[i]) / period
            avg_loss.iloc[i] = ((avg_loss.iloc[i-1] * (period - 1)) + losses.iloc[i]) / period
        
        return avg_gain, avg_loss
    
    def calculate_from_dataframe(
        self,
        data: pd.DataFrame,
        close_col: str = "close",
        **kwargs
    ) -> Dict[str, pd.Series]:
        """
        Calculate RSI from a DataFrame with price data.
        
        Args:
            data: DataFrame containing close price data
            close_col: Column name for close prices
            **kwargs: Optional parameters (period)
            
        Returns:
            Dictionary with 'rsi' key containing the RSI series
        """
        if close_col not in data.columns:
            raise ValueError(f"Column '{close_col}' not found in DataFrame")
        
        return self.calculate(data[close_col], **kwargs)


def calculate_rsi(
    data: pd.Series,
    period: int = 14,
) -> Dict[str, pd.Series]:
    """
    Calculate RSI indicator (convenience function).
    
    Args:
        data: Close price series
        period: Number of periods for calculating average gain/loss
        
    Returns:
        Dictionary with 'rsi' key containing the RSI series
    """
    indicator = RSIIndicator(period=period)
    return indicator.calculate(data)
