"""Base class for technical indicators."""

from abc import ABC, abstractmethod
from typing import Dict, Any

import pandas as pd

from utils import get_logger

logger = get_logger(__name__)


class BaseIndicator(ABC):
    """Base class for all technical indicators."""
    
    def __init__(self, name: str):
        """
        Initialize indicator.
        
        Args:
            name: Indicator name
        """
        self.name = name
    
    @abstractmethod
    def calculate(self, data: pd.Series, **kwargs) -> Dict[str, pd.Series]:
        """
        Calculate indicator values.
        
        Args:
            data: Price data series
            **kwargs: Indicator-specific parameters
            
        Returns:
            Dictionary mapping signal names to Series
        """
        pass
    
    def validate_data(self, data: pd.Series, min_length: int = 1) -> bool:
        """
        Validate input data.
        
        Args:
            data: Data to validate
            min_length: Minimum required length
            
        Returns:
            True if valid, False otherwise
        """
        if data is None or len(data) < min_length:
            logger.warning(f"{self.name}: Insufficient data (length: {len(data) if data is not None else 0})")
            return False
        return True
