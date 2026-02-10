"""Long-only signal strategy combining MACD and Stochastic indicators."""

from typing import Any, Union

import numpy as np
import pandas as pd

from utils import get_logger

from indicators.macd import MACDIndicator
from indicators.stochastic import StochasticIndicator

from .base_signal_strategy import (
    BaseSignalStrategy,
    DEFAULT_CLOSE_COL,
    DEFAULT_HIGH_COL,
    DEFAULT_LOW_COL,
    DEFAULT_OPEN_COL,
)

logger = get_logger(__name__)


class MACDStochasticLongStrategy(BaseSignalStrategy):
    """Long-only strategy: enter when MACD and Stochastic are both bullish, exit on bearish.

    Entry (go long) when both are true:
    - MACD bullish: histogram crosses above 0 (histogram > 0 and previous <= 0).
    - Stochastic bullish: %K crosses above %D in oversold zone, or both were
      below oversold and now %K > %D.

    Exit (go flat) when any of:
    - MACD bearish: histogram crosses below 0.
    - Stochastic overbought exit: %K crosses below %D in overbought zone, or
      %K < %D and %K > overbought threshold.
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        k_period: int = 14,
        d_period: int = 3,
        stoch_oversold: float = 20.0,
        stoch_overbought: float = 80.0,
    ):
        """
        Initialize MACD + Stochastic long strategy.

        Args:
            fast_period: MACD fast EMA period.
            slow_period: MACD slow EMA period.
            signal_period: MACD signal line period.
            k_period: Stochastic %K period.
            d_period: Stochastic %D period.
            stoch_oversold: Oversold threshold (e.g. 20).
            stoch_overbought: Overbought threshold (e.g. 80).
        """
        super().__init__("MACDStochasticLong")
        if slow_period < 1 or signal_period < 1 or k_period < 1 or d_period < 1:
            raise ValueError("Periods must be positive")
        self._macd = MACDIndicator(
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
        )
        self._stoch = StochasticIndicator(k_period=k_period, d_period=d_period)
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._signal_period = signal_period
        self._k_period = k_period
        self._d_period = d_period
        self._stoch_oversold = stoch_oversold
        self._stoch_overbought = stoch_overbought
        self._warmup = max(
            slow_period + signal_period,
            k_period + d_period - 1,
        )

    def generate(
        self,
        data: pd.DataFrame,
        *,
        open_col: str = DEFAULT_OPEN_COL,
        high_col: str = DEFAULT_HIGH_COL,
        low_col: str = DEFAULT_LOW_COL,
        close_col: str = DEFAULT_CLOSE_COL,
        include_components: bool = False,
        **kwargs: Any,
    ) -> Union[pd.Series, pd.DataFrame]:
        """
        Generate long/flat (1/0) signals from OHLC data using MACD + Stochastic.

        Signal at bar t means position held at end of bar t (1=long, 0=flat).
        """
        self._require_ohlc(data, open_col, high_col, low_col, close_col)
        close = data[close_col]
        high = data[high_col]
        low = data[low_col]
        n = len(data)
        index = data.index

        macd_result = self._macd.calculate(close)
        stoch_result = self._stoch.calculate(high, low, close)
        histogram = macd_result["histogram"]
        stoch_k = stoch_result["stoch_k"]
        stoch_d = stoch_result["stoch_d"]

        # Valid bars: all indicators non-NaN (warm-up handled in state machine via valid)
        valid = (
            histogram.notna()
            & stoch_k.notna()
            & stoch_d.notna()
        )

        # MACD entry: histogram crosses above 0
        entry_macd = (histogram > 0) & (histogram.shift(1) <= 0)
        entry_macd = entry_macd.fillna(False).astype(bool)

        # MACD exit: histogram crosses below 0
        exit_macd = (histogram < 0) & (histogram.shift(1) >= 0)
        exit_macd = exit_macd.fillna(False).astype(bool)

        # Stochastic entry: (a) %K crosses above %D in oversold, or
        # (b) both %K and %D were below oversold on prior bar and now %K > %D
        in_oversold = (stoch_k < self._stoch_oversold) | (stoch_d < self._stoch_oversold)
        k_crosses_above_d = (stoch_k > stoch_d) & (stoch_k.shift(1) <= stoch_d.shift(1))
        both_oversold_prev = (
            (stoch_k.shift(1) < self._stoch_oversold)
            & (stoch_d.shift(1) < self._stoch_oversold)
        )
        entry_stoch = (
            (k_crosses_above_d & in_oversold)
            | (both_oversold_prev & (stoch_k > stoch_d))
        )
        entry_stoch = entry_stoch.fillna(False).astype(bool)

        # Stochastic exit: %K crosses below %D in overbought, or %K < %D and %K > overbought
        in_overbought = (stoch_k > self._stoch_overbought) | (stoch_d > self._stoch_overbought)
        k_crosses_below_d = (stoch_k < stoch_d) & (stoch_k.shift(1) >= stoch_d.shift(1))
        exit_stoch = (
            (k_crosses_below_d & in_overbought)
            | ((stoch_k < stoch_d) & (stoch_k > self._stoch_overbought))
        )
        exit_stoch = exit_stoch.fillna(False).astype(bool)

        entry_signal = entry_macd & entry_stoch & valid
        exit_signal = (exit_macd | exit_stoch) & valid

        # State machine: long[t] = (long[t-1] and not exit[t]) or (not long[t-1] and entry[t])
        signal = np.zeros(n, dtype=np.int64)
        for i in range(1, n):
            if not valid.iloc[i] if hasattr(valid, "iloc") else not valid[i]:
                signal[i] = 0
                continue
            if signal[i - 1] == 1:
                signal[i] = 0 if exit_signal.iloc[i] else 1
            else:
                signal[i] = 1 if entry_signal.iloc[i] else 0

        out_series = pd.Series(signal, index=index, dtype=np.int64)
        if not include_components:
            return out_series

        components = pd.DataFrame(
            {
                "signal": out_series,
                "macd_bullish": entry_macd,
                "macd_bearish": exit_macd,
                "stoch_bullish": entry_stoch,
                "stoch_bearish": exit_stoch,
            },
            index=index,
        )
        return components


def generate_macd_stochastic_long_signal(
    data: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    k_period: int = 14,
    d_period: int = 3,
    stoch_oversold: float = 20.0,
    stoch_overbought: float = 80.0,
    include_components: bool = False,
    **kwargs: Any,
) -> Union[pd.Series, pd.DataFrame]:
    """
    Generate long/flat signals using MACD + Stochastic (convenience function).

    Args:
        data: OHLC DataFrame (columns Open, High, Low, Close).
        fast_period: MACD fast period.
        slow_period: MACD slow period.
        signal_period: MACD signal period.
        k_period: Stochastic %K period.
        d_period: Stochastic %D period.
        stoch_oversold: Oversold threshold.
        stoch_overbought: Overbought threshold.
        include_components: If True, return DataFrame with signal and components.

    Returns:
        Series (1=long, 0=flat) or DataFrame if include_components is True.
    """
    strategy = MACDStochasticLongStrategy(
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        k_period=k_period,
        d_period=d_period,
        stoch_oversold=stoch_oversold,
        stoch_overbought=stoch_overbought,
    )
    return strategy.generate(data, include_components=include_components, **kwargs)
