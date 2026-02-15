"""Tests for OSF utility functions."""

import pytest

from dvc_osf.utils import (
    get_directory,
    get_filename,
    get_parent,
    join_path,
    normalize_path,
    parse_osf_url,
    path_to_api_url,
    serialize_path,
    validate_osf_url,
)


class TestParseOSFUrl:
    """Tests for parse_osf_url function."""

    def test_parse_full_url(self):
        """Test parsing complete OSF URL with project, provider, and path."""
        project_id, provider, path = parse_osf_url(
            "osf://abc123/osfstorage/data/file.csv"
        )
        assert project_id == "abc123"
        assert provider == "osfstorage"
        assert path == "data/file.csv"

    def test_parse_url_without_path(self):
        """Test parsing URL with just project and provider."""
        project_id, provider, path = parse_osf_url("osf://abc123/osfstorage")
        assert project_id == "abc123"
        assert provider == "osfstorage"
        assert path == ""

    def test_parse_url_with_non_standard_provider(self):
        """Test parsing URL with non-standard provider name."""
        # OSF URLs are osf://project/provider/path, so 'data' is treated as provider
        project_id, provider, path = parse_osf_url("osf://abc123/data/file.csv")
        assert project_id == "abc123"
        assert provider == "data"  # 'data' is treated as the provider name
        assert path == "file.csv"

    def test_parse_url_project_only(self):
        """Test parsing URL with only project ID."""
        project_id, provider, path = parse_osf_url("osf://abc123")
        assert project_id == "abc123"
        assert provider == "osfstorage"
        assert path == ""

    def test_parse_url_with_known_provider(self):
        """Test parsing URL with known provider names."""
        project_id, provider, path = parse_osf_url("osf://abc123/github")
        assert project_id == "abc123"
        assert provider == "github"
        assert path == ""

    def test_parse_url_invalid_scheme(self):
        """Test that invalid scheme raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OSF URL scheme"):
            parse_osf_url("http://abc123/osfstorage")

    def test_parse_url_no_project_id(self):
        """Test that missing project ID raises ValueError."""
        with pytest.raises(ValueError, match="must contain a project ID"):
            parse_osf_url("osf:///osfstorage/file.csv")

    def test_parse_url_short_project_id(self):
        """Test that short project ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid project ID"):
            parse_osf_url("osf://abc/osfstorage")  # Only 3 chars

    def test_parse_url_with_special_chars_in_path(self):
        """Test parsing URL with special characters in path."""
        project_id, provider, path = parse_osf_url(
            "osf://abc123/osfstorage/my%20file.txt"
        )
        assert project_id == "abc123"
        assert provider == "osfstorage"
        assert path == "my%20file.txt"


class TestNormalizePath:
    """Tests for normalize_path function."""

    def test_normalize_simple_path(self):
        """Test normalizing a simple path."""
        assert normalize_path("data/file.csv") == "data/file.csv"

    def test_normalize_leading_slash(self):
        """Test removing leading slash."""
        assert normalize_path("/data/file.csv") == "data/file.csv"

    def test_normalize_trailing_slash(self):
        """Test removing trailing slash."""
        assert normalize_path("data/file.csv/") == "data/file.csv"

    def test_normalize_multiple_slashes(self):
        """Test collapsing multiple slashes."""
        assert normalize_path("data//subdir///file.csv") == "data/subdir/file.csv"

    def test_normalize_empty_path(self):
        """Test normalizing empty path."""
        assert normalize_path("") == ""

    def test_normalize_just_slashes(self):
        """Test normalizing path with only slashes."""
        assert normalize_path("///") == ""


class TestJoinPath:
    """Tests for join_path function."""

    def test_join_simple_paths(self):
        """Test joining simple path components."""
        assert join_path("data", "file.csv") == "data/file.csv"

    def test_join_multiple_paths(self):
        """Test joining multiple path components."""
        assert join_path("data", "subdir", "file.csv") == "data/subdir/file.csv"

    def test_join_with_slashes(self):
        """Test joining paths that already have slashes."""
        assert join_path("data/", "/subdir", "file.csv") == "data/subdir/file.csv"

    def test_join_empty_components(self):
        """Test joining with empty components."""
        assert join_path("data", "", "file.csv") == "data/file.csv"

    def test_join_all_empty(self):
        """Test joining all empty components."""
        assert join_path("", "", "") == ""

    def test_join_no_components(self):
        """Test joining with no components."""
        assert join_path() == ""


