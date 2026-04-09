"""Fundamental data module exceptions."""


class FundamentalDataError(Exception):
    """Base exception for fundamental data errors."""

    pass


class FundamentalDataStorageError(FundamentalDataError):
    """Raised when persistence operations fail."""

    pass


class FundamentalDataConfigurationError(FundamentalDataError):
    """Raised when configuration is invalid or missing."""

    pass


class FundamentalDataParseError(FundamentalDataError):
    """Raised when XML payload cannot be parsed."""

    pass


class FundamentalDataRequestIdExhaustedError(FundamentalDataError):
    """Raised when no more unique request IDs are available."""

    pass
