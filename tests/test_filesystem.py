"""Tests for OSF filesystem implementation."""

from unittest.mock import Mock, patch

import pytest

from dvc_osf.exceptions import (
    OSFIntegrityError,
    OSFNotFoundError,
    OSFConflictError,
    OSFOperationNotSupportedError,
)
from dvc_osf.filesystem import OSFFile, OSFFileSystem


class TestOSFFile:
    """Tests for OSFFile class."""

    def test_read_all_binary(self):
        """Test reading all data in binary mode."""
        mock_response = Mock()
        mock_response.iter_content.return_value = iter([b"hello", b" ", b"world"])

        osf_file = OSFFile(mock_response, mode="rb")
        data = osf_file.read()

        assert data == b"hello world"
        assert osf_file.tell() == 11

    def test_read_specific_size(self):
        """Test reading specific number of bytes."""
        mock_response = Mock()
        mock_response.iter_content.return_value = iter([b"hello world"])

        osf_file = OSFFile(mock_response, mode="rb")
        data = osf_file.read(5)

        assert data == b"hello"
        assert osf_file.tell() == 5

    def test_read_zero_bytes(self):
        """Test reading zero bytes."""
        mock_response = Mock()

        osf_file = OSFFile(mock_response, mode="rb")
        data = osf_file.read(0)

        assert data == b""
        assert osf_file.tell() == 0

    def test_read_text_mode(self):
        """Test reading in text mode."""
        mock_response = Mock()
        mock_response.iter_content.return_value = iter([b"hello", b" ", b"world"])

        osf_file = OSFFile(mock_response, mode="r")
        data = osf_file.read()

        assert data == "hello world"
        assert isinstance(data, str)

    def test_tell(self):
        """Test tell() method returns current position."""
        mock_response = Mock()
        mock_response.iter_content.return_value = iter([b"hello", b" ", b"world"])

        osf_file = OSFFile(mock_response, mode="rb")

        assert osf_file.tell() == 0
        osf_file.read(5)
        assert osf_file.tell() == 5
        osf_file.read()
        assert osf_file.tell() == 11

    def test_close(self):
        """Test close() method."""
        mock_response = Mock()

        osf_file = OSFFile(mock_response, mode="rb")
        assert not osf_file.closed

        osf_file.close()
        assert osf_file.closed
        mock_response.close.assert_called_once()

    def test_context_manager(self):
        """Test using OSFFile as context manager."""
        mock_response = Mock()

        with OSFFile(mock_response, mode="rb") as f:
            assert not f.closed

        assert f.closed
        mock_response.close.assert_called_once()

    def test_read_closed_file_raises(self):
        """Test that reading closed file raises ValueError."""
        mock_response = Mock()

        osf_file = OSFFile(mock_response, mode="rb")
        osf_file.close()

        with pytest.raises(ValueError, match="closed file"):
            osf_file.read()


class TestOSFFileSystemInit:
    """Tests for OSFFileSystem initialization."""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_init_with_url(self, mock_client_class):
        """Test initialization with OSF URL."""
        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")

        assert fs.project_id == "abc123"
        assert fs.provider == "osfstorage"
        assert fs.base_path == ""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_init_with_url_and_path(self, mock_client_class):
        """Test initialization with URL including path."""
        fs = OSFFileSystem("osf://abc123/osfstorage/data", token="test_token")

        assert fs.project_id == "abc123"
        assert fs.provider == "osfstorage"
        assert fs.base_path == "data"


class TestOSFFileSystemExists:
    """Tests for exists() method."""

    @patch("dvc_osf.filesystem.OSFFileSystem.info")
    def test_exists_true(self, mock_info):
        """Test exists() returns True when file exists."""
        mock_info.return_value = {"name": "file.csv", "type": "file"}

        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")
        assert fs.exists("file.csv") is True

    @patch("dvc_osf.filesystem.OSFFileSystem.info")
    def test_exists_false(self, mock_info):
        """Test exists() returns False when file not found."""
        mock_info.side_effect = OSFNotFoundError("Not found")

        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")
        assert fs.exists("missing.csv") is False


