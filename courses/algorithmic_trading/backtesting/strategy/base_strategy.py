"""Base class for backtesting strategies."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import pandas as pd

from utils import get_logger

logger = get_logger(__name__)


class BaseBacktestStrategy(ABC):
    """Abstract base class for backtest performance strategies.

    Strategies evaluate equity curves or price series and produce
    performance metrics (e.g. CAGR, Sharpe) over configurable periods.
    """

    def __init__(self, name: str):
        """
        Initialize the strategy.

        Args:
            name: Strategy name for logging and identification.
        """
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        self.name = name

    @abstractmethod
    def evaluate(
        self,
        equity: pd.Series,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Evaluate performance from an equity curve or price series.

        Args:
            equity: Time series of equity or close prices (index: datetime).
            **kwargs: Strategy-specific parameters.

        Returns:
            Dictionary of metric names to values (floats, Series, or other).
        """
        pass

    def evaluate_from_dataframe(
        self,
        data: pd.DataFrame,
        value_col: str = "Close",
        date_col: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Evaluate from a DataFrame (e.g. OHLC or equity table).

        Args:
            data: DataFrame with a value column and optional date index/column.
            value_col: Column name for equity/price values.
            date_col: Column name for dates; if None, uses data.index.
            **kwargs: Passed to evaluate().

        Returns:
            Same as evaluate().
        """
        if value_col not in data.columns:
            raise ValueError(f"Column '{value_col}' not found in DataFrame")

        if date_col is not None:
            if date_col not in data.columns:
                raise ValueError(f"Column '{date_col}' not found in DataFrame")
            series = data.set_index(date_col)[value_col]
        else:
            series = data[value_col].copy()
            if series.index.name is None and not isinstance(
                series.index, pd.DatetimeIndex
            ):
                raise ValueError(
                    "DataFrame must have a DatetimeIndex or provide date_col"
                )

        return self.evaluate(series, **kwargs)
