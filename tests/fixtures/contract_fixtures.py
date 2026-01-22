"""Contract test fixtures."""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import after path setup
try:
    from consts.contracts import get_contract
except ImportError:
    # Fallback for relative import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from consts.contracts import get_contract


def get_test_contract_apple():
    """Get Apple test contract."""
    return get_contract("contract_test_1_apple")


def get_test_contract_google():
    """Get Google test contract."""
    return get_contract("contract_test_1_google")


def get_test_contract_palantir():
    """Get Palantir test contract."""
    return get_contract("contract_test_1_palantir")


def get_test_contract_nvidia():
    """Get NVIDIA test contract."""
    return get_contract("contract_test_1_nvidia")


def get_test_contract_microsoft():
    """Get Microsoft test contract."""
    return get_contract("contract_test_1_microsoft")


def get_test_contract_amazon():
    """Get Amazon test contract."""
    return get_contract("contract_test_1_amazon")


def get_test_contract_facebook():
    """Get Facebook (Meta) test contract."""
    return get_contract("contract_test_1_facebook")


# Aliases for backward compatibility
get_test_contract1 = get_test_contract_apple
get_test_contract2 = get_test_contract_google
get_test_contract3 = get_test_contract_palantir
