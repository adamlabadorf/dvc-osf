"""Integration tests for OSF filesystem copy operations.

These tests require:
- OSF_TEST_TOKEN environment variable (your OSF Personal Access Token)
- OSF_TEST_PROJECT_ID environment variable (test project ID)
- Write permissions on the test project

To run integration tests:
    export OSF_TEST_TOKEN="your_token_here"
    export OSF_TEST_PROJECT_ID="your_project_id"
    pytest tests/integration/test_osf_copy.py -v -m integration

To skip integration tests (default):
    pytest tests/  # automatically skips if env vars not set
"""

import os
import tempfile
import time

import pytest

from dvc_osf.exceptions import (
    OSFConflictError,
    OSFNotFoundError,
    OSFOperationNotSupportedError,
)
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


@pytest.fixture
def osf_fs():
    """Create OSFFileSystem instance for testing."""
    url = f"osf://{OSF_TEST_PROJECT_ID}/osfstorage"
    return OSFFileSystem(url, token=OSF_TEST_TOKEN)


@pytest.fixture
def test_file_small(osf_fs):
    """Create a small test file in OSF storage."""
    filename = f"test_copy_small_{int(time.time())}.txt"
    content = b"This is a small test file for copy operations."

    # Upload test file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        osf_fs.put_file(tmp.name, filename)

    yield filename, content

    # Cleanup - try to delete if it still exists
    try:
        osf_fs.rm_file(filename)
    except Exception:
        pass


@pytest.fixture
def test_file_large(osf_fs):
    """Create a large test file (>10MB) in OSF storage."""
    filename = f"test_copy_large_{int(time.time())}.bin"
    # Create 10MB of data
    content = b"X" * (10 * 1024 * 1024)

    # Upload test file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        osf_fs.put_file(tmp.name, filename)

    yield filename, content

    # Cleanup
    try:
        osf_fs.rm_file(filename)
    except Exception:
        pass


@pytest.fixture
def test_directory(osf_fs):
    """Create a test directory with files in OSF storage."""
    base_dir = f"test_copy_dir_{int(time.time())}"
    files = []

    # Create a simple directory structure (OSF may not support deeply nested creation)
    structure = [
        f"{base_dir}/file1.txt",
        f"{base_dir}/file2.txt",
        f"{base_dir}/file3.txt",
    ]

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test content")
        tmp.flush()

        for file_path in structure:
            try:
                osf_fs.put_file(tmp.name, file_path)
                files.append(file_path)
            except Exception as e:
                # If directory creation fails, skip this test
                print(f"Failed to create {file_path}: {e}")

    os.unlink(tmp.name)

    yield base_dir, files

    # Cleanup - delete all created files
    for file_path in files:
        try:
            osf_fs.rm_file(file_path)
        except Exception:
            pass


class TestOSFCopySmallFile:
    """Integration tests for copying small files."""

    def test_copy_small_file(self, osf_fs, test_file_small):
        """Test copying a small file successfully."""
        source, content = test_file_small
        dest = f"test_copy_dest_{int(time.time())}.txt"

        try:
            # Copy file
            osf_fs.cp(source, dest)

            # Verify destination exists
            assert osf_fs.exists(dest)

            # Verify content matches
            info_src = osf_fs.info(source)
            info_dest = osf_fs.info(dest)

            # Size should match
            assert info_dest["size"] == info_src["size"]

            # Download and verify content
            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = os.path.join(tmpdir, "downloaded.txt")
                osf_fs.get_file(dest, local_path)

                with open(local_path, "rb") as f:
                    downloaded_content = f.read()

                assert downloaded_content == content

        finally:
            # Cleanup destination
            try:
                osf_fs.rm_file(dest)
            except Exception:
                pass

    def test_copy_file_not_found(self, osf_fs):
        """Test copying non-existent file raises OSFNotFoundError."""
        source = "nonexistent_file_12345.txt"
        dest = f"test_copy_dest_{int(time.time())}.txt"

        with pytest.raises(OSFNotFoundError):
            osf_fs.cp(source, dest)

    def test_copy_destination_exists_no_overwrite(self, osf_fs, test_file_small):
        """Test copying to existing destination without overwrite raises OSFConflictError."""
        source, _ = test_file_small
        dest = f"test_copy_dest_{int(time.time())}.txt"

        try:
            # Create destination file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"existing content")
                tmp.flush()
                osf_fs.put_file(tmp.name, dest)
            os.unlink(tmp.name)

            # Try to copy with overwrite=False
            with pytest.raises(OSFConflictError):
                osf_fs.cp(source, dest, overwrite=False)

        finally:
            try:
                osf_fs.rm_file(dest)
            except Exception:
                pass

    def test_copy_destination_exists_with_overwrite(self, osf_fs, test_file_small):
        """Test copying to existing destination with overwrite=True succeeds."""
        source, content = test_file_small
        dest = f"test_copy_dest_{int(time.time())}.txt"

        try:
            # Create destination file with different content
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"existing content that will be replaced")
                tmp.flush()
                osf_fs.put_file(tmp.name, dest)
            os.unlink(tmp.name)

            # Copy with overwrite=True
            osf_fs.cp(source, dest, overwrite=True)

            # Verify destination was replaced
            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = os.path.join(tmpdir, "downloaded.txt")
                osf_fs.get_file(dest, local_path)

                with open(local_path, "rb") as f:
                    downloaded_content = f.read()

                assert downloaded_content == content

        finally:
            try:
                osf_fs.rm_file(dest)
            except Exception:
                pass

    def test_copy_checksum_verification(self, osf_fs, test_file_small):
        """Test that copy verifies checksums match."""
        source, _ = test_file_small
        dest = f"test_copy_dest_{int(time.time())}.txt"

        try:
            # Copy file
            osf_fs.cp(source, dest)

            # Get checksums (if available in metadata)
            info_src = osf_fs.info(source)
            info_dest = osf_fs.info(dest)

            # If checksums are provided, they should match
            if "checksum" in info_src and "checksum" in info_dest:
                assert info_dest["checksum"] == info_src["checksum"]

        finally:
            try:
                osf_fs.rm_file(dest)
            except Exception:
                pass


