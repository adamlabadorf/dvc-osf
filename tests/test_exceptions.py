"""Tests for custom exceptions."""

from dvc_osf.exceptions import (
    OSFAPIError,
    OSFAuthenticationError,
    OSFConnectionError,
    OSFException,
    OSFFileNotFoundError,
    OSFInvalidPathError,
    OSFPermissionError,
    OSFProjectNotFoundError,
)


def test_osf_exception():
    """Test base OSFException."""
    exc = OSFException("test error")
    assert str(exc) == "test error"


def test_osf_authentication_error():
    """Test OSFAuthenticationError."""
    exc = OSFAuthenticationError("auth failed")
    assert isinstance(exc, OSFException)


def test_osf_project_not_found_error():
    """Test OSFProjectNotFoundError."""
    exc = OSFProjectNotFoundError("project not found")
    assert isinstance(exc, OSFException)


def test_osf_file_not_found_error():
    """Test OSFFileNotFoundError."""
    exc = OSFFileNotFoundError("file not found")
    assert isinstance(exc, OSFException)


def test_osf_permission_error():
    """Test OSFPermissionError."""
    exc = OSFPermissionError("permission denied")
    assert isinstance(exc, OSFException)


def test_osf_connection_error():
    """Test OSFConnectionError."""
    exc = OSFConnectionError("connection failed")
    assert isinstance(exc, OSFException)


def test_osf_api_error():
    """Test OSFAPIError with status code."""
    exc = OSFAPIError("api error", status_code=404)
    assert isinstance(exc, OSFException)
    assert exc.status_code == 404


def test_osf_api_error_no_status():
    """Test OSFAPIError without status code."""
    exc = OSFAPIError("api error")
    assert exc.status_code is None


def test_osf_invalid_path_error():
    """Test OSFInvalidPathError."""
    exc = OSFInvalidPathError("invalid path")
    assert isinstance(exc, OSFException)
