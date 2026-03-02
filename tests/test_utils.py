"""Tests for OSF utility functions."""

import io

import pytest

from dvc_osf.utils import (
    ProgressTracker,
    chunk_file,
    compute_upload_checksum,
    determine_upload_strategy,
    format_bytes,
    get_directory,
    get_file_size,
    get_filename,
    get_parent,
    join_path,
    normalize_path,
    parse_osf_url,
    path_to_api_url,
    serialize_path,
    validate_chunk_size,
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
        """Test converting simple path to API URL.

        OSF requires a trailing slash on directory paths to return a listing;
        path_to_api_url always appends one.
        """
        url = path_to_api_url("abc123", "osfstorage", "data/file.csv")
        assert (
            url == "https://api.osf.io/v2/nodes/abc123/files/osfstorage/data/file.csv/"
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
        """Test with nested directory path (trailing slash always added)."""
        url = path_to_api_url("abc123", "osfstorage", "data/subdir/file.csv")
        assert url == (
            "https://api.osf.io/v2/nodes/abc123/files/osfstorage/data/subdir/file.csv/"
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


class TestComputeUploadChecksum:
    """Tests for compute_upload_checksum function."""

    def test_compute_checksum_simple(self):
        """Test computing checksum for simple content."""
        data = b"Hello, World!"
        file_obj = io.BytesIO(data)
        checksum = compute_upload_checksum(file_obj)
        assert checksum == "65a8e27d8879283831b664bd8b7f0ad4"

    def test_compute_checksum_empty(self):
        """Test computing checksum for empty content."""
        file_obj = io.BytesIO(b"")
        checksum = compute_upload_checksum(file_obj)
        assert checksum == "d41d8cd98f00b204e9800998ecf8427e"

    def test_compute_checksum_large(self):
        """Test computing checksum for large content."""
        data = b"x" * (10 * 1024 * 1024)  # 10MB
        file_obj = io.BytesIO(data)
        checksum = compute_upload_checksum(file_obj)
        assert len(checksum) == 32  # MD5 is 32 hex chars


class TestChunkFile:
    """Tests for chunk_file function."""

    def test_chunk_single(self):
        """Test chunking file smaller than chunk size."""
        data = b"Hello, World!"
        file_obj = io.BytesIO(data)
        chunks = list(chunk_file(file_obj, chunk_size=1024))

        assert len(chunks) == 1
        chunk_data, start, end = chunks[0]
        assert chunk_data == data
        assert start == 0
        assert end == len(data) - 1

    def test_chunk_multiple(self):
        """Test chunking file larger than chunk size."""
        data = b"x" * 1000
        file_obj = io.BytesIO(data)
        chunks = list(chunk_file(file_obj, chunk_size=300))

        assert len(chunks) == 4  # 300 + 300 + 300 + 100

        # Check first chunk
        chunk_data, start, end = chunks[0]
        assert len(chunk_data) == 300
        assert start == 0
        assert end == 299

        # Check last chunk
        chunk_data, start, end = chunks[-1]
        assert len(chunk_data) == 100
        assert start == 900
        assert end == 999

    def test_chunk_exact_multiple(self):
        """Test chunking file that's exact multiple of chunk size."""
        data = b"x" * 600
        file_obj = io.BytesIO(data)
        chunks = list(chunk_file(file_obj, chunk_size=300))

        assert len(chunks) == 2

        for i, (chunk_data, start, end) in enumerate(chunks):
            assert len(chunk_data) == 300
            assert start == i * 300
            assert end == (i + 1) * 300 - 1


class TestGetFileSize:
    """Tests for get_file_size function."""

    def test_get_size_from_seekable(self):
        """Test getting size from seekable file object."""
        data = b"x" * 1024
        file_obj = io.BytesIO(data)
        size = get_file_size(file_obj)
        assert size == 1024
        # Check position is restored
        assert file_obj.tell() == 0

    def test_get_size_with_seek(self):
        """Test getting size from file with current position."""
        data = b"x" * 1024
        file_obj = io.BytesIO(data)
        file_obj.read(100)  # Advance position
        size = get_file_size(file_obj)
        assert size == 1024
        # Position should be restored
        assert file_obj.tell() == 100


class TestDetermineUploadStrategy:
    """Tests for determine_upload_strategy function."""

    def test_strategy_small_file(self):
        """Test strategy for small files."""
        strategy = determine_upload_strategy(
            1024 * 1024, chunk_threshold=5 * 1024 * 1024
        )
        assert strategy == "single"

    def test_strategy_large_file(self):
        """Test strategy for large files."""
        strategy = determine_upload_strategy(
            10 * 1024 * 1024, chunk_threshold=5 * 1024 * 1024
        )
        assert strategy == "chunked"

    def test_strategy_exact_threshold(self):
        """Test strategy at exact threshold."""
        threshold = 5 * 1024 * 1024
        strategy = determine_upload_strategy(threshold, chunk_threshold=threshold)
        assert strategy == "chunked"  # Equal to threshold uses chunked


class TestValidateChunkSize:
    """Tests for validate_chunk_size function."""

    def test_validate_valid_size(self):
        """Test validation with valid chunk size."""
        result = validate_chunk_size(5 * 1024 * 1024)
        assert result == 5 * 1024 * 1024

    def test_validate_too_small(self):
        """Test validation bounds too small chunk size to minimum."""
        result = validate_chunk_size(512 * 1024)  # 512KB, less than 1MB min
        assert result == 1 * 1024 * 1024  # Should be bounded to 1MB

    def test_validate_too_large(self):
        """Test validation bounds too large chunk size to maximum."""
        result = validate_chunk_size(200 * 1024 * 1024)  # 200MB, more than 100MB max
        assert result == 100 * 1024 * 1024  # Should be bounded to 100MB

    def test_validate_at_boundaries(self):
        """Test validation at min/max boundaries."""
        result_min = validate_chunk_size(1 * 1024 * 1024)  # Min: 1MB
        assert result_min == 1 * 1024 * 1024

        result_max = validate_chunk_size(100 * 1024 * 1024)  # Max: 100MB
        assert result_max == 100 * 1024 * 1024


class TestFormatBytes:
    """Tests for format_bytes function."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_bytes(0) == "0.0 B"
        assert format_bytes(1023) == "1023.0 B"

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(2048) == "2.0 KB"

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(5 * 1024 * 1024) == "5.0 MB"

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
        assert format_bytes(int(2.5 * 1024 * 1024 * 1024)) == "2.5 GB"


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    def test_init(self):
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker(1024, None)
        assert tracker.total_size == 1024
        assert tracker.bytes_uploaded == 0
        assert tracker.callback is None

    def test_update_without_callback(self):
        """Test update without callback."""
        tracker = ProgressTracker(1024, None)
        tracker.update(512)
        assert tracker.bytes_uploaded == 512

    def test_update_with_callback(self):
        """Test update with callback."""
        calls = []

        def callback(uploaded, total):
            calls.append((uploaded, total))

        tracker = ProgressTracker(1024, callback)
        tracker.update(512)

        assert len(calls) == 1
        assert calls[0] == (512, 1024)

    def test_complete(self):
        """Test complete method."""
        calls = []

        def callback(uploaded, total):
            calls.append((uploaded, total))

        tracker = ProgressTracker(1024, callback)
        tracker.update(512)
        tracker.complete()

        assert len(calls) == 2
        assert calls[-1] == (1024, 1024)

    def test_callback_exception_handled(self):
        """Test that callback exceptions are handled gracefully."""

        def bad_callback(uploaded, total):
            raise ValueError("Callback error")

        tracker = ProgressTracker(1024, bad_callback)
        # Should not raise
        tracker.update(512)
        tracker.complete()
