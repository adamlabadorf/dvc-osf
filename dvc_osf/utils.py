"""Utility functions for DVC-OSF."""

import hashlib
import logging
import os
from typing import BinaryIO, Callable, Iterator, Optional, Tuple
from urllib.parse import quote, urlparse

from .config import Config

logger = logging.getLogger(__name__)


def parse_osf_url(url: str) -> Tuple[str, str, str]:
    """
    Parse an OSF URL to extract project ID, storage provider, and path.

    Format: osf://PROJECT_ID/PROVIDER/PATH
    If provider is omitted, defaults to 'osfstorage'.

    Args:
        url: OSF URL (e.g., 'osf://abc123/osfstorage/data/file.csv')

    Returns:
        Tuple of (project_id, provider, path)

    Raises:
        ValueError: If URL is invalid or malformed
    """
    parsed = urlparse(url)

    if parsed.scheme != "osf":
        raise ValueError(f"Invalid OSF URL scheme: '{parsed.scheme}'. Expected 'osf'.")

    project_id = parsed.netloc
    if not project_id:
        raise ValueError("OSF URL must contain a project ID.")

    # Validate project ID format
    if not _validate_project_id(project_id):
        raise ValueError(
            f"Invalid project ID: '{project_id}'. "
            f"Must be alphanumeric and at least "
            f"{Config.MIN_PROJECT_ID_LENGTH} characters."
        )

    # Parse path to extract provider and file path
    path = parsed.path.lstrip("/")

    if not path:
        # Root of project, use default provider
        return project_id, Config.DEFAULT_PROVIDER, ""

    # Split into provider and path components
    parts = path.split("/", 1)
    if len(parts) == 1:
        # No path after provider (or no provider specified)
        # Check if this looks like a provider name or a path
        if parts[0] in ["osfstorage", "github", "dropbox", "googledrive", "box", "s3"]:
            return project_id, parts[0], ""
        else:
            # Treat as path with default provider
            return project_id, Config.DEFAULT_PROVIDER, parts[0]
    else:
        provider, file_path = parts
        return project_id, provider, file_path


def _validate_project_id(project_id: str) -> bool:
    """
    Validate OSF project ID format.

    Args:
        project_id: Project ID to validate

    Returns:
        True if valid, False otherwise
    """
    if len(project_id) < Config.MIN_PROJECT_ID_LENGTH:
        return False

    # OSF project IDs are alphanumeric
    # (may include some special chars, but we're conservative)
    return project_id.replace("_", "").replace("-", "").isalnum()


def normalize_path(path: str) -> str:
    """
    Normalize an OSF path.

    Removes leading/trailing slashes and collapses multiple slashes.

    Args:
        path: Path to normalize

    Returns:
        Normalized path
    """
    if not path:
        return ""

    # Remove leading and trailing slashes
    path = path.strip("/")

    # Collapse multiple slashes into one
    while "//" in path:
        path = path.replace("//", "/")

    return path


def join_path(*parts: str) -> str:
    """
    Join path components correctly, handling slashes and normalization.

    Args:
        *parts: Path components to join

    Returns:
        Joined and normalized path
    """
    if not parts:
        return ""

    # Filter out empty parts
    non_empty = [p for p in parts if p]

    if not non_empty:
        return ""

    # Join with slashes and normalize
    joined = "/".join(non_empty)
    return normalize_path(joined)


def path_to_api_url(
    project_id: str, provider: str, path: str, base_url: Optional[str] = None
) -> str:
    """
    Convert OSF path components to OSF API endpoint URL.

    Args:
        project_id: OSF project ID
        provider: Storage provider (e.g., 'osfstorage')
        path: File path within the provider
        base_url: API base URL (defaults to Config.API_BASE_URL)

    Returns:
        Complete OSF API URL
    """
    if base_url is None:
        base_url = Config.API_BASE_URL

    # Normalize the base URL (remove trailing slash)
    base_url = base_url.rstrip("/")

    # Encode path components while preserving slashes
    if path:
        encoded_path = "/".join(quote(part, safe="") for part in path.split("/"))
    else:
        encoded_path = ""

    # Build the API URL for files
    # Format: {base_url}/nodes/{project_id}/files/{provider}/{path}
    if encoded_path:
        return f"{base_url}/nodes/{project_id}/files/{provider}/{encoded_path}"
    else:
        return f"{base_url}/nodes/{project_id}/files/{provider}/"


def serialize_path(project_id: str, provider: str, path: str) -> str:
    """
    Convert internal path representation back to osf:// URL format.

    Args:
        project_id: OSF project ID
        provider: Storage provider
        path: File path

    Returns:
        OSF URL string
    """
    normalized_path = normalize_path(path)

    if normalized_path:
        return f"osf://{project_id}/{provider}/{normalized_path}"
    else:
        return f"osf://{project_id}/{provider}"


