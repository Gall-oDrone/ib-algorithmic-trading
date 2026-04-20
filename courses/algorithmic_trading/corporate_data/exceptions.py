"""Corporate data module exceptions."""


class CorporateDataError(Exception):
    """Base exception for corporate data errors."""

    pass


class CorporateDataStorageError(CorporateDataError):
    """Raised when persistence operations fail."""

    pass


class CorporateDataConfigurationError(CorporateDataError):
    """Raised when configuration is invalid or missing."""

    pass


class CorporateDataParseError(CorporateDataError):
    """Raised when WSH JSON payload cannot be parsed."""

    pass


class CorporateDataRequestIdExhaustedError(CorporateDataError):
    """Raised when no more unique request IDs are available."""

    pass