class TestPathToApiUrl:
    """Tests for path_to_api_url function."""

    def test_path_to_api_url_simple(self):
        """Test converting simple path to API URL."""
        url = path_to_api_url("abc123", "osfstorage", "data/file.csv")
        assert (
            url == "https://api.osf.io/v2/nodes/abc123/files/osfstorage/data/file.csv"
        )

    def test_path_to_api_url_empty_path(self):
        """Test converting empty path to API URL."""
        url = path_to_api_url("abc123", "osfstorage", "")
        assert url == "https://api.osf.io/v2/nodes/abc123/files/osfstorage/"

    def test_path_to_api_url_with_spaces(self):
        """Test URL encoding of special characters."""
        url = path_to_api_url("abc123", "osfstorage", "my file.txt")
        assert "my%20file.txt" in url

    def test_path_to_api_url_custom_base(self):
        """Test with custom base URL."""
        url = path_to_api_url(
            "abc123", "osfstorage", "file.csv", base_url="https://test.osf.io/v2"
        )
        assert url.startswith("https://test.osf.io/v2")

    def test_path_to_api_url_nested_path(self):
        """Test with nested directory path."""
        url = path_to_api_url("abc123", "osfstorage", "data/subdir/file.csv")
        assert url == (
            "https://api.osf.io/v2/nodes/abc123/files/osfstorage/data/subdir/file.csv"
        )


class TestSerializePath:
    """Tests for serialize_path function."""

    def test_serialize_simple_path(self):
        """Test serializing simple path."""
        url = serialize_path("abc123", "osfstorage", "data/file.csv")
        assert url == "osf://abc123/osfstorage/data/file.csv"

    def test_serialize_empty_path(self):
        """Test serializing empty path."""
        url = serialize_path("abc123", "osfstorage", "")
        assert url == "osf://abc123/osfstorage"

    def test_serialize_with_leading_slash(self):
        """Test serializing path with leading slash (should be normalized)."""
        url = serialize_path("abc123", "osfstorage", "/data/file.csv")
        assert url == "osf://abc123/osfstorage/data/file.csv"

    def test_serialize_different_provider(self):
        """Test serializing with different provider."""
        url = serialize_path("abc123", "github", "file.csv")
        assert url == "osf://abc123/github/file.csv"


class TestGetFilename:
    """Tests for get_filename function."""

    def test_get_filename_simple(self):
        """Test extracting filename from simple path."""
        assert get_filename("data/file.csv") == "file.csv"

    def test_get_filename_nested(self):
        """Test extracting filename from nested path."""
        assert get_filename("data/subdir/file.csv") == "file.csv"

    def test_get_filename_no_directory(self):
        """Test extracting filename when no directory."""
        assert get_filename("file.csv") == "file.csv"

    def test_get_filename_empty(self):
        """Test extracting filename from empty path."""
        assert get_filename("") == ""

    def test_get_filename_with_slashes(self):
        """Test extracting filename from path with slashes."""
        assert get_filename("/data/file.csv/") == "file.csv"


class TestGetDirectory:
    """Tests for get_directory function."""

    def test_get_directory_simple(self):
        """Test extracting directory from simple path."""
        assert get_directory("data/file.csv") == "data"

    def test_get_directory_nested(self):
        """Test extracting directory from nested path."""
        assert get_directory("data/subdir/file.csv") == "data/subdir"

    def test_get_directory_no_directory(self):
        """Test extracting directory when no directory."""
        assert get_directory("file.csv") == ""

    def test_get_directory_empty(self):
        """Test extracting directory from empty path."""
        assert get_directory("") == ""


class TestGetParent:
    """Tests for get_parent function."""

    def test_get_parent_simple(self):
        """Test getting parent of simple path."""
        assert get_parent("data/file.csv") == "data"

    def test_get_parent_nested(self):
        """Test getting parent of nested path."""
        assert get_parent("data/subdir/file.csv") == "data/subdir"

    def test_get_parent_directory(self):
        """Test getting parent of directory path."""
        assert get_parent("data/subdir") == "data"


class TestValidateOSFUrl:
    """Tests for validate_osf_url function."""

    def test_validate_valid_url(self):
        """Test that valid URL passes validation."""
        validate_osf_url("osf://abc123/osfstorage/file.csv")  # Should not raise

    def test_validate_invalid_scheme(self):
        """Test that invalid scheme raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OSF URL"):
            validate_osf_url("http://abc123/osfstorage")

    def test_validate_short_project_id(self):
        """Test that short project ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OSF URL"):
            validate_osf_url("osf://ab/osfstorage")

    def test_validate_no_project_id(self):
        """Test that missing project ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OSF URL"):
            validate_osf_url("osf:///osfstorage/file.csv")
