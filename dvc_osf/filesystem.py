"""OSF filesystem implementation for DVC."""

import hashlib
import io
import logging
import os
import re
import tempfile
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Union

import requests
from dvc_objects.fs.base import ObjectFileSystem

from .api import OSFAPIClient
from .auth import get_token
from .config import Config
from .exceptions import (
    OSFConflictError,
    OSFIntegrityError,
    OSFNotFoundError,
    OSFOperationNotSupportedError,
    OSFVersionConflictError,
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

EMPTY_FILE_MD5 = "d41d8cd98f00b204e9800998ecf8427e"


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

    def readline(self, size: int = -1) -> Union[bytes, str]:  # type: ignore[override]
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
                bchunk = chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
                newline_pos = bchunk.find(b"\n")
            else:
                schunk = chunk if isinstance(chunk, str) else chunk.decode("utf-8")
                newline_pos = schunk.find("\n")

            if newline_pos >= 0:
                # Found newline - include it and stop
                line_parts.append(chunk[: newline_pos + 1])
                # Put the rest back in the buffer
                remaining = chunk[newline_pos + 1 :]
                remaining_bytes = (
                    remaining
                    if isinstance(remaining, bytes)
                    else remaining.encode("utf-8")
                )
                self._buffer = remaining_bytes + self._buffer
                if "b" in self.mode:
                    self._position -= len(remaining_bytes)
                else:
                    self._position -= len(remaining)
                break
            else:
                line_parts.append(chunk)
                bytes_read += len(chunk)

        if "b" in self.mode:
            return b"".join(line_parts)  # type: ignore
        else:
            return "".join(line_parts)  # type: ignore

    def __iter__(self) -> "OSFFile":  # type: ignore[override]
        """Return iterator for line-by-line reading."""
        return self

    def __next__(self) -> Union[bytes, str]:  # type: ignore[override]
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
            chunk_size: Chunk size for uploads (defaults to Config.OSF_UPLOAD_CHUNK_SIZE) # noqa: E501
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
    PARAM_CHECKSUM = "md5"

    # DVC md5 cache uses 2-char prefix dirs (e.g. "ab/cdef1234…").
    # The default ObjectFileSystem value is 3, which causes _estimate_remote_size
    # to return 4096 instead of 256, pushing num_pages above the threshold
    # that triggers multi-path prefix traversal — a code path that passes a
    # list of paths to find() instead of a single string.  Override to 2
    # (the correct value for md5) to stay in the simple _list_oids(None) path.
    TRAVERSE_PREFIX_LEN = 2

    # OSF uses a synchronous implementation; declare explicitly so that
    # dvc_objects._put (and other callers) don't raise AttributeError when
    # they check `fs.async_impl` on our OSFFileSystem instance directly
    # (which happens because our `fs` property returns `self`).
    async_impl = False

    # DVC config schema for OSF remotes (discovered via entry points)
    REMOTE_CONFIG = {
        "url": str,  # osf://project_id/provider/path
        "token": str,  # OSF personal access token
        "project_id": str,  # OSF project ID (can also come from URL)
        "provider": str,  # Storage provider (default: osfstorage)
        "endpoint_url": str,  # Custom OSF API endpoint (default: https://api.osf.io/v2/) # noqa: E501
    }

    def __init__(
        self,
        *args: Any,
        token: Optional[str] = None,
        project_id: Optional[str] = None,
        provider: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize OSF filesystem.

        Can be initialized with an osf:// URL or explicit parameters.

        Args:
            *args: Positional arguments (may include osf:// URL)
            token: OSF personal access token for authentication
            project_id: OSF project ID (alternative to URL)
            provider: OSF storage provider (default: osfstorage)
            endpoint_url: Custom OSF API endpoint URL
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
            self.project_id = project_id or kwargs.get("project_id", "")
            self.provider = provider or kwargs.get("provider", Config.DEFAULT_PROVIDER)
            self.base_path = ""

        # Resolve credentials via _prepare_credentials flow
        creds = self._prepare_credentials(
            token=token,
            endpoint_url=endpoint_url,
            **{k: v for k, v in kwargs.items() if k in ("token", "endpoint_url")},
        )

        self.token = get_token(
            token=creds.get("token"),
            dvc_config=kwargs.get("fs_args", {}),
        )

        # Apply custom endpoint if provided
        if creds.get("endpoint_url"):
            Config.API_BASE_URL = creds["endpoint_url"]

        # Initialize API client
        self.client = OSFAPIClient(token=self.token)

    def _prepare_credentials(self, **config: Any) -> Dict[str, Any]:
        """
        Prepare credentials for the OSF filesystem.

        Resolves token from config kwargs, then environment variables.
        Integrates with DVC's credential management flow.

        Args:
            **config: Configuration dict (may contain token, endpoint_url)

        Returns:
            Dict with resolved credentials (token, endpoint_url)
        """
        creds: Dict[str, Any] = {}

        # Token resolution: explicit config > OSF_TOKEN env > OSF_ACCESS_TOKEN env
        token = config.get("token")
        if not token:
            token = os.environ.get("OSF_TOKEN") or os.environ.get("OSF_ACCESS_TOKEN")
        if token:
            creds["token"] = token

        # Endpoint URL
        endpoint_url = config.get("endpoint_url")
        if endpoint_url:
            creds["endpoint_url"] = endpoint_url

        return creds

    @staticmethod
    def _get_kwargs_from_urls(urlpath: str) -> Dict[str, Any]:
        """
        Parse an osf:// URL into constructor kwargs.

        Used by DVC/fsspec to convert remote URLs into filesystem
        constructor parameters.

        Args:
            urlpath: OSF URL (e.g., 'osf://abc123/osfstorage/data')

        Returns:
            Dict with project_id, provider, and optionally path
        """
        project_id, provider, _ = parse_osf_url(urlpath)
        # Do NOT include 'path' here — DVC extracts fs_path separately via
        # _strip_protocol() and passes it as a positional arg to Remote.__init__.
        # Returning 'path' in this dict causes a "multiple values for argument
        # 'path'" TypeError when DVC spreads **config over the Remote call.
        return {
            "project_id": project_id,
            "provider": provider,
        }

    @property
    def fs(self):
        """Return the underlying fsspec filesystem (dvc-objects ObjectFileSystem API).

        OSFFileSystem is itself the fsspec implementation, so return self.
        """
        return self

    @fs.setter
    def fs(self, value: Any) -> None:
        """No-op setter — OSFFileSystem is its own fsspec implementation.

        fsspec's AbstractFileSystem.__init__ may attempt to set ``self.fs``
        during construction; we accept (and discard) the assignment so that
        our read-only property doesn't raise AttributeError.
        """

    def unstrip_protocol(self, path: str) -> str:
        """
        Reconstruct a full osf:// URL from an internal path.

        Args:
            path: Internal path (without protocol)

        Returns:
            Full osf:// URL
        """
        path = path.strip("/") if path else ""
        return serialize_path(self.project_id, self.provider, path)

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
    def _strip_protocol(path):
        """
        Remove osf:// protocol prefix from path.

        Accepts a single path string or a list of path strings, matching
        the fsspec AbstractFileSystem interface (DVC passes lists during push).

        Args:
            path: Path string or list of path strings

        Returns:
            Path or list of paths without osf:// prefix
        """
        if isinstance(path, list):
            return [OSFFileSystem._strip_protocol(p) for p in path]
        if path.startswith("osf://"):
            return path[6:]
        return path

    def exists(self, path: str, **kwargs: Any) -> bool:  # type: ignore[override]
        """
        Check if a path exists on OSF.

        Args:
            path: Path to check
            **kwargs: Additional arguments

        Returns:
            True if path exists, False otherwise.
            If path is a list, returns a list of booleans (dvc-objects batch API).
        """
        if isinstance(path, list):
            return [self.exists(p) for p in path]
        try:
            self.info(path)
            return True
        except OSFNotFoundError:
            return False

    def ls(  # type: ignore[override]
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

        # Navigate to the directory using IDs (required for nested paths)
        try:
            listing_url, _ = self._navigate_to_dir(
                project_id, provider, file_path, create_missing=False
            )
        except OSFNotFoundError:
            raise FileNotFoundError(f"Directory not found: {path}")

        # Fetch directory listing (paginated) using the ID-based URL
        items = list(self.client.get_paginated(listing_url))

        if not detail:
            return [
                self._build_path(project_id, provider, file_path, item)
                for item in items
            ]
        else:
            return [
                self._parse_metadata(project_id, provider, file_path, item)
                for item in items
            ]

    def walk(  # type: ignore[override]
        self,
        path: str,
        maxdepth: Optional[int] = None,
        topdown: bool = True,
        detail: bool = False,
        **kwargs: Any,
    ):
        """Walk directory tree, yielding (dirpath, dirnames, filenames) tuples.

        ``dvc ls-url`` uses ``fs.walk(path, detail=True)`` internally.  The
        default ``ObjectFileSystem.walk`` delegates to ``self.fs.walk`` where
        ``self.fs is self``, causing infinite recursion.  This override uses
        our ``ls()`` implementation directly.

        Args:
            path: Root directory path
            maxdepth: Maximum recursion depth (None = unlimited)
            topdown: Yield parent before children when True
            detail: If True, yield info dicts; otherwise yield name strings
            **kwargs: Additional arguments passed to ``ls()``
        """
        try:
            raw = self.ls(path, detail=True, **kwargs)
        except (FileNotFoundError, OSFNotFoundError):
            return
        items: List[Dict[str, Any]] = raw  # type: ignore[assignment]

        dirs: Dict[str, Any] = {}
        files: Dict[str, Any] = {}
        for item in items:
            name = item["name"].rstrip("/").rsplit("/", 1)[-1]
            if item["type"] == "directory":
                dirs[name] = item
            else:
                files[name] = item

        if topdown:
            yield path, (dirs if detail else list(dirs)), (
                files if detail else list(files)
            )

        if maxdepth is None or maxdepth > 1:
            next_depth = (maxdepth - 1) if maxdepth is not None else None
            for subdir_info in dirs.values():
                yield from self.walk(
                    subdir_info["name"],
                    maxdepth=next_depth,
                    topdown=topdown,
                    detail=detail,
                    **kwargs,
                )

        if not topdown:
            yield path, (dirs if detail else list(dirs)), (
                files if detail else list(files)
            )

    def find(  # type: ignore[override]
        self,
        path: str,
        maxdepth: Optional[int] = None,
        withdirs: bool = False,
        detail: bool = False,
        prefix: Union[str, bool] = "",
        **kwargs: Any,
    ) -> Union[List[str], List[Dict]]:
        """List all files under *path*, optionally filtered by a name prefix.

        ``dvc_objects.fs.base.ObjectFileSystem.find`` calls this method with
        ``prefix`` set to a **string** (e.g. ``'0'``) expecting only entries
        whose name starts with that string.  fsspec's default ``find()``
        treats ``prefix`` as a boolean and recurses up the path hierarchy
        until it produces an empty path — crashing with IndexError.  We
        override here to handle both boolean and string prefix values.

        Args:
            path: Directory path to list (osf:// or stripped form)
            maxdepth: Maximum recursion depth (None = unlimited)
            withdirs: Include directories in results
            detail: If True return dicts, otherwise return path strings
            prefix: If a non-empty string, only return entries whose name
                starts with that value.  Boolean True/False is treated as
                no prefix filter (fsspec compatibility).
        """
        try:
            project_id, provider, dir_path = self._resolve_path(path)
        except Exception:
            return []

        # Navigate to the target directory using IDs
        try:
            listing_url, _ = self._navigate_to_dir(
                project_id, provider, dir_path, create_missing=False
            )
        except OSFNotFoundError:
            return []

        # Normalise prefix: treat booleans as "no filter"
        name_prefix: str = prefix if isinstance(prefix, str) else ""

        # Preserve the scheme style of the caller.  dvc-objects builds the
        # remote ODB path WITHOUT "osf://" (e.g. "3eugf/osfstorage/…").
        # When find() is called with such a path, returned paths must also
        # omit the scheme so that ObjectDB.path_to_oid() correctly slices
        # the path components (PurePosixPath adds an extra "osf:" component
        # for scheme-prefixed paths, misaligning the slice).
        _input_has_scheme = path.lower().startswith("osf://")

        results: List = []

        def _collect(listing_url: str, current_dir: str, depth: int) -> None:
            next_url: Optional[str] = listing_url
            while next_url and isinstance(next_url, str):
                response = self.client.get(next_url)
                data = response.json()
                for item in data.get("data", []):
                    attrs = item.get("attributes", {})
                    name = attrs.get("name", "")
                    kind = attrs.get("kind", "")

                    # Apply name prefix filter only at the immediate listing level
                    if name_prefix and not name.startswith(name_prefix):
                        continue

                    item_dir = f"{current_dir}/{name}".lstrip("/")
                    raw = f"{project_id}/{provider}/{item_dir}"
                    full_path = f"osf://{raw}" if _input_has_scheme else raw

                    if kind == "file":
                        if detail:
                            results.append(
                                self._parse_metadata(
                                    project_id, provider, current_dir, item
                                )
                            )
                        else:
                            results.append(full_path)
                    elif kind == "folder":
                        if withdirs:
                            results.append(full_path)
                        # Recurse unless maxdepth reached.
                        # Hard cap at 20 regardless of maxdepth to guard
                        # against runaway recursion when navigation returns a
                        # listing URL that points to a parent directory.
                        hard_limit = 20
                        if (maxdepth is None or depth < maxdepth) and (
                            depth < hard_limit
                        ):
                            sub_listing = (
                                item.get("relationships", {})
                                .get("files", {})
                                .get("links", {})
                                .get("related", {})
                                .get("href")
                            )
                            if sub_listing:
                                _collect(sub_listing, item_dir, depth + 1)

                next_url = data.get("links", {}).get("next")

        _collect(listing_url, dir_path, 1)

        # ObjectDB.path_to_oid expects result paths to use the same format as
        # odb.path (no protocol prefix when called via internal dvc-objects
        # traversal).  _collect always produces osf:// paths via serialize_path;
        # strip the prefix when the caller supplied a path without it so that
        # path_to_oid can correctly compute relative path parts.
        if not path.startswith("osf://"):
            results = [
                r[len("osf://") :] if r.startswith("osf://") else r for r in results
            ]

        return results

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

    def info(self, path: str, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override] # noqa: E501
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

        # Need to search for file by listing parent directory.
        # OSF uses internal IDs for nested paths, so we navigate using
        # _navigate_to_dir instead of constructing the URL by string concatenation.
        parent_path = get_directory(file_path)
        filename = get_filename(file_path)

        try:
            listing_url, _ = self._navigate_to_dir(
                project_id, provider, parent_path, create_missing=False
            )
        except OSFNotFoundError:
            raise OSFNotFoundError(f"File not found: {path}")

        next_url: Optional[str] = listing_url
        while next_url and isinstance(next_url, str):
            response = self.client.get(next_url)
            data = response.json()

            if "data" in data:
                for item in data["data"]:
                    item_name = item.get("attributes", {}).get("name", "")
                    if item_name == filename:
                        return self._parse_metadata(
                            project_id, provider, parent_path, item
                        )

            next_url = data.get("links", {}).get("next")

        # File not found
        raise OSFNotFoundError(f"File not found: {path}")

    def open(  # type: ignore[override]
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

        # Navigate to parent directory using IDs (handles nested paths + pagination)
        try:
            listing_url, _ = self._navigate_to_dir(
                project_id, provider, parent_path, create_missing=False
            )
        except OSFNotFoundError:
            raise OSFNotFoundError(f"Download URL not found for path: {path}")

        # Search the listing for the file, following pagination
        download_url = None
        next_url: Optional[str] = listing_url
        while next_url and isinstance(next_url, str) and download_url is None:
            response = self.client.get(next_url)
            data = response.json()
            for item in data.get("data", []):
                item_name = item.get("attributes", {}).get("name", "")
                if item_name == filename:
                    links = item.get("links", {})
                    # Use 'upload' link which supports authentication for downloads
                    # The 'download' link goes to osf.io which doesn't support API auth
                    download_url = links.get("upload") or links.get("move")
                    break
            next_url = data.get("links", {}).get("next")

        if not download_url:
            raise OSFNotFoundError(f"Download URL not found for path: {path}")

        # Download file with streaming
        stream_response = self.client.download_file(download_url)

        return OSFFile(stream_response, mode=mode)

    def get_file(self, rpath: str, lpath: str, **kwargs: Any) -> None:  # type: ignore[override] # noqa: E501
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

                    chunk_bytes = chunk if isinstance(chunk, bytes) else chunk.encode()
                    local_file.write(chunk_bytes)
                    md5_hash.update(chunk_bytes)

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

    def put_file(  # type: ignore[override]
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
        # Get file size to determine upload strategy
        file_size = os.path.getsize(lpath)
        upload_strategy = determine_upload_strategy(
            file_size, Config.OSF_UPLOAD_CHUNK_SIZE
        )

        # OSF / WaterButler have eventual consistency: directories created
        # during put may not be visible in the listing API for a few seconds.
        # Retry once on OSFNotFoundError with a short backoff.
        import time as _time

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                if upload_strategy == "single":
                    remote_md5 = self._put_file_simple(lpath, rpath, callback)
                else:
                    remote_md5 = self._put_file_chunked(lpath, rpath, callback)
                break  # success
            except OSFVersionConflictError:
                # 409: file already exists at target location.
                # For DVC's content-addressed cache, filename == MD5, so same
                # name means same content — treat as success without checking.
                return
            except OSFNotFoundError:
                if attempt < max_attempts:
                    _time.sleep(2 * attempt)  # 2s, 4s
                else:
                    raise

        # Verify checksum using MD5 returned directly in the upload response.
        # This avoids a second OSF API round-trip (info() → _navigate_to_dir)
        # which is unreliable for freshly created WaterButler paths whose
        # parent directories may not yet appear in the OSF listing API.
        if remote_md5:
            with open(lpath, "rb") as f:
                local_md5 = compute_upload_checksum(f)
            if local_md5 != remote_md5:
                raise OSFIntegrityError(
                    f"Checksum mismatch after upload for {rpath}: "
                    f"expected {local_md5}, got {remote_md5}. "
                    f"If remote is {EMPTY_FILE_MD5!r} the upload body was empty.",
                    expected_checksum=local_md5,
                    actual_checksum=remote_md5,
                )
        else:
            # Response did not include MD5 — fall back to info()-based check.
            self._verify_upload_checksum(lpath, rpath)

    def _put_file_simple(
        self,
        lpath: str,
        rpath: str,
        callback: Optional[Callable[[int, int], None]] = None,
    ) -> Optional[str]:
        """Upload a small file using single PUT request.

        Returns:
            MD5 checksum from upload response, or None if not available.
        """
        project_id, provider, file_path = self._resolve_path(rpath)

        # Get upload URL (creates parent directories as needed)
        upload_url = self._get_upload_url(project_id, provider, file_path)

        # Upload file
        file_size = os.path.getsize(lpath)
        with open(lpath, "rb") as f:
            response = self.client.upload_file(upload_url, f, callback, file_size)

        # Invoke final callback if provided (only if directly callable;
        # DVC may pass fsspec Callback objects which are not callable)
        if callback and callable(callback):
            try:
                callback(file_size, file_size)
            except Exception:
                pass

        # Return MD5 from upload response to avoid a second API round-trip.
        try:
            return (
                str(
                    response.json().get("data", {}).get("attributes", {}).get("md5")
                    or ""
                )
                or None
            )
        except Exception:
            return None

    def _put_file_chunked(
        self,
        lpath: str,
        rpath: str,
        callback: Optional[Callable[[int, int], None]] = None,
    ) -> Optional[str]:
        """Upload a large file using streaming PUT (not multi-request chunking).

        Note: OSF doesn't support true multi-request chunked uploads. Instead,
        we stream the file in a single PUT request for memory efficiency.

        Returns:
            MD5 checksum from upload response, or None if not available.
        """
        project_id, provider, file_path = self._resolve_path(rpath)

        # Get upload URL (creates parent directories as needed)
        upload_url = self._get_upload_url(project_id, provider, file_path)

        # Get file size
        file_size = os.path.getsize(lpath)

        # Upload file with streaming for memory efficiency
        with open(lpath, "rb") as f:
            response = self.client.upload_file(upload_url, f, callback, file_size)

        try:
            return (
                str(
                    response.json().get("data", {}).get("attributes", {}).get("md5")
                    or ""
                )
                or None
            )
        except Exception:
            return None

    def _navigate_to_dir(
        self,
        project_id: str,
        provider: str,
        dir_path: str,
        create_missing: bool = False,
    ) -> tuple:
        """Walk the directory tree using OSF file IDs and return URLs for the target dir. # noqa: E501

        OSF uses internal file IDs in API and WaterButler URLs for all
        directories below the root — path-constructed URLs only work at root
        level.  This method navigates each path component in turn, following
        ``relationships.files.links.related.href`` from listing responses.

        Args:
            project_id: OSF project ID
            provider: Storage provider (e.g. osfstorage)
            dir_path: Target directory path (e.g. ``files/md5/37``)
            create_missing: If True, create any missing folders along the way

        Returns:
            ``(listing_url, waterbutler_url)`` for the target directory.
            ``listing_url`` is the OSF API URL to list its contents.
            ``waterbutler_url`` is the WaterButler URL base for uploads/subfolder creation. # noqa: E501
        """
        parts = [p for p in dir_path.strip("/").split("/") if p]
        root_listing_url = path_to_api_url(project_id, provider, "")
        root_wb_url = (
            f"https://files.osf.io/v1/resources/{project_id}/providers/{provider}/"
        )

        current_listing_url: str = root_listing_url
        current_wb_url: str = root_wb_url
        # Tracks accumulated human-readable path for path-based URL fallback.
        path_so_far: list = []

        for part in parts:
            path_so_far.append(part)
            # Search current directory for this component (follow pagination).
            # OSF API and WaterButler have eventual consistency: a folder just
            # created via WB may not yet appear in the OSF metadata API.  If
            # the listing URL returns 404, treat it as an empty directory so
            # that create_missing=True falls through to folder creation.
            next_url: Optional[str] = current_listing_url
            found_item = None
            listing_404 = False
            while next_url and isinstance(next_url, str) and found_item is None:
                try:
                    response = self.client.get(next_url)
                except OSFNotFoundError:
                    # Listing URL itself returned 404 — folder was just created
                    # via WB and isn't reflected in OSF metadata API yet.
                    listing_404 = True
                    break
                data = response.json()
                for item in data.get("data", []):
                    if item.get("attributes", {}).get("name") == part:
                        found_item = item
                        break
                next_url = data.get("links", {}).get("next")

            # If OSF metadata API returned 404 and we can't create, bail out.
            if listing_404 and not create_missing:
                raise OSFNotFoundError(f"Directory not found: {dir_path}")

            if found_item is not None:
                # Navigate into the existing folder.
                #
                # Listing URL derivation priority:
                # 1. relationships.files.links.related.href — standard OSF API.
                #    Present in root/path-based listings; gives ID-based URL.
                # 2. Extract folder ID from WaterButler upload URL.
                #    links.upload for a folder is its own WB URL:
                #    files.osf.io/v1/resources/{p}/providers/{pv}/{id}/
                #    → api.osf.io/v2/nodes/{p}/files/{pv}/{id}/
                # 3. Raise — never silently keep the parent URL (old bug).
                listing_href: Optional[str] = (
                    found_item.get("relationships", {})
                    .get("files", {})
                    .get("links", {})
                    .get("related", {})
                    .get("href")
                )
                wb_href = found_item.get("links", {}).get("upload")
                if wb_href:
                    wb_href = wb_href.split("?")[0].rstrip("/") + "/"

                if not listing_href and wb_href:
                    # Fallback: derive from WaterButler upload URL.
                    # WB folder URL: .../providers/{pv}/{id}/
                    # → OSF API listing: .../files/{pv}/{id}/
                    _m = re.search(
                        r"/providers/[^/]+/(.+?)/?$",
                        wb_href.rstrip("/"),
                    )
                    if _m:
                        _fid = _m.group(1).strip("/")
                        if _fid:
                            listing_href = (
                                f"https://api.osf.io/v2/nodes/{project_id}"
                                f"/files/{provider}/{_fid}/"
                            )

                if not listing_href:
                    # Last resort: attributes.path (human-readable or ID).
                    # Better than silently reusing the parent listing URL.
                    _ap = found_item.get("attributes", {}).get("path", "").strip("/")
                    if _ap:
                        listing_href = (
                            f"https://api.osf.io/v2/nodes/{project_id}"
                            f"/files/{provider}/{_ap}/"
                        )

                current_listing_url = listing_href or current_listing_url
                current_wb_url = wb_href or current_wb_url
            elif create_missing:
                # Create the missing folder then navigate into it.
                # If a 409 is returned the folder already exists — re-list the
                # current directory to find it and navigate in normally.
                create_url = f"{current_wb_url.rstrip('/')}/?kind=folder&name={part}"
                try:
                    resp = self.client._request("PUT", create_url)
                    new_item = resp.json().get("data", {})
                except OSFVersionConflictError:
                    # Folder exists; find it via current listing and fall
                    # through to the found_item navigation logic.
                    refresh_url: Optional[str] = current_listing_url
                    found_item = None
                    while refresh_url and found_item is None:
                        r = self.client.get(refresh_url)
                        d = r.json()
                        for it in d.get("data", []):
                            if it.get("attributes", {}).get("name") == part:
                                found_item = it
                                break
                        refresh_url = d.get("links", {}).get("next")
                    if found_item is None:
                        raise OSFNotFoundError(
                            f"Folder '{part}' not found after 409: {dir_path}"
                        )
                    wb_href = found_item.get("links", {}).get("upload")
                    if wb_href:
                        wb_href = wb_href.split("?")[0].rstrip("/") + "/"
                    attr_path = (
                        found_item.get("attributes", {}).get("path", "").strip("/")
                    )
                    if attr_path:
                        listing_href = (
                            f"https://api.osf.io/v2/nodes/{project_id}"
                            f"/files/{provider}/{attr_path}/"
                        )
                    else:
                        listing_href = (
                            found_item.get("relationships", {})
                            .get("files", {})
                            .get("links", {})
                            .get("related", {})
                            .get("href")
                        )
                    current_listing_url = listing_href or current_listing_url
                    current_wb_url = wb_href or current_wb_url
                    continue

                wb_href = new_item.get("links", {}).get("upload")
                if wb_href:
                    wb_href = wb_href.split("?")[0].rstrip("/") + "/"

                # WaterButler folder-creation responses do NOT include
                # 'relationships', so we can't get the listing URL from there.
                # Derive it from attributes.path which contains the internal
                # folder ID (e.g. "/69ae5335816a04950ce7d39d/").
                folder_path = new_item.get("attributes", {}).get("path", "").strip("/")
                if folder_path:
                    listing_href = (
                        f"https://api.osf.io/v2/nodes/{project_id}"
                        f"/files/{provider}/{folder_path}/"
                    )
                else:
                    listing_href = None

                current_listing_url = listing_href or current_listing_url
                current_wb_url = wb_href or current_wb_url
            else:
                # Item not found and we are not creating it.  OSF has
                # eventual consistency: a folder created via WB may not
                # appear in the parent listing for a short time, but the
                # OSF API *does* respond correctly to a direct path-based
                # URL once WB has committed the object.  Try constructing
                # a path-based URL from the accumulated human-readable path
                # before giving up.
                candidate_path = "/".join(path_so_far)
                candidate_url = (
                    f"https://api.osf.io/v2/nodes/{project_id}"
                    f"/files/{provider}/{candidate_path}/"
                )
                try:
                    self.client.get(candidate_url)  # raises on 404
                    # Path-based navigation worked — use it for listing.
                    current_listing_url = candidate_url
                    current_wb_url = (
                        f"https://files.osf.io/v1/resources/{project_id}"
                        f"/providers/{provider}/{candidate_path}/"
                    )
                except OSFNotFoundError:
                    raise OSFNotFoundError(f"Directory not found: {dir_path}")

        return current_listing_url, current_wb_url

    def _get_upload_url(self, project_id: str, provider: str, file_path: str) -> str:
        """Get WaterButler upload URL for a file (existing update URL or new-file URL).

        Navigates to the parent directory using OSF file IDs, checks whether
        the file already exists, and returns the appropriate WaterButler URL.
        """
        parent_path = get_directory(file_path)
        filename = get_filename(file_path)

        # Navigate to parent directory, creating it if needed; get both URLs in one pass
        current_listing_url, parent_wb_url = self._navigate_to_dir(
            project_id, provider, parent_path, create_missing=True
        )

        # Search the parent listing for the file.  The listing URL may 404
        # if the parent dir was just created via WB and the OSF metadata API
        # hasn't caught up yet — treat that as "file doesn't exist yet".
        next_url: Optional[str] = current_listing_url
        while next_url and isinstance(next_url, str):
            try:
                response = self.client.get(next_url)
            except OSFNotFoundError:
                break  # Newly-created dir not in OSF API yet → file absent.
            data = response.json()
            for item in data.get("data") or []:
                if item.get("attributes", {}).get("name", "") == filename:
                    upload_url = item.get("links", {}).get("upload")
                    if upload_url:
                        return str(upload_url)
            raw_next = (data.get("links") or {}).get("next")
            next_url = raw_next if isinstance(raw_next, str) else None

        # File doesn't exist — return new-file creation URL using parent WaterButler URL
        return f"{parent_wb_url.rstrip('/')}/?kind=file&name={filename}"

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

    def put(  # type: ignore[override]
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
            items: List[Dict[str, Any]] = self.ls(path1, detail=True)  # type: ignore[assignment] # noqa: E501
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

    def mv(  # type: ignore[override]
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
            f"Batch delete completed: {success} succeeded, {failed} failed out of {total}"  # noqa: E501
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

    def rm(  # type: ignore[override]
        self,
        path: Union[str, List[str]],
        recursive: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Delete a file or directory from OSF.

        Args:
            path: Path to delete
            recursive: If True, delete directory contents recursively
            **kwargs: Additional arguments

        Raises:
            OSFNotFoundError: If path doesn't exist
        """
        # dvc gc passes a list of paths when batch-deleting; handle both cases.
        if isinstance(path, list):
            for p in path:
                self.rm(p, recursive=recursive, **kwargs)
            return

        # Resolve path components.
        project_id, provider, file_path = self._resolve_path(path)
        if not file_path:
            return  # Root — nothing to delete.

        parent_path = get_directory(file_path)
        filename = get_filename(file_path)

        # Navigate to parent directory using internal IDs.
        # Do NOT call info() first: info() uses the same _navigate_to_dir
        # path and will silently raise OSFNotFoundError if navigation is
        # imperfect, causing rm() to return without deleting anything.
        # Instead, navigate directly to the parent and search for the item.
        try:
            parent_listing_url, _ = self._navigate_to_dir(
                project_id, provider, parent_path, create_missing=False
            )
        except OSFNotFoundError:
            return  # Parent doesn't exist — nothing to delete.

        next_url: Optional[str] = parent_listing_url
        while next_url and isinstance(next_url, str):
            response = self.client.get(next_url)
            data = response.json()

            for item in data.get("data", []):
                item_name = item.get("attributes", {}).get("name", "")
                if item_name != filename:
                    continue

                kind = item.get("attributes", {}).get("kind", "")
                links = item.get("links", {})

                if kind == "folder":
                    if recursive:
                        # Delete the folder via WaterButler DELETE (not a
                        # no-op — WaterButler supports folder deletion).
                        delete_url = links.get("delete")
                        if delete_url:
                            self.client.delete(delete_url)
                    return  # Done (recursive=False means leave folder alone).

                # It's a file — delete it.
                delete_url = links.get("delete") or links.get("upload")
                if delete_url:
                    self.client.delete(delete_url)
                return

            next_url = data.get("links", {}).get("next")

        # Item not found — treat as already deleted (idempotent).
        return

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
