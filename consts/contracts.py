"""Contract constants for testing and trading."""

from typing import Dict, Any


# Contract definitions
CONTRACTS: Dict[str, Dict[str, str]] = {
    "contract_test_1_apple": {
        "symbol": "AAPL",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_google": {
        "symbol": "GOOG",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_palantir": {
        "symbol": "PLTR",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_nvidia": {
        "symbol": "NVDA",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_microsoft": {
        "symbol": "MSFT",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_amazon": {
        "symbol": "AMZN",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_facebook": {
        "symbol": "META",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_twitter": {
        "symbol": "TWTR",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_tiktok": {
        "symbol": "TTD",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_netflix": {
        "symbol": "NFLX",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
    "contract_test_1_tesla": {
        "symbol": "TSLA",
        "sec": "STK",
        "currency": "USD",
        "exchange": "SMART",
    },
}


def get_contracts() -> Dict[str, Dict[str, str]]:
    """
    Get all contract definitions.
    
    Returns:
        Dictionary of contract definitions
    """
    return CONTRACTS.copy()


def get_contract(key: str) -> Dict[str, str]:
    """
    Get a specific contract by key.
    
    Args:
        key: Contract key
        
    Returns:
        Contract definition dictionary
    """
    return CONTRACTS.get(key, {})
