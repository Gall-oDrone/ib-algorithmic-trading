"""Portfolio management for IB API."""

import pandas as pd
from typing import Dict, Optional

from ibapi.contract import Contract

from ..utils import get_logger

logger = get_logger(__name__)


class PortfolioManager:
    """Manages portfolio position tracking."""
    
    def __init__(self):
        """Initialize portfolio manager."""
        self._positions = pd.DataFrame(
            columns=["Account", "Symbol", "SecType", "Currency", "Position", "AvgCost"]
        )
    
    def add_position(
        self,
        account: str,
        contract: Contract,
        position: float,
        avg_cost: float,
    ) -> None:
        """
        Add or update a position.
        
        Args:
            account: Account number
            contract: Contract object
            position: Position size
            avg_cost: Average cost
        """
        position_row = {
            "Account": account,
            "Symbol": contract.symbol,
            "SecType": contract.secType,
            "Currency": contract.currency,
            "Position": position,
            "AvgCost": avg_cost,
        }
        
        # Check if position exists for this account and symbol
        existing = self._positions[
            (self._positions["Account"] == account) &
            (self._positions["Symbol"] == contract.symbol)
        ]
        
        if not existing.empty:
            # Update existing position
            idx = existing.index[0]
            self._positions.loc[idx] = position_row
            logger.debug(f"Updated position: {account} {contract.symbol} = {position}")
        else:
            # Add new position
            self._positions = pd.concat(
                [self._positions, pd.DataFrame([position_row])],
                ignore_index=True
            )
            logger.debug(f"Added position: {account} {contract.symbol} = {position}")
    
    def get_positions(self) -> pd.DataFrame:
        """
        Get all positions.
        
        Returns:
            DataFrame with position data
        """
        return self._positions.copy()
    
    def get_positions_by_account(self, account: str) -> pd.DataFrame:
        """
        Get positions for a specific account.
        
        Args:
            account: Account number
            
        Returns:
            DataFrame with positions for the account
        """
        return self._positions[self._positions["Account"] == account].copy()
    
    def clear_positions(self) -> None:
        """Clear all position data."""
        self._positions = pd.DataFrame(
            columns=["Account", "Symbol", "SecType", "Currency", "Position", "AvgCost"]
        )
        logger.info("Cleared all positions")
