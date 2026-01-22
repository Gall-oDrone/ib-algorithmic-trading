"""Contract handling utilities."""

from typing import Dict, Optional

from ibapi.contract import Contract

from exceptions import ContractError
from utils import get_logger

logger = get_logger(__name__)


class ContractHandler:
    """Handles creation and validation of IB contracts."""
    
    @staticmethod
    def create_contract(
        symbol: str,
        sec_type: str = "STK",
        currency: str = "USD",
        exchange: str = "SMART",
    ) -> Contract:
        """
        Create an IB contract.
        
        Args:
            symbol: Symbol/ticker
            sec_type: Security type (STK, OPT, FUT, etc.)
            currency: Currency code
            exchange: Exchange name
            
        Returns:
            Contract object
            
        Raises:
            ContractError: If contract creation fails
        """
        try:
            contract = Contract()
            contract.symbol = symbol
            contract.secType = sec_type
            contract.currency = currency
            contract.exchange = exchange
            
            logger.debug(f"Created contract: {symbol} ({sec_type}) on {exchange}")
            return contract
            
        except Exception as e:
            logger.error(f"Failed to create contract for {symbol}: {e}")
            raise ContractError(f"Contract creation failed: {e}") from e
    
    @staticmethod
    def create_contract_from_dict(contract_dict: Dict[str, str]) -> Contract:
        """
        Create contract from dictionary.
        
        Args:
            contract_dict: Dictionary with contract details
            
        Returns:
            Contract object
        """
        return ContractHandler.create_contract(
            symbol=contract_dict.get("symbol", ""),
            sec_type=contract_dict.get("sec", "STK"),
            currency=contract_dict.get("currency", "USD"),
            exchange=contract_dict.get("exchange", "SMART"),
        )
    
    @staticmethod
    def validate_contract(contract: Contract) -> bool:
        """
        Validate a contract object.
        
        Args:
            contract: Contract to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not contract.symbol:
            logger.warning("Contract missing symbol")
            return False
        if not contract.secType:
            logger.warning("Contract missing security type")
            return False
        return True
