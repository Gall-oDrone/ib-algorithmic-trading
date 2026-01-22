"""Custom exceptions for trading operations."""


class TradingAppError(Exception):
    """Base exception for all trading application errors."""
    pass


class ConnectionError(TradingAppError):
    """Raised when connection to IB API fails."""
    pass


class OrderError(TradingAppError):
    """Raised when order operations fail."""
    pass


class ContractError(TradingAppError):
    """Raised when contract operations fail."""
    pass


class DataError(TradingAppError):
    """Raised when data operations fail."""
    pass
