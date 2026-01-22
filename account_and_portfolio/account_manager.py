"""Account management for IB API."""

import pandas as pd
from typing import Dict, Optional

from ibapi.client import EClient
from ibapi.wrapper import EWrapper

from ..utils import get_logger

logger = get_logger(__name__)


class AccountManager(EWrapper, EClient):
    """Manages account summary and PnL data."""
    
    def __init__(self):
        """Initialize account manager."""
        EClient.__init__(self, self)
        self._account_summary = pd.DataFrame(
            columns=["ReqId", "Account", "Tag", "Value", "Currency"]
        )
        self._pnl = pd.DataFrame(
            columns=["ReqId", "DailyPnL", "UnrealizedPnL", "RealizedPnL"]
        )
    
    def account_summary(
        self,
        req_id: int,
        account: str,
        tag: str,
        value: str,
        currency: str,
    ) -> None:
        """
        Callback for account summary updates.
        
        Args:
            req_id: Request ID
            account: Account number
            tag: Account tag
            value: Tag value
            currency: Currency
        """
        super().accountSummary(req_id, account, tag, value, currency)
        summary_row = {
            "ReqId": req_id,
            "Account": account,
            "Tag": tag,
            "Value": value,
            "Currency": currency,
        }
        self._account_summary = pd.concat(
            [self._account_summary, pd.DataFrame([summary_row])],
            ignore_index=True
        )
        logger.debug(f"Account summary update: {account} {tag} = {value}")
    
    def pnl(
        self,
        req_id: int,
        daily_pnl: float,
        unrealized_pnl: float,
        realized_pnl: float,
    ) -> None:
        """
        Callback for PnL updates.
        
        Args:
            req_id: Request ID
            daily_pnl: Daily P&L
            unrealized_pnl: Unrealized P&L
            realized_pnl: Realized P&L
        """
        super().pnl(req_id, daily_pnl, unrealized_pnl, realized_pnl)
        pnl_row = {
            "ReqId": req_id,
            "DailyPnL": daily_pnl,
            "UnrealizedPnL": unrealized_pnl,
            "RealizedPnL": realized_pnl,
        }
        self._pnl = pd.concat(
            [self._pnl, pd.DataFrame([pnl_row])],
            ignore_index=True
        )
        logger.debug(f"PnL update: Daily={daily_pnl}, Unrealized={unrealized_pnl}, Realized={realized_pnl}")
    
    def get_account_summary(self) -> pd.DataFrame:
        """
        Get account summary dataframe.
        
        Returns:
            DataFrame with account summary data
        """
        return self._account_summary.copy()
    
    def get_pnl(self) -> pd.DataFrame:
        """
        Get PnL dataframe.
        
        Returns:
            DataFrame with PnL data
        """
        return self._pnl.copy()
    
    def clear_account_summary(self) -> None:
        """Clear account summary data."""
        self._account_summary = pd.DataFrame(
            columns=["ReqId", "Account", "Tag", "Value", "Currency"]
        )
        logger.info("Cleared account summary data")
    
    def clear_pnl(self) -> None:
        """Clear PnL data."""
        self._pnl = pd.DataFrame(
            columns=["ReqId", "DailyPnL", "UnrealizedPnL", "RealizedPnL"]
        )
        logger.info("Cleared PnL data")
