"""Historical data handling."""

from typing import Dict, List, Optional

from ibapi.bar import BarData
from ibapi.contract import Contract

from ..utils import get_logger

logger = get_logger(__name__)


class HistoricalDataHandler:
    """Handles historical data requests and storage."""
    
    def __init__(self):
        """Initialize historical data handler."""
        self._data: Dict[int, List[Dict[str, any]]] = {}
        self._request_map: Dict[int, str] = {}  # Maps reqId to symbol
    
    def add_bar(self, req_id: int, bar: BarData) -> None:
        """
        Add a bar to the data storage.
        
        Args:
            req_id: Request ID
            bar: Bar data
        """
        bar_data = {
            "Date": bar.date,
            "Open": float(bar.open),
            "High": float(bar.high),
            "Low": float(bar.low),
            "Close": float(bar.close),
            "Volume": int(bar.volume),
        }
        
        if req_id not in self._data:
            self._data[req_id] = []
        
        self._data[req_id].append(bar_data)
        logger.debug(f"Added bar for req_id {req_id}: {bar_data}")
    
    def get_data(self, req_id: int) -> List[Dict[str, any]]:
        """
        Get historical data for a request ID.
        
        Args:
            req_id: Request ID
            
        Returns:
            List of bar data dictionaries
        """
        return self._data.get(req_id, [])
    
    def get_all_data(self) -> Dict[int, List[Dict[str, any]]]:
        """
        Get all historical data.
        
        Returns:
            Dictionary mapping req_id to bar data
        """
        return self._data.copy()
    
    def clear_data(self, req_id: Optional[int] = None) -> None:
        """
        Clear historical data.
        
        Args:
            req_id: Optional request ID to clear specific data
        """
        if req_id is None:
            self._data.clear()
            self._request_map.clear()
            logger.info("Cleared all historical data")
        else:
            if req_id in self._data:
                del self._data[req_id]
            if req_id in self._request_map:
                del self._request_map[req_id]
            logger.info(f"Cleared data for req_id {req_id}")
    
    def register_request(self, req_id: int, symbol: str) -> None:
        """
        Register a request with its symbol.
        
        Args:
            req_id: Request ID
            symbol: Symbol being requested
        """
        self._request_map[req_id] = symbol
        logger.debug(f"Registered request {req_id} for symbol {symbol}")
    
    def get_symbol(self, req_id: int) -> Optional[str]:
        """
        Get symbol for a request ID.
        
        Args:
            req_id: Request ID
            
        Returns:
            Symbol if found, None otherwise
        """
        return self._request_map.get(req_id)
