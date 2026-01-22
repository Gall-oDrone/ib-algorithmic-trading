"""Tests for ContractHandler."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from handlers.contract_handler import ContractHandler
    from exceptions import ContractError
except ImportError:
    from ..handlers.contract_handler import ContractHandler
    from ..exceptions import ContractError

from .conftest import contract_handler, sample_contract


def test_create_contract(contract_handler):
    """Test contract creation."""
    contract = contract_handler.create_contract("AAPL")
    
    assert contract.symbol == "AAPL"
    assert contract.secType == "STK"
    assert contract.currency == "USD"
    assert contract.exchange == "SMART"


def test_create_contract_custom_params(contract_handler):
    """Test contract creation with custom parameters."""
    contract = contract_handler.create_contract(
        "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
    )
    
    assert contract.symbol == "NDX"
    assert contract.secType == "IND"
    assert contract.currency == "USD"
    assert contract.exchange == "NASDAQ"


def test_create_contract_from_dict(contract_handler):
    """Test contract creation from dictionary."""
    contract_dict = {
        "symbol": "GOOGL",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    }
    contract = contract_handler.create_contract_from_dict(contract_dict)
    
    assert contract.symbol == "GOOGL"
    assert contract.secType == "STK"


def test_validate_contract(contract_handler, sample_contract):
    """Test contract validation."""
    assert contract_handler.validate_contract(sample_contract) is True


def test_validate_invalid_contract(contract_handler):
    """Test validation of invalid contract."""
    from ibapi.contract import Contract
    
    invalid_contract = Contract()
    assert contract_handler.validate_contract(invalid_contract) is False
