"""Integration tests for OSF filesystem move operations.

These tests require:
- OSF_TEST_TOKEN environment variable (your OSF Personal Access Token)
- OSF_TEST_PROJECT_ID environment variable (test project ID)
- Write permissions on the test project

To run integration tests:
    export OSF_TEST_TOKEN="your_token_here"
    export OSF_TEST_PROJECT_ID="your_project_id"
    pytest tests/integration/test_osf_move.py -v -m integration

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
def test_file(osf_fs):
    """Create a test file in OSF storage."""
    filename = f"test_move_{int(time.time())}.txt"
    content = b"This is a test file for move operations."

    # Upload test file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        osf_fs.put_file(tmp.name, filename)

    os.unlink(tmp.name)

    yield filename, content

    # Cleanup - try to delete if it still exists
    try:
        osf_fs.rm_file(filename)
    except Exception:
        pass


@pytest.fixture
def test_directory(osf_fs):
    """Create a test directory with files in OSF storage."""
    base_dir = f"test_move_dir_{int(time.time())}"
    files = []

    # Create a simple directory structure
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
                print(f"Failed to create {file_path}: {e}")

    os.unlink(tmp.name)

    yield base_dir, files

    # Cleanup - delete all created files
    for file_path in files:
        try:
            osf_fs.rm_file(file_path)
        except Exception:
            pass


class TestOSFMoveFile:
    """Integration tests for moving files."""

    def test_move_file(self, osf_fs, test_file):
        """Test moving a file successfully."""
        source, content = test_file
        dest = f"test_move_dest_{int(time.time())}.txt"

        try:
            # Move file
            osf_fs.mv(source, dest)

            # Verify source no longer exists
            assert not osf_fs.exists(source)

            # Verify destination exists
            assert osf_fs.exists(dest)

            # Verify content matches
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

    def test_move_verify_source_deleted(self, osf_fs, test_file):
        """Test that source is deleted after successful move."""
        source, _ = test_file
        dest = f"test_move_dest_{int(time.time())}.txt"

        try:
            # Move file
            osf_fs.mv(source, dest)

            # Verify source is gone
            assert not osf_fs.exists(source)

            # Try to access source should fail
            with pytest.raises(OSFNotFoundError):
                osf_fs.info(source)

        finally:
            try:
                osf_fs.rm_file(dest)
            except Exception:
                pass

    def test_rename_file(self, osf_fs, test_file):
        """Test renaming a file within same directory."""
        source, content = test_file
        # Extract directory and create new name in same directory
        if "/" in source:
            directory = source.rsplit("/", 1)[0]
            dest = f"{directory}/renamed_{int(time.time())}.txt"
        else:
            dest = f"renamed_{int(time.time())}.txt"

        try:
            # Rename file
            osf_fs.mv(source, dest)

            # Verify source no longer exists
            assert not osf_fs.exists(source)

            # Verify destination exists
            assert osf_fs.exists(dest)

            # Verify content preserved
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

    @pytest.mark.skip(reason="OSF may not support moving to non-existent directories")
    def test_move_to_subdirectory(self, osf_fs, test_file):
        """Test moving a file to a subdirectory."""
        source, content = test_file
        dest = f"subdir_{int(time.time())}/moved_file.txt"

        try:
            # Move file to subdirectory
            osf_fs.mv(source, dest)

            # Verify source no longer exists
            assert not osf_fs.exists(source)

            # Verify destination exists
            assert osf_fs.exists(dest)

            # Verify content
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

    def test_move_file_not_found(self, osf_fs):
        """Test moving non-existent file raises OSFNotFoundError."""
        source = "nonexistent_file_12345.txt"
        dest = f"test_move_dest_{int(time.time())}.txt"

        with pytest.raises(OSFNotFoundError):
            osf_fs.mv(source, dest)

    def test_move_destination_exists(self, osf_fs, test_file):
        """Test moving to existing destination raises OSFConflictError."""
        source, _ = test_file
        dest = f"test_move_dest_{int(time.time())}.txt"

        try:
            # Create destination file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"existing content")
                tmp.flush()
                osf_fs.put_file(tmp.name, dest)
            os.unlink(tmp.name)

            # Try to move to existing destination
            with pytest.raises(OSFConflictError):
                osf_fs.mv(source, dest)

        finally:
            try:
                osf_fs.rm_file(dest)
            except Exception:
                pass


class TestOSFMoveDirectory:
    """Integration tests for moving directories recursively."""

    def test_move_directory_recursive(self, osf_fs, test_directory):
        """Test moving directory with files."""
        source_dir, source_files = test_directory
        dest_dir = f"test_move_dest_dir_{int(time.time())}"

        # Skip if no files were created
        if not source_files:
            pytest.skip(
                "Unable to create test directory - OSF may not support directory creation via API"
            )

        try:
            # Move directory recursively
            osf_fs.mv(source_dir, dest_dir, recursive=True)

            # Verify source files no longer exist
            for source_file in source_files:
                assert not osf_fs.exists(
                    source_file
                ), f"Expected {source_file} to be deleted"

            # Verify all files were moved to destination
            for source_file in source_files:
                # Construct destination path
                rel_path = source_file.replace(source_dir, "", 1).lstrip("/")
                dest_file = f"{dest_dir}/{rel_path}"

                # Check file exists at destination
                assert osf_fs.exists(dest_file), f"Expected {dest_file} to exist"

        finally:
            # Cleanup destination directory
            dest_files = [f.replace(source_dir, dest_dir, 1) for f in source_files]
            for file_path in dest_files:
                try:
                    osf_fs.rm_file(file_path)
                except Exception:
                    pass


class TestOSFMoveConstraints:
    """Integration tests for move operation constraints."""

    def test_move_cross_project_raises(self, osf_fs, test_file):
        """Test that cross-project move raises OSFOperationNotSupportedError."""
        source, _ = test_file
        # Use different project ID in destination
        dest = f"osf://different_project/osfstorage/file.txt"

        with pytest.raises(OSFOperationNotSupportedError):
            osf_fs.mv(source, dest)

    def test_move_cross_provider_raises(self, osf_fs, test_file):
        """Test that cross-provider move raises OSFOperationNotSupportedError."""
        source, _ = test_file
        # Use different provider in destination
        dest = f"osf://{OSF_TEST_PROJECT_ID}/github/file.txt"

        with pytest.raises(OSFOperationNotSupportedError):
            osf_fs.mv(source, dest)


class TestOSFMoveErrorHandling:
    """Integration tests for move error handling."""

    def test_move_atomicity(self, osf_fs, test_file):
        """Test that move uses copy-then-delete (not atomic but reliable)."""
        source, content = test_file
        dest = f"test_move_atomicity_{int(time.time())}.txt"

        try:
            # Move file
            osf_fs.mv(source, dest)

            # After successful move:
            # - Source should be deleted
            assert not osf_fs.exists(source)
            # - Destination should exist with correct content
            assert osf_fs.exists(dest)

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
