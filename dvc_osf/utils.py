"""Utility functions for DVC-OSF."""

from typing import Any, Dict
from urllib.parse import urlparse


def parse_osf_url(url: str) -> Dict[str, str]:
    """
    Parse an OSF URL to extract project ID and path.

    Args:
        url: OSF URL (e.g., 'osf://project_id/path/to/file')

    Returns:
        Dictionary with 'project_id' and 'path' keys
    """
    parsed = urlparse(url)
    if parsed.scheme != "osf":
        raise ValueError(f"Invalid OSF URL scheme: {parsed.scheme}")

    project_id = parsed.netloc
    path = parsed.path.lstrip("/")

    return {"project_id": project_id, "path": path}


def normalize_path(path: str) -> str:
    """
    Normalize an OSF path.

    Args:
        path: OSF path to normalize

    Returns:
        Normalized path
    """
    # Remove leading/trailing slashes, collapse multiple slashes
    path = path.strip("/")
    while "//" in path:
        path = path.replace("//", "/")
    return path


def build_osf_url(project_id: str, path: str = "") -> str:
    """
    Build an OSF URL from components.

    Args:
        project_id: OSF project identifier
        path: Path within the project

    Returns:
        Complete OSF URL
    """
    path = normalize_path(path)
    if path:
        return f"osf://{project_id}/{path}"
    return f"osf://{project_id}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def extract_metadata(osf_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant metadata from OSF API response.

    Args:
        osf_response: Raw OSF API response

    Returns:
        Simplified metadata dictionary
    """
    raise NotImplementedError("Metadata extraction not yet implemented")
