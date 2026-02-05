"""Backtesting module for algorithmic trading strategies and metrics."""

from .strategy.base_strategy import BaseBacktestStrategy
from .strategy.cagar import CAGARStrategy, calculate_cagar
from .strategy.volatility_sharpe import (
    VolatilitySharpeStrategy,
    calculate_volatility_sharpe,
)
from .strategy.max_drawdown import MaxDrawdownStrategy, calculate_max_drawdown
from .metrics import (
    BaseTradeMetric,
    IntradayTradeMetrics,
    calculate_intraday_metrics,
)

__all__ = [
    "BaseBacktestStrategy",
    "CAGARStrategy",
    "calculate_cagar",
    "VolatilitySharpeStrategy",
    "calculate_volatility_sharpe",
    "MaxDrawdownStrategy",
    "calculate_max_drawdown",
    "BaseTradeMetric",
    "IntradayTradeMetrics",
    "calculate_intraday_metrics",
]