def get_filename(path: str) -> str:
    """
    Extract filename from path.

    Args:
        path: File path

    Returns:
        Filename (last component of path)
    """
    if not path:
        return ""

    normalized = normalize_path(path)
    if not normalized:
        return ""

    return normalized.split("/")[-1]


def get_directory(path: str) -> str:
    """
    Extract directory path from file path.

    Args:
        path: File path

    Returns:
        Directory path (all but last component)
    """
    if not path:
        return ""

    normalized = normalize_path(path)
    if not normalized or "/" not in normalized:
        return ""

    return "/".join(normalized.split("/")[:-1])


def get_parent(path: str) -> str:
    """
    Get parent directory of path.

    Args:
        path: File or directory path

    Returns:
        Parent directory path
    """
    return get_directory(path)


def validate_osf_url(url: str) -> None:
    """
    Validate that a URL is a properly formatted OSF URL.

    Args:
        url: URL to validate

    Raises:
        ValueError: If URL is invalid or malformed
    """
    try:
        _ = parse_osf_url(url)
        # parse_osf_url already does validation
    except Exception as e:
        raise ValueError(f"Invalid OSF URL '{url}': {e}") from e


def compute_upload_checksum(file_obj: BinaryIO) -> str:
    """
    Compute MD5 checksum of a file during upload.

    Args:
        file_obj: File-like object to compute checksum for

    Returns:
        MD5 checksum as hex string
    """
    md5 = hashlib.md5()
    chunk_size = Config.CHUNK_SIZE

    # Save current position
    start_pos = file_obj.tell()

    # Read file in chunks
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        md5.update(chunk)

    # Reset file position
    file_obj.seek(start_pos)

    return md5.hexdigest()


def chunk_file(file_obj: BinaryIO, chunk_size: int) -> Iterator[Tuple[bytes, int, int]]:
    """
    Generator that yields file chunks with byte positions.

    Args:
        file_obj: File-like object to chunk
        chunk_size: Size of each chunk in bytes

    Yields:
        Tuple of (chunk_data, start_byte, end_byte)
    """
    start_byte = 0

    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break

        end_byte = start_byte + len(chunk) - 1
        yield chunk, start_byte, end_byte

        start_byte += len(chunk)


def get_file_size(file_obj: BinaryIO) -> int:
    """
    Get size of a file object.

    Args:
        file_obj: File-like object

    Returns:
        File size in bytes
    """
    # Save current position
    current_pos = file_obj.tell()

    # Seek to end to get size
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()

    # Restore original position
    file_obj.seek(current_pos)

    return size


def determine_upload_strategy(file_size: int, chunk_threshold: int) -> str:
    """
    Determine whether to use single or chunked upload based on file size.

    Args:
        file_size: Size of file in bytes
        chunk_threshold: Threshold for chunked uploads

    Returns:
        'single' or 'chunked'
    """
    if file_size < chunk_threshold:
        return "single"
    else:
        return "chunked"


def validate_chunk_size(chunk_size: int) -> int:
    """
    Validate and bound chunk size within acceptable limits.

    Args:
        chunk_size: Desired chunk size in bytes

    Returns:
        Validated chunk size (bounded by min/max)
    """
    if chunk_size < Config.UPLOAD_CHUNK_MIN_SIZE:
        return Config.UPLOAD_CHUNK_MIN_SIZE
    elif chunk_size > Config.UPLOAD_CHUNK_MAX_SIZE:
        return Config.UPLOAD_CHUNK_MAX_SIZE
    else:
        return chunk_size


def format_bytes(num_bytes: int) -> str:
    """
    Format byte count as human-readable string.

    Args:
        num_bytes: Number of bytes

    Returns:
        Formatted string (e.g., '1.5 MB', '2.3 GB')
    """
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0

    return f"{size:.1f} PB"


class ProgressTracker:
    """Track and report upload progress."""

    def __init__(
        self, total_size: int, callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize progress tracker.

        Args:
            total_size: Total size in bytes
            callback: Optional callback function (bytes_uploaded, total_bytes)
        """
        self.total_size = total_size
        self.bytes_uploaded = 0
        self.callback = callback

    def update(self, bytes_count: int) -> None:
        """
        Update progress.

        Args:
            bytes_count: Number of bytes uploaded in this update
        """
        self.bytes_uploaded += bytes_count

        if self.callback:
            try:
                self.callback(self.bytes_uploaded, self.total_size)
            except Exception as e:
                # Don't let callback errors fail the upload
                logger.warning(f"Progress callback error: {e}")

    def complete(self) -> None:
        """Mark upload as complete."""
        if self.callback:
            try:
                self.callback(self.total_size, self.total_size)
            except Exception as e:
                logger.warning(f"Progress callback error on completion: {e}")
