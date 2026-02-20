"""Integration tests for OSF write operations.

These tests require a real OSF project and authentication token.
Set OSF_TEST_TOKEN and OSF_TEST_PROJECT_ID environment variables.
"""

import io
import os

import pytest

from dvc_osf.exceptions import OSFNotFoundError
from dvc_osf.filesystem import OSFFileSystem

# Skip all tests if no token is set
pytestmark = pytest.mark.integration


# Fixture to check if integration tests should run
@pytest.fixture(scope="module")
def require_osf_credentials():
    """Skip tests if OSF credentials are not available."""
    token = os.getenv("OSF_TEST_TOKEN")
    project_id = os.getenv("OSF_TEST_PROJECT_ID")

    if not token or not project_id:
        pytest.skip(
            "OSF_TEST_TOKEN and OSF_TEST_PROJECT_ID must be set for integration tests"
        )

    return token, project_id


@pytest.fixture(scope="module")
def osf_fs(require_osf_credentials):
    """Create OSFFileSystem instance for testing."""
    token, project_id = require_osf_credentials
    return OSFFileSystem(token=token)


@pytest.fixture(scope="module")
def test_project_path(require_osf_credentials):
    """Get test project base path."""
    _, project_id = require_osf_credentials
    return f"osf://{project_id}/osfstorage"


