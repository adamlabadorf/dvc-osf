"""OSF API client for interacting with the Open Science Framework."""

import logging
import time
from typing import Any, BinaryIO, Callable, Dict, Iterator, Optional

import requests
from requests.adapters import HTTPAdapter

from .auth import format_auth_header
from .config import Config
from .exceptions import (
    OSFAPIError,
    OSFAuthenticationError,
    OSFConnectionError,
    OSFFileLockedError,
    OSFNotFoundError,
    OSFPermissionError,
    OSFQuotaExceededError,
    OSFRateLimitError,
    OSFVersionConflictError,
)

logger = logging.getLogger(__name__)


class OSFAPIClient:
    """
    Client for interacting with the OSF API v2.

    This class handles all HTTP requests to the OSF REST API,
    including authentication, retry logic, rate limiting, pagination,
    and error handling with streaming support for large file downloads.
    """

    def __init__(
        self,
        token: str,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        upload_timeout: Optional[int] = None,
    ) -> None:
        """
        Initialize OSF API client.

        Args:
            token: OSF personal access token for authentication
            base_url: API base URL (defaults to Config.API_BASE_URL)
            timeout: Request timeout in seconds (defaults to Config.DEFAULT_TIMEOUT)
            max_retries: Maximum retry attempts (defaults to Config.MAX_RETRIES)
            upload_timeout: Upload timeout in seconds (defaults to Config.OSF_UPLOAD_TIMEOUT)
        """
        self.token = token
        self.base_url = (base_url or Config.API_BASE_URL).rstrip("/")
        self.timeout = timeout or Config.DEFAULT_TIMEOUT
        self.max_retries = max_retries or Config.MAX_RETRIES
        self.upload_timeout = upload_timeout or Config.OSF_UPLOAD_TIMEOUT

        # Create session with connection pooling
        self.session = requests.Session()

        # Configure HTTPAdapter with retry settings
        adapter = HTTPAdapter(
            pool_connections=Config.CONNECTION_POOL_SIZE,
            pool_maxsize=Config.CONNECTION_POOL_SIZE,
            max_retries=0,  # We'll handle retries manually for more control
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers including authentication
        auth_headers = format_auth_header(token)
        self.session.headers.update(auth_headers)
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Any = None,
        stream: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """
        Make an HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Complete URL to request
            params: Query parameters
            json: JSON payload
            data: Raw data payload
            stream: Enable streaming for large responses
            headers: Additional headers

        Returns:
            Response object

        Raises:
            OSFAuthenticationError: Authentication failed (401)
            OSFPermissionError: Permission denied (403)
            OSFNotFoundError: Resource not found (404)
            OSFRateLimitError: Rate limit exceeded (429)
            OSFAPIError: Other API errors
            OSFConnectionError: Network/connection errors
        """
        attempt = 0
        last_exception = None

        while attempt <= self.max_retries:
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    timeout=self.timeout,
                    stream=stream,
                    headers=headers,
                )

                # Handle response and check for errors
                self._handle_response(response)

                return response

            except (OSFConnectionError, OSFRateLimitError) as e:
                # Retryable errors
                last_exception = e
                attempt += 1

                if attempt > self.max_retries:
                    raise

                # Calculate backoff delay
                if isinstance(e, OSFRateLimitError) and e.retry_after:
                    delay = e.retry_after
                else:
                    delay = Config.RETRY_BACKOFF**attempt

                time.sleep(delay)

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                # Network errors - retryable
                last_exception = OSFConnectionError(f"Connection to OSF failed: {e}")
                attempt += 1

                if attempt > self.max_retries:
                    raise last_exception

                delay = Config.RETRY_BACKOFF**attempt
                time.sleep(delay)

            except OSFVersionConflictError:
                # Version conflicts should NOT be retried
                raise

            except OSFAPIError as e:
                # Check if this API error is retryable (5xx errors)
                if e.retryable:
                    last_exception = e
                    attempt += 1

                    if attempt > self.max_retries:
                        raise

                    delay = Config.RETRY_BACKOFF**attempt
                    time.sleep(delay)
                else:
                    # Non-retryable error, raise immediately
                    raise

        # If we get here, we've exhausted retries
        if last_exception:
            raise last_exception

        # This shouldn't happen, but just in case
        raise OSFConnectionError("Request failed after retries")

    def _handle_response(self, response: requests.Response) -> None:
        """
        Handle HTTP response, mapping status codes to exceptions.

        Args:
            response: HTTP response object

        Raises:
            OSFAuthenticationError: 401 status code
            OSFPermissionError: 403 status code
            OSFNotFoundError: 404 status code
            OSFVersionConflictError: 409 status code
            OSFQuotaExceededError: 413 status code
            OSFFileLockedError: 423 status code
            OSFRateLimitError: 429 status code
            OSFAPIError: Other 4xx/5xx status codes
        """
        if response.status_code < 400:
            # Success - no error
            return

        # Extract error message from response if available
        error_message = self._extract_error_message(response)

        status_code = response.status_code

        if status_code == 400:
            raise OSFAPIError(
                error_message or "Bad request",
                status_code=status_code,
                response=response,
            )
        elif status_code == 401:
            raise OSFAuthenticationError(
                error_message or "Authentication failed. Check your OSF token.",
                status_code=status_code,
                response=response,
            )
        elif status_code == 403:
            raise OSFPermissionError(
                error_message
                or (
                    "Permission denied for OSF operation. "
                    "Please check that your OSF token has the required "
                    "permissions (osf.full_write for uploads)."
                ),
                status_code=status_code,
                response=response,
            )
        elif status_code == 404:
            raise OSFNotFoundError(
                error_message or "Resource not found on OSF.",
                status_code=status_code,
                response=response,
            )
        elif status_code == 409:
            logger.warning(
                f"Version conflict detected (409): {error_message or 'File version conflict'}"
            )
            raise OSFVersionConflictError(
                error_message
                or (
                    "File version conflict detected. "
                    "Another process may have modified the file. "
                    "Please retry the operation."
                ),
                status_code=status_code,
                response=response,
            )
        elif status_code == 413:
            logger.error(
                f"Storage quota exceeded (413): {error_message or 'OSF storage quota exceeded'}"
            )
            raise OSFQuotaExceededError(
                error_message
                or (
                    "OSF storage quota exceeded. "
                    "Please free up space in your OSF project or upgrade your storage plan. "
                    "Visit https://osf.io/settings/ to manage your storage."
                ),
                status_code=status_code,
                response=response,
            )
        elif status_code == 423:
            logger.warning(f"File locked (423): {error_message or 'File is locked'}")
            raise OSFFileLockedError(
                error_message
                or (
                    "File is locked and cannot be modified. "
                    "Another process may be accessing the file. "
                    "Please wait and try again."
                ),
                status_code=status_code,
                response=response,
            )
        elif status_code == 429:
            # Rate limit - check for Retry-After header
            retry_after = None
            if "Retry-After" in response.headers:
                try:
                    retry_after = int(response.headers["Retry-After"])
                except (ValueError, TypeError):
                    pass

            raise OSFRateLimitError(
                error_message or "OSF API rate limit exceeded.",
                status_code=status_code,
                response=response,
                retry_after=retry_after,
            )
        elif status_code >= 500:
            # Server errors - retryable
            raise OSFAPIError(
                error_message or f"OSF server error: {status_code}",
                status_code=status_code,
                response=response,
            )
        else:
            # Other client errors
            raise OSFAPIError(
                error_message or f"OSF API error: {status_code}",
                status_code=status_code,
                response=response,
            )

    def _extract_error_message(self, response: requests.Response) -> Optional[str]:
        """
        Extract error message from OSF API response JSON.

        Args:
            response: HTTP response object

        Returns:
            Error message if found, None otherwise
        """
        try:
            data = response.json()

            # OSF API error format varies, try common fields
            if "errors" in data and isinstance(data["errors"], list) and data["errors"]:
                error = data["errors"][0]
                if "detail" in error:
                    return error["detail"]

            if "message" in data:
                return data["message"]

            if "detail" in data:
                return data["detail"]

        except (ValueError, KeyError, TypeError):
            pass

        return None

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> requests.Response:
        """
        Make a GET request to the OSF API.

        Args:
            url: Complete URL or path (if starts with /, appended to base_url)
            params: Query parameters
            stream: Enable streaming for large responses

        Returns:
            Response object
        """
        if url.startswith("/"):
            url = f"{self.base_url}{url}"

        return self._request("GET", url, params=params, stream=stream)

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Any = None,
    ) -> requests.Response:
        """
        Make a POST request to the OSF API.

        Args:
            url: Complete URL or path (if starts with /, appended to base_url)
            json: JSON payload
            data: Raw data payload

        Returns:
            Response object
        """
        if url.startswith("/"):
            url = f"{self.base_url}{url}"

        return self._request("POST", url, json=json, data=data)

    def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Any = None,
    ) -> requests.Response:
        """
        Make a PUT request to the OSF API.

        Args:
            url: Complete URL or path (if starts with /, appended to base_url)
            json: JSON payload
            data: Raw data payload (for file uploads)

        Returns:
            Response object
        """
        if url.startswith("/"):
            url = f"{self.base_url}{url}"

        return self._request("PUT", url, json=json, data=data)

    def delete(self, url: str) -> requests.Response:
        """
        Make a DELETE request to the OSF API.

        Args:
            url: Complete URL or path (if starts with /, appended to base_url)

        Returns:
            Response object
        """
        if url.startswith("/"):
            url = f"{self.base_url}{url}"

        return self._request("DELETE", url)

    def download_file(self, url: str) -> requests.Response:
        """
        Download a file with streaming support.

        Args:
            url: Complete download URL

        Returns:
            Response object with streaming enabled
        """
        # Download URLs are typically complete URLs from OSF API
        return self._request("GET", url, stream=True)

    def get_paginated(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch all pages of a paginated API response.

        Automatically follows 'links.next' to fetch all pages.

        Args:
            url: Initial URL or path
            params: Query parameters

        Yields:
            Items from all pages
        """
        if url.startswith("/"):
            url = f"{self.base_url}{url}"

        current_url: Optional[str] = url
        current_params = params

        while current_url:
            response = self.get(current_url, params=current_params)
            data = response.json()

            # Yield items from current page
            if "data" in data:
                items = data["data"]
                if isinstance(items, list):
                    for item in items:
                        yield item
                else:
                    yield items

            # Check for next page
            links = data.get("links", {})
            current_url = links.get("next")
            current_params = None  # Params already in next URL

            if not current_url:
                break

    def upload_file(
        self,
        url: str,
        file_obj: BinaryIO,
        callback: Optional[Callable[[int, int], None]] = None,
        total_size: Optional[int] = None,
    ) -> requests.Response:
        """
        Upload a file with streaming support and progress tracking.

        Args:
            url: Upload URL (typically from OSF API links.upload)
            file_obj: File-like object to upload
            callback: Optional progress callback function (bytes_uploaded, total_bytes)
            total_size: Total file size in bytes (for progress tracking)

        Returns:
            Response object

        Raises:
            OSFQuotaExceededError: Storage quota exceeded
            OSFFileLockedError: File is locked
            OSFVersionConflictError: Version conflict
            Other OSF exceptions
        """
        # Wrap file object with progress tracking if callback provided
        if callback and callable(callback) and total_size:
            file_data = self._stream_upload(file_obj, callback, total_size)
        else:
            file_data = file_obj

        # Use upload_timeout for file uploads
        headers = {"Content-Type": "application/octet-stream"}

        return self._request(
            "PUT",
            url,
            data=file_data,
            headers=headers,
        )

    def upload_chunk(
        self,
        url: str,
        chunk_data: bytes,
        start_byte: int,
        end_byte: int,
        total_size: int,
    ) -> requests.Response:
        """
        Upload a file chunk with Content-Range header.

        Args:
            url: Upload URL
            chunk_data: Chunk data bytes
            start_byte: Starting byte position (0-indexed)
            end_byte: Ending byte position (inclusive)
            total_size: Total file size in bytes

        Returns:
            Response object
        """
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Range": f"bytes {start_byte}-{end_byte}/{total_size}",
        }

        return self._request(
            "PUT",
            url,
            data=chunk_data,
            headers=headers,
        )

    def _stream_upload(
        self,
        file_obj: BinaryIO,
        callback: Callable[[int, int], None],
        total_size: int,
    ) -> Iterator[bytes]:
        """
        Stream file data with progress callbacks.

        Args:
            file_obj: File-like object to read from
            callback: Progress callback function
            total_size: Total file size

        Yields:
            Chunks of file data
        """
        bytes_sent = 0
        chunk_size = Config.CHUNK_SIZE

        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break

            bytes_sent += len(chunk)

            # Invoke callback with progress
            try:
                callback(bytes_sent, total_size)
            except Exception:
                # Don't let callback errors fail the upload
                pass

            yield chunk

    def close(self) -> None:
        """Close the session and release resources."""
        if self.session:
            self.session.close()

    def __enter__(self) -> "OSFAPIClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close session."""
        self.close()
