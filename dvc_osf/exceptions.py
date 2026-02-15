"""Custom exceptions for DVC-OSF."""

from typing import Any, Optional


class OSFException(Exception):
    """Base exception for all OSF-related errors."""

    retryable: bool = False

    def __init__(self, message: str) -> None:
        """
        Initialize OSF exception.

        Args:
            message: Error message
        """
        super().__init__(message)
        self.message = message


class OSFAuthenticationError(OSFException, PermissionError):
    """Raised when authentication with OSF fails (401)."""

    retryable: bool = False

    def __init__(
        self,
        message: str = "Authentication failed. Check your OSF token.",
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
    ) -> None:
        """
        Initialize authentication error.

        Args:
            message: Error message
            status_code: HTTP status code (401)
            response: HTTP response object
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class OSFNotFoundError(OSFException, FileNotFoundError):
    """Raised when a file or resource is not found (404)."""

    retryable: bool = False

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
    ) -> None:
        """
        Initialize not found error.

        Args:
            message: Error message
            status_code: HTTP status code (404)
            response: HTTP response object
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class OSFPermissionError(OSFException, PermissionError):
    """Raised when user lacks permission for an OSF operation (403)."""

    retryable: bool = False

    def __init__(
        self,
        message: str = "Permission denied for OSF operation.",
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
    ) -> None:
        """
        Initialize permission error.

        Args:
            message: Error message
            status_code: HTTP status code (403)
            response: HTTP response object
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class OSFConnectionError(OSFException, ConnectionError):
    """Raised when connection to OSF fails (network issues)."""

    retryable: bool = True

    def __init__(
        self,
        message: str = "Failed to connect to OSF. Check your network connection.",
    ) -> None:
        """
        Initialize connection error.

        Args:
            message: Error message
        """
        super().__init__(message)


class OSFRateLimitError(OSFException, ConnectionError):
    """Raised when OSF API rate limit is hit (429)."""

    retryable: bool = True

    def __init__(
        self,
        message: str = "OSF API rate limit exceeded. Retry after backoff.",
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        """
        Initialize rate limit error.

        Args:
            message: Error message
            status_code: HTTP status code (429)
            response: HTTP response object
            retry_after: Seconds to wait before retrying (from Retry-After header)
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.retry_after = retry_after


class OSFAPIError(OSFException):
    """Raised when OSF API returns an error response."""

    retryable: bool = False

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
    ) -> None:
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response: HTTP response object
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response

        # Server errors (5xx) are retryable
        if status_code and status_code >= 500:
            self.retryable = True


class OSFIntegrityError(OSFException):
    """Raised when file checksum verification fails."""

    retryable: bool = True  # May be transient corruption

    def __init__(
        self,
        message: str,
        expected_checksum: Optional[str] = None,
        actual_checksum: Optional[str] = None,
    ) -> None:
        """
        Initialize integrity error.

        Args:
            message: Error message
            expected_checksum: Expected checksum value
            actual_checksum: Actual computed checksum value
        """
        super().__init__(message)
        self.expected_checksum = expected_checksum
        self.actual_checksum = actual_checksum


class OSFQuotaExceededError(OSFException):
    """Raised when OSF storage quota is exceeded (413)."""

    retryable: bool = False

    def __init__(
        self,
        message: str = "OSF storage quota exceeded.",
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
        bytes_uploaded: Optional[int] = None,
        total_size: Optional[int] = None,
    ) -> None:
        """
        Initialize quota exceeded error.

        Args:
            message: Error message
            status_code: HTTP status code (413)
            response: HTTP response object
            bytes_uploaded: Number of bytes uploaded before failure
            total_size: Total size of file being uploaded
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.bytes_uploaded = bytes_uploaded
        self.total_size = total_size


class OSFFileLockedError(OSFPermissionError):
    """Raised when file is locked for modification (423)."""

    retryable: bool = False

    def __init__(
        self,
        message: str = "File is locked and cannot be modified.",
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
        bytes_uploaded: Optional[int] = None,
        total_size: Optional[int] = None,
    ) -> None:
        """
        Initialize file locked error.

        Args:
            message: Error message
            status_code: HTTP status code (423)
            response: HTTP response object
            bytes_uploaded: Number of bytes uploaded before failure
            total_size: Total size of file being uploaded
        """
        super().__init__(message, status_code, response)
        self.bytes_uploaded = bytes_uploaded
        self.total_size = total_size


class OSFVersionConflictError(OSFException):
    """Raised when file version conflict occurs (409)."""

    retryable: bool = False

    def __init__(
        self,
        message: str = "File version conflict detected.",
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
        bytes_uploaded: Optional[int] = None,
        total_size: Optional[int] = None,
    ) -> None:
        """
        Initialize version conflict error.

        Args:
            message: Error message
            status_code: HTTP status code (409)
            response: HTTP response object
            bytes_uploaded: Number of bytes uploaded before failure
            total_size: Total size of file being uploaded
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.bytes_uploaded = bytes_uploaded
        self.total_size = total_size