class TestOSFCopyLargeFile:
    """Integration tests for copying large files."""

    def test_copy_large_file(self, osf_fs, test_file_large):
        """Test copying a large file (>10MB) successfully."""
        source, content = test_file_large
        dest = f"test_copy_large_dest_{int(time.time())}.bin"

        try:
            # Copy file
            osf_fs.cp(source, dest)

            # Verify destination exists
            assert osf_fs.exists(dest)

            # Verify size matches
            info_src = osf_fs.info(source)
            info_dest = osf_fs.info(dest)
            assert info_dest["size"] == info_src["size"]
            assert info_dest["size"] == len(content)

        finally:
            try:
                osf_fs.rm_file(dest)
            except Exception:
                pass


class TestOSFCopyDirectory:
    """Integration tests for copying directories recursively."""

    def test_copy_directory_recursive(self, osf_fs, test_directory):
        """Test copying directory with files."""
        source_dir, source_files = test_directory
        timestamp = int(time.time())

        # Skip if no files were created (directory creation may not be supported)
        if not source_files:
            pytest.skip(
                "Unable to create test directory - OSF may not support directory creation via API"
            )

        dest_dir = f"test_copy_dest_dir_{timestamp}"

        try:
            # Copy directory recursively
            osf_fs.cp(source_dir, dest_dir, recursive=True)

            # Verify all files were copied
            for source_file in source_files:
                # Construct destination path
                rel_path = source_file.replace(source_dir, "", 1).lstrip("/")
                dest_file = f"{dest_dir}/{rel_path}"

                # Check file exists
                assert osf_fs.exists(dest_file), f"Expected {dest_file} to exist"

        finally:
            # Cleanup destination directory
            dest_files = [f.replace(source_dir, dest_dir, 1) for f in source_files]
            for file_path in dest_files:
                try:
                    osf_fs.rm_file(file_path)
                except Exception:
                    pass

    def test_copy_empty_directory(self, osf_fs):
        """Test copying empty directory completes successfully."""
        source_dir = f"test_empty_dir_{int(time.time())}"
        dest_dir = f"test_copy_empty_dest_{int(time.time())}"

        try:
            # Create empty directory by creating and deleting a file
            temp_file = f"{source_dir}/temp.txt"
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"temp")
                tmp.flush()
                osf_fs.put_file(tmp.name, temp_file)
            os.unlink(tmp.name)
            osf_fs.rm_file(temp_file)

            # Copy empty directory
            osf_fs.cp(source_dir, dest_dir, recursive=True)

            # Should complete without error
            # (May or may not create destination directory depending on implementation)

        except OSFNotFoundError:
            # Empty directory might not exist, which is acceptable
            pass
        finally:
            pass


class TestOSFCopyConstraints:
    """Integration tests for copy operation constraints."""

    def test_copy_cross_project_raises(self, osf_fs, test_file_small):
        """Test that cross-project copy raises OSFOperationNotSupportedError."""
        source, _ = test_file_small
        # Use different project ID in destination
        dest = f"osf://different_project/osfstorage/file.txt"

        with pytest.raises(OSFOperationNotSupportedError):
            osf_fs.cp(source, dest)

    def test_copy_cross_provider_raises(self, osf_fs, test_file_small):
        """Test that cross-provider copy raises OSFOperationNotSupportedError."""
        source, _ = test_file_small
        # Use different provider in destination
        dest = f"osf://{OSF_TEST_PROJECT_ID}/github/file.txt"

        with pytest.raises(OSFOperationNotSupportedError):
            osf_fs.cp(source, dest)


class TestOSFCopyOverwriteBehavior:
    """Integration tests for copy overwrite behavior."""

    def test_copy_overwrite_flag_default(self, osf_fs, test_file_small):
        """Test that overwrite defaults to True."""
        source, content = test_file_small
        dest = f"test_copy_overwrite_dest_{int(time.time())}.txt"

        try:
            # Create destination
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"will be overwritten")
                tmp.flush()
                osf_fs.put_file(tmp.name, dest)
            os.unlink(tmp.name)

            # Copy without specifying overwrite (should default to True)
            osf_fs.cp(source, dest)

            # Verify destination was overwritten
            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = os.path.join(tmpdir, "downloaded.txt")
                osf_fs.get_file(dest, local_path)

                with open(local_path, "rb") as f:
                    downloaded_content = f.read()

                assert downloaded_content == content

        finally:
            try:
                osf_fs.rm_file(dest)
            except Exception:
                pass
