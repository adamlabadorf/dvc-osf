"""OSF filesystem implementation for DVC."""

import hashlib
import io
import os
from typing import Any, Dict, List, Optional, Union

import requests
from dvc_objects.fs.base import ObjectFileSystem

from .api import OSFAPIClient
from .auth import get_token
from .config import Config
from .exceptions import OSFIntegrityError, OSFNotFoundError
from .utils import (
    get_directory,
    get_filename,
    normalize_path,
    parse_osf_url,
    path_to_api_url,
    serialize_path,
)


class OSFFile(io.IOBase):
    """
    File-like object for reading OSF files with streaming support.

    Supports reading in both binary and text modes, with limited seeking
    (forward seeks only) and position tracking.
    """

    def __init__(
        self,
        response: requests.Response,
        mode: str = "rb",
        chunk_size: Optional[int] = None,
    ) -> None:
        """
        Initialize OSF file wrapper.

        Args:
            response: Streaming HTTP response from OSF API
            mode: File mode ('rb' for binary, 'r' for text)
            chunk_size: Chunk size for reading (defaults to Config.CHUNK_SIZE)
        """
        self.response = response
        self.mode = mode
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self._position = 0
        self._closed = False
        self._iterator = response.iter_content(chunk_size=self.chunk_size)
        self._buffer = b""

    def read(self, size: int = -1) -> Union[bytes, str]:
        """
        Read bytes or characters from the file.

        Args:
            size: Number of bytes/chars to read (-1 for all)

        Returns:
            Bytes if binary mode, str if text mode
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")

        if size == 0:
            return b"" if "b" in self.mode else ""

        chunks = []
        bytes_read = 0

        try:
            if size < 0:
                # Read all remaining data
                if self._buffer:
                    chunks.append(self._buffer)
                    bytes_read += len(self._buffer)
                    self._buffer = b""

                for chunk in self._iterator:
                    chunks.append(chunk)
                    bytes_read += len(chunk)
            else:
                # Read specific number of bytes
                while bytes_read < size:
                    if not self._buffer:
                        try:
                            self._buffer = next(self._iterator)
                        except StopIteration:
                            break

                    needed = size - bytes_read
                    chunk = self._buffer[:needed]
                    self._buffer = self._buffer[needed:]

                    chunks.append(chunk)
                    bytes_read += len(chunk)

        except Exception:
            self.close()
            raise

        data = b"".join(chunks)
        self._position += len(data)

        if "b" in self.mode:
            return data
        else:
            return data.decode("utf-8")

    def readline(self, size: int = -1) -> Union[bytes, str]:
        """
        Read a single line from the file.

        Args:
            size: Maximum number of bytes/chars to read

        Returns:
            Line as bytes or str
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")

        # Simple implementation: read chunks until we find a newline
        line_parts = []
        bytes_read = 0

        while True:
            if size > 0 and bytes_read >= size:
                break

            chunk = self.read(self.chunk_size)
            if not chunk:
                break

            # Look for newline
            if "b" in self.mode:
                newline_pos = chunk.find(b"\n")
            else:
                newline_pos = chunk.find("\n")

            if newline_pos >= 0:
                # Found newline - include it and stop
                line_parts.append(chunk[: newline_pos + 1])
                # Put the rest back in the buffer
                remaining = chunk[newline_pos + 1 :]
                if "b" in self.mode:
                    self._buffer = remaining.encode("utf-8") + self._buffer
                    self._position -= len(remaining.encode("utf-8"))
                else:
                    self._buffer = remaining.encode("utf-8") + self._buffer
                    self._position -= len(remaining)
                break
            else:
                line_parts.append(chunk)
                bytes_read += len(chunk)

        if "b" in self.mode:
            return b"".join(line_parts)  # type: ignore
        else:
            return "".join(line_parts)  # type: ignore

    def __iter__(self) -> "OSFFile":
        """Return iterator for line-by-line reading."""
        return self

    def __next__(self) -> Union[bytes, str]:
        """Read next line when iterating."""
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def seek(self, offset: int, whence: int = 0) -> int:
        """
        Seek to a position in the file (limited support).

        Only supports forward seeks (reading and discarding data).

        Args:
            offset: Position offset
            whence: Reference point (0=start, 1=current, 2=end)

        Returns:
            New position

        Raises:
            OSError: If backward seek is attempted
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")

        if whence == 0:
            # Seek from start
            if offset < self._position:
                raise OSError("Backward seeks not supported on streaming files")
            skip = offset - self._position
        elif whence == 1:
            # Seek from current
            if offset < 0:
                raise OSError("Backward seeks not supported on streaming files")
            skip = offset
        else:
            raise OSError("Seeking from end not supported on streaming files")

        # Read and discard data to simulate seek
        while skip > 0:
            chunk_size = min(skip, self.chunk_size)
            data = self.read(chunk_size)
            if not data:
                break
            skip -= len(data)

        return self._position

    def tell(self) -> int:
        """
        Get current position in file.

        Returns:
            Current byte position
        """
        return self._position

    def close(self) -> None:
        """Close the file and release response resources."""
        if not self._closed:
            self._closed = True
            if self.response:
                self.response.close()

    def __enter__(self) -> "OSFFile":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    @property
    def closed(self) -> bool:
        """Check if file is closed."""
        return self._closed


class OSFFileSystem(ObjectFileSystem):
    """
    Filesystem interface for Open Science Framework (OSF) storage.

    This class implements the DVC filesystem protocol for OSF,
    allowing DVC to use OSF as a remote storage backend. Supports
    read-only operations for Phase 1.
    """

    protocol = "osf"
    REQUIRES = {"requests": "requests"}

    def __init__(
        self,
        *args: Any,
        token: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize OSF filesystem.

        Can be initialized with an osf:// URL or explicit parameters.

        Args:
            *args: Positional arguments (may include osf:// URL)
            token: OSF personal access token for authentication
            **kwargs: Additional arguments (may include fs_args, host, etc.)
        """
        super().__init__(*args, **kwargs)

        # Extract URL from args if present
        url = None
        if args and isinstance(args[0], str) and args[0].startswith("osf://"):
            url = args[0]
        elif "host" in kwargs and kwargs["host"]:
            # Reconstruct URL from host
            url = f"osf://{kwargs['host']}"

        # Parse URL to get project_id, provider, base_path
        if url:
            self.project_id, self.provider, self.base_path = parse_osf_url(url)
        else:
            # No URL provided - will fail, but let's set defaults
            self.project_id = ""
            self.provider = Config.DEFAULT_PROVIDER
            self.base_path = ""

        # Get authentication token
        fs_args = kwargs.get("fs_args", {})
        token_to_use = token or fs_args.get("token")

        self.token = get_token(token=token_to_use, dvc_config=fs_args)

        # Initialize API client
        self.client = OSFAPIClient(token=self.token)

    def _resolve_path(self, path: str) -> tuple[str, str, str]:
        """
        Resolve a path to (project_id, provider, path) tuple.

        Args:
            path: Path to resolve (relative to base_path)

        Returns:
            Tuple of (project_id, provider, full_path)
        """
        # Remove protocol prefix if present
        path = self._strip_protocol(path)

        # If path starts with project ID, parse it
        if "/" in path:
            first_part = path.split("/")[0]
            # Check if it looks like a project ID
            if (
                len(first_part) >= Config.MIN_PROJECT_ID_LENGTH
                and first_part.replace("_", "").replace("-", "").isalnum()
            ):
                # This is a full osf:// path, parse it
                project_id, provider, file_path = parse_osf_url(f"osf://{path}")
                return project_id, provider, file_path

        # Relative path - use instance's project and provider
        if self.base_path:
            full_path = normalize_path(f"{self.base_path}/{path}")
        else:
            full_path = normalize_path(path)

        return self.project_id, self.provider, full_path

    @staticmethod
    def _strip_protocol(path: str) -> str:
        """
        Remove osf:// protocol prefix from path.

        Args:
            path: Path that may have osf:// prefix

        Returns:
            Path without protocol prefix
        """
        if path.startswith("osf://"):
            return path[6:]
        return path

    def exists(self, path: str, **kwargs: Any) -> bool:
        """
        Check if a path exists on OSF.

        Args:
            path: Path to check
            **kwargs: Additional arguments

        Returns:
            True if path exists, False otherwise
        """
        try:
            self.info(path)
            return True
        except OSFNotFoundError:
            return False

    def ls(
        self, path: str, detail: bool = False, **kwargs: Any
    ) -> Union[List[str], List[Dict[str, Any]]]:
        """
        List contents of a directory on OSF.

        Args:
            path: Directory path
            detail: If True, return detailed info for each entry
            **kwargs: Additional arguments

        Returns:
            List of paths (if detail=False) or list of info dicts (if detail=True)
        """
        project_id, provider, file_path = self._resolve_path(path)

        # Build API URL
        api_url = path_to_api_url(project_id, provider, file_path)

        # Fetch directory listing (paginated)
        items = []
        for item in self.client.get_paginated(api_url):
            items.append(item)

        if not detail:
            # Return just paths/names
            return [
                self._build_path(project_id, provider, file_path, item)
                for item in items
            ]
        else:
            # Return detailed metadata
            return [
                self._parse_metadata(project_id, provider, file_path, item)
                for item in items
            ]

    def _build_path(
        self, project_id: str, provider: str, parent_path: str, item: Dict[str, Any]
    ) -> str:
        """
        Build a full path from API response item.

        Args:
            project_id: OSF project ID
            provider: Storage provider
            parent_path: Parent directory path
            item: API response item

        Returns:
            Full path string
        """
        # Extract name from item
        name = item.get("attributes", {}).get("name", "")

        if parent_path:
            full_path = f"{parent_path}/{name}"
        else:
            full_path = name

        return serialize_path(project_id, provider, full_path)

    def _parse_metadata(
        self, project_id: str, provider: str, parent_path: str, item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse OSF API response item into filesystem metadata.

        Args:
            project_id: OSF project ID
            provider: Storage provider
            parent_path: Parent directory path
            item: API response item

        Returns:
            Metadata dictionary
        """
        attributes = item.get("attributes", {})

        name = attributes.get("name", "")
        kind = attributes.get("kind", "file")
        size = attributes.get("size")
        modified = attributes.get("date_modified")

        # Get checksum (MD5)
        extra = attributes.get("extra", {})
        hashes = extra.get("hashes", {})
        checksum = hashes.get("md5")

        # Build full path
        if parent_path:
            full_path = f"{parent_path}/{name}"
        else:
            full_path = name

        path_str = serialize_path(project_id, provider, full_path)

        return {
            "name": path_str,
            "type": "directory" if kind == "folder" else "file",
            "size": size or 0,
            "modified": modified,
            "checksum": checksum,
        }

    def info(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Get information about a file or directory.

        Args:
            path: Path to query
            **kwargs: Additional arguments

        Returns:
            Dictionary with file/directory metadata
        """
        project_id, provider, file_path = self._resolve_path(path)

        # For empty path (root directory), list it
        if not file_path:
            # Return info for root directory
            return {
                "name": serialize_path(project_id, provider, ""),
                "type": "directory",
                "size": 0,
                "modified": None,
                "checksum": None,
            }

        # Need to search for file by listing parent directory
        # OSF API doesn't support direct file lookup by path
        parent_path = get_directory(file_path)
        filename = get_filename(file_path)

        # List parent directory
        parent_api_url = path_to_api_url(project_id, provider, parent_path)
        response = self.client.get(parent_api_url)
        data = response.json()

        # Search for file in listing
        if "data" in data:
            items = data["data"]
            for item in items:
                item_name = item.get("attributes", {}).get("name", "")
                if item_name == filename:
                    return self._parse_metadata(project_id, provider, parent_path, item)

        # File not found
        raise OSFNotFoundError(f"File not found: {path}")

    def open(self, path: str, mode: str = "rb", **kwargs: Any) -> OSFFile:
        """
        Open a file on OSF.

        Args:
            path: Path to the file
            mode: File mode ('rb' for binary read, 'r' for text read)
            **kwargs: Additional arguments

        Returns:
            File-like object

        Raises:
            NotImplementedError: For write modes
        """
        if "w" in mode or "a" in mode:
            raise NotImplementedError(
                "Write operations not yet supported. "
                "Only read operations (mode='rb' or 'r') are implemented."
            )

        # Get file info (which finds the file and gets its metadata)
        _ = self.info(path)

        # We need to get the full item to extract download URL
        # Re-query to get the full item with links
        project_id, provider, file_path = self._resolve_path(path)
        parent_path = get_directory(file_path)
        filename = get_filename(file_path)

        # List parent directory
        parent_api_url = path_to_api_url(project_id, provider, parent_path)
        response = self.client.get(parent_api_url)
        data = response.json()

        # Find file and get download URL
        download_url = None
        if "data" in data:
            items = data["data"]
            for item in items:
                item_name = item.get("attributes", {}).get("name", "")
                if item_name == filename:
                    links = item.get("links", {})
                    # Use 'upload' link which supports authentication for downloads
                    # The 'download' link goes to osf.io which doesn't support API auth
                    download_url = links.get("upload") or links.get("move")
                    break

        if not download_url:
            raise OSFNotFoundError(f"Download URL not found for path: {path}")

        # Download file with streaming
        stream_response = self.client.download_file(download_url)

        return OSFFile(stream_response, mode=mode)

    def get_file(self, rpath: str, lpath: str, **kwargs: Any) -> None:
        """
        Download a file from OSF to local path.

        Downloads with streaming, computes MD5 checksum, and verifies integrity.

        Args:
            rpath: Remote path on OSF
            lpath: Local path to save to
            **kwargs: Additional arguments

        Raises:
            OSFIntegrityError: If checksum verification fails
        """
        # Get file metadata for expected checksum
        file_info = self.info(rpath)
        expected_checksum = file_info.get("checksum")

        # Create parent directories if needed
        os.makedirs(os.path.dirname(os.path.abspath(lpath)), exist_ok=True)

        # Download and compute checksum
        md5_hash = hashlib.md5()

        with self.open(rpath, mode="rb") as remote_file:
            with open(lpath, "wb") as local_file:
                while True:
                    chunk = remote_file.read(Config.CHUNK_SIZE)
                    if not chunk:
                        break

                    local_file.write(chunk)
                    md5_hash.update(chunk)

        # Verify checksum if available
        if expected_checksum:
            actual_checksum = md5_hash.hexdigest()
            if actual_checksum != expected_checksum:
                # Remove corrupted file
                os.remove(lpath)
                raise OSFIntegrityError(
                    f"Checksum mismatch for {rpath}: "
                    f"expected {expected_checksum}, got {actual_checksum}",
                    expected_checksum=expected_checksum,
                    actual_checksum=actual_checksum,
                )
