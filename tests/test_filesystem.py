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
    def test_open_write_raises(self, mock_client_class):
        """Test that write mode raises NotImplementedError."""
        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")

        with pytest.raises(
            NotImplementedError, match="Write operations not yet supported"
        ):
            fs.open("file.csv", mode="wb")

    @patch("dvc_osf.filesystem.OSFAPIClient")
    def test_open_append_raises(self, mock_client_class):
        """Test that append mode raises NotImplementedError."""
        fs = OSFFileSystem("osf://abc123/osfstorage", token="test_token")

        with pytest.raises(
            NotImplementedError, match="Write operations not yet supported"
        ):
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