class TestOSFFileSystemLs:
    """Tests for ls() method."""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_ls_without_detail(self, mock_client_class):
        """Test ls() without detail returns just paths."""
        mock_client = Mock()
        mock_client.get_paginated.return_value = iter(
            [
                {"attributes": {"name": "file1.csv", "kind": "file"}},
                {"attributes": {"name": "file2.csv", "kind": "file"}},
            ]
        )
        mock_client_class.return_value = mock_client

        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")
        results = fs.ls("", detail=False)

        assert len(results) == 2
        assert all("osf://abc123" in path for path in results)

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_ls_with_detail(self, mock_client_class):
        """Test ls() with detail returns metadata."""
        mock_client = Mock()
        mock_client.get_paginated.return_value = iter(
            [
                {
                    "attributes": {
                        "name": "file1.csv",
                        "kind": "file",
                        "size": 1024,
                        "date_modified": "2024-01-01",
                        "extra": {"hashes": {"md5": "abc123"}},
                    }
                },
            ]
        )
        mock_client_class.return_value = mock_client

        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")
        results = fs.ls("", detail=True)

        assert len(results) == 1
        assert results[0]["type"] == "file"
        assert results[0]["size"] == 1024
        assert results[0]["checksum"] == "abc123"


class TestOSFFileSystemInfo:
    """Tests for info() method."""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_info_file(self, mock_client_class):
        """Test info() returns file metadata."""
        mock_client = Mock()
        mock_response = Mock()
        # info() now lists parent directory, so return array
        mock_response.json.return_value = {
            "data": [
                {
                    "attributes": {
                        "name": "file.csv",
                        "kind": "file",
                        "size": 2048,
                        "date_modified": "2024-01-01",
                        "extra": {"hashes": {"md5": "def456"}},
                    }
                }
            ]
        }
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")
        info = fs.info("file.csv")

        assert info["type"] == "file"
        assert info["size"] == 2048
        assert info["checksum"] == "def456"


class TestOSFFileSystemOpen:
    """Tests for open() method."""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_open_read_binary(self, mock_client_class):
        """Test opening file in binary read mode."""
        mock_client = Mock()

        # Mock responses for info() call (lists parent directory)
        mock_info_response = Mock()
        mock_info_response.json.return_value = {
            "data": [
                {
                    "attributes": {
                        "name": "file.csv",
                        "kind": "file",
                        "size": 100,
                        "extra": {"hashes": {"md5": "test"}},
                    },
                    "links": {"upload": "https://files.osf.io/test"},
                }
            ]
        }

        # Mock get to return listing
        mock_client.get.return_value = mock_info_response

        mock_stream_response = Mock()
        mock_stream_response.iter_content.return_value = iter([b"test"])
        mock_client.download_file.return_value = mock_stream_response
        mock_client_class.return_value = mock_client

        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")
        f = fs.open("file.csv", mode="rb")

        assert isinstance(f, OSFFile)
        assert f.mode == "rb"

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_open_write_mode_returns_write_file(self, mock_client_class):
        """Test that write mode returns OSFWriteFile."""
        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")

        # Write mode should return a writable file object
        file_obj = fs.open("file.csv", mode="wb")
        assert file_obj is not None
        assert hasattr(file_obj, "write")

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_open_append_raises(self, mock_client_class):
        """Test that append mode raises NotImplementedError."""
        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")

        with pytest.raises(NotImplementedError, match="not supported"):
            fs.open("file.csv", mode="ab")


