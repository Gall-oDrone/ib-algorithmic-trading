"""Volatility and Sharpe Ratio backtesting strategy."""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from utils import get_logger

from .base_strategy import BaseBacktestStrategy

logger = get_logger(__name__)

TRADING_DAYS_PER_YEAR = 252
DEFAULT_TIME_PERIODS: List[int] = [1, 3, 5]


class VolatilitySharpeStrategy(BaseBacktestStrategy):
    """Backtesting strategy for annualized volatility and Sharpe ratio.

    Uses daily resampling of the equity series so that volatility and Sharpe
    are comparable across intraday and daily data. Risk-free rate is
    configurable (default 0); per-period rate is derived from annual rate.
    """

    def __init__(
        self,
        time_periods: Optional[List[int]] = None,
        include_full_period: bool = True,
        include_rolling: bool = False,
        risk_free_rate_annual: float = 0.0,
    ):
        """
        Initialize the strategy.

        Args:
            time_periods: Trailing periods in years (e.g. [1, 3, 5]).
            include_full_period: If True, add volatility_full and sharpe_full.
            include_rolling: If True, add rolling volatility and Sharpe series.
            risk_free_rate_annual: Annual risk-free rate (e.g. 0.02 for 2%).
        """
        super().__init__("VolatilitySharpe")
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
        self._risk_free_rate_annual = float(risk_free_rate_annual)

    @property
    def risk_free_rate_annual(self) -> float:
        """Return the configured annual risk-free rate."""
        return self._risk_free_rate_annual

    def _daily_equity(self, equity: pd.Series) -> pd.Series:
        """Resample to daily (last value per day) and dropna."""
        if not isinstance(equity.index, pd.DatetimeIndex):
            return equity
        daily = equity.resample("D").last().dropna()
        return daily

    def _daily_returns(self, equity: pd.Series) -> pd.Series:
        """Return daily returns from equity series (daily or resampled)."""
        daily = self._daily_equity(equity)
        if len(daily) < 2:
            return pd.Series(dtype=float)
        return daily.pct_change().dropna()

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

    def _years_between(self, start: pd.Timestamp, end: pd.Timestamp) -> float:
        """Approximate years between two timestamps."""
        delta = end - start
        return delta.total_seconds() / (365.25 * 24 * 3600)

    def _period_key(self, years: float, prefix: str) -> str:
        """Metric key for period (e.g. volatility_1y, sharpe_1y)."""
        if years == int(years):
            return f"{prefix}_{int(years)}y"
        return f"{prefix}_{years}y"

    def _annualized_volatility(self, returns: pd.Series) -> float:
        """Annualized volatility = std(returns) * sqrt(252)."""
        if returns is None or len(returns) < 2:
            return np.nan
        std = returns.std()
        if std <= 0 or np.isnan(std):
            return np.nan
        return float(std * np.sqrt(TRADING_DAYS_PER_YEAR))

    def _annualized_sharpe(
        self,
        returns: pd.Series,
        risk_free_rate_annual: float,
    ) -> float:
        """Annualized Sharpe = (mean(R) - rf_daily) / std(R) * sqrt(252)."""
        if returns is None or len(returns) < 2:
            return np.nan
        std = returns.std()
        if std <= 0 or np.isnan(std):
            return np.nan
        rf_daily = (1.0 + risk_free_rate_annual) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0
        excess = returns.mean() - rf_daily
        return float(excess / std * np.sqrt(TRADING_DAYS_PER_YEAR))

    def evaluate(
        self,
        equity: pd.Series,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Evaluate volatility and Sharpe over configured periods.

        Returns:
            Dict with volatility_1y, volatility_full, sharpe_1y, sharpe_full,
            and optionally rolling_* series.
        """
        time_periods = kwargs.get("time_periods", self._time_periods)
        include_full = kwargs.get("include_full_period", self._include_full_period)
        include_rolling = kwargs.get("include_rolling", self._include_rolling)
        rf = kwargs.get("risk_free_rate_annual", self._risk_free_rate_annual)

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
                "daily resampling may be approximate."
            )

        returns = self._daily_returns(equity)
        if len(returns) < 2:
            return self._empty_result(time_periods, include_full, include_rolling)

        daily = self._daily_equity(equity)
        end_date = daily.index[-1]
        result: Dict[str, Any] = {}

        for years in time_periods:
            start_date = self._start_date_for_period(end_date, years)
            mask = returns.index <= end_date
            if start_date is not None:
                mask = mask & (returns.index >= start_date)
            segment = returns.loc[mask]
            if len(segment) < 2:
                result[self._period_key(years, "volatility")] = np.nan
                result[self._period_key(years, "sharpe")] = np.nan
                continue
            result[self._period_key(years, "volatility")] = self._annualized_volatility(
                segment
            )
            result[self._period_key(years, "sharpe")] = self._annualized_sharpe(
                segment, rf
            )

        if include_full:
            result["volatility_full"] = self._annualized_volatility(returns)
            result["sharpe_full"] = self._annualized_sharpe(returns, rf)

        if include_rolling:
            for years in time_periods:
                vol_series = self._rolling_volatility(equity, years)
                sharpe_series = self._rolling_sharpe(equity, years, rf)
                result[f"rolling_{self._period_key(years, 'volatility')}"] = vol_series
                result[f"rolling_{self._period_key(years, 'sharpe')}"] = sharpe_series

        logger.debug(
            f"Calculated Volatility/Sharpe for {len(equity)} points, "
            f"periods={time_periods}, rf_annual={rf}"
        )
        return result

    def _rolling_volatility(self, equity: pd.Series, years: float) -> pd.Series:
        """Rolling annualized volatility over the given period in years."""
        daily = self._daily_equity(equity)
        returns = daily.pct_change().dropna()
        out = pd.Series(index=equity.index, dtype=float)
        min_days = max(2, int(365.25 * years * 0.5))
        for i in range(len(equity)):
            end_ts = equity.index[i]
            start_ts = self._start_date_for_period(end_ts, years)
            if start_ts is None:
                out.iloc[i] = np.nan
                continue
            segment = returns.loc[
                (returns.index >= start_ts) & (returns.index <= end_ts)
            ]
            if len(segment) < min_days:
                out.iloc[i] = np.nan
                continue
            out.iloc[i] = self._annualized_volatility(segment)
        return out

    def _rolling_sharpe(
        self,
        equity: pd.Series,
        years: float,
        risk_free_rate_annual: float,
    ) -> pd.Series:
        """Rolling annualized Sharpe over the given period in years."""
        daily = self._daily_equity(equity)
        returns = daily.pct_change().dropna()
        out = pd.Series(index=equity.index, dtype=float)
        min_days = max(2, int(365.25 * years * 0.5))
        for i in range(len(equity)):
            end_ts = equity.index[i]
            start_ts = self._start_date_for_period(end_ts, years)
            if start_ts is None:
                out.iloc[i] = np.nan
                continue
            segment = returns.loc[
                (returns.index >= start_ts) & (returns.index <= end_ts)
            ]
            if len(segment) < min_days:
                out.iloc[i] = np.nan
                continue
            out.iloc[i] = self._annualized_sharpe(segment, risk_free_rate_annual)
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
            result[self._period_key(years, "volatility")] = np.nan
            result[self._period_key(years, "sharpe")] = np.nan
        if include_full:
            result["volatility_full"] = np.nan
            result["sharpe_full"] = np.nan
        if include_rolling:
            for years in time_periods:
                result[f"rolling_{self._period_key(years, 'volatility')}"] = pd.Series(
                    dtype=float
                )
                result[f"rolling_{self._period_key(years, 'sharpe')}"] = pd.Series(
                    dtype=float
                )
        return result


def calculate_volatility_sharpe(
    equity: pd.Series,
    time_periods: Optional[List[int]] = None,
    include_full_period: bool = True,
    include_rolling: bool = False,
    risk_free_rate_annual: float = 0.0,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Compute volatility and Sharpe metrics (convenience function).

    Args:
        equity: Time series of equity or close prices.
        time_periods: Trailing periods in years (e.g. [1, 3, 5]).
        include_full_period: Include full-period volatility and Sharpe.
        include_rolling: Include rolling series per period.
        risk_free_rate_annual: Annual risk-free rate for Sharpe.
        **kwargs: Passed to VolatilitySharpeStrategy.evaluate().

    Returns:
        Dictionary of volatility_* and sharpe_* metrics.
    """
    strategy = VolatilitySharpeStrategy(
        time_periods=time_periods,
        include_full_period=include_full_period,
        include_rolling=include_rolling,
        risk_free_rate_annual=risk_free_rate_annual,
    )
    return strategy.evaluate(equity, **kwargs)
