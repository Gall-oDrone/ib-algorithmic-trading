"""CAGAR (Compound Annual Growth And Return) backtesting strategy."""

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from utils import get_logger

from .base_strategy import BaseBacktestStrategy

logger = get_logger(__name__)

# Default time periods in years for CAGR calculation
DEFAULT_TIME_PERIODS: List[int] = [1, 3, 5]


class CAGARStrategy(BaseBacktestStrategy):
    """CAGAR backtesting strategy.

    Evaluates performance using Compound Annual Growth Rate (CAGR) over
    configurable time periods. Supports multiple trailing periods (e.g. 1Y, 3Y, 5Y)
    and optional full-period and rolling CAGR series.

    CAGR formula: (Ending Value / Beginning Value)^(1/years) - 1
    """

    def __init__(
        self,
        time_periods: Optional[List[int]] = None,
        include_full_period: bool = True,
        include_rolling: bool = False,
    ):
        """
        Initialize CAGAR strategy.

        Args:
            time_periods: List of trailing periods in years (e.g. [1, 3, 5]).
                If None, uses DEFAULT_TIME_PERIODS.
            include_full_period: If True, add 'cagar_full' over entire series.
            include_rolling: If True, add rolling CAGR series per period.
        """
        super().__init__("CAGAR")
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

    @property
    def time_periods(self) -> List[float]:
        """Return the configured time periods in years."""
        return list(self._time_periods)

    def evaluate(
        self,
        equity: pd.Series,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Evaluate performance using CAGR over configured time periods.

        Args:
            equity: Time series of equity or close prices (DatetimeIndex).
            **kwargs: Optional overrides: time_periods, include_full_period,
                include_rolling.

        Returns:
            Dictionary with:
            - cagar_{n}y: trailing CAGR over last n years (float)
            - cagar_full: CAGR over entire series (if include_full_period)
            - rolling_cagar_{n}y: rolling CAGR series (if include_rolling)
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
                "CAGR periods may be approximate."
            )

        result: Dict[str, Any] = {}

        # Trailing CAGRs from end of series
        end_value = float(equity.iloc[-1])
        end_date = equity.index[-1]

        for years in time_periods:
            key = self._period_key(years)
            start_date = self._start_date_for_period(end_date, years)
            mask = equity.index <= end_date
            if start_date is not None:
                mask = mask & (equity.index >= start_date)
            segment = equity.loc[mask].sort_index()
            if len(segment) < 2:
                result[key] = np.nan
                continue
            start_value = float(segment.iloc[0])
            segment_end_value = float(segment.iloc[-1])
            actual_years = self._years_between(segment.index[0], segment.index[-1])
            if actual_years <= 0:
                result[key] = np.nan
                continue
            result[key] = self._cagr(start_value, segment_end_value, actual_years)

        if include_full:
            start_value = float(equity.iloc[0])
            total_years = self._years_between(equity.index[0], equity.index[-1])
            if total_years > 0:
                result["cagar_full"] = self._cagr(
                    start_value, end_value, total_years
                )
            else:
                result["cagar_full"] = np.nan

        if include_rolling:
            for years in time_periods:
                key = f"rolling_{self._period_key(years)}"
                result[key] = self._rolling_cagr(equity, years)

        logger.debug(
            f"Calculated CAGAR for {len(equity)} points, "
            f"periods={time_periods}"
        )
        return result

    def _period_key(self, years: float) -> str:
        """Return metric key for period (e.g. cagar_1y, cagar_3y)."""
        if years == int(years):
            return f"cagar_{int(years)}y"
        return f"cagar_{years}y"

    def _years_between(self, start: pd.Timestamp, end: pd.Timestamp) -> float:
        """Return approximate years between two timestamps."""
        delta = end - start
        return delta.total_seconds() / (365.25 * 24 * 3600)

    def _start_date_for_period(
        self,
        end_date: pd.Timestamp,
        years: float,
    ) -> Optional[pd.Timestamp]:
        """Return start date for a trailing period (years before end_date)."""
        try:
            # Use floor so that exact N-year spacing is included (e.g. 2024-01-01 to 2025-01-01)
            days = int(365.25 * years)
            return end_date - pd.Timedelta(days=days + 1)
        except Exception:
            return None

    def _cagr(
        self,
        start_value: float,
        end_value: float,
        years: float,
    ) -> float:
        """Compute CAGR: (end/start)^(1/years) - 1."""
        if start_value <= 0 or years <= 0:
            return np.nan
        return float((end_value / start_value) ** (1.0 / years) - 1.0)

    def _rolling_cagr(self, equity: pd.Series, years: float) -> pd.Series:
        """Compute rolling CAGR over a given period in years."""
        out = pd.Series(index=equity.index, dtype=float)
        min_days = max(2, int(365.25 * years * 0.5))
        for i in range(len(equity)):
            end_val = float(equity.iloc[i])
            end_ts = equity.index[i]
            start_ts = self._start_date_for_period(end_ts, years)
            if start_ts is None:
                out.iloc[i] = np.nan
                continue
            segment = equity.loc[
                (equity.index >= start_ts) & (equity.index <= end_ts)
            ]
            if len(segment) < 2:
                out.iloc[i] = np.nan
                continue
            start_val = float(segment.iloc[0])
            actual_years = self._years_between(segment.index[0], segment.index[-1])
            if actual_years <= 0:
                out.iloc[i] = np.nan
                continue
            out.iloc[i] = self._cagr(start_val, end_val, actual_years)
        return out

    def _empty_result(
        self,
        time_periods: List[float],
        include_full: bool,
        include_rolling: bool,
    ) -> Dict[str, Any]:
        """Return result dict with NaN for all metrics."""
        result: Dict[str, Any] = {}
        for years in time_periods:
            result[self._period_key(years)] = np.nan
        if include_full:
            result["cagar_full"] = np.nan
        if include_rolling:
            for years in time_periods:
                result[f"rolling_{self._period_key(years)}"] = pd.Series(
                    dtype=float
                )
        return result

    def evaluate_from_dataframe(
        self,
        data: pd.DataFrame,
        value_col: str = "Close",
        date_col: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Evaluate CAGAR from a DataFrame (OHLC or equity)."""
        return super().evaluate_from_dataframe(
            data, value_col=value_col, date_col=date_col, **kwargs
        )


def calculate_cagar(
    equity: pd.Series,
    time_periods: Optional[List[int]] = None,
    include_full_period: bool = True,
    include_rolling: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Compute CAGAR metrics (convenience function).

    Args:
        equity: Time series of equity or close prices.
        time_periods: List of trailing periods in years (e.g. [1, 3, 5]).
        include_full_period: Include CAGR over full series.
        include_rolling: Include rolling CAGR series per period.
        **kwargs: Passed to CAGARStrategy.evaluate().

    Returns:
        Dictionary of CAGAR metrics (same as CAGARStrategy.evaluate()).
    """
    strategy = CAGARStrategy(
        time_periods=time_periods,
        include_full_period=include_full_period,
        include_rolling=include_rolling,
    )
    return strategy.evaluate(equity, **kwargs)
