"""Base class for signal strategies that produce long/flat (or long/short) signals from OHLC data."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import pandas as pd

from utils import get_logger

logger = get_logger(__name__)

# Default OHLC column names expected by signal strategies
DEFAULT_OPEN_COL = "Open"
DEFAULT_HIGH_COL = "High"
DEFAULT_LOW_COL = "Low"
DEFAULT_CLOSE_COL = "Close"


class BaseSignalStrategy(ABC):
    """Abstract base for strategies that generate entry/exit signals from OHLC data.

    Signal strategies consume a DataFrame with OHLC (and optionally Volume) and
    produce a signal series: e.g. 1 = long, 0 = flat (and optionally -1 = short).
    """

    def __init__(self, name: str):
        """
        Initialize the signal strategy.

        Args:
            name: Strategy name for logging and identification.
        """
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        self.name = name

    @abstractmethod
    def generate(
        self,
        data: pd.DataFrame,
        *,
        open_col: str = DEFAULT_OPEN_COL,
        high_col: str = DEFAULT_HIGH_COL,
        low_col: str = DEFAULT_LOW_COL,
        close_col: str = DEFAULT_CLOSE_COL,
        include_components: bool = False,
        **kwargs: Any,
    ) -> Union[pd.Series, pd.DataFrame]:
        """
        Generate signals from OHLC data.

        Args:
            data: DataFrame with Open, High, Low, Close (and optionally Volume).
            open_col: Column name for open prices.
            high_col: Column name for high prices.
            low_col: Column name for low prices.
            close_col: Column name for close prices.
            include_components: If True, return a DataFrame with 'signal' plus
                helper columns (e.g. macd_bullish, stoch_bullish) for debugging.
            **kwargs: Strategy-specific parameters.

        Returns:
            If include_components is False: a Series with same index as data,
            values 1 (long), 0 (flat), and optionally -1 (short).
            If include_components is True: a DataFrame with at least 'signal'
            and optional component columns.
        """
        pass

    def _require_ohlc(
        self,
        data: pd.DataFrame,
        open_col: str,
        high_col: str,
        low_col: str,
        close_col: str,
    ) -> None:
        """Raise ValueError if any OHLC column is missing."""
        for col, name in [
            (open_col, "open_col"),
            (high_col, "high_col"),
            (low_col, "low_col"),
            (close_col, "close_col"),
        ]:
            if col not in data.columns:
                raise ValueError(
                    f"{self.name}: Column '{col}' ({name}) not found in DataFrame. "
                    f"Available: {list(data.columns)}"
                )