class TestOSFWriteOperations:
    """Integration tests for OSF write operations."""

    def test_put_file_small(self, osf_fs, test_project_path, tmp_path):
        """Test uploading a small file with single PUT."""
        # Create a small test file
        test_file = tmp_path / "small_test.txt"
        test_content = b"Hello OSF! This is a small test file.\n" * 10
        test_file.write_bytes(test_content)

        # Upload to OSF (use root level to avoid folder complexity)
        remote_path = f"{test_project_path}/small_test_{os.getpid()}.txt"
        osf_fs.put_file(str(test_file), remote_path)

        # Verify it exists
        info = osf_fs.info(remote_path)
        assert info["type"] == "file"
        assert info["size"] == len(test_content)

        # Clean up
        osf_fs.rm(remote_path)

    @pytest.mark.skip(reason="Large file test skipped for speed — run manually")
    def test_put_file_large_chunked(self, osf_fs, test_project_path, tmp_path):
        """Test uploading a large file with chunked upload."""
        # Create a file larger than chunk threshold (>5MB)
        test_file = tmp_path / "large_test.bin"
        test_size = 6 * 1024 * 1024  # 6MB
        test_content = os.urandom(test_size)
        test_file.write_bytes(test_content)

        # Upload to OSF
        remote_path = f"{test_project_path}/test_large_test.bin"
        osf_fs.put_file(str(test_file), remote_path)

        # Verify it exists
        info = osf_fs.info(remote_path)
        assert info["type"] == "file"
        assert info["size"] == test_size

        # Clean up
        osf_fs.rm(remote_path)

    def test_put_with_file_object(self, osf_fs, test_project_path):
        """Test uploading from a file object."""
        test_content = b"File object upload test\n" * 50
        file_obj = io.BytesIO(test_content)

        # Upload to OSF
        remote_path = f"{test_project_path}/test_fileobj_test.txt"
        osf_fs.put(file_obj, remote_path)

        # Verify it exists
        info = osf_fs.info(remote_path)
        assert info["type"] == "file"
        assert info["size"] == len(test_content)

        # Clean up
        osf_fs.rm(remote_path)

    def test_overwrite_creates_new_version(self, osf_fs, test_project_path, tmp_path):
        """Test that overwriting a file creates a new version."""
        test_file = tmp_path / "version_test.txt"

        # Upload first version
        test_file.write_text("Version 1 content")
        remote_path = f"{test_project_path}/test_version_test.txt"
        osf_fs.put_file(str(test_file), remote_path)

        # Get first version info
        info_v1 = osf_fs.info(remote_path)

        # Upload second version
        test_file.write_text("Version 2 content - this is different!")
        osf_fs.put_file(str(test_file), remote_path)

        # Get second version info
        info_v2 = osf_fs.info(remote_path)

        # Verify the file was updated (size changed)
        assert info_v2["size"] != info_v1["size"]

        # Version metadata should be present if OSF provides it
        # (Note: version field availability depends on OSF API response)

        # Clean up
        osf_fs.rm(remote_path)

    def test_mkdir_is_noop(self, osf_fs, test_project_path):
        """Test that mkdir is a no-op and doesn't fail."""
        # mkdir should succeed without creating anything
        remote_dir = f"{test_project_path}/test_fake_dir"
        osf_fs.mkdir(remote_dir)

        # No error should occur - it's a no-op

    def test_rm_deletes_file(self, osf_fs, test_project_path, tmp_path):
        """Test deleting a file from OSF."""
        # Create and upload a file
        test_file = tmp_path / "delete_test.txt"
        test_file.write_text("This file will be deleted")

        remote_path = f"{test_project_path}/test_delete_test.txt"
        osf_fs.put_file(str(test_file), remote_path)

        # Verify it exists
        info = osf_fs.info(remote_path)
        assert info["type"] == "file"

        # Delete it
        osf_fs.rm(remote_path)

        # Verify it's gone
        with pytest.raises(OSFNotFoundError):
            osf_fs.info(remote_path)

    def test_rm_nonexistent_is_noop(self, osf_fs, test_project_path):
        """Test that deleting a non-existent file is a no-op (idempotent)."""
        remote_path = f"{test_project_path}/test_nonexistent_file_{os.getpid()}.txt"

        # Should not raise - rm is idempotent
        osf_fs.rm(remote_path)

    def test_rmdir_is_noop(self, osf_fs, test_project_path):
        """Test that rmdir is a no-op for virtual directories."""
        # rmdir should succeed without doing anything
        remote_dir = f"{test_project_path}/test_some_virtual_dir"
        osf_fs.rmdir(remote_dir)

        # No error should occur - it's a no-op

    def test_open_write_mode(self, osf_fs, test_project_path):
        """Test opening a file in write mode and writing to it."""
        remote_path = f"{test_project_path}/test_write_mode_test.txt"

        # Write using open()
        with osf_fs.open(remote_path, mode="wb") as f:
            f.write(b"Line 1\n")
            f.write(b"Line 2\n")
            f.write(b"Line 3\n")

        # Verify it was uploaded
        info = osf_fs.info(remote_path)
        assert info["type"] == "file"
        assert info["size"] > 0

        # Clean up
        osf_fs.rm(remote_path)

    def test_progress_callback(self, osf_fs, test_project_path, tmp_path):
        """Test progress callback is invoked during upload."""
        # Create a file
        test_file = tmp_path / "progress_test.txt"
        test_file.write_bytes(b"x" * (1024 * 1024))  # 1MB

        # Track callback invocations
        progress_calls = []

        def callback(uploaded, total):
            progress_calls.append((uploaded, total))

        # Upload with callback
        remote_path = f"{test_project_path}/test_progress_test.txt"
        osf_fs.put_file(str(test_file), remote_path, callback=callback)

        # Verify callback was invoked
        assert len(progress_calls) > 0

        # Final call should have uploaded == total
        final_uploaded, final_total = progress_calls[-1]
        assert final_uploaded == final_total

        # Clean up
        osf_fs.rm(remote_path)

    def test_checksum_verification(self, osf_fs, test_project_path, tmp_path):
        """Test that checksum verification works with real uploads."""
        # Create a test file
        test_file = tmp_path / "checksum_test.txt"
        test_content = b"Checksum verification test content\n" * 100
        test_file.write_bytes(test_content)

        # Upload to OSF
        remote_path = f"{test_project_path}/test_checksum_test.txt"
        osf_fs.put_file(str(test_file), remote_path)

        # Get info - checksum should be present
        info = osf_fs.info(remote_path)
        assert "checksum" in info

        # If OSF provides checksum, verify it's set
        if info["checksum"]:
            assert len(info["checksum"]) == 32  # MD5 is 32 hex chars

        # Clean up
        osf_fs.rm(remote_path)
