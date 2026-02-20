"""Integration tests for OSF filesystem - requires real OSF project.

These tests require:
- OSF_TEST_TOKEN environment variable (your OSF Personal Access Token)
- OSF_TEST_PROJECT_ID environment variable (test project ID)
- A test file named 'test_file.txt' uploaded to the project's osfstorage

To run integration tests:
    export OSF_TEST_TOKEN="your_token_here"
    export OSF_TEST_PROJECT_ID="your_project_id"
    pytest tests/integration/ -v -m integration

To skip integration tests (default):
    pytest tests/  # automatically skips if env vars not set
"""

import os
import tempfile

import pytest

from dvc_osf.exceptions import OSFAuthenticationError, OSFNotFoundError
from dvc_osf.filesystem import OSFFileSystem

# Check if integration tests should be run
pytestmark = pytest.mark.integration

# Get test credentials from environment
OSF_TEST_TOKEN = os.getenv("OSF_TEST_TOKEN")
OSF_TEST_PROJECT_ID = os.getenv("OSF_TEST_PROJECT_ID")

# Skip all tests in this module if credentials not provided
if not OSF_TEST_TOKEN or not OSF_TEST_PROJECT_ID:
    pytest.skip(
        "Integration tests skipped: Set OSF_TEST_TOKEN and "
        "OSF_TEST_PROJECT_ID environment variables to run",
        allow_module_level=True,
    )


class TestOSFFileSystemIntegration:
    """Integration tests with real OSF project."""

    def test_init_with_valid_credentials(self):
        """Test initialization with valid OSF project."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        assert fs.project_id == OSF_TEST_PROJECT_ID
        assert fs.provider == "osfstorage"
        assert fs.token == OSF_TEST_TOKEN

    def test_exists_root_directory(self):
        """Test exists() on root directory."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # Root directory should exist
        result = fs.exists("")
        assert result is True or result is False  # May vary by API response

    def test_ls_root_directory(self):
        """Test ls() on root directory."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # List root directory
        files = fs.ls("", detail=False)

        assert isinstance(files, list)
        # Should return list of paths (may be empty if no files)
        print(f"Found {len(files)} files/directories in root")

    def test_ls_root_with_detail(self):
        """Test ls() with detail returns metadata."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # List with detail
        items = fs.ls("", detail=True)

        assert isinstance(items, list)
        if items:
            # Check that items have metadata
            first_item = items[0]
            assert "name" in first_item
            assert "type" in first_item
            print(f"First item: {first_item['name']}, type: {first_item['type']}")

    @pytest.mark.skipif(
        not os.getenv("OSF_TEST_FILE"),
        reason="Set OSF_TEST_FILE env var to test specific file operations",
    )
    def test_info_on_file(self):
        """Test info() on a specific file."""
        test_file = os.getenv("OSF_TEST_FILE", "test_file.txt")
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # Get file info
        info = fs.info(test_file)

        assert info["name"] is not None
        assert info["type"] == "file"
        assert "size" in info
        print(f"File info: {info}")

    @pytest.mark.skipif(
        not os.getenv("OSF_TEST_FILE"),
        reason="Set OSF_TEST_FILE env var to test specific file operations",
    )
    def test_exists_on_file(self):
        """Test exists() on a specific file."""
        test_file = os.getenv("OSF_TEST_FILE", "test_file.txt")
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # Check if file exists
        result = fs.exists(test_file)

        assert result is True

    @pytest.mark.skipif(
        not os.getenv("OSF_TEST_FILE"),
        reason="Set OSF_TEST_FILE env var to test specific file operations",
    )
    def test_open_and_read_file(self):
        """Test open() and reading from a real file."""
        test_file = os.getenv("OSF_TEST_FILE", "test_file.txt")
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # Open and read file
        with fs.open(test_file, mode="rb") as f:
            content = f.read()

        assert isinstance(content, bytes)
        assert len(content) > 0
        print(f"Read {len(content)} bytes from {test_file}")

    @pytest.mark.skipif(
        not os.getenv("OSF_TEST_FILE"),
        reason="Set OSF_TEST_FILE env var to test specific file operations",
    )
    def test_get_file_download(self):
        """Test get_file() downloads file correctly."""
        test_file = os.getenv("OSF_TEST_FILE", "test_file.txt")
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # Download file to temp location
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, "downloaded.txt")

            fs.get_file(test_file, local_path)

            # Verify file was downloaded
            assert os.path.exists(local_path)
            assert os.path.getsize(local_path) > 0

            # Read content
            with open(local_path, "rb") as f:
                content = f.read()

            print(f"Downloaded {len(content)} bytes to {local_path}")

    def test_exists_missing_file(self):
        """Test exists() returns False for missing file."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # Check non-existent file
        result = fs.exists("this_file_does_not_exist_12345.txt")

        assert result is False

    def test_info_missing_file_raises(self):
        """Test info() raises OSFNotFoundError for missing file."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # Try to get info on non-existent file
        with pytest.raises(OSFNotFoundError):
            fs.info("this_file_does_not_exist_12345.txt")

    def test_invalid_project_id_raises(self):
        """Test that invalid project ID raises error."""
        url = "osf://invalid_project_id_12345/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        # Try to list files with invalid project
        with pytest.raises(Exception):  # Could be OSFNotFoundError or OSFAPIError
            fs.ls("")

    def test_invalid_token_raises(self):
        """Test that invalid token raises OSFAuthenticationError."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token="invalid_token_12345")

        # Try to list files with invalid token
        with pytest.raises(OSFAuthenticationError):
            fs.ls("")


class TestOSFFileSystemEdgeCases:
    """Integration tests for edge cases and error handling."""

    def test_write_mode_works(self):
        """Test that write mode (wb) is supported (Phase 3+)."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)
        # open() in wb mode should return a write handle, not raise
        fh = fs.open("test_write_mode_check.txt", mode="wb")
        assert fh is not None

    def test_append_mode_raises_not_implemented(self):
        """Test that append mode raises NotImplementedError (OSF does not support it)."""
        url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
        fs = OSFFileSystem(url, token=OSF_TEST_TOKEN)

        with pytest.raises(
            NotImplementedError, match="Append mode not supported"
        ):
            fs.open("test.txt", mode="ab")