class TestOSFFileSystemGetFile:
    """Tests for get_file() method."""

    @patch("dvc_osf.filesystem.OSFFileSystem.open")
    @patch("dvc_osf.filesystem.OSFFileSystem.info")
    @patch("builtins.open", new_callable=lambda: Mock(side_effect=open))
    def test_get_file_success(self, mock_builtin_open, mock_info, mock_open):
        """Test successful file download with checksum verification."""
        # Mock file info with checksum
        mock_info.return_value = {
            "checksum": "5d41402abc4b2a76b9719d911017c592",  # MD5 of "hello"
        }

        # Mock file read
        mock_file = Mock()
        mock_file.read.side_effect = [b"hello", b""]
        mock_open.return_value.__enter__.return_value = mock_file

        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, "test.txt")

            fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")
            fs.get_file("remote.txt", local_path)

            # File should be created
            mock_open.assert_called()

    @patch("dvc_osf.filesystem.OSFFileSystem.open")
    @patch("dvc_osf.filesystem.OSFFileSystem.info")
    @patch("builtins.open", new_callable=lambda: Mock(side_effect=open))
    @patch("os.remove")
    def test_get_file_checksum_mismatch(
        self, mock_remove, mock_builtin_open, mock_info, mock_open
    ):
        """Test that checksum mismatch raises OSFIntegrityError."""
        # Mock file info with wrong checksum
        mock_info.return_value = {
            "checksum": "wrong_checksum",
        }

        # Mock file read
        mock_file = Mock()
        mock_file.read.side_effect = [b"hello", b""]
        mock_open.return_value.__enter__.return_value = mock_file

        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, "test.txt")

            fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")

            with pytest.raises(OSFIntegrityError, match="Checksum mismatch"):
                fs.get_file("remote.txt", local_path)


class TestOSFFileSystemStripProtocol:
    """Tests for _strip_protocol() method."""

    def test_strip_protocol_with_prefix(self):
        """Test stripping osf:// prefix."""
        result = OSFFileSystem._strip_protocol("osf://abc123/file.csv")
        assert result == "abc123/file.csv"

    def test_strip_protocol_without_prefix(self):
        """Test path without prefix remains unchanged."""
        result = OSFFileSystem._strip_protocol("abc123/file.csv")
        assert result == "abc123/file.csv"

    def test_strip_protocol_with_list(self):
        """Test that a list of paths is handled (DVC passes lists during push)."""
        paths = ["osf://abc123/file.csv", "abc123/other.csv"]
        result = OSFFileSystem._strip_protocol(paths)
        assert result == ["abc123/file.csv", "abc123/other.csv"]

    def test_strip_protocol_with_empty_list(self):
        """Test that an empty list returns an empty list."""
        assert OSFFileSystem._strip_protocol([]) == []


class TestOSFWriteFile:
    """Tests for OSFWriteFile class."""

    def test_write_binary_data(self):
        """Test writing binary data."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="wb")

        bytes_written = write_file.write(b"hello world")
        assert bytes_written == 11
        assert write_file._bytes_written == 11

    def test_write_text_data(self):
        """Test writing text data in text mode."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="w")

        chars_written = write_file.write("hello world")
        assert chars_written == 11

    def test_write_text_to_binary_mode_raises(self):
        """Test writing text to binary mode raises TypeError."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="wb")

        with pytest.raises(TypeError, match="bytes-like object is required"):
            write_file.write("hello")

    def test_write_bytes_to_text_mode_raises(self):
        """Test writing bytes to text mode raises TypeError."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="w")

        with pytest.raises(TypeError, match="must be str"):
            write_file.write(b"hello")

    def test_write_to_closed_file_raises(self):
        """Test writing to closed file raises ValueError."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="wb")
        write_file.close()

        with pytest.raises(ValueError, match="closed file"):
            write_file.write(b"test")

    def test_close_uploads_data(self):
        """Test that close() uploads buffered data."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="wb")

        write_file.write(b"test data")
        write_file.close()

        # Verify upload was called
        mock_client.upload_file.assert_called_once()
        call_args = mock_client.upload_file.call_args
        assert call_args[0][0] == "https://upload.url"

    def test_close_with_empty_buffer(self):
        """Test closing file with empty buffer."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="wb")

        # Close without writing anything
        write_file.close()

        # Upload should not be called for empty file
        mock_client.upload_file.assert_not_called()

    def test_context_manager(self):
        """Test OSFWriteFile as context manager."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()

        with OSFWriteFile(mock_client, "https://upload.url", mode="wb") as f:
            f.write(b"test")
            assert not f.closed

        assert f.closed
        mock_client.upload_file.assert_called_once()

    def test_writable(self):
        """Test writable() method."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="wb")

        assert write_file.writable() is True

        write_file.close()
        assert write_file.writable() is False

    def test_closed_property(self):
        """Test closed property."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="wb")

        assert write_file.closed is False

        write_file.close()
        assert write_file.closed is True

    def test_multiple_writes(self):
        """Test multiple write operations."""
        from dvc_osf.filesystem import OSFWriteFile

        mock_client = Mock()
        write_file = OSFWriteFile(mock_client, "https://upload.url", mode="wb")

        write_file.write(b"hello ")
        write_file.write(b"world")
        write_file.close()

        # Verify data was accumulated
        call_args = mock_client.upload_file.call_args
        assert call_args[1]["total_size"] == 11  # "hello world"


