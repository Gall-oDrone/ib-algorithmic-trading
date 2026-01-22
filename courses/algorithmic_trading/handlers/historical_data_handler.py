"""Historical data handling."""

from pathlib import Path
from typing import Dict, List, Literal, Optional

import pandas as pd
from ibapi.common import BarData
from ibapi.contract import Contract

from utils import get_logger

logger = get_logger(__name__)

# Default output directory for historical data exports
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "data" / "historical_output"


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
    
    def export_data(
        self,
        req_id: Optional[int] = None,
        symbol: Optional[str] = None,
        output_format: Literal["csv", "json", "parquet", "excel"] = "csv",
        output_path: Optional[Path] = None,
        include_index: bool = True,
        keep_files: bool = False,
    ) -> Dict[str, Path]:
        """
        Export historical data to a specified format.
        
        Args:
            req_id: Optional specific request ID to export. If None, exports all data.
            symbol: Optional symbol name for the filename (used when req_id is specified).
            output_format: Output format - 'csv', 'json', 'parquet', or 'excel'. Default is 'csv'.
            output_path: Output directory path. Default is data/historical_output folder.
            include_index: Whether to include the Date index in the output. Default is True.
            keep_files: If True, keeps the exported files. If False, deletes them after export. Default is False.
            
        Returns:
            Dictionary mapping symbols to their exported file paths.
            
        Raises:
            ValueError: If no data is available to export or invalid format specified.
        """
        self._keep_files = keep_files
        # Set default output path
        if output_path is None:
            output_path = DEFAULT_OUTPUT_DIR
        else:
            output_path = Path(output_path)
        
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Validate format
        valid_formats = ["csv", "json", "parquet", "excel"]
        if output_format not in valid_formats:
            raise ValueError(f"Invalid format '{output_format}'. Must be one of: {valid_formats}")
        
        exported_files: Dict[str, Path] = {}
        
        # Determine which data to export
        if req_id is not None:
            # Export specific request
            data = self.get_data(req_id)
            if not data:
                raise ValueError(f"No data found for req_id {req_id}")
            
            # Use symbol from parameter or request map
            file_symbol = symbol or self.get_symbol(req_id) or f"req_{req_id}"
            df = pd.DataFrame(data)
            if "Date" in df.columns:
                df.set_index("Date", inplace=True)
            
            file_path = self._export_dataframe(
                df, file_symbol, output_format, output_path, include_index
            )
            exported_files[file_symbol] = file_path
        else:
            # Export all data
            if not self._data:
                raise ValueError("No data available to export")
            
            for rid, data in self._data.items():
                file_symbol = self.get_symbol(rid) or f"req_{rid}"
                df = pd.DataFrame(data)
                if "Date" in df.columns:
                    df.set_index("Date", inplace=True)
                
                file_path = self._export_dataframe(
                    df, file_symbol, output_format, output_path, include_index
                )
                exported_files[file_symbol] = file_path
        
        return exported_files
    
    def _export_dataframe(
        self,
        df: pd.DataFrame,
        symbol: str,
        output_format: str,
        output_path: Path,
        include_index: bool,
    ) -> Path:
        """
        Export a single DataFrame to the specified format.
        
        Args:
            df: DataFrame to export
            symbol: Symbol name for the filename
            output_format: Output format
            output_path: Output directory
            include_index: Whether to include index
            
        Returns:
            Path to the exported file
        """
        # Determine file extension
        extension_map = {
            "csv": ".csv",
            "json": ".json",
            "parquet": ".parquet",
            "excel": ".xlsx",
        }
        extension = extension_map[output_format]
        file_path = output_path / f"{symbol}_historical{extension}"
        
        # Export based on format
        if output_format == "csv":
            df.to_csv(file_path, index=include_index)
        elif output_format == "json":
            df.to_json(file_path, orient="index" if include_index else "records", indent=2)
        elif output_format == "parquet":
            df.to_parquet(file_path, index=include_index)
        elif output_format == "excel":
            df.to_excel(file_path, index=include_index)
        
        logger.info(f"Exported {symbol} historical data to {file_path}")
        
        # Delete file if keep_files is False
        if not self._keep_files:
            file_path.unlink()
            logger.info(f"Deleted {file_path} (keep_files=False)")
        
        return file_path
