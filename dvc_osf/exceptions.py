"""Custom exceptions for DVC-OSF."""

from typing import Optional


class OSFException(Exception):
    """Base exception for all OSF-related errors."""

    pass


class OSFAuthenticationError(OSFException):
    """Raised when authentication with OSF fails."""

    pass


class OSFProjectNotFoundError(OSFException):
    """Raised when an OSF project cannot be found."""

    pass


class OSFFileNotFoundError(OSFException):
    """Raised when a file or directory is not found on OSF."""

    pass


class OSFPermissionError(OSFException):
    """Raised when user lacks permission for an OSF operation."""

    pass


class OSFConnectionError(OSFException):
    """Raised when connection to OSF fails."""

    pass


class OSFAPIError(OSFException):
    """Raised when OSF API returns an error response."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        """
        Initialize OSF API error.

        Args:
            message: Error message
            status_code: HTTP status code from API response
        """
        super().__init__(message)
        self.status_code = status_code


class OSFInvalidPathError(OSFException):
    """Raised when an OSF path is invalid or malformed."""

    pass
