"""DataFrame management for historical data storage."""

import pandas as pd
from typing import Dict, List, Optional

from handlers.historical_data_handler import HistoricalDataHandler
from utils import get_logger

logger = get_logger(__name__)


class DataFrameManager:
    """Manages conversion of historical data to DataFrames."""
    
    def __init__(self, data_handler: Optional[HistoricalDataHandler] = None):
        """
        Initialize dataframe manager.
        
        Args:
            data_handler: HistoricalDataHandler instance
        """
        self.data_handler = data_handler or HistoricalDataHandler()
    
    def create_dataframes(
        self,
        tickers: Optional[List[str]] = None,
        data: Optional[Dict[int, List[Dict[str, any]]]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Create DataFrames from historical data.
        
        Args:
            tickers: List of tickers (optional, if data dict maps to tickers)
            data: Historical data dictionary mapping req_id to bar data
            
        Returns:
            Dictionary mapping ticker symbols to DataFrames
        """
        if data is None:
            data = self.data_handler.get_all_data()
        
        df_dict: Dict[str, pd.DataFrame] = {}
        
        if tickers:
            # Map tickers to request IDs
            for i, ticker in enumerate(tickers):
                if i in data:
                    df = pd.DataFrame(data[i])
                    if "Date" in df.columns:
                        df.set_index("Date", inplace=True)
                    df_dict[ticker] = df
                    logger.debug(f"Created DataFrame for {ticker}: {df.shape}")
        else:
            # Use request map from handler
            for req_id, symbol in self.data_handler._request_map.items():
                if req_id in data:
                    df = pd.DataFrame(data[req_id])
                    if "Date" in df.columns:
                        df.set_index("Date", inplace=True)
                    df_dict[symbol] = df
                    logger.debug(f"Created DataFrame for {symbol}: {df.shape}")
        
        return df_dict
    
    def create_dataframe_from_data(
        self,
        data: List[Dict[str, any]],
        index_column: str = "Date",
    ) -> pd.DataFrame:
        """
        Create a single DataFrame from bar data.
        
        Args:
            data: List of bar data dictionaries
            index_column: Column to use as index
            
        Returns:
            DataFrame with bar data
        """
        df = pd.DataFrame(data)
        if index_column in df.columns:
            df.set_index(index_column, inplace=True)
        return df
