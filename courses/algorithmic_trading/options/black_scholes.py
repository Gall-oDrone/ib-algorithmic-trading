"""Black-Scholes option pricing model."""

from dataclasses import dataclass
from enum import Enum
from math import erf, exp, log, sqrt
from typing import Optional, Tuple

import pandas as pd

from indicators.historical_volatility import HistoricalVolatilityIndicator
from utils import get_logger

logger = get_logger(__name__)


class OptionType(str, Enum):
    """Supported option types."""

    CALL = "call"
    PUT = "put"


class OptionStyle(str, Enum):
    """Supported exercise styles."""

    EUROPEAN = "european"
    AMERICAN = "american"


@dataclass(frozen=True)
class BlackScholesInputs:
    """Inputs required to price a vanilla option."""

    spot_price: float
    strike_price: float
    time_to_maturity: float
    risk_free_rate: float
    volatility: float
    option_type: OptionType
    dividend_yield: float = 0.0
    option_style: OptionStyle = OptionStyle.EUROPEAN


class BlackScholesModel:
    """Black-Scholes model for European and American call/put options."""

    def __init__(self, annualization_periods: int = 252, american_steps: int = 200):
        if american_steps <= 1:
            raise ValueError("american_steps must be greater than 1")
        self._volatility_indicator = HistoricalVolatilityIndicator(
            annualization_periods=annualization_periods
        )
        self.american_steps = american_steps

    def price(self, params: BlackScholesInputs) -> float:
        """Price an option using closed-form (European) or binomial tree (American)."""
        self._validate_inputs(params)
        if params.option_style == OptionStyle.AMERICAN:
            return self._price_american(params)

        return self._price_european(params)

    def _price_european(self, params: BlackScholesInputs) -> float:
        """Price a European option using Black-Scholes closed form."""
        d1, d2 = self._compute_d1_d2(params)

        if params.option_type == OptionType.CALL:
            return (
                params.spot_price
                * exp(-params.dividend_yield * params.time_to_maturity)
                * self._standard_normal_cdf(d1)
                - params.strike_price
                * exp(-params.risk_free_rate * params.time_to_maturity)
                * self._standard_normal_cdf(d2)
            )

        return (
            params.strike_price
            * exp(-params.risk_free_rate * params.time_to_maturity)
            * self._standard_normal_cdf(-d2)
            - params.spot_price
            * exp(-params.dividend_yield * params.time_to_maturity)
            * self._standard_normal_cdf(-d1)
        )

    def _price_american(self, params: BlackScholesInputs) -> float:
        """
        Price an American option using a Cox-Ross-Rubinstein binomial tree.

        This enables early exercise at each time step.
        """
        steps = self.american_steps
        dt = params.time_to_maturity / steps
        up = exp(params.volatility * sqrt(dt))
        down = 1.0 / up
        growth = exp((params.risk_free_rate - params.dividend_yield) * dt)
        discount = exp(-params.risk_free_rate * dt)

        probability = (growth - down) / (up - down)
        if not 0.0 <= probability <= 1.0:
            raise ValueError(
                "Invalid risk-neutral probability. Adjust inputs or increase steps."
            )

        terminal_values = []
        for i in range(steps + 1):
            stock_price = params.spot_price * (up ** (steps - i)) * (down**i)
            terminal_values.append(
                self._intrinsic_value(
                    option_type=params.option_type,
                    spot_price=stock_price,
                    strike_price=params.strike_price,
                )
            )

        option_values = terminal_values
        for step in range(steps - 1, -1, -1):
            for i in range(step + 1):
                stock_price = params.spot_price * (up ** (step - i)) * (down**i)
                continuation = discount * (
                    probability * option_values[i]
                    + (1.0 - probability) * option_values[i + 1]
                )
                exercise = self._intrinsic_value(
                    option_type=params.option_type,
                    spot_price=stock_price,
                    strike_price=params.strike_price,
                )
                option_values[i] = max(exercise, continuation)

        return option_values[0]

    def price_from_market_data(
        self,
        spot_price: float,
        strike_price: float,
        time_to_maturity: float,
        risk_free_rate: float,
        option_type: OptionType,
        price_history: Optional[pd.Series] = None,
        volatility: Optional[float] = None,
        dividend_yield: float = 0.0,
        volatility_window: int = 30,
        option_style: OptionStyle = OptionStyle.EUROPEAN,
    ) -> float:
        """Price using explicit volatility or estimated historical volatility."""
        if volatility is None:
            if price_history is None:
                raise ValueError(
                    "price_history is required when volatility is not provided"
                )
            estimated_vol = self._volatility_indicator.calculate(
                data=price_history, window=volatility_window
            )["historical_volatility"]
            volatility = float(estimated_vol.dropna().iloc[-1])
            logger.debug("Estimated historical volatility: %.6f", volatility)

        params = BlackScholesInputs(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_maturity=time_to_maturity,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            option_type=option_type,
            dividend_yield=dividend_yield,
            option_style=option_style,
        )
        return self.price(params)

    @staticmethod
    def _standard_normal_cdf(value: float) -> float:
        """Compute the standard normal CDF."""
        return 0.5 * (1.0 + erf(value / sqrt(2.0)))

    def _compute_d1_d2(self, params: BlackScholesInputs) -> Tuple[float, float]:
        variance_term = params.volatility * sqrt(params.time_to_maturity)
        carry = params.risk_free_rate - params.dividend_yield
        d1 = (
            log(params.spot_price / params.strike_price)
            + (carry + 0.5 * params.volatility**2) * params.time_to_maturity
        ) / variance_term
        d2 = d1 - variance_term
        return d1, d2

    @staticmethod
    def _validate_inputs(params: BlackScholesInputs) -> None:
        if params.spot_price <= 0:
            raise ValueError("spot_price must be greater than 0")
        if params.strike_price <= 0:
            raise ValueError("strike_price must be greater than 0")
        if params.time_to_maturity <= 0:
            raise ValueError("time_to_maturity must be greater than 0")
        if params.volatility <= 0:
            raise ValueError("volatility must be greater than 0")

    @staticmethod
    def _intrinsic_value(option_type: OptionType, spot_price: float, strike_price: float) -> float:
        if option_type == OptionType.CALL:
            return max(spot_price - strike_price, 0.0)
        return max(strike_price - spot_price, 0.0)
