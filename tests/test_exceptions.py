"""Tests for OSF exception classes."""

from dvc_osf.exceptions import (
    OSFAPIError,
    OSFAuthenticationError,
    OSFConflictError,
    OSFConnectionError,
    OSFException,
    OSFFileLockedError,
    OSFIntegrityError,
    OSFNotFoundError,
    OSFOperationNotSupportedError,
    OSFPermissionError,
    OSFQuotaExceededError,
    OSFRateLimitError,
    OSFVersionConflictError,
)


class TestOSFException:
    """Tests for base OSFException class."""

    def test_inheritance(self):
        """Test that OSFException inherits from Exception."""
        exc = OSFException("test error")
        assert isinstance(exc, Exception)

    def test_message(self):
        """Test that message is stored correctly."""
        exc = OSFException("test error")
        assert exc.message == "test error"
        assert str(exc) == "test error"

    def test_retryable_default(self):
        """Test that base exception is not retryable by default."""
        exc = OSFException("test error")
        assert exc.retryable is False


class TestOSFAuthenticationError:
    """Tests for OSFAuthenticationError."""

    def test_inheritance(self):
        """Test multiple inheritance from OSFException and PermissionError."""
        exc = OSFAuthenticationError()
        assert isinstance(exc, OSFException)
        assert isinstance(exc, PermissionError)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFAuthenticationError()
        assert "Authentication failed" in exc.message

    def test_custom_message(self):
        """Test custom error message."""
        exc = OSFAuthenticationError("Custom auth error")
        assert exc.message == "Custom auth error"

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFAuthenticationError(status_code=401)
        assert exc.status_code == 401

    def test_response(self):
        """Test response attribute."""
        mock_response = {"error": "invalid token"}
        exc = OSFAuthenticationError(response=mock_response)
        assert exc.response == mock_response

    def test_not_retryable(self):
        """Test that authentication errors are not retryable."""
        exc = OSFAuthenticationError()
        assert exc.retryable is False


class TestOSFNotFoundError:
    """Tests for OSFNotFoundError."""

    def test_inheritance(self):
        """Test multiple inheritance from OSFException and FileNotFoundError."""
        exc = OSFNotFoundError("not found")
        assert isinstance(exc, OSFException)
        assert isinstance(exc, FileNotFoundError)

    def test_message(self):
        """Test error message."""
        exc = OSFNotFoundError("File not found")
        assert exc.message == "File not found"

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFNotFoundError("not found", status_code=404)
        assert exc.status_code == 404

    def test_not_retryable(self):
        """Test that not found errors are not retryable."""
        exc = OSFNotFoundError("not found")
        assert exc.retryable is False


class TestOSFPermissionError:
    """Tests for OSFPermissionError."""

    def test_inheritance(self):
        """Test multiple inheritance."""
        exc = OSFPermissionError()
        assert isinstance(exc, OSFException)
        assert isinstance(exc, PermissionError)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFPermissionError()
        assert "Permission denied" in exc.message

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFPermissionError(status_code=403)
        assert exc.status_code == 403

    def test_not_retryable(self):
        """Test that permission errors are not retryable."""
        exc = OSFPermissionError()
        assert exc.retryable is False


class TestOSFConnectionError:
    """Tests for OSFConnectionError."""

    def test_inheritance(self):
        """Test multiple inheritance."""
        exc = OSFConnectionError()
        assert isinstance(exc, OSFException)
        assert isinstance(exc, ConnectionError)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFConnectionError()
        assert "Failed to connect" in exc.message

    def test_retryable(self):
        """Test that connection errors are retryable."""
        exc = OSFConnectionError()
        assert exc.retryable is True


class TestOSFRateLimitError:
    """Tests for OSFRateLimitError."""

    def test_inheritance(self):
        """Test multiple inheritance."""
        exc = OSFRateLimitError()
        assert isinstance(exc, OSFException)
        assert isinstance(exc, ConnectionError)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFRateLimitError()
        assert "rate limit" in exc.message.lower()

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFRateLimitError(status_code=429)
        assert exc.status_code == 429

    def test_retry_after(self):
        """Test retry_after attribute."""
        exc = OSFRateLimitError(retry_after=60)
        assert exc.retry_after == 60

    def test_retryable(self):
        """Test that rate limit errors are retryable."""
        exc = OSFRateLimitError()
        assert exc.retryable is True


class TestOSFAPIError:
    """Tests for OSFAPIError."""

    def test_inheritance(self):
        """Test inheritance from OSFException."""
        exc = OSFAPIError("API error")
        assert isinstance(exc, OSFException)

    def test_message(self):
        """Test error message."""
        exc = OSFAPIError("Bad request")
        assert exc.message == "Bad request"

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFAPIError("error", status_code=400)
        assert exc.status_code == 400

    def test_response(self):
        """Test response attribute."""
        mock_response = {"error": "bad request"}
        exc = OSFAPIError("error", response=mock_response)
        assert exc.response == mock_response

    def test_client_error_not_retryable(self):
        """Test that 4xx errors are not retryable."""
        exc = OSFAPIError("error", status_code=400)
        assert exc.retryable is False

    def test_server_error_retryable(self):
        """Test that 5xx errors are retryable."""
        exc = OSFAPIError("error", status_code=500)
        assert exc.retryable is True

        exc = OSFAPIError("error", status_code=502)
        assert exc.retryable is True

        exc = OSFAPIError("error", status_code=503)
        assert exc.retryable is True


