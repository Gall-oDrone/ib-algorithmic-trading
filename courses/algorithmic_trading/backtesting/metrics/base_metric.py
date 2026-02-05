"""Base class for trade-based backtesting metrics."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union

import numpy as np
import pandas as pd

from utils import get_logger

logger = get_logger(__name__)


class BaseTradeMetric(ABC):
    """Abstract base for metrics computed from a sequence of trade returns.

    Trade returns are decimal (e.g. 0.02 = 2% gain). Input can be a
    pandas Series, a 1-d array, or a DataFrame with a 'return' or 'pnl' column.
    """

    def __init__(self, name: str):
        """
        Initialize the metric.

        Args:
            name: Metric name for logging and identification.
        """
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        self.name = name

    @staticmethod
    def _trade_returns_from_input(
        data: Union[pd.Series, pd.DataFrame, np.ndarray, list],
        return_col: str = "return",
    ) -> np.ndarray:
        """Extract 1-d array of trade returns from Series, DataFrame, or array."""
        if isinstance(data, pd.DataFrame):
            for col in (return_col, "pnl", "PnL", "return"):
                if col in data.columns:
                    out = data[col].dropna().values
                    break
            else:
                raise ValueError(
                    f"DataFrame must have a '{return_col}', 'pnl', or 'return' column"
                )
        elif isinstance(data, pd.Series):
            out = data.dropna().values
        elif isinstance(data, (list, np.ndarray)):
            out = np.asarray(data, dtype=float)
        else:
            raise TypeError(
                "data must be pandas Series, DataFrame, list, or numpy array"
            )
        return np.ravel(out)

    @abstractmethod
    def evaluate(
        self,
        trade_returns: Union[pd.Series, pd.DataFrame, np.ndarray, list],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Compute metrics from trade returns.

        Args:
            trade_returns: Per-trade decimal returns (e.g. 0.02 = 2%).
            **kwargs: Metric-specific options.

        Returns:
            Dictionary of metric names to values (floats or other).
        """
        pass
