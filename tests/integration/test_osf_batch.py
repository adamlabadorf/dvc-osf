"""Integration tests for OSF filesystem batch operations.

These tests require:
- OSF_TEST_TOKEN environment variable (your OSF Personal Access Token)
- OSF_TEST_PROJECT_ID environment variable (test project ID)
- Write permissions on the test project

To run integration tests:
    export OSF_TEST_TOKEN="your_token_here"
    export OSF_TEST_PROJECT_ID="your_project_id"
    pytest tests/integration/test_osf_batch.py -v -m integration

To skip integration tests (default):
    pytest tests/  # automatically skips if env vars not set
"""

import os
import tempfile
import time

import pytest

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
def multiple_test_files(osf_fs):
    """Create multiple test files in OSF storage."""
    timestamp = int(time.time())
    files = []
    content = b"This is test content for batch operations."

    # Create 10 test files at root level
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp.flush()

        for i in range(10):
            filename = f"test_batch_{timestamp}_{i}.txt"
            try:
                osf_fs.put_file(tmp.name, filename)
                files.append(filename)
            except Exception as e:
                print(f"Failed to create {filename}: {e}")

    os.unlink(tmp.name)

    # Skip test if no files were created
    if not files:
        pytest.skip("Unable to create test files in OSF")

    yield files, content

    # Cleanup - try to delete all files
    for filename in files:
        try:
            osf_fs.rm_file(filename)
        except Exception:
            pass


@pytest.fixture
def large_batch_files(osf_fs):
    """Create many test files for large batch operations."""
    timestamp = int(time.time())
    files = []
    content = b"Batch test content"

    # Create 20+ files for large batch testing
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp.flush()

        for i in range(25):
            filename = f"test_large_batch_{timestamp}_{i}.txt"
            try:
                osf_fs.put_file(tmp.name, filename)
                files.append(filename)
            except Exception as e:
                print(f"Failed to create {filename}: {e}")

    os.unlink(tmp.name)

    # Skip test if no files were created
    if not files:
        pytest.skip("Unable to create test files in OSF")

    yield files, content

    # Cleanup
    for filename in files:
        try:
            osf_fs.rm_file(filename)
        except Exception:
            pass


class TestBatchCopy:
    """Integration tests for batch copy operations."""

    def test_batch_copy_multiple_files(self, osf_fs, multiple_test_files):
        """Test batch copying 10+ files successfully."""
        source_files, content = multiple_test_files
        timestamp = int(time.time())

        # Create list of (source, dest) tuples
        copy_pairs = [
            (src, f"batch_copy_dest_{timestamp}_{i}.txt")
            for i, src in enumerate(source_files)
        ]

        dest_files = [dest for _, dest in copy_pairs]

        try:
            # Batch copy
            result = osf_fs.batch_copy(copy_pairs)

            # Verify result
            assert result["total"] == len(copy_pairs)
            assert result["successful"] == len(copy_pairs)
            assert result["failed"] == 0
            assert len(result["errors"]) == 0

            # Verify all destination files exist
            for dest in dest_files:
                assert osf_fs.exists(dest), f"Expected {dest} to exist"

            # Verify source files still exist (copy doesn't delete source)
            for src in source_files:
                assert osf_fs.exists(src), f"Expected {src} to still exist"

        finally:
            # Cleanup destination files
            for dest in dest_files:
                try:
                    osf_fs.rm_file(dest)
                except Exception:
                    pass

    def test_batch_copy_with_progress_callback(self, osf_fs, multiple_test_files):
        """Test batch copy with progress callback."""
        source_files, _ = multiple_test_files
        timestamp = int(time.time())

        copy_pairs = [
            (src, f"batch_copy_callback_{timestamp}_{i}.txt")
            for i, src in enumerate(source_files[:5])  # Use first 5 files
        ]

        dest_files = [dest for _, dest in copy_pairs]
        callback_calls = []

        def progress_callback(current, total, path, operation):
            callback_calls.append((current, total, path, operation))

        try:
            # Batch copy with callback
            result = osf_fs.batch_copy(copy_pairs, callback=progress_callback)

            # Verify callback was called
            assert len(callback_calls) == len(copy_pairs)

            # Verify callback arguments
            for i, (current, total, path, operation) in enumerate(callback_calls):
                assert current == i + 1
                assert total == len(copy_pairs)
                assert operation == "copy"

            # Verify result
            assert result["successful"] == len(copy_pairs)

        finally:
            for dest in dest_files:
                try:
                    osf_fs.rm_file(dest)
                except Exception:
                    pass

    def test_batch_copy_partial_failure(self, osf_fs, multiple_test_files):
        """Test batch copy handles partial failures."""
        source_files, _ = multiple_test_files
        timestamp = int(time.time())

        # Create copy pairs with one invalid source
        copy_pairs = [
            (source_files[0], f"batch_copy_partial_{timestamp}_0.txt"),
            ("nonexistent_file_12345.txt", f"batch_copy_partial_{timestamp}_1.txt"),
            (source_files[1], f"batch_copy_partial_{timestamp}_2.txt"),
        ]

        dest_files = [dest for _, dest in copy_pairs]

        try:
            # Batch copy with one failure
            result = osf_fs.batch_copy(copy_pairs)

            # Verify result shows partial failure
            assert result["total"] == 3
            assert result["successful"] == 2
            assert result["failed"] == 1
            assert len(result["errors"]) == 1

            # Verify successful copies exist
            assert osf_fs.exists(dest_files[0])
            assert osf_fs.exists(dest_files[2])

            # Verify failed copy doesn't exist
            assert not osf_fs.exists(dest_files[1])

        finally:
            for dest in dest_files:
                try:
                    osf_fs.rm_file(dest)
                except Exception:
                    pass


