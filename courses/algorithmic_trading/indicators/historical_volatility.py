"""Historical volatility indicator."""

from typing import Dict

import numpy as np
import pandas as pd

from .base_indicator import BaseIndicator
from utils import get_logger

logger = get_logger(__name__)


class HistoricalVolatilityIndicator(BaseIndicator):
    """Rolling historical volatility based on log returns."""

    def __init__(self, window: int = 30, annualization_periods: int = 252):
        super().__init__("HistoricalVolatility")
        if window <= 1:
            raise ValueError("window must be greater than 1")
        if annualization_periods <= 0:
            raise ValueError("annualization_periods must be greater than 0")

        self.window = window
        self.annualization_periods = annualization_periods

    def calculate(self, data: pd.Series, **kwargs) -> Dict[str, pd.Series]:
        """Calculate annualized rolling historical volatility."""
        window = kwargs.get("window", self.window)
        annualization_periods = kwargs.get(
            "annualization_periods", self.annualization_periods
        )

        if window <= 1:
            raise ValueError("window must be greater than 1")
        if annualization_periods <= 0:
            raise ValueError("annualization_periods must be greater than 0")

        if not self.validate_data(data, min_length=window + 1):
            if data is None:
                return {"historical_volatility": pd.Series(dtype=float)}
            return {"historical_volatility": pd.Series(index=data.index, dtype=float)}

        log_returns = np.log(data / data.shift(1))
        rolling_std = log_returns.rolling(window=window).std()
        historical_volatility = rolling_std * np.sqrt(annualization_periods)

        logger.debug(
            "Calculated historical volatility for %s data points (window=%s)",
            len(data),
            window,
        )
        return {"historical_volatility": historical_volatility}


def calculate_historical_volatility(
    data: pd.Series, window: int = 30, annualization_periods: int = 252
) -> Dict[str, pd.Series]:
    """Convenience function for historical volatility."""
    indicator = HistoricalVolatilityIndicator(
        window=window, annualization_periods=annualization_periods
    )
    return indicator.calculate(data)