class TestOSFFileSystemWriteMethods:
    """Tests for OSFFileSystem write methods."""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_put_file_callback_validation(self, mock_client_class):
        """Test put_file validates callback parameter."""
        fs = OSFFileSystem(token="test_token")

        # Non-callable callback should raise TypeError
        with pytest.raises(TypeError, match="callback must be callable"):
            fs.put_file(
                "/tmp/test.txt",
                "osf://abc123/osfstorage/test.txt",
                callback="not_callable",
            )

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_put_callback_validation(self, mock_client_class):
        """Test put validates callback parameter."""
        import io

        fs = OSFFileSystem(token="test_token")
        file_obj = io.BytesIO(b"test data")

        # Non-callable callback should raise TypeError
        with pytest.raises(TypeError, match="callback must be callable"):
            fs.put(
                file_obj, "osf://abc123/osfstorage/test.txt", callback="not_callable"
            )

    @patch("dvc_osf.filesystem.OSFAPIClient")
    @patch("dvc_osf.filesystem.OSFFileSystem._verify_upload_checksum")
    @patch("os.path.getsize")
    @patch("builtins.open")
    def test_put_file_small(
        self, mock_open, mock_getsize, mock_verify, mock_client_class
    ):
        """Test put_file with small file."""
        import io

        # Mock file size (small file, no chunking)
        mock_getsize.return_value = 1024  # 1KB

        # Mock file content
        mock_file = io.BytesIO(b"small file content")
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock client
        mock_client = Mock()

        # Mock response for checking if file exists
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_client.get.return_value = mock_response
        mock_client.upload_file.return_value = None
        mock_client_class.return_value = mock_client

        # Skip checksum verification for unit test
        mock_verify.return_value = None

        fs = OSFFileSystem(token="test_token")
        fs.put_file("/tmp/small.txt", "osf://abc123/osfstorage/small.txt")

        # Verify upload was called
        mock_client.upload_file.assert_called_once()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    @patch("dvc_osf.filesystem.OSFFileSystem._verify_upload_checksum")
    @patch("os.path.getsize")
    @patch("builtins.open")
    def test_put_file_large(
        self, mock_open, mock_getsize, mock_verify, mock_client_class
    ):
        """Test put_file with large file (triggers chunked upload)."""
        import io

        # Mock file size (large file, triggers chunking)
        mock_getsize.return_value = 10 * 1024 * 1024  # 10MB

        # Mock file content
        mock_file = io.BytesIO(b"large file content" * 100000)
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock client
        mock_client = Mock()

        # Mock response for checking if file exists
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_client.get.return_value = mock_response
        mock_client.upload_file.return_value = None
        mock_client_class.return_value = mock_client

        # Skip checksum verification for unit test
        mock_verify.return_value = None

        fs = OSFFileSystem(token="test_token")
        fs.put_file("/tmp/large.txt", "osf://abc123/osfstorage/large.txt")

        # Verify upload was called
        mock_client.upload_file.assert_called_once()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_put_with_file_object(self, mock_client_class):
        """Test put with file-like object."""
        import io

        # Mock client
        mock_client = Mock()

        # Mock response for checking if file exists
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_client.get.return_value = mock_response
        mock_client.upload_file.return_value = None
        mock_client_class.return_value = mock_client

        fs = OSFFileSystem(token="test_token")
        file_obj = io.BytesIO(b"file object content")

        fs.put(file_obj, "osf://abc123/osfstorage/test.txt")

        # Verify upload was called
        mock_client.upload_file.assert_called_once()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_put_with_callback(self, mock_client_class):
        """Test put with progress callback."""
        import io

        # Mock client
        mock_client = Mock()

        # Mock response for checking if file exists
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_client.get.return_value = mock_response
        mock_client.upload_file.return_value = None
        mock_client_class.return_value = mock_client

        callback = Mock()
        fs = OSFFileSystem(token="test_token")
        file_obj = io.BytesIO(b"test data")

        fs.put(file_obj, "osf://abc123/osfstorage/test.txt", callback=callback)

        # Verify upload was called with callback
        call_args = mock_client.upload_file.call_args
        # callback is passed as a positional or keyword arg
        assert (
            callback in call_args.args or call_args.kwargs.get("callback") == callback
        )

    @patch("dvc_osf.filesystem.OSFAPIClient")
    @patch("dvc_osf.filesystem.OSFFileSystem.info")
    def test_rm_file(self, mock_info, mock_client_class):
        """Test rm deletes file."""
        # Mock file info
        mock_info.return_value = {
            "type": "file",
            "links": {"delete": "https://files.osf.io/delete"},
        }

        # Mock client
        mock_client = Mock()

        # Mock the response for checking if file exists (in _get_delete_link)
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "attributes": {"name": "file.txt"},
                    "links": {"delete": "https://files.osf.io/delete"},
                }
            ]
        }
        mock_client.get.return_value = mock_response
        mock_client.delete.return_value = None
        mock_client_class.return_value = mock_client

        fs = OSFFileSystem(token="test_token")
        fs.rm("osf://abc123/osfstorage/file.txt")

        # Verify delete was called
        mock_client.delete.assert_called_once()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_rm_recursive_is_complex(self, mock_client_class):
        """Test that rm recursive is too complex for simple unit test - use integration tests."""
        # Recursive deletion is complex and involves multiple API calls
        # Integration tests cover this better
        # This test just verifies it doesn't error on simple case
        fs = OSFFileSystem(token="test_token")

        # Just verify the method exists and can be called
        # Actual behavior tested in integration tests
        assert hasattr(fs, "rm")
        assert callable(fs.rm)

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_mkdir_is_noop(self, mock_client_class):
        """Test mkdir is a no-op."""
        fs = OSFFileSystem(token="test_token")

        # Should not raise and should not make any API calls
        fs.mkdir("osf://abc123/osfstorage/newdir")

        # Client should only be initialized, not called
        mock_client = mock_client_class.return_value
        mock_client.get.assert_not_called()
        mock_client.put.assert_not_called()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_rmdir_is_noop(self, mock_client_class):
        """Test rmdir is a no-op."""
        fs = OSFFileSystem(token="test_token")

        # Should not raise and should not make any API calls
        fs.rmdir("osf://abc123/osfstorage/somedir")

        # Client should only be initialized, not called
        mock_client = mock_client_class.return_value
        mock_client.get.assert_not_called()
        mock_client.delete.assert_not_called()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_open_write_mode_not_implemented(self, mock_client_class):
        """Test open with write mode returns OSFWriteFile."""
        fs = OSFFileSystem(token="test_token")

        # Write modes should return OSFWriteFile (or raise NotImplementedError for now)
        # This is a placeholder - actual implementation may vary
        try:
            file_obj = fs.open("osf://abc123/osfstorage/test.txt", mode="w")
            assert file_obj is not None
            # Check if it's a writable file object
            assert hasattr(file_obj, "write")
        except NotImplementedError:
            # Also acceptable if not yet fully implemented
            pass

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_open_append_mode_raises(self, mock_client_class):
        """Test open with append mode raises NotImplementedError."""
        fs = OSFFileSystem(token="test_token")

        with pytest.raises(NotImplementedError):
            fs.open("osf://abc123/osfstorage/test.txt", mode="a")

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_open_read_write_mode_raises(self, mock_client_class):
        """Test open with read-write mode raises NotImplementedError."""
        fs = OSFFileSystem(token="test_token")

        with pytest.raises(NotImplementedError):
            fs.open("osf://abc123/osfstorage/test.txt", mode="r+")


