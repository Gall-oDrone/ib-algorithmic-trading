"""Streaming market data module exceptions."""


class StreamingMarketDataError(Exception):
    """Base exception for streaming market data errors."""

    pass


class StorageError(StreamingMarketDataError):
    """Raised when persistence (e.g. PostgreSQL) operations fail."""

    pass


class ConfigurationError(StreamingMarketDataError):
    """Raised when configuration is invalid or missing."""

    pass


class RequestIdExhaustedError(StreamingMarketDataError):
    """Raised when no more unique request IDs are available."""

    pass
