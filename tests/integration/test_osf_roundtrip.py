"""Integration tests for OSF upload/download roundtrip.

These tests verify that data uploaded to OSF can be downloaded
and matches the original content exactly.
"""

import hashlib
import os

import pytest

from dvc_osf.filesystem import OSFFileSystem

pytestmark = pytest.mark.integration


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


def compute_file_checksum(file_path):
    """Compute MD5 checksum of a file."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


class TestOSFRoundtrip:
    """Integration tests for upload/download roundtrip."""

    def test_roundtrip_small_text_file(self, osf_fs, test_project_path, tmp_path):
        """Test roundtrip with a small text file."""
        # Create original file
        original_file = tmp_path / "original_small.txt"
        original_content = "Hello OSF!\nThis is a test file.\n" * 50
        original_file.write_text(original_content)
        original_checksum = compute_file_checksum(original_file)

        # Upload to OSF
        remote_path = f"{test_project_path}/test_roundtrip_small.txt"
        osf_fs.put_file(str(original_file), remote_path)

        # Download from OSF
        downloaded_file = tmp_path / "downloaded_small.txt"
        osf_fs.get_file(remote_path, str(downloaded_file))

        # Verify content matches
        downloaded_checksum = compute_file_checksum(downloaded_file)
        assert original_checksum == downloaded_checksum

        # Verify content is identical
        assert downloaded_file.read_text() == original_content

        # Clean up
        osf_fs.rm(remote_path)

    def test_roundtrip_large_binary_file(self, osf_fs, test_project_path, tmp_path):
        """Test roundtrip with a large binary file (triggers chunking)."""
        # Create original file (6MB to trigger chunked upload)
        original_file = tmp_path / "original_large.bin"
        original_size = 6 * 1024 * 1024  # 6MB
        original_content = os.urandom(original_size)
        original_file.write_bytes(original_content)
        original_checksum = compute_file_checksum(original_file)

        # Upload to OSF
        remote_path = f"{test_project_path}/test_roundtrip_large.bin"
        osf_fs.put_file(str(original_file), remote_path)

        # Download from OSF
        downloaded_file = tmp_path / "downloaded_large.bin"
        osf_fs.get_file(remote_path, str(downloaded_file))

        # Verify checksums match
        downloaded_checksum = compute_file_checksum(downloaded_file)
        assert original_checksum == downloaded_checksum

        # Verify size matches
        assert downloaded_file.stat().st_size == original_size

        # Clean up
        osf_fs.rm(remote_path)

    def test_roundtrip_medium_file(self, osf_fs, test_project_path, tmp_path):
        """Test roundtrip with a medium-sized file."""
        # Create original file (2MB)
        original_file = tmp_path / "original_medium.txt"
        original_content = b"Medium file content\n" * 100000  # ~2MB
        original_file.write_bytes(original_content)
        original_checksum = compute_file_checksum(original_file)

        # Upload to OSF
        remote_path = f"{test_project_path}/test_roundtrip_medium.txt"
        osf_fs.put_file(str(original_file), remote_path)

        # Download from OSF
        downloaded_file = tmp_path / "downloaded_medium.txt"
        osf_fs.get_file(remote_path, str(downloaded_file))

        # Verify checksums match
        downloaded_checksum = compute_file_checksum(downloaded_file)
        assert original_checksum == downloaded_checksum

        # Clean up
        osf_fs.rm(remote_path)

    def test_roundtrip_with_special_characters(
        self, osf_fs, test_project_path, tmp_path
    ):
        """Test roundtrip with file containing special characters."""
        # Create file with special characters
        original_file = tmp_path / "special_chars.txt"
        original_content = "Special chars: áéíóú ñ 中文 العربية 🎉\n" * 100
        original_file.write_text(original_content, encoding="utf-8")
        original_checksum = compute_file_checksum(original_file)

        # Upload to OSF
        remote_path = f"{test_project_path}/test_roundtrip_special.txt"
        osf_fs.put_file(str(original_file), remote_path)

        # Download from OSF
        downloaded_file = tmp_path / "downloaded_special.txt"
        osf_fs.get_file(remote_path, str(downloaded_file))

        # Verify checksums match
        downloaded_checksum = compute_file_checksum(downloaded_file)
        assert original_checksum == downloaded_checksum

        # Verify text content matches exactly
        downloaded_content = downloaded_file.read_text(encoding="utf-8")
        assert downloaded_content == original_content

        # Clean up
        osf_fs.rm(remote_path)

    def test_roundtrip_empty_file(self, osf_fs, test_project_path, tmp_path):
        """Test roundtrip with an empty file."""
        # Create empty file
        original_file = tmp_path / "empty.txt"
        original_file.write_text("")

        # Upload to OSF
        remote_path = f"{test_project_path}/test_roundtrip_empty.txt"
        osf_fs.put_file(str(original_file), remote_path)

        # Download from OSF
        downloaded_file = tmp_path / "downloaded_empty.txt"
        osf_fs.get_file(remote_path, str(downloaded_file))

        # Verify both are empty
        assert downloaded_file.stat().st_size == 0
        assert downloaded_file.read_text() == ""

        # Clean up
        osf_fs.rm(remote_path)

    def test_roundtrip_preserves_binary_data(self, osf_fs, test_project_path, tmp_path):
        """Test that binary data is preserved exactly in roundtrip."""
        # Create file with various byte values
        original_file = tmp_path / "binary_data.bin"
        # Include all byte values from 0-255
        original_content = bytes(range(256)) * 1000  # Repeat pattern
        original_file.write_bytes(original_content)

        # Upload to OSF
        remote_path = f"{test_project_path}/test_roundtrip_binary.bin"
        osf_fs.put_file(str(original_file), remote_path)

        # Download from OSF
        downloaded_file = tmp_path / "downloaded_binary.bin"
        osf_fs.get_file(remote_path, str(downloaded_file))

        # Verify byte-for-byte match
        downloaded_content = downloaded_file.read_bytes()
        assert downloaded_content == original_content

        # Clean up
        osf_fs.rm(remote_path)

    def test_multiple_roundtrips_same_file(self, osf_fs, test_project_path, tmp_path):
        """Test multiple upload/download cycles preserve data."""
        # Create original file
        original_file = tmp_path / "multi_roundtrip.txt"
        original_content = "Multi-roundtrip test\n" * 1000
        original_file.write_text(original_content)
        original_checksum = compute_file_checksum(original_file)

        remote_path = f"{test_project_path}/test_multi_roundtrip.txt"

        # Perform 3 upload/download cycles
        for i in range(3):
            # Upload
            osf_fs.put_file(str(original_file), remote_path)

            # Download
            downloaded_file = tmp_path / f"downloaded_cycle_{i}.txt"
            osf_fs.get_file(remote_path, str(downloaded_file))

            # Verify checksum
            downloaded_checksum = compute_file_checksum(downloaded_file)
            assert original_checksum == downloaded_checksum, (
                f"Checksum mismatch in cycle {i}"
            )

        # Clean up
        osf_fs.rm(remote_path)
