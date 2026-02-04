"""Backtesting module for algorithmic trading strategies."""

from .strategy.base_strategy import BaseBacktestStrategy
from .strategy.cagar import CAGARStrategy, calculate_cagar
from .strategy.volatility_sharpe import (
    VolatilitySharpeStrategy,
    calculate_volatility_sharpe,
)

__all__ = [
    "BaseBacktestStrategy",
    "CAGARStrategy",
    "calculate_cagar",
    "VolatilitySharpeStrategy",
    "calculate_volatility_sharpe",
]
