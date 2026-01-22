"""MACD (Moving Average Convergence Divergence) indicator."""

from typing import Dict

import pandas as pd

from .base_indicator import BaseIndicator
from ..utils import get_logger

logger = get_logger(__name__)


class MACDIndicator(BaseIndicator):
    """MACD indicator implementation."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialize MACD indicator.
        
        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period
        """
        super().__init__("MACD")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate(self, data: pd.Series, **kwargs) -> Dict[str, pd.Series]:
        """
        Calculate MACD indicator.
        
        Args:
            data: Price data series
            **kwargs: Optional parameters (fast_period, slow_period, signal_period)
            
        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' keys
        """
        if not self.validate_data(data, min_length=self.slow_period):
            return {
                "macd": pd.Series(dtype=float),
                "signal": pd.Series(dtype=float),
                "histogram": pd.Series(dtype=float),
            }
        
        fast_period = kwargs.get("fast_period", self.fast_period)
        slow_period = kwargs.get("slow_period", self.slow_period)
        signal_period = kwargs.get("signal_period", self.signal_period)
        
        # Calculate EMAs
        ema_fast = data.ewm(span=fast_period, adjust=False).mean()
        ema_slow = data.ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        logger.debug(f"Calculated MACD for {len(data)} data points")
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        }


def calculate_macd(
    data: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Dict[str, pd.Series]:
    """
    Calculate MACD indicator (convenience function).
    
    Args:
        data: Price data
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line EMA period
        
    Returns:
        Dictionary with 'macd', 'signal', and 'histogram' keys
    """
    indicator = MACDIndicator(fast_period, slow_period, signal_period)
    return indicator.calculate(data)
