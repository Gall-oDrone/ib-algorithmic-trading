"""NDX intraday signal strategy: MACD + Stochastic for entries/exits, ATR for stop loss levels."""

from typing import Any, Union

import numpy as np
import pandas as pd

from utils import get_logger

from indicators.macd import MACDIndicator
from indicators.stochastic import StochasticIndicator
from indicators.atr import ATRIndicator

from .base_signal_strategy import (
    BaseSignalStrategy,
    DEFAULT_CLOSE_COL,
    DEFAULT_HIGH_COL,
    DEFAULT_LOW_COL,
    DEFAULT_OPEN_COL,
)

logger = get_logger(__name__)


class NDXIntradayStrategy(BaseSignalStrategy):
    """Intraday strategy: MACD + Stochastic for signals, ATR for stop loss. Supports long (1) and short (-1).

    Long: enter when both MACD and Stochastic bullish, exit on bearish. Stop = close - atr_mult*ATR.
    Short: enter when both MACD and Stochastic bearish, exit on bullish. Stop = close + atr_mult*ATR.
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
        atr_period: int = 14,
        atr_mult: float = 2.0,
        allow_short: bool = True,
    ):
        """
        Initialize NDX intraday strategy.

        Args:
            fast_period: MACD fast EMA period.
            slow_period: MACD slow EMA period.
            signal_period: MACD signal line period.
            k_period: Stochastic %K period.
            d_period: Stochastic %D period.
            stoch_oversold: Oversold threshold (e.g. 20).
            stoch_overbought: Overbought threshold (e.g. 80).
            atr_period: ATR period for stop distance.
            atr_mult: Multiplier for ATR (long stop = close - atr_mult*ATR, short stop = close + atr_mult*ATR).
            allow_short: If True, emit -1 (short) signals; if False, long-only (1/0).
        """
        super().__init__("NDXIntraday")
        if slow_period < 1 or signal_period < 1 or k_period < 1 or d_period < 1 or atr_period < 1:
            raise ValueError("Periods must be positive")
        if atr_mult <= 0:
            raise ValueError("atr_mult must be positive")
        self._macd = MACDIndicator(
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
        )
        self._stoch = StochasticIndicator(k_period=k_period, d_period=d_period)
        self._atr = ATRIndicator(period=atr_period)
        self._stoch_oversold = stoch_oversold
        self._stoch_overbought = stoch_overbought
        self._atr_period = atr_period
        self._atr_mult = atr_mult
        self._allow_short = allow_short
        self._warmup = max(
            slow_period + signal_period,
            k_period + d_period - 1,
            atr_period + 1,
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
        include_stop_levels: bool = False,
        **kwargs: Any,
    ) -> Union[pd.Series, pd.DataFrame]:
        """
        Generate long/short/flat (1/-1/0) signals and optionally stop level series.

        Signal at bar t means position held at end of bar t: 1=long, -1=short, 0=flat.
        When include_stop_levels is True, returns DataFrame with 'signal' and 'stop_level'.
        Long stop_level = close - atr_mult*ATR; short stop_level = close + atr_mult*ATR.
        """
        self._require_ohlc(data, open_col, high_col, low_col, close_col)
        close = data[close_col]
        high = data[high_col]
        low = data[low_col]
        n = len(data)
        index = data.index

        macd_result = self._macd.calculate(close)
        stoch_result = self._stoch.calculate(high, low, close)
        atr_result = self._atr.calculate(high, low, close)
        histogram = macd_result["histogram"]
        stoch_k = stoch_result["stoch_k"]
        stoch_d = stoch_result["stoch_d"]
        atr = atr_result["atr"]

        valid = (
            histogram.notna()
            & stoch_k.notna()
            & stoch_d.notna()
            & atr.notna()
        )

        # MACD entry/exit
        entry_macd = (histogram > 0) & (histogram.shift(1) <= 0)
        entry_macd = entry_macd.fillna(False).astype(bool)
        exit_macd = (histogram < 0) & (histogram.shift(1) >= 0)
        exit_macd = exit_macd.fillna(False).astype(bool)

        # Stochastic entry
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

        # Stochastic exit
        in_overbought = (stoch_k > self._stoch_overbought) | (stoch_d > self._stoch_overbought)
        k_crosses_below_d = (stoch_k < stoch_d) & (stoch_k.shift(1) >= stoch_d.shift(1))
        exit_stoch = (
            (k_crosses_below_d & in_overbought)
            | ((stoch_k < stoch_d) & (stoch_k > self._stoch_overbought))
        )
        exit_stoch = exit_stoch.fillna(False).astype(bool)

        entry_long = entry_macd & entry_stoch & valid
        exit_long = (exit_macd | exit_stoch) & valid
        # Short: enter when both bearish, exit when either bullish
        entry_short = exit_macd & exit_stoch & valid if self._allow_short else pd.Series(False, index=index)
        exit_short = (entry_macd | entry_stoch) & valid

        signal = np.zeros(n, dtype=np.int64)
        for i in range(1, n):
            if not valid.iloc[i]:
                signal[i] = 0
                continue
            prev = signal[i - 1]
            if prev == 1:
                signal[i] = 0 if exit_long.iloc[i] else 1
            elif prev == -1:
                signal[i] = 0 if exit_short.iloc[i] else -1
            else:
                if entry_long.iloc[i]:
                    signal[i] = 1
                elif self._allow_short and entry_short.iloc[i]:
                    signal[i] = -1
                else:
                    signal[i] = 0

        out_series = pd.Series(signal, index=index, dtype=np.int64)

        # Stop level: long = close - atr_mult*ATR; short = close + atr_mult*ATR
        stop_level = pd.Series(np.nan, index=index, dtype=float)
        where_long = out_series == 1
        where_short = out_series == -1
        stop_level.loc[where_long] = (
            close.loc[where_long] - self._atr_mult * atr.loc[where_long]
        )
        stop_level.loc[where_short] = (
            close.loc[where_short] + self._atr_mult * atr.loc[where_short]
        )

        if not include_components and not include_stop_levels:
            return out_series

        out_dict = {"signal": out_series}
        if include_stop_levels:
            out_dict["stop_level"] = stop_level
        if include_components:
            out_dict["macd_bullish"] = entry_macd
            out_dict["macd_bearish"] = exit_macd
            out_dict["stoch_bullish"] = entry_stoch
            out_dict["stoch_bearish"] = exit_stoch
            if self._allow_short:
                out_dict["entry_short"] = entry_short
                out_dict["exit_short"] = exit_short
        return pd.DataFrame(out_dict, index=index)


def generate_ndx_intraday_signal(
    data: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    k_period: int = 14,
    d_period: int = 3,
    stoch_oversold: float = 20.0,
    stoch_overbought: float = 80.0,
    atr_period: int = 14,
    atr_mult: float = 2.0,
    allow_short: bool = True,
    include_components: bool = False,
    include_stop_levels: bool = False,
    **kwargs: Any,
) -> Union[pd.Series, pd.DataFrame]:
    """
    Generate NDX intraday signals (convenience function).

    Returns:
        Series (1=long, -1=short, 0=flat) or DataFrame if include_components or include_stop_levels.
    """
    strategy = NDXIntradayStrategy(
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        k_period=k_period,
        d_period=d_period,
        stoch_oversold=stoch_oversold,
        stoch_overbought=stoch_overbought,
        atr_period=atr_period,
        atr_mult=atr_mult,
        allow_short=allow_short,
    )
    return strategy.generate(
        data,
        include_components=include_components,
        include_stop_levels=include_stop_levels,
        **kwargs,
    )
