"""Bollinger Bands indicator implementation."""

from typing import Dict

import pandas as pd
import numpy as np

from .base_indicator import BaseIndicator
from utils import get_logger

logger = get_logger(__name__)


class BollingerBandsIndicator(BaseIndicator):
    """Bollinger Bands indicator implementation.
    
    Bollinger Bands consist of:
    - Middle Band: Simple Moving Average (SMA) of the price
    - Upper Band: SMA + (num_std * standard deviation)
    - Lower Band: SMA - (num_std * standard deviation)
    
    The bands expand and contract based on volatility, providing
    dynamic support and resistance levels.
    """
    
    def __init__(self, period: int = 20, num_std: float = 2.0):
        """
        Initialize Bollinger Bands indicator.
        
        Args:
            period: Number of periods for moving average and standard deviation
            num_std: Number of standard deviations for band width
        """
        super().__init__("BollingerBands")
        if period <= 0:
            raise ValueError("Period must be greater than 0")
        if num_std <= 0:
            raise ValueError("Number of standard deviations must be greater than 0")
        
        self.period = period
        self.num_std = num_std
    
    def calculate(self, data: pd.Series, **kwargs) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands indicator.
        
        Args:
            data: Price data series (typically closing prices)
            **kwargs: Optional parameters (period, num_std)
            
        Returns:
            Dictionary with 'middle', 'upper', and 'lower' keys
        """
        if not self.validate_data(data, min_length=self.period):
            return {
                "middle": pd.Series(index=data.index, dtype=float),
                "upper": pd.Series(index=data.index, dtype=float),
                "lower": pd.Series(index=data.index, dtype=float),
            }
        
        period = kwargs.get("period", self.period)
        num_std = kwargs.get("num_std", self.num_std)
        
        # Calculate middle band (SMA)
        middle_band = data.rolling(window=period, min_periods=period).mean()
        
        # Calculate standard deviation
        std = data.rolling(window=period, min_periods=period).std()
        
        # Calculate upper and lower bands
        upper_band = middle_band + (num_std * std)
        lower_band = middle_band - (num_std * std)
        
        logger.debug(
            f"Calculated Bollinger Bands for {len(data)} data points "
            f"(period={period}, num_std={num_std})"
        )
        
        return {
            "middle": middle_band,
            "upper": upper_band,
            "lower": lower_band,
        }
    
    def get_bandwidth(self, data: pd.Series, **kwargs) -> pd.Series:
        """
        Calculate Bollinger Bandwidth.
        
        Bandwidth = (Upper Band - Lower Band) / Middle Band
        
        This metric indicates the relative width of the bands and can be
        used to identify periods of high or low volatility.
        
        Args:
            data: Price data series
            **kwargs: Optional parameters (period, num_std)
            
        Returns:
            Bandwidth series
        """
        bands = self.calculate(data, **kwargs)
        
        middle = bands["middle"]
        upper = bands["upper"]
        lower = bands["lower"]
        
        # Avoid division by zero
        bandwidth = (upper - lower) / middle.replace(0, np.nan)
        
        return bandwidth
    
    def get_percent_b(self, data: pd.Series, **kwargs) -> pd.Series:
        """
        Calculate %B (Percent B) indicator.
        
        %B = (Price - Lower Band) / (Upper Band - Lower Band)
        
        This metric shows where the price is relative to the bands:
        - %B > 1: Price is above upper band
        - %B = 1: Price is at upper band
        - %B = 0.5: Price is at middle band
        - %B = 0: Price is at lower band
        - %B < 0: Price is below lower band
        
        Args:
            data: Price data series
            **kwargs: Optional parameters (period, num_std)
            
        Returns:
            %B series
        """
        bands = self.calculate(data, **kwargs)
        
        upper = bands["upper"]
        lower = bands["lower"]
        band_width = upper - lower
        
        # Avoid division by zero
        percent_b = (data - lower) / band_width.replace(0, np.nan)
        
        return percent_b


def calculate_bollinger_bands(
    data: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> Dict[str, pd.Series]:
    """
    Calculate Bollinger Bands indicator (convenience function).
    
    Args:
        data: Price data series
        period: Number of periods for moving average and standard deviation
        num_std: Number of standard deviations for band width
        
    Returns:
        Dictionary with 'middle', 'upper', and 'lower' keys
    """
    indicator = BollingerBandsIndicator(period=period, num_std=num_std)
    return indicator.calculate(data)
