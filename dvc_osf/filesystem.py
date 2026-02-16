"""OSF filesystem implementation for DVC."""

import hashlib
import io
import logging
import os
import tempfile
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Union

import requests
from dvc_objects.fs.base import ObjectFileSystem

from .api import OSFAPIClient
from .auth import get_token
from .config import Config
from .exceptions import (
    OSFIntegrityError,
    OSFNotFoundError,
    OSFConflictError,
    OSFOperationNotSupportedError,
)
from .utils import (
    compute_upload_checksum,
    determine_upload_strategy,
    get_directory,
    get_file_size,
    get_filename,
    normalize_path,
    parse_osf_url,
    path_to_api_url,
    serialize_path,
)

logger = logging.getLogger(__name__)


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


class OSFWriteFile(io.IOBase):
    """
    File-like object for writing to OSF files.

    Buffers data and uploads on close or explicit flush.
    Supports both binary and text write modes.
    """

    def __init__(
        self,
        api_client: OSFAPIClient,
        upload_url: str,
        mode: str = "wb",
        chunk_size: Optional[int] = None,
    ) -> None:
        """
        Initialize OSF write file wrapper.

        Args:
            api_client: OSF API client instance
            upload_url: URL for uploading the file
            mode: File mode ('wb' for binary, 'w' for text)
            chunk_size: Chunk size for uploads (defaults to Config.OSF_UPLOAD_CHUNK_SIZE)
        """
        self.api_client = api_client
        self.upload_url = upload_url
        self.mode = mode
        self.chunk_size = chunk_size or Config.OSF_UPLOAD_CHUNK_SIZE
        self._buffer = io.BytesIO()
        self._closed = False
        self._bytes_written = 0

    def write(self, data: Union[bytes, str]) -> int:
        """
        Write data to the file buffer.

        Args:
            data: Data to write (bytes if binary mode, str if text mode)

        Returns:
            Number of bytes/characters written

        Raises:
            ValueError: If file is closed or mode mismatch
        """
        if self._closed:
            raise ValueError("I/O operation on closed file")

        # Convert text to bytes if needed
        if isinstance(data, str):
            if "b" in self.mode:
                raise TypeError("a bytes-like object is required, not 'str'")
            data_bytes = data.encode("utf-8")
        else:
            if "b" not in self.mode:
                raise TypeError("write() argument must be str, not 'bytes'")
            data_bytes = data

        # Write to buffer
        bytes_written = self._buffer.write(data_bytes)
        self._bytes_written += bytes_written

        return len(data) if isinstance(data, str) else bytes_written

    def flush(self) -> None:
        """Flush buffer (no-op, upload happens on close)."""
        pass

    def close(self) -> None:
        """Close file and upload buffered data."""
        if self._closed:
            return

        try:
            # Get buffered data
            self._buffer.seek(0)
            file_data = self._buffer.read()

            if file_data:
                # Upload the data
                self.api_client.upload_file(
                    self.upload_url,
                    io.BytesIO(file_data),
                    callback=None,
                    total_size=len(file_data),
                )
        finally:
            self._closed = True
            self._buffer.close()

    def writable(self) -> bool:
        """Check if file is writable."""
        return not self._closed

    def __enter__(self) -> "OSFWriteFile":
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

        # Get version information if available
        version = attributes.get("version")
        version_id = attributes.get("version_identifier")

        # Build full path
        if parent_path:
            full_path = f"{parent_path}/{name}"
        else:
            full_path = name

        path_str = serialize_path(project_id, provider, full_path)

        metadata = {
            "name": path_str,
            "type": "directory" if kind == "folder" else "file",
            "size": size or 0,
            "modified": modified,
            "checksum": checksum,
        }

        # Include version metadata if available
        if version is not None:
            metadata["version"] = version
        if version_id is not None:
            metadata["version_id"] = version_id

        return metadata

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

    def open(
        self, path: str, mode: str = "rb", **kwargs: Any
    ) -> Union[OSFFile, OSFWriteFile]:
        """
        Open a file on OSF.

        Args:
            path: Path to the file
            mode: File mode ('rb', 'r' for read, 'wb', 'w' for write)
            **kwargs: Additional arguments

        Returns:
            File-like object

        Raises:
            NotImplementedError: For append or read-write modes
        """
        # Check for unsupported modes
        if "a" in mode:
            raise NotImplementedError(
                "Append mode not supported. "
                "OSF does not support appending to existing files."
            )
        if "+" in mode or ("r" in mode and "w" in mode):
            raise NotImplementedError(
                "Read-write mode not supported. "
                "Use separate open() calls for reading and writing."
            )

        # Handle write modes
        if "w" in mode:
            project_id, provider, file_path = self._resolve_path(path)

            # Get upload URL using the same logic as put_file
            upload_url = self._get_upload_url(project_id, provider, file_path)

            return OSFWriteFile(self.client, upload_url, mode=mode)

        # Handle read modes (existing logic)
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

    def put_file(
        self,
        lpath: str,
        rpath: str,
        callback: Optional[Callable[[int, int], None]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Upload a local file to OSF.

        Args:
            lpath: Local file path
            rpath: Remote OSF path
            callback: Optional progress callback (bytes_uploaded, total_bytes)
            **kwargs: Additional arguments

        Raises:
            OSFIntegrityError: If checksum verification fails
            OSFQuotaExceededError: If storage quota exceeded
            Other OSF exceptions
        """
        # Validate callback if provided
        if callback is not None and not callable(callback):
            raise TypeError("callback must be callable")

        # Get file size to determine upload strategy
        file_size = os.path.getsize(lpath)
        upload_strategy = determine_upload_strategy(
            file_size, Config.OSF_UPLOAD_CHUNK_SIZE
        )

        if upload_strategy == "single":
            self._put_file_simple(lpath, rpath, callback)
        else:
            self._put_file_chunked(lpath, rpath, callback)

        # Verify checksum after upload
        self._verify_upload_checksum(lpath, rpath)

    def _put_file_simple(
        self,
        lpath: str,
        rpath: str,
        callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Upload a small file using single PUT request."""
        project_id, provider, file_path = self._resolve_path(rpath)

        # Get upload URL
        upload_url = self._get_upload_url(project_id, provider, file_path)

        # Upload file
        file_size = os.path.getsize(lpath)
        with open(lpath, "rb") as f:
            self.client.upload_file(upload_url, f, callback, file_size)

        # Invoke final callback if provided
        if callback:
            try:
                callback(file_size, file_size)
            except Exception:
                pass

    def _put_file_chunked(
        self,
        lpath: str,
        rpath: str,
        callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Upload a large file using streaming PUT (not multi-request chunking).

        Note: OSF doesn't support true multi-request chunked uploads. Instead,
        we stream the file in a single PUT request for memory efficiency.
        """
        project_id, provider, file_path = self._resolve_path(rpath)

        # Get upload URL
        upload_url = self._get_upload_url(project_id, provider, file_path)

        # Get file size
        file_size = os.path.getsize(lpath)

        # Upload file with streaming for memory efficiency
        with open(lpath, "rb") as f:
            self.client.upload_file(upload_url, f, callback, file_size)

    def _get_upload_url(self, project_id: str, provider: str, file_path: str) -> str:
        """Get upload URL for a file (existing or new)."""
        parent_path = get_directory(file_path)
        filename = get_filename(file_path)

        # List parent directory to check if file exists
        parent_api_url = path_to_api_url(project_id, provider, parent_path)
        try:
            response = self.client.get(parent_api_url)
            data = response.json()

            # Check if file exists
            if "data" in data:
                items = data["data"]
                for item in items:
                    item_name = item.get("attributes", {}).get("name", "")
                    if item_name == filename:
                        # File exists, return its upload URL from links
                        links = item.get("links", {})
                        upload_url = links.get("upload")
                        if upload_url:
                            return upload_url
        except OSFNotFoundError:
            # Parent directory doesn't exist - that's okay for new files
            # OSF will create directories implicitly when we upload
            pass

        # File doesn't exist, construct WaterButler upload URL for new files
        # Format: https://files.osf.io/v1/resources/{project}/providers/{provider}/{path}?kind=file
        base_url = (
            f"https://files.osf.io/v1/resources/{project_id}/providers/{provider}"
        )
        if parent_path:
            waterbutler_url = f"{base_url}/{parent_path}/?kind=file&name={filename}"
        else:
            waterbutler_url = f"{base_url}/?kind=file&name={filename}"

        return waterbutler_url

    def _verify_upload_checksum(self, lpath: str, rpath: str) -> None:
        """Verify uploaded file checksum matches local file."""
        # Compute local checksum
        with open(lpath, "rb") as f:
            local_checksum = compute_upload_checksum(f)

        # Get remote file info
        remote_info = self.info(rpath)
        remote_checksum = remote_info.get("checksum")

        if remote_checksum and local_checksum != remote_checksum:
            raise OSFIntegrityError(
                f"Checksum mismatch after upload for {rpath}: "
                f"expected {local_checksum}, got {remote_checksum}",
                expected_checksum=local_checksum,
                actual_checksum=remote_checksum,
            )

    def put(
        self,
        file_obj: BinaryIO,
        rpath: str,
        callback: Optional[Callable[[int, int], None]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Upload a file-like object to OSF.

        Args:
            file_obj: File-like object to upload
            rpath: Remote OSF path
            callback: Optional progress callback (bytes_uploaded, total_bytes)
            **kwargs: Additional arguments
        """
        # Validate callback if provided
        if callback is not None and not callable(callback):
            raise TypeError("callback must be callable")

        project_id, provider, file_path = self._resolve_path(rpath)

        # Get upload URL
        upload_url = self._get_upload_url(project_id, provider, file_path)

        # Try to get file size
        try:
            file_size = get_file_size(file_obj)
        except (AttributeError, OSError):
            # File object doesn't support size - read into memory
            data = file_obj.read()
            file_size = len(data)
            file_obj = io.BytesIO(data)

        # Upload
        self.client.upload_file(upload_url, file_obj, callback, file_size)

    def cp(
        self,
        path1: str,
        path2: str,
        recursive: bool = False,
        overwrite: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Copy a file or directory within OSF storage.

        Uses download-then-upload strategy for reliability. Verifies checksums
        to ensure data integrity.

        Args:
            path1: Source path
            path2: Destination path
            recursive: If True, copy directories recursively
            overwrite: If True, overwrite existing destination (default: True)
            **kwargs: Additional arguments

        Raises:
            OSFNotFoundError: If source doesn't exist
            OSFConflictError: If destination exists and overwrite=False
            OSFOperationNotSupportedError: For cross-project or cross-provider copies
            OSFIntegrityError: If checksum verification fails

        Example:
            >>> fs.cp("osf://abc123/data.csv", "osf://abc123/backup/data.csv")
        """
        logger.info(f"Copying {path1} to {path2}")

        # Resolve and validate paths
        src_project, src_provider, src_path = self._resolve_path(path1)
        dst_project, dst_provider, dst_path = self._resolve_path(path2)

        # Validate same project and provider
        if src_project != dst_project:
            raise OSFOperationNotSupportedError(
                f"Cross-project copy not supported: {src_project} -> {dst_project}",
                operation="copy",
            )
        if src_provider != dst_provider:
            raise OSFOperationNotSupportedError(
                f"Cross-provider copy not supported: {src_provider} -> {dst_provider}",
                operation="copy",
            )

        # Get source info
        try:
            src_info = self.info(path1)
        except OSFNotFoundError:
            raise OSFNotFoundError(f"Source not found: {path1}")

        # Handle directory copy
        if src_info["type"] == "directory":
            if not recursive:
                raise OSFOperationNotSupportedError(
                    f"Cannot copy directory without recursive=True: {path1}",
                    operation="copy",
                )

            # List source directory contents
            items = self.ls(path1, detail=True)
            logger.debug(f"Recursively copying {len(items)} items from {path1}")

            for item in items:
                item_name = item["name"]
                # Build destination path
                rel_path = item_name[
                    len(serialize_path(src_project, src_provider, src_path)) :
                ]
                if rel_path.startswith("/"):
                    rel_path = rel_path[1:]
                dest_item = serialize_path(dst_project, dst_provider, dst_path)
                if rel_path:
                    dest_item = f"{dest_item}/{rel_path}"

                # Recursively copy
                self.cp(item_name, dest_item, recursive=True, overwrite=overwrite)

            logger.info(f"Completed recursive copy of {path1} to {path2}")
            return

        # Single file copy
        # Check destination
        if not overwrite and self.exists(path2):
            raise OSFConflictError(f"Destination exists: {path2}")

        # Create temp file for download
        temp_fd, temp_path = tempfile.mkstemp(prefix="dvc_osf_copy_")
        try:
            # Close the file descriptor as we'll open it properly
            os.close(temp_fd)

            # Download source to temp file
            logger.debug(f"Downloading {path1} to temp file")
            self.get_file(path1, temp_path)

            # Upload temp file to destination
            logger.debug(f"Uploading temp file to {path2}")
            self.put_file(temp_path, path2)

            # Verify checksums match
            src_checksum = src_info.get("checksum")
            if src_checksum:
                dst_info = self.info(path2)
                dst_checksum = dst_info.get("checksum")
                if dst_checksum and src_checksum != dst_checksum:
                    raise OSFIntegrityError(
                        f"Checksum mismatch after copy: {path1} -> {path2}",
                        expected_checksum=src_checksum,
                        actual_checksum=dst_checksum,
                    )

            logger.info(f"Successfully copied {path1} to {path2}")

        finally:
            # Clean up temp file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_path}: {e}")

    def mv(
        self,
        path1: str,
        path2: str,
        recursive: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Move or rename a file or directory within OSF storage.

        Implements move as copy-then-delete for reliability. Not fully atomic,
        but prioritizes data safety (file may be duplicated if delete fails,
        but will not be lost).

        Args:
            path1: Source path
            path2: Destination path
            recursive: If True, move directories recursively
            **kwargs: Additional arguments

        Raises:
            OSFNotFoundError: If source doesn't exist
            OSFConflictError: If destination already exists
            OSFOperationNotSupportedError: For cross-project or cross-provider moves

        Note:
            Move is not atomic. If the delete operation fails after a successful
            copy, a warning will be logged but no exception will be raised,
            leaving the source file in place (orphaned copy).

        Example:
            >>> fs.mv("osf://abc123/old.csv", "osf://abc123/new.csv")
        """
        logger.info(f"Moving {path1} to {path2}")

        # Resolve and validate paths
        src_project, src_provider, src_path = self._resolve_path(path1)
        dst_project, dst_provider, dst_path = self._resolve_path(path2)

        # Validate same project and provider
        if src_project != dst_project:
            raise OSFOperationNotSupportedError(
                f"Cross-project move not supported: {src_project} -> {dst_project}",
                operation="move",
            )
        if src_provider != dst_provider:
            raise OSFOperationNotSupportedError(
                f"Cross-provider move not supported: {src_provider} -> {dst_provider}",
                operation="move",
            )

        # Check if destination exists
        if self.exists(path2):
            raise OSFConflictError(f"Destination exists: {path2}")

        # Copy source to destination
        try:
            self.cp(path1, path2, recursive=recursive, overwrite=False)
        except Exception as e:
            logger.error(f"Copy failed during move operation: {e}")
            raise

        # Verify copy succeeded
        if not self.exists(path2):
            raise OSFIntegrityError(
                f"Move failed: destination not found after copy: {path2}"
            )

        # Delete source
        # If delete fails, log warning but don't raise exception
        # (copy succeeded, so file is safely at destination)
        try:
            self.rm(path1, recursive=recursive)
            logger.info(f"Successfully moved {path1} to {path2}")
        except Exception as e:
            logger.warning(
                f"Move completed but source deletion failed: {path1}. "
                f"File successfully copied to {path2} but source remains. "
                f"Error: {e}"
            )

    def batch_copy(
        self,
        path_pairs: List[tuple[str, str]],
        overwrite: bool = True,
        callback: Optional[Callable[[int, int, str, str], None]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Copy multiple files in batch.

        Collects errors without failing early, allowing partial success.

        Args:
            path_pairs: List of (source, destination) path tuples
            overwrite: If True, overwrite existing destinations
            callback: Optional progress callback (index, total, path, operation)
            **kwargs: Additional arguments

        Returns:
            Summary dictionary with keys:
                - total: Total number of operations
                - success: Number of successful copies
                - failed: Number of failed copies
                - errors: List of (source, dest, error) tuples

        Raises:
            ValueError: If path_pairs is empty or contains duplicate destinations

        Example:
            >>> result = fs.batch_copy([
            ...     ("osf://abc/a.txt", "osf://abc/backup/a.txt"),
            ...     ("osf://abc/b.txt", "osf://abc/backup/b.txt"),
            ... ])
            >>> print(f"Copied {result['success']}/{result['total']} files")
        """
        # Validate input
        if not path_pairs:
            raise ValueError("path_pairs cannot be empty")

        # Check for duplicate destinations
        destinations = [dst for _, dst in path_pairs]
        if len(destinations) != len(set(destinations)):
            raise ValueError("Duplicate destinations not allowed")

        logger.info(f"Starting batch copy of {len(path_pairs)} files")

        total = len(path_pairs)
        success = 0
        failed = 0
        errors = []

        for i, (src, dst) in enumerate(path_pairs):
            try:
                self.cp(src, dst, overwrite=overwrite)
                success += 1
                logger.debug(f"Batch copy [{i + 1}/{total}]: {src} -> {dst} SUCCESS")
            except Exception as e:
                failed += 1
                errors.append((src, dst, str(e)))
                logger.warning(
                    f"Batch copy [{i + 1}/{total}]: {src} -> {dst} FAILED: {e}"
                )

            # Invoke callback if provided
            if callback:
                try:
                    callback(i + 1, total, src, "copy")
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        result = {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors,
        }

        logger.info(
            f"Batch copy completed: {success} succeeded, {failed} failed out of {total}"
        )

        return result

    def batch_move(
        self,
        path_pairs: List[tuple[str, str]],
        callback: Optional[Callable[[int, int, str, str], None]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Move multiple files in batch.

        Collects errors without failing early, allowing partial success.

        Args:
            path_pairs: List of (source, destination) path tuples
            callback: Optional progress callback (index, total, path, operation)
            **kwargs: Additional arguments

        Returns:
            Summary dictionary with keys:
                - total: Total number of operations
                - success: Number of successful moves
                - failed: Number of failed moves
                - errors: List of (source, dest, error) tuples

        Raises:
            ValueError: If path_pairs is empty or contains duplicate destinations

        Example:
            >>> result = fs.batch_move([
            ...     ("osf://abc/old1.txt", "osf://abc/new1.txt"),
            ...     ("osf://abc/old2.txt", "osf://abc/new2.txt"),
            ... ])
        """
        # Validate input
        if not path_pairs:
            raise ValueError("path_pairs cannot be empty")

        # Check for duplicate destinations
        destinations = [dst for _, dst in path_pairs]
        if len(destinations) != len(set(destinations)):
            raise ValueError("Duplicate destinations not allowed")

        logger.info(f"Starting batch move of {len(path_pairs)} files")

        total = len(path_pairs)
        success = 0
        failed = 0
        errors = []

        for i, (src, dst) in enumerate(path_pairs):
            try:
                self.mv(src, dst)
                success += 1
                logger.debug(f"Batch move [{i + 1}/{total}]: {src} -> {dst} SUCCESS")
            except Exception as e:
                failed += 1
                errors.append((src, dst, str(e)))
                logger.warning(
                    f"Batch move [{i + 1}/{total}]: {src} -> {dst} FAILED: {e}"
                )

            # Invoke callback if provided
            if callback:
                try:
                    callback(i + 1, total, src, "move")
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        result = {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors,
        }

        logger.info(
            f"Batch move completed: {success} succeeded, {failed} failed out of {total}"
        )

        return result

    def batch_delete(
        self,
        paths: List[str],
        callback: Optional[Callable[[int, int, str, str], None]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Delete multiple files in batch.

        Collects errors without failing early, allowing partial success.

        Args:
            paths: List of file paths to delete
            callback: Optional progress callback (index, total, path, operation)
            **kwargs: Additional arguments

        Returns:
            Summary dictionary with keys:
                - total: Total number of operations
                - success: Number of successful deletes
                - failed: Number of failed deletes
                - errors: List of (path, error) tuples

        Raises:
            ValueError: If paths is empty

        Example:
            >>> result = fs.batch_delete([
            ...     "osf://abc/temp1.txt",
            ...     "osf://abc/temp2.txt",
            ... ])
        """
        # Validate input
        if not paths:
            raise ValueError("paths cannot be empty")

        logger.info(f"Starting batch delete of {len(paths)} files")

        total = len(paths)
        success = 0
        failed = 0
        errors = []

        for i, path in enumerate(paths):
            try:
                self.rm_file(path)
                success += 1
                logger.debug(f"Batch delete [{i + 1}/{total}]: {path} SUCCESS")
            except Exception as e:
                failed += 1
                errors.append((path, str(e)))
                logger.warning(f"Batch delete [{i + 1}/{total}]: {path} FAILED: {e}")

            # Invoke callback if provided
            if callback:
                try:
                    callback(i + 1, total, path, "delete")
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        result = {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors,
        }

        logger.info(
            f"Batch delete completed: {success} succeeded, {failed} failed out of {total}"
        )

        return result

    def mkdir(self, path: str, create_parents: bool = True, **kwargs: Any) -> None:
        """
        Create a directory (no-op on OSF - directories are virtual).

        Args:
            path: Directory path
            create_parents: Ignored (OSF creates implicitly)
            **kwargs: Additional arguments
        """
        # OSF doesn't have real directories - they're inferred from file paths
        # This is a no-op that always succeeds
        pass

    def rm(self, path: str, recursive: bool = False, **kwargs: Any) -> None:
        """
        Delete a file or directory from OSF.

        Args:
            path: Path to delete
            recursive: If True, delete directory contents recursively
            **kwargs: Additional arguments

        Raises:
            OSFNotFoundError: If path doesn't exist
        """
        # Check if path exists and get its type
        try:
            info = self.info(path)
        except OSFNotFoundError:
            # Path doesn't exist - that's okay for delete
            return

        if info["type"] == "directory":
            if recursive:
                # List and delete all files in directory
                items = self.ls(path, detail=True)
                for item in items:
                    self.rm(item["name"], recursive=True)
            # OSF directories are virtual - nothing to delete
            return

        # Delete file
        project_id, provider, file_path = self._resolve_path(path)
        parent_path = get_directory(file_path)
        filename = get_filename(file_path)

        # Get file's delete URL
        parent_api_url = path_to_api_url(project_id, provider, parent_path)
        response = self.client.get(parent_api_url)
        data = response.json()

        if "data" in data:
            items = data["data"]
            for item in items:
                item_name = item.get("attributes", {}).get("name", "")
                if item_name == filename:
                    # Found file, get delete URL
                    links = item.get("links", {})
                    delete_url = links.get("delete") or links.get("upload")
                    if delete_url:
                        self.client.delete(delete_url)
                    return

        raise OSFNotFoundError(f"File not found: {path}")

    def rm_file(self, path: str, **kwargs: Any) -> None:
        """
        Delete a single file.

        Args:
            path: File path
            **kwargs: Additional arguments
        """
        self.rm(path, recursive=False, **kwargs)

    def rmdir(self, path: str, **kwargs: Any) -> None:
        """
        Remove a directory (no-op on OSF - directories are virtual).

        Args:
            path: Directory path
            **kwargs: Additional arguments
        """
        # OSF directories are virtual - this is a no-op
        pass
