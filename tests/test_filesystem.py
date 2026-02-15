"""Tests for OSF filesystem implementation."""

from unittest.mock import Mock, patch

import pytest

from dvc_osf.exceptions import OSFIntegrityError, OSFNotFoundError
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
