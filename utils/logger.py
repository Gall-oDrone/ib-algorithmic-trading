"""Logging utility module."""

import logging
import os
from pathlib import Path
from typing import Optional

_logger: Optional[logging.Logger] = None


def setup_logger(
    name: str = "ib_trading",
    level: str = "INFO",
    log_dir: str = "logs",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Setup and configure logger.
    
    Args:
        name: Logger name
        level: Logging level
        log_dir: Directory for log files
        log_file: Optional log file name
        
    Returns:
        Configured logger instance
    """
    global _logger
    
    if _logger is not None:
        return _logger
    
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter(
        "%(levelname)s - %(message)s"
    )
    
    # File handler
    if log_file is None:
        log_file = f"{name}.log"
    file_handler = logging.FileHandler(log_path / log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    _logger = logger
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger instance."""
    if _logger is None:
        return setup_logger(name or "ib_trading")
    return _logger