class TestBatchMove:
    """Integration tests for batch move operations."""

    def test_batch_move_multiple_files(self, osf_fs, multiple_test_files):
        """Test batch moving 10+ files successfully."""
        source_files, content = multiple_test_files
        timestamp = int(time.time())

        # Create list of (source, dest) tuples
        move_pairs = [
            (src, f"batch_move_dest_{timestamp}_{i}.txt")
            for i, src in enumerate(source_files)
        ]

        dest_files = [dest for _, dest in move_pairs]

        try:
            # Batch move
            result = osf_fs.batch_move(move_pairs)

            # Verify result
            assert result["total"] == len(move_pairs)
            assert result["successful"] == len(move_pairs)
            assert result["failed"] == 0
            assert len(result["errors"]) == 0

            # Verify all destination files exist
            for dest in dest_files:
                assert osf_fs.exists(dest), f"Expected {dest} to exist"

            # Verify source files no longer exist
            for src in source_files:
                assert not osf_fs.exists(src), f"Expected {src} to be deleted"

        finally:
            # Cleanup destination files
            for dest in dest_files:
                try:
                    osf_fs.rm_file(dest)
                except Exception:
                    pass

    def test_batch_move_with_errors(self, osf_fs, multiple_test_files):
        """Test batch move handles errors gracefully."""
        source_files, _ = multiple_test_files
        timestamp = int(time.time())

        # Create move pairs with one invalid source
        move_pairs = [
            (source_files[0], f"batch_move_error_{timestamp}_0.txt"),
            ("nonexistent_file_12345.txt", f"batch_move_error_{timestamp}_1.txt"),
            (source_files[1], f"batch_move_error_{timestamp}_2.txt"),
        ]

        dest_files = [dest for _, dest in move_pairs]

        try:
            # Batch move with one failure
            result = osf_fs.batch_move(move_pairs)

            # Verify result shows partial failure
            assert result["total"] == 3
            assert result["successful"] == 2
            assert result["failed"] == 1
            assert len(result["errors"]) == 1

            # Verify successful moves
            assert osf_fs.exists(dest_files[0])
            assert osf_fs.exists(dest_files[2])
            assert not osf_fs.exists(source_files[0])
            assert not osf_fs.exists(source_files[1])

            # Verify failed move doesn't exist
            assert not osf_fs.exists(dest_files[1])

        finally:
            for dest in dest_files:
                try:
                    osf_fs.rm_file(dest)
                except Exception:
                    pass


