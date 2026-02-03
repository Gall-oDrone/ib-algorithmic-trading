"""Backtesting module for algorithmic trading strategies."""

from .strategy.base_strategy import BaseBacktestStrategy
from .strategy.cagar import CAGARStrategy, calculate_cagar

__all__ = [
    "BaseBacktestStrategy",
    "CAGARStrategy",
    "calculate_cagar",
]
