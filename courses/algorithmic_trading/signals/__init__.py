"""Signal strategies: generate long/flat (or long/short) signals from OHLC data."""

from .base_signal_strategy import (
    BaseSignalStrategy,
    DEFAULT_CLOSE_COL,
    DEFAULT_HIGH_COL,
    DEFAULT_LOW_COL,
    DEFAULT_OPEN_COL,
)
from .macd_stochastic_long import (
    MACDStochasticLongStrategy,
    generate_macd_stochastic_long_signal,
)

__all__ = [
    "BaseSignalStrategy",
    "DEFAULT_OPEN_COL",
    "DEFAULT_HIGH_COL",
    "DEFAULT_LOW_COL",
    "DEFAULT_CLOSE_COL",
    "MACDStochasticLongStrategy",
    "generate_macd_stochastic_long_signal",
]
