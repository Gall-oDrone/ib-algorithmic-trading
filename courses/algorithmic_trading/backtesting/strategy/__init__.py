"""Backtesting strategies."""

from .base_strategy import BaseBacktestStrategy
from .cagar import CAGARStrategy, calculate_cagar

__all__ = [
    "BaseBacktestStrategy",
    "CAGARStrategy",
    "calculate_cagar",
]