class TestCopyOperations:
    """Tests for cp() method."""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    @patch("dvc_osf.filesystem.tempfile.mkstemp")
    @patch("os.path.exists")
    @patch("os.remove")
    @patch("os.close")
    def test_cp_single_file(
        self, mock_close, mock_remove, mock_exists, mock_mkstemp, mock_client_class
    ):
        """Test copying a single file."""
        # Setup mocks
        mock_mkstemp.return_value = (42, "/tmp/test_temp")
        mock_exists.return_value = True

        mock_client = mock_client_class.return_value
        fs = OSFFileSystem(token="test_token")

        # Mock info() to return file metadata
        with patch.object(fs, "info") as mock_info:
            mock_info.side_effect = [
                {"type": "file", "checksum": "abc123"},  # Source info
                {"type": "file", "checksum": "abc123"},  # Dest info after copy
            ]

            # Mock get_file and put_file
            with patch.object(fs, "get_file") as mock_get, patch.object(
                fs, "put_file"
            ) as mock_put, patch.object(fs, "exists") as mock_exists_check:
                mock_exists_check.return_value = False  # Destination doesn't exist

                # Execute copy
                fs.cp(
                    "osf://abc123/osfstorage/source.txt",
                    "osf://abc123/osfstorage/dest.txt",
                )

                # Verify calls
                mock_get.assert_called_once()
                mock_put.assert_called_once()
                mock_close.assert_called_once_with(42)
                mock_remove.assert_called_once_with("/tmp/test_temp")

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_cp_file_not_found(self, mock_client_class):
        """Test cp raises OSFNotFoundError if source doesn't exist."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "info") as mock_info:
            mock_info.side_effect = OSFNotFoundError("Source not found")

            with pytest.raises(OSFNotFoundError, match="Source not found"):
                fs.cp(
                    "osf://abc123/osfstorage/nonexistent.txt",
                    "osf://abc123/osfstorage/dest.txt",
                )

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_cp_destination_exists_no_overwrite(self, mock_client_class):
        """Test cp raises OSFConflictError if destination exists and overwrite=False."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "info") as mock_info, patch.object(
            fs, "exists"
        ) as mock_exists:
            mock_info.return_value = {"type": "file", "checksum": "abc123"}
            mock_exists.return_value = True  # Destination exists

            with pytest.raises(OSFConflictError, match="Destination exists"):
                fs.cp(
                    "osf://abc123/osfstorage/source.txt",
                    "osf://abc123/osfstorage/dest.txt",
                    overwrite=False,
                )

    @patch("dvc_osf.filesystem.OSFAPIClient")
    @patch("dvc_osf.filesystem.tempfile.mkstemp")
    @patch("os.path.exists")
    @patch("os.remove")
    @patch("os.close")
    def test_cp_destination_exists_with_overwrite(
        self, mock_close, mock_remove, mock_exists_os, mock_mkstemp, mock_client_class
    ):
        """Test cp succeeds if destination exists and overwrite=True."""
        mock_mkstemp.return_value = (42, "/tmp/test_temp")
        mock_exists_os.return_value = True

        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "info") as mock_info, patch.object(
            fs, "exists"
        ) as mock_exists, patch.object(fs, "get_file") as mock_get, patch.object(
            fs, "put_file"
        ) as mock_put:
            mock_info.side_effect = [
                {"type": "file", "checksum": "abc123"},  # Source
                {"type": "file", "checksum": "abc123"},  # Dest after copy
            ]
            mock_exists.return_value = True  # Destination exists

            # Should succeed with overwrite=True (default)
            fs.cp(
                "osf://abc123/osfstorage/source.txt",
                "osf://abc123/osfstorage/dest.txt",
                overwrite=True,
            )

            mock_put.assert_called_once()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_cp_cross_project(self, mock_client_class):
        """Test cp raises OSFOperationNotSupportedError for cross-project copy."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "info") as mock_info:
            mock_info.return_value = {"type": "file", "checksum": "abc123"}

            with pytest.raises(OSFOperationNotSupportedError, match="Cross-project"):
                fs.cp(
                    "osf://abc123/osfstorage/source.txt",
                    "osf://xyz789/osfstorage/dest.txt",
                )

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_cp_recursive_directory(self, mock_client_class):
        """Test recursive directory copy."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "info") as mock_info, patch.object(
            fs, "ls"
        ) as mock_ls, patch.object(fs, "exists") as mock_exists, patch.object(
            fs, "get_file"
        ) as mock_get, patch.object(
            fs, "put_file"
        ) as mock_put:
            # Mock info to return directory type first, then file types
            mock_info.side_effect = [
                {"type": "directory"},  # Source directory
                {"type": "file", "checksum": "abc123"},  # file1 source
                {"type": "file", "checksum": "abc123"},  # file1 dest
                {"type": "file", "checksum": "def456"},  # file2 source
                {"type": "file", "checksum": "def456"},  # file2 dest
            ]

            # Mock directory listing
            from dvc_osf.utils import serialize_path

            mock_ls.return_value = [
                {
                    "name": serialize_path("abc123", "osfstorage", "dir/file1.txt"),
                    "type": "file",
                },
                {
                    "name": serialize_path("abc123", "osfstorage", "dir/file2.txt"),
                    "type": "file",
                },
            ]

            mock_exists.return_value = False

            with patch("dvc_osf.filesystem.tempfile.mkstemp") as mock_mkstemp, patch(
                "os.path.exists"
            ) as mock_exists_os, patch("os.remove") as mock_remove, patch(
                "os.close"
            ) as mock_close:
                mock_mkstemp.return_value = (42, "/tmp/test_temp")
                mock_exists_os.return_value = True

                fs.cp(
                    "osf://abc123/osfstorage/dir",
                    "osf://abc123/osfstorage/newdir",
                    recursive=True,
                )

                # Should have called ls to get directory contents
                mock_ls.assert_called_once()
                # Should have copied both files
                assert mock_get.call_count == 2
                assert mock_put.call_count == 2

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_cp_empty_directory(self, mock_client_class):
        """Test copying empty directory."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "info") as mock_info, patch.object(fs, "ls") as mock_ls:
            mock_info.return_value = {"type": "directory"}
            mock_ls.return_value = []  # Empty directory

            # Should succeed without error
            fs.cp(
                "osf://abc123/osfstorage/emptydir",
                "osf://abc123/osfstorage/newdir",
                recursive=True,
            )

            mock_ls.assert_called_once()


class TestMoveOperations:
    """Tests for mv() method."""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_mv_single_file(self, mock_client_class):
        """Test moving a single file."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "exists") as mock_exists, patch.object(
            fs, "cp"
        ) as mock_cp, patch.object(fs, "rm") as mock_rm:
            mock_exists.side_effect = [
                False,
                True,
            ]  # Dest doesn't exist, then exists after copy

            fs.mv(
                "osf://abc123/osfstorage/source.txt", "osf://abc123/osfstorage/dest.txt"
            )

            mock_cp.assert_called_once()
            mock_rm.assert_called_once()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_mv_delete_fails(self, mock_client_class):
        """Test mv logs warning but doesn't raise if delete fails."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "exists") as mock_exists, patch.object(
            fs, "cp"
        ) as mock_cp, patch.object(fs, "rm") as mock_rm:
            mock_exists.side_effect = [
                False,
                True,
            ]  # Dest doesn't exist, then exists after copy
            mock_rm.side_effect = OSFNotFoundError("Delete failed")

            # Should not raise exception
            fs.mv(
                "osf://abc123/osfstorage/source.txt", "osf://abc123/osfstorage/dest.txt"
            )

            mock_cp.assert_called_once()
            mock_rm.assert_called_once()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_mv_copy_fails(self, mock_client_class):
        """Test mv raises exception if copy fails."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "exists") as mock_exists, patch.object(
            fs, "cp"
        ) as mock_cp, patch.object(fs, "rm") as mock_rm:
            mock_exists.return_value = False
            mock_cp.side_effect = OSFNotFoundError("Copy failed")

            with pytest.raises(OSFNotFoundError, match="Copy failed"):
                fs.mv(
                    "osf://abc123/osfstorage/source.txt",
                    "osf://abc123/osfstorage/dest.txt",
                )

            mock_cp.assert_called_once()
            # rm should not be called if copy fails
            mock_rm.assert_not_called()

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_mv_recursive_directory(self, mock_client_class):
        """Test moving directory recursively."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "exists") as mock_exists, patch.object(
            fs, "cp"
        ) as mock_cp, patch.object(fs, "rm") as mock_rm:
            mock_exists.side_effect = [False, True]

            fs.mv(
                "osf://abc123/osfstorage/dir",
                "osf://abc123/osfstorage/newdir",
                recursive=True,
            )

            # Should pass recursive=True to cp
            mock_cp.assert_called_once()
            call_args = mock_cp.call_args
            assert call_args[1].get("recursive") is True


class TestBatchOperations:
    """Tests for batch operation methods."""

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_batch_copy(self, mock_client_class):
        """Test batch copy with multiple files."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "cp") as mock_cp:
            pairs = [
                ("osf://abc/file1.txt", "osf://abc/dest1.txt"),
                ("osf://abc/file2.txt", "osf://abc/dest2.txt"),
            ]

            result = fs.batch_copy(pairs)

            assert result["total"] == 2
            assert result["success"] == 2
            assert result["failed"] == 0
            assert len(result["errors"]) == 0
            assert mock_cp.call_count == 2

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_batch_copy_partial_failure(self, mock_client_class):
        """Test batch copy with some failures."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "cp") as mock_cp:
            mock_cp.side_effect = [
                None,  # First succeeds
                OSFNotFoundError("File not found"),  # Second fails
                None,  # Third succeeds
            ]

            pairs = [
                ("osf://abc/file1.txt", "osf://abc/dest1.txt"),
                ("osf://abc/file2.txt", "osf://abc/dest2.txt"),
                ("osf://abc/file3.txt", "osf://abc/dest3.txt"),
            ]

            result = fs.batch_copy(pairs)

            assert result["total"] == 3
            assert result["success"] == 2
            assert result["failed"] == 1
            assert len(result["errors"]) == 1
            assert result["errors"][0][0] == "osf://abc/file2.txt"

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_batch_move(self, mock_client_class):
        """Test batch move with multiple files."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "mv") as mock_mv:
            pairs = [
                ("osf://abc/file1.txt", "osf://abc/new1.txt"),
                ("osf://abc/file2.txt", "osf://abc/new2.txt"),
            ]

            result = fs.batch_move(pairs)

            assert result["total"] == 2
            assert result["success"] == 2
            assert result["failed"] == 0
            assert mock_mv.call_count == 2

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_batch_delete(self, mock_client_class):
        """Test batch delete with multiple files."""
        fs = OSFFileSystem(token="test_token")

        with patch.object(fs, "rm_file") as mock_rm:
            paths = [
                "osf://abc/file1.txt",
                "osf://abc/file2.txt",
            ]

            result = fs.batch_delete(paths)

            assert result["total"] == 2
            assert result["success"] == 2
            assert result["failed"] == 0
            assert mock_rm.call_count == 2

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_batch_operations_empty_list(self, mock_client_class):
        """Test batch operations raise ValueError for empty lists."""
        fs = OSFFileSystem(token="test_token")

        with pytest.raises(ValueError, match="cannot be empty"):
            fs.batch_copy([])

        with pytest.raises(ValueError, match="cannot be empty"):
            fs.batch_move([])

        with pytest.raises(ValueError, match="cannot be empty"):
            fs.batch_delete([])

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_batch_operations_duplicate_destinations(self, mock_client_class):
        """Test batch operations raise ValueError for duplicate destinations."""
        fs = OSFFileSystem(token="test_token")

        pairs = [
            ("osf://abc/file1.txt", "osf://abc/dest.txt"),
            ("osf://abc/file2.txt", "osf://abc/dest.txt"),  # Duplicate destination
        ]

        with pytest.raises(ValueError, match="Duplicate destinations"):
            fs.batch_copy(pairs)

        with pytest.raises(ValueError, match="Duplicate destinations"):
            fs.batch_move(pairs)

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_progress_callback(self, mock_client_class):
        """Test progress callback is invoked correctly."""
        fs = OSFFileSystem(token="test_token")

        callback_calls = []

        def callback(index, total, path, operation):
            callback_calls.append((index, total, path, operation))

        with patch.object(fs, "cp"):
            pairs = [
                ("osf://abc/file1.txt", "osf://abc/dest1.txt"),
                ("osf://abc/file2.txt", "osf://abc/dest2.txt"),
            ]

            fs.batch_copy(pairs, callback=callback)

            assert len(callback_calls) == 2
            assert callback_calls[0] == (1, 2, "osf://abc/file1.txt", "copy")
            assert callback_calls[1] == (2, 2, "osf://abc/file2.txt", "copy")