class TestOSFIntegrityError:
    """Tests for OSFIntegrityError."""

    def test_inheritance(self):
        """Test inheritance from OSFException."""
        exc = OSFIntegrityError("checksum mismatch")
        assert isinstance(exc, OSFException)

    def test_message(self):
        """Test error message."""
        exc = OSFIntegrityError("Checksum mismatch")
        assert exc.message == "Checksum mismatch"

    def test_checksums(self):
        """Test checksum attributes."""
        exc = OSFIntegrityError(
            "mismatch",
            expected_checksum="abc123",
            actual_checksum="def456",
        )
        assert exc.expected_checksum == "abc123"
        assert exc.actual_checksum == "def456"

    def test_retryable(self):
        """Test that integrity errors are retryable."""
        exc = OSFIntegrityError("mismatch")
        assert exc.retryable is True


class TestOSFQuotaExceededError:
    """Tests for OSFQuotaExceededError."""

    def test_inheritance(self):
        """Test inheritance from OSFException."""
        exc = OSFQuotaExceededError()
        assert isinstance(exc, OSFException)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFQuotaExceededError()
        assert "quota exceeded" in exc.message.lower()

    def test_custom_message(self):
        """Test custom error message."""
        exc = OSFQuotaExceededError("Custom quota error")
        assert exc.message == "Custom quota error"

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFQuotaExceededError(status_code=413)
        assert exc.status_code == 413

    def test_bytes_uploaded(self):
        """Test bytes_uploaded attribute."""
        exc = OSFQuotaExceededError(bytes_uploaded=1024000, total_size=2048000)
        assert exc.bytes_uploaded == 1024000
        assert exc.total_size == 2048000

    def test_not_retryable(self):
        """Test that quota exceeded errors are not retryable."""
        exc = OSFQuotaExceededError()
        assert exc.retryable is False


class TestOSFFileLockedError:
    """Tests for OSFFileLockedError."""

    def test_inheritance(self):
        """Test inheritance from OSFPermissionError."""
        exc = OSFFileLockedError()
        assert isinstance(exc, OSFPermissionError)
        assert isinstance(exc, OSFException)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFFileLockedError()
        assert "locked" in exc.message.lower()

    def test_custom_message(self):
        """Test custom error message."""
        exc = OSFFileLockedError("Custom lock error")
        assert exc.message == "Custom lock error"

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFFileLockedError(status_code=423)
        assert exc.status_code == 423

    def test_bytes_uploaded(self):
        """Test bytes_uploaded attribute."""
        exc = OSFFileLockedError(bytes_uploaded=512000, total_size=1024000)
        assert exc.bytes_uploaded == 512000
        assert exc.total_size == 1024000

    def test_not_retryable(self):
        """Test that file locked errors are not retryable."""
        exc = OSFFileLockedError()
        assert exc.retryable is False


class TestOSFVersionConflictError:
    """Tests for OSFVersionConflictError."""

    def test_inheritance(self):
        """Test inheritance from OSFException."""
        exc = OSFVersionConflictError()
        assert isinstance(exc, OSFException)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFVersionConflictError()
        assert "conflict" in exc.message.lower()

    def test_custom_message(self):
        """Test custom error message."""
        exc = OSFVersionConflictError("Custom conflict error")
        assert exc.message == "Custom conflict error"

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFVersionConflictError(status_code=409)
        assert exc.status_code == 409

    def test_bytes_uploaded(self):
        """Test bytes_uploaded attribute."""
        exc = OSFVersionConflictError(bytes_uploaded=256000, total_size=512000)
        assert exc.bytes_uploaded == 256000
        assert exc.total_size == 512000

    def test_not_retryable(self):
        """Test that version conflict errors are not retryable."""
        exc = OSFVersionConflictError()
        assert exc.retryable is False


class TestOSFConflictError:
    """Tests for OSFConflictError."""

    def test_inheritance(self):
        """Test multiple inheritance from OSFException and FileExistsError."""
        exc = OSFConflictError()
        assert isinstance(exc, OSFException)
        assert isinstance(exc, FileExistsError)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFConflictError()
        assert "exists" in exc.message.lower()

    def test_custom_message(self):
        """Test custom error message."""
        exc = OSFConflictError("Cannot copy: /data.csv already exists")
        assert exc.message == "Cannot copy: /data.csv already exists"

    def test_status_code(self):
        """Test status_code attribute."""
        exc = OSFConflictError(status_code=409)
        assert exc.status_code == 409

    def test_response(self):
        """Test response attribute."""
        mock_response = {"error": "file exists"}
        exc = OSFConflictError(response=mock_response)
        assert exc.response == mock_response

    def test_not_retryable(self):
        """Test that conflict errors are not retryable."""
        exc = OSFConflictError()
        assert exc.retryable is False


class TestOSFOperationNotSupportedError:
    """Tests for OSFOperationNotSupportedError."""

    def test_inheritance(self):
        """Test inheritance from OSFException."""
        exc = OSFOperationNotSupportedError()
        assert isinstance(exc, OSFException)

    def test_default_message(self):
        """Test default error message."""
        exc = OSFOperationNotSupportedError()
        assert "not supported" in exc.message.lower()

    def test_custom_message(self):
        """Test custom error message."""
        exc = OSFOperationNotSupportedError("Cross-project copy not supported")
        assert exc.message == "Cross-project copy not supported"

    def test_operation_attribute(self):
        """Test operation attribute."""
        exc = OSFOperationNotSupportedError(
            "Cross-project copy not supported", operation="copy"
        )
        assert exc.operation == "copy"

    def test_not_retryable(self):
        """Test that operation not supported errors are not retryable."""
        exc = OSFOperationNotSupportedError()
        assert exc.retryable is False
