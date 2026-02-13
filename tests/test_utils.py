"""Tests for utility functions."""

import pytest

from dvc_osf.utils import (
    build_osf_url,
    format_file_size,
    normalize_path,
    parse_osf_url,
)


def test_parse_osf_url():
    """Test parsing OSF URLs."""
    result = parse_osf_url("osf://proj123/path/to/file.txt")
    assert result["project_id"] == "proj123"
    assert result["path"] == "path/to/file.txt"


def test_parse_osf_url_no_path():
    """Test parsing OSF URL without path."""
    result = parse_osf_url("osf://proj123")
    assert result["project_id"] == "proj123"
    assert result["path"] == ""


def test_parse_osf_url_invalid_scheme():
    """Test parsing URL with invalid scheme."""
    with pytest.raises(ValueError):
        parse_osf_url("http://example.com/file.txt")


def test_normalize_path():
    """Test path normalization."""
    assert normalize_path("/path/to/file") == "path/to/file"
    assert normalize_path("path/to/file/") == "path/to/file"
    assert normalize_path("//path//to//file//") == "path/to/file"


def test_build_osf_url():
    """Test building OSF URLs."""
    assert build_osf_url("proj123", "path/to/file") == "osf://proj123/path/to/file"
    assert build_osf_url("proj123", "") == "osf://proj123"
    assert build_osf_url("proj123") == "osf://proj123"


def test_format_file_size():
    """Test file size formatting."""
    assert format_file_size(0) == "0.0 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1024 * 1024) == "1.0 MB"
    assert format_file_size(1536) == "1.5 KB"


@pytest.mark.skip(reason="Not yet implemented")
def test_extract_metadata():
    """Test extracting metadata from OSF responses."""
    pass
