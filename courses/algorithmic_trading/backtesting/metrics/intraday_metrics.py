"""Intraday trade-based metrics: absolute return, win rate, mean returns, max consecutive loss."""

from typing import Any, Dict, Union

import numpy as np
import pandas as pd

from utils import get_logger

from .base_metric import BaseTradeMetric

logger = get_logger(__name__)


class IntradayTradeMetrics(BaseTradeMetric):
    """Compute intraday-style metrics from a sequence of trade returns.

    Metrics:
    - absolute_return: Cumulative compounded return (product of (1 + r_i) - 1).
    - win_rate: Fraction of trades with positive return (0..1).
    - mean_return_per_trade: Mean of trade returns.
    - mean_return_winning_trades: Mean return over winning trades only; NaN if none.
    - mean_return_losing_trades: Mean return over losing trades only; NaN if none.
    - maximum_consecutive_loss: Max number of consecutive losing trades (return < 0).
    """

    def __init__(self) -> None:
        super().__init__("IntradayTradeMetrics")

    def evaluate(
        self,
        trade_returns: Union[pd.Series, pd.DataFrame, np.ndarray, list],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Compute all six intraday metrics from trade returns.

        Args:
            trade_returns: Per-trade decimal returns (e.g. 0.02 = 2%).
            **kwargs: Unused; for API compatibility.

        Returns:
            Dict with keys: absolute_return, win_rate, mean_return_per_trade,
            mean_return_winning_trades, mean_return_losing_trades,
            maximum_consecutive_loss.
        """
        return_col = kwargs.get("return_col", "return")
        r = self._trade_returns_from_input(trade_returns, return_col=return_col)

        if len(r) == 0:
            logger.warning(
                f"{self.name}: No trade returns provided; returning NaN metrics."
            )
            return self._empty_result()

        n = len(r)
        wins = r > 0
        losses = r < 0
        n_wins = int(np.sum(wins))
        n_losses = int(np.sum(losses))

        # Absolute return: compounded (1+r1)(1+r2)... - 1
        absolute_return = float(np.prod(1.0 + r) - 1.0)

        # Win rate: fraction of trades that are winners
        win_rate = float(np.mean(wins))

        # Mean return per trade
        mean_return_per_trade = float(np.mean(r))

        # Mean return winning / losing trades
        mean_return_winning_trades = (
            float(np.mean(r[wins])) if n_wins > 0 else np.nan
        )
        mean_return_losing_trades = (
            float(np.mean(r[losses])) if n_losses > 0 else np.nan
        )

        # Maximum consecutive losing trades
        maximum_consecutive_loss = self._max_consecutive_losses(r)

        result: Dict[str, Any] = {
            "absolute_return": absolute_return,
            "win_rate": win_rate,
            "mean_return_per_trade": mean_return_per_trade,
            "mean_return_winning_trades": mean_return_winning_trades,
            "mean_return_losing_trades": mean_return_losing_trades,
            "maximum_consecutive_loss": maximum_consecutive_loss,
        }
        logger.debug(
            f"{self.name}: Computed metrics for {n} trades, "
            f"win_rate={win_rate:.2%}, abs_return={absolute_return:.4f}"
        )
        return result

    @staticmethod
    def _max_consecutive_losses(returns: np.ndarray) -> int:
        """Return the maximum number of consecutive trades with negative return."""
        if len(returns) == 0:
            return 0
        is_loss = returns < 0
        max_streak = 0
        current = 0
        for x in is_loss:
            if x:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return int(max_streak)

    def _empty_result(self) -> Dict[str, Any]:
        """Return dict of NaN for all metrics when there are no trades."""
        return {
            "absolute_return": np.nan,
            "win_rate": np.nan,
            "mean_return_per_trade": np.nan,
            "mean_return_winning_trades": np.nan,
            "mean_return_losing_trades": np.nan,
            "maximum_consecutive_loss": 0,
        }


def calculate_intraday_metrics(
    trade_returns: Union[pd.Series, pd.DataFrame, np.ndarray, list],
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Convenience function to compute intraday trade metrics.

    Args:
        trade_returns: Per-trade decimal returns.
        **kwargs: Passed to IntradayTradeMetrics.evaluate().

    Returns:
        Dictionary of metric names to values.
    """
    calculator = IntradayTradeMetrics()
    return calculator.evaluate(trade_returns, **kwargs)
