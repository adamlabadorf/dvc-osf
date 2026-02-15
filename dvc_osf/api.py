"""OSF API client for interacting with the Open Science Framework."""

import time
from typing import Any, Dict, Iterator, Optional

import requests
from requests.adapters import HTTPAdapter

from .auth import format_auth_header
from .config import Config
from .exceptions import (
    OSFAPIError,
    OSFAuthenticationError,
    OSFConnectionError,
    OSFNotFoundError,
    OSFPermissionError,
    OSFRateLimitError,
)


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
    ) -> None:
        """
        Initialize OSF API client.

        Args:
            token: OSF personal access token for authentication
            base_url: API base URL (defaults to Config.API_BASE_URL)
            timeout: Request timeout in seconds (defaults to Config.DEFAULT_TIMEOUT)
            max_retries: Maximum retry attempts (defaults to Config.MAX_RETRIES)
        """
        self.token = token
        self.base_url = (base_url or Config.API_BASE_URL).rstrip("/")
        self.timeout = timeout or Config.DEFAULT_TIMEOUT
        self.max_retries = max_retries or Config.MAX_RETRIES

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
                error_message or "Permission denied for OSF operation.",
                status_code=status_code,
                response=response,
            )
        elif status_code == 404:
            raise OSFNotFoundError(
                error_message or "Resource not found on OSF.",
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