class TestBatchDelete:
    """Integration tests for batch delete operations."""

    def test_batch_delete_multiple_files(self, osf_fs, multiple_test_files):
        """Test batch deleting 10+ files successfully."""
        files_to_delete, _ = multiple_test_files

        # Batch delete
        result = osf_fs.batch_delete(files_to_delete)

        # Verify result
        assert result["total"] == len(files_to_delete)
        assert result["successful"] == len(files_to_delete)
        assert result["failed"] == 0
        assert len(result["errors"]) == 0

        # Verify all files were deleted
        for file_path in files_to_delete:
            assert not osf_fs.exists(file_path), f"Expected {file_path} to be deleted"

    def test_batch_delete_with_progress_callback(self, osf_fs, multiple_test_files):
        """Test batch delete with progress callback."""
        files_to_delete, _ = multiple_test_files
        callback_calls = []

        def progress_callback(current, total, path, operation):
            callback_calls.append((current, total, path, operation))

        # Batch delete with callback
        result = osf_fs.batch_delete(files_to_delete[:5], callback=progress_callback)

        # Verify callback was called
        assert len(callback_calls) == 5

        # Verify callback arguments
        for i, (current, total, path, operation) in enumerate(callback_calls):
            assert current == i + 1
            assert total == 5
            assert operation == "delete"

        # Verify result
        assert result["successful"] == 5

    def test_batch_delete_partial_failure(self, osf_fs, multiple_test_files):
        """Test batch delete handles partial failures."""
        existing_files, _ = multiple_test_files

        # Create list with some non-existent files
        files_to_delete = [
            existing_files[0],
            "nonexistent_file_12345.txt",
            existing_files[1],
            "another_nonexistent_file.txt",
            existing_files[2],
        ]

        # Batch delete with some failures
        result = osf_fs.batch_delete(files_to_delete)

        # Verify result shows partial failure
        assert result["total"] == 5
        assert result["successful"] == 3
        assert result["failed"] == 2
        assert len(result["errors"]) == 2

        # Verify successful deletes
        assert not osf_fs.exists(existing_files[0])
        assert not osf_fs.exists(existing_files[1])
        assert not osf_fs.exists(existing_files[2])


class TestBatchPerformance:
    """Integration tests for batch operation performance."""

    def test_batch_copy_large_set(self, osf_fs, large_batch_files):
        """Test batch copy with 20+ files."""
        source_files, _ = large_batch_files
        timestamp = int(time.time())

        copy_pairs = [
            (src, f"batch_large_copy_{timestamp}_{i}.txt")
            for i, src in enumerate(source_files)
        ]

        dest_files = [dest for _, dest in copy_pairs]

        try:
            # Batch copy large set
            result = osf_fs.batch_copy(copy_pairs)

            # Verify all succeeded
            assert result["total"] == len(copy_pairs)
            assert result["successful"] == len(copy_pairs)
            assert result["failed"] == 0

            # Verify destinations exist
            for dest in dest_files:
                assert osf_fs.exists(dest)

        finally:
            for dest in dest_files:
                try:
                    osf_fs.rm_file(dest)
                except Exception:
                    pass

    def test_batch_delete_large_set(self, osf_fs, large_batch_files):
        """Test batch delete with 20+ files."""
        files_to_delete, _ = large_batch_files

        # Batch delete large set
        result = osf_fs.batch_delete(files_to_delete)

        # Verify all succeeded
        assert result["total"] == len(files_to_delete)
        assert result["successful"] == len(files_to_delete)
        assert result["failed"] == 0

        # Verify all deleted
        for file_path in files_to_delete:
            assert not osf_fs.exists(file_path)


class TestBatchValidation:
    """Integration tests for batch operation validation."""

    def test_batch_copy_empty_list(self, osf_fs):
        """Test batch copy with empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            osf_fs.batch_copy([])

    def test_batch_move_empty_list(self, osf_fs):
        """Test batch move with empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            osf_fs.batch_move([])

    def test_batch_delete_empty_list(self, osf_fs):
        """Test batch delete with empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            osf_fs.batch_delete([])

    def test_batch_copy_duplicate_destinations(self, osf_fs, multiple_test_files):
        """Test batch copy with duplicate destinations raises ValueError."""
        source_files, _ = multiple_test_files
        timestamp = int(time.time())

        # Create pairs with duplicate destination
        copy_pairs = [
            (source_files[0], f"duplicate_dest_{timestamp}.txt"),
            (source_files[1], f"duplicate_dest_{timestamp}.txt"),  # Duplicate!
        ]

        with pytest.raises(ValueError, match="duplicate"):
            osf_fs.batch_copy(copy_pairs)

    def test_batch_move_duplicate_destinations(self, osf_fs, multiple_test_files):
        """Test batch move with duplicate destinations raises ValueError."""
        source_files, _ = multiple_test_files
        timestamp = int(time.time())

        # Create pairs with duplicate destination
        move_pairs = [
            (source_files[0], f"duplicate_dest_{timestamp}.txt"),
            (source_files[1], f"duplicate_dest_{timestamp}.txt"),  # Duplicate!
        ]

        with pytest.raises(ValueError, match="duplicate"):
            osf_fs.batch_move(move_pairs)
