"""Maximum Drawdown backtesting strategy."""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from utils import get_logger

from .base_strategy import BaseBacktestStrategy

logger = get_logger(__name__)

DEFAULT_TIME_PERIODS: List[int] = [1, 3, 5]


class MaxDrawdownStrategy(BaseBacktestStrategy):
    """Backtesting strategy for Maximum Drawdown.

    Maximum drawdown is the largest peak-to-trough decline in equity over a
    given period. Reported as a positive fraction (e.g. 0.15 = 15% drawdown).
    Uses the same trailing periods (e.g. 1Y, 3Y, 5Y) and optional full-period
    and rolling series as CAGAR and Volatility/Sharpe.
    """

    def __init__(
        self,
        time_periods: Optional[List[int]] = None,
        include_full_period: bool = True,
        include_rolling: bool = False,
    ):
        """
        Initialize the strategy.

        Args:
            time_periods: Trailing periods in years (e.g. [1, 3, 5]).
            include_full_period: If True, add max_drawdown_full.
            include_rolling: If True, add rolling max drawdown series per period.
        """
        super().__init__("MaxDrawdown")
        periods = time_periods if time_periods is not None else list(DEFAULT_TIME_PERIODS)
        if not periods:
            raise ValueError("time_periods must contain at least one period")
        for p in periods:
            if not isinstance(p, (int, float)) or p <= 0:
                raise ValueError(
                    f"Each time period must be a positive number, got {p!r}"
                )
        self._time_periods: List[float] = [float(p) for p in periods]
        self._include_full_period = include_full_period
        self._include_rolling = include_rolling

    def _period_key(self, years: float) -> str:
        """Metric key for period (e.g. max_drawdown_1y, max_drawdown_3y)."""
        if years == int(years):
            return f"max_drawdown_{int(years)}y"
        return f"max_drawdown_{years}y"

    def _start_date_for_period(
        self,
        end_date: pd.Timestamp,
        years: float,
    ) -> Optional[pd.Timestamp]:
        """Start date for a trailing period (years before end_date)."""
        try:
            days = int(365.25 * years)
            return end_date - pd.Timedelta(days=days + 1)
        except Exception:
            return None

    def _max_drawdown_from_series(self, equity: pd.Series) -> float:
        """
        Maximum drawdown over the equity series.
        Drawdown at each time = (running_max - equity) / running_max.
        Returns the maximum drawdown as a positive fraction (e.g. 0.20 = 20%).
        """
        if equity is None or len(equity) < 2:
            return np.nan
        equity = equity.dropna()
        if len(equity) < 2:
            return np.nan
        running_max = equity.cummax()
        # Avoid division by zero; treat 0 peak as no drawdown
        drawdowns = np.where(running_max > 0, (running_max - equity) / running_max, 0.0)
        return float(np.max(drawdowns))

    def evaluate(
        self,
        equity: pd.Series,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Evaluate maximum drawdown over configured periods.

        Returns:
            Dict with max_drawdown_1y, max_drawdown_3y, ..., max_drawdown_full,
            and optionally rolling_max_drawdown_* series.
        """
        time_periods = kwargs.get("time_periods", self._time_periods)
        include_full = kwargs.get("include_full_period", self._include_full_period)
        include_rolling = kwargs.get("include_rolling", self._include_rolling)

        if equity is None or len(equity) < 2:
            logger.warning(
                f"{self.name}: Insufficient equity data (length "
                f"{len(equity) if equity is not None else 0})"
            )
            return self._empty_result(time_periods, include_full, include_rolling)
        equity = equity.dropna()
        if len(equity) < 2:
            return self._empty_result(time_periods, include_full, include_rolling)

        if not isinstance(equity.index, pd.DatetimeIndex):
            logger.warning(
                f"{self.name}: Equity index is not DatetimeIndex; "
                "periods may be approximate."
            )

        end_date = equity.index[-1]
        result: Dict[str, Any] = {}

        for years in time_periods:
            start_date = self._start_date_for_period(end_date, years)
            mask = equity.index <= end_date
            if start_date is not None:
                mask = mask & (equity.index >= start_date)
            segment = equity.loc[mask]
            if len(segment) < 2:
                result[self._period_key(years)] = np.nan
                continue
            result[self._period_key(years)] = self._max_drawdown_from_series(segment)

        if include_full:
            result["max_drawdown_full"] = self._max_drawdown_from_series(equity)

        if include_rolling:
            for years in time_periods:
                result[f"rolling_{self._period_key(years)}"] = self._rolling_max_drawdown(
                    equity, years
                )

        logger.debug(
            f"Calculated Max Drawdown for {len(equity)} points, "
            f"periods={time_periods}"
        )
        return result

    def _rolling_max_drawdown(self, equity: pd.Series, years: float) -> pd.Series:
        """Rolling maximum drawdown over the given period in years."""
        out = pd.Series(index=equity.index, dtype=float)
        min_points = max(2, int(365.25 * years * 0.5))
        for i in range(len(equity)):
            end_ts = equity.index[i]
            start_ts = self._start_date_for_period(end_ts, years)
            if start_ts is None:
                out.iloc[i] = np.nan
                continue
            segment = equity.loc[
                (equity.index >= start_ts) & (equity.index <= end_ts)
            ]
            if len(segment) < min_points:
                out.iloc[i] = np.nan
                continue
            out.iloc[i] = self._max_drawdown_from_series(segment)
        return out

    def _empty_result(
        self,
        time_periods: List[float],
        include_full: bool,
        include_rolling: bool,
    ) -> Dict[str, Any]:
        """Result dict with NaN for all scalar metrics and empty series for rolling."""
        result: Dict[str, Any] = {}
        for years in time_periods:
            result[self._period_key(years)] = np.nan
        if include_full:
            result["max_drawdown_full"] = np.nan
        if include_rolling:
            for years in time_periods:
                result[f"rolling_{self._period_key(years)}"] = pd.Series(dtype=float)
        return result


def calculate_max_drawdown(
    equity: pd.Series,
    time_periods: Optional[List[int]] = None,
    include_full_period: bool = True,
    include_rolling: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Compute maximum drawdown metrics (convenience function).

    Args:
        equity: Time series of equity or close prices.
        time_periods: Trailing periods in years (e.g. [1, 3, 5]).
        include_full_period: Include full-period max drawdown.
        include_rolling: Include rolling max drawdown series per period.
        **kwargs: Passed to MaxDrawdownStrategy.evaluate().

    Returns:
        Dictionary of max_drawdown_* metrics.
    """
    strategy = MaxDrawdownStrategy(
        time_periods=time_periods,
        include_full_period=include_full_period,
        include_rolling=include_rolling,
    )
    return strategy.evaluate(equity, **kwargs)
