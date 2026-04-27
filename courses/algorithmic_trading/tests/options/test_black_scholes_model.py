"""Tests for Black-Scholes options pricing model."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from options.black_scholes import BlackScholesInputs, BlackScholesModel, OptionType


def test_black_scholes_call_known_value():
    """Validate call option pricing against a known benchmark."""
    model = BlackScholesModel()
    params = BlackScholesInputs(
        spot_price=100.0,
        strike_price=100.0,
        time_to_maturity=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
        option_type=OptionType.CALL,
    )

    call_price = model.price(params)
    assert call_price == pytest.approx(10.4506, rel=1e-4)


def test_black_scholes_put_known_value():
    """Validate put option pricing against a known benchmark."""
    model = BlackScholesModel()
    params = BlackScholesInputs(
        spot_price=100.0,
        strike_price=100.0,
        time_to_maturity=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
        option_type=OptionType.PUT,
    )

    put_price = model.price(params)
    assert put_price == pytest.approx(5.5735, rel=1e-4)


def test_black_scholes_put_call_parity():
    """Verify put-call parity for European options."""
    model = BlackScholesModel()
    common = dict(
        spot_price=100.0,
        strike_price=95.0,
        time_to_maturity=0.75,
        risk_free_rate=0.03,
        volatility=0.25,
    )

    call = model.price(BlackScholesInputs(option_type=OptionType.CALL, **common))
    put = model.price(BlackScholesInputs(option_type=OptionType.PUT, **common))
    rhs = common["spot_price"] - common["strike_price"] * np.exp(
        -common["risk_free_rate"] * common["time_to_maturity"]
    )

    assert (call - put) == pytest.approx(rhs, rel=1e-4)


def test_price_from_market_data_with_explicit_volatility():
    """Use direct volatility input when pricing from market data."""
    model = BlackScholesModel()
    price = model.price_from_market_data(
        spot_price=100.0,
        strike_price=100.0,
        time_to_maturity=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
        option_type=OptionType.CALL,
    )
    assert price == pytest.approx(10.4506, rel=1e-4)


def test_price_from_market_data_with_historical_volatility():
    """Estimate volatility from historical prices when not provided."""
    model = BlackScholesModel()
    np.random.seed(42)
    returns = np.random.normal(0.0003, 0.01, 120)
    prices = 100 * np.exp(np.cumsum(returns))
    price_history = pd.Series(prices)

    price = model.price_from_market_data(
        spot_price=float(prices[-1]),
        strike_price=102.0,
        time_to_maturity=0.5,
        risk_free_rate=0.03,
        option_type=OptionType.CALL,
        price_history=price_history,
        volatility_window=30,
    )
    assert price > 0.0


def test_price_from_market_data_requires_history_when_no_volatility():
    """Raise when no volatility source is available."""
    model = BlackScholesModel()
    with pytest.raises(
        ValueError, match="price_history is required when volatility is not provided"
    ):
        model.price_from_market_data(
            spot_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            option_type=OptionType.CALL,
            volatility=None,
            price_history=None,
        )


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("spot_price", 0.0, "spot_price must be greater than 0"),
        ("strike_price", 0.0, "strike_price must be greater than 0"),
        ("time_to_maturity", 0.0, "time_to_maturity must be greater than 0"),
        ("volatility", 0.0, "volatility must be greater than 0"),
    ],
)
def test_black_scholes_input_validation(field, value, message):
    """Validate pricing inputs."""
    base = dict(
        spot_price=100.0,
        strike_price=100.0,
        time_to_maturity=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
        option_type=OptionType.CALL,
    )
    base[field] = value
    params = BlackScholesInputs(**base)
    model = BlackScholesModel()

    with pytest.raises(ValueError, match=message):
        model.price(params)
