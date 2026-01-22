"""Custom exceptions for AWS S3 operations."""

from exceptions import TradingAppError


class S3Error(TradingAppError):
    """Base exception for all S3-related errors."""
    pass


class S3ConnectionError(S3Error):
    """Raised when connection to S3 fails."""
    pass


class S3BucketError(S3Error):
    """Raised when bucket operations fail."""
    pass


class S3ObjectError(S3Error):
    """Raised when object operations fail."""
    pass


class S3UploadError(S3Error):
    """Raised when upload operations fail."""
    pass


class S3DownloadError(S3Error):
    """Raised when download operations fail."""
    pass
