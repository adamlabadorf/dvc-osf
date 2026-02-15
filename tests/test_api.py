"""Tests for OSF API client."""

from unittest.mock import Mock, patch

import pytest
import requests

from dvc_osf.api import OSFAPIClient
from dvc_osf.config import Config
from dvc_osf.exceptions import (
    OSFAPIError,
    OSFAuthenticationError,
    OSFNotFoundError,
    OSFPermissionError,
    OSFRateLimitError,
)


class TestOSFAPIClientInit:
    """Tests for OSFAPIClient initialization."""

    def test_init_with_token(self):
        """Test initialization with token."""
        client = OSFAPIClient(token="test_token")
        assert client.token == "test_token"
        assert client.base_url == Config.API_BASE_URL
        assert client.timeout == Config.DEFAULT_TIMEOUT
        assert client.max_retries == Config.MAX_RETRIES

    def test_init_with_custom_base_url(self):
        """Test initialization with custom base URL."""
        client = OSFAPIClient(token="test_token", base_url="https://test.osf.io/v2")
        assert client.base_url == "https://test.osf.io/v2"

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = OSFAPIClient(token="test_token", timeout=60)
        assert client.timeout == 60

    def test_init_with_custom_max_retries(self):
        """Test initialization with custom max retries."""
        client = OSFAPIClient(token="test_token", max_retries=5)
        assert client.max_retries == 5

    def test_init_creates_session(self):
        """Test that initialization creates a requests session."""
        client = OSFAPIClient(token="test_token")
        assert isinstance(client.session, requests.Session)

    def test_init_sets_auth_header(self):
        """Test that authorization header is set."""
        client = OSFAPIClient(token="test_token")
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer test_token"


class TestHTTPMethods:
    """Tests for HTTP method implementations."""

    @patch("dvc_osf.api.requests.Session.request")
    def test_get_method(self, mock_request):
        """Test GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        _ = client.get("/nodes/abc123")

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "GET"
        assert "abc123" in kwargs["url"]

    @patch("dvc_osf.api.requests.Session.request")
    def test_post_method(self, mock_request):
        """Test POST request."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        _ = client.post("/nodes/abc123", json={"key": "value"})

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["json"] == {"key": "value"}

    @patch("dvc_osf.api.requests.Session.request")
    def test_put_method(self, mock_request):
        """Test PUT request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        _ = client.put("/nodes/abc123", json={"key": "value"})

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "PUT"

    @patch("dvc_osf.api.requests.Session.request")
    def test_delete_method(self, mock_request):
        """Test DELETE request."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        _ = client.delete("/nodes/abc123")

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "DELETE"

    @patch("dvc_osf.api.requests.Session.request")
    def test_get_with_params(self, mock_request):
        """Test GET request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        _ = client.get("/nodes", params={"filter[public]": "true"})

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["params"] == {"filter[public]": "true"}


class TestStatusCodeMapping:
    """Tests for mapping status codes to exceptions."""

    @patch("dvc_osf.api.requests.Session.request")
    def test_400_bad_request(self, mock_request):
        """Test that 400 raises OSFAPIError."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        with pytest.raises(OSFAPIError) as exc_info:
            client.get("/test")

        assert exc_info.value.status_code == 400

    @patch("dvc_osf.api.requests.Session.request")
    def test_401_unauthorized(self, mock_request):
        """Test that 401 raises OSFAuthenticationError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        with pytest.raises(OSFAuthenticationError) as exc_info:
            client.get("/test")

        assert exc_info.value.status_code == 401

    @patch("dvc_osf.api.requests.Session.request")
    def test_403_forbidden(self, mock_request):
        """Test that 403 raises OSFPermissionError."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        with pytest.raises(OSFPermissionError) as exc_info:
            client.get("/test")

        assert exc_info.value.status_code == 403

    @patch("dvc_osf.api.requests.Session.request")
    def test_404_not_found(self, mock_request):
        """Test that 404 raises OSFNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        with pytest.raises(OSFNotFoundError) as exc_info:
            client.get("/test")

        assert exc_info.value.status_code == 404

    @patch("dvc_osf.api.requests.Session.request")
    def test_429_rate_limit(self, mock_request):
        """Test that 429 raises OSFRateLimitError."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token", max_retries=0)
        with pytest.raises(OSFRateLimitError) as exc_info:
            client.get("/test")

        assert exc_info.value.status_code == 429

    @patch("dvc_osf.api.requests.Session.request")
    def test_500_server_error(self, mock_request):
        """Test that 500 raises retryable OSFAPIError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token", max_retries=0)
        with pytest.raises(OSFAPIError) as exc_info:
            client.get("/test")

        assert exc_info.value.status_code == 500
        assert exc_info.value.retryable is True


class TestRetryLogic:
    """Tests for retry logic with exponential backoff."""

    @patch("dvc_osf.api.requests.Session.request")
    @patch("dvc_osf.api.time.sleep")
    def test_retry_on_500_error(self, mock_sleep, mock_request):
        """Test retry on 500 server error."""
        # First two attempts fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.json.return_value = {}

        mock_response_success = Mock()
        mock_response_success.status_code = 200

        mock_request.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success,
        ]

        client = OSFAPIClient(token="test_token", max_retries=3)
        response = client.get("/test")

        assert response.status_code == 200
        assert mock_request.call_count == 3
        assert mock_sleep.call_count == 2  # Two retries

    @patch("dvc_osf.api.requests.Session.request")
    @patch("dvc_osf.api.time.sleep")
    def test_retry_on_connection_error(self, mock_sleep, mock_request):
        """Test retry on connection error."""
        # First two attempts fail with connection error, third succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200

        mock_request.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            mock_response_success,
        ]

        client = OSFAPIClient(token="test_token", max_retries=3)
        response = client.get("/test")

        assert response.status_code == 200
        assert mock_request.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("dvc_osf.api.requests.Session.request")
    def test_no_retry_on_401_error(self, mock_request):
        """Test no retry on authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token", max_retries=3)
        with pytest.raises(OSFAuthenticationError):
            client.get("/test")

        # Should only try once (no retries for 401)
        assert mock_request.call_count == 1

    @patch("dvc_osf.api.requests.Session.request")
    @patch("dvc_osf.api.time.sleep")
    def test_exponential_backoff(self, mock_sleep, mock_request):
        """Test exponential backoff delays."""
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503
        mock_response_fail.json.return_value = {}

        mock_request.return_value = mock_response_fail

        client = OSFAPIClient(token="test_token", max_retries=3)
        with pytest.raises(OSFAPIError):
            client.get("/test")

        # Check that sleep was called with increasing delays
        assert mock_sleep.call_count == 3
        # Backoff should be 2^1, 2^2, 2^3 = 2, 4, 8
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert calls[0] == 2.0
        assert calls[1] == 4.0
        assert calls[2] == 8.0


class TestRateLimitHandling:
    """Tests for rate limit handling with Retry-After header."""

    @patch("dvc_osf.api.requests.Session.request")
    @patch("dvc_osf.api.time.sleep")
    def test_rate_limit_with_retry_after_header(self, mock_sleep, mock_request):
        """Test rate limit handling with Retry-After header."""
        # First request hits rate limit, second succeeds
        mock_response_rate_limit = Mock()
        mock_response_rate_limit.status_code = 429
        mock_response_rate_limit.json.return_value = {}
        mock_response_rate_limit.headers = {"Retry-After": "60"}

        mock_response_success = Mock()
        mock_response_success.status_code = 200

        mock_request.side_effect = [
            mock_response_rate_limit,
            mock_response_success,
        ]

        client = OSFAPIClient(token="test_token", max_retries=3)
        response = client.get("/test")

        assert response.status_code == 200
        assert mock_sleep.call_count == 1
        # Should sleep for the retry-after duration
        assert mock_sleep.call_args[0][0] == 60

    @patch("dvc_osf.api.requests.Session.request")
    @patch("dvc_osf.api.time.sleep")
    def test_rate_limit_without_retry_after(self, mock_sleep, mock_request):
        """Test rate limit handling without Retry-After header."""
        mock_response_rate_limit = Mock()
        mock_response_rate_limit.status_code = 429
        mock_response_rate_limit.json.return_value = {}
        mock_response_rate_limit.headers = {}

        mock_response_success = Mock()
        mock_response_success.status_code = 200

        mock_request.side_effect = [
            mock_response_rate_limit,
            mock_response_success,
        ]

        client = OSFAPIClient(token="test_token", max_retries=3)
        response = client.get("/test")

        assert response.status_code == 200
        assert mock_sleep.call_count == 1
        # Should use exponential backoff (2^1 = 2)
        assert mock_sleep.call_args[0][0] == 2.0


class TestPaginationLogic:
    """Tests for pagination with get_paginated method."""

    @patch("dvc_osf.api.requests.Session.request")
    def test_pagination_single_page(self, mock_request):
        """Test pagination with single page of results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "1"}, {"id": "2"}],
            "links": {},
        }
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        items = list(client.get_paginated("/nodes"))

        assert len(items) == 2
        assert items[0]["id"] == "1"
        assert items[1]["id"] == "2"

    @patch("dvc_osf.api.requests.Session.request")
    def test_pagination_multiple_pages(self, mock_request):
        """Test pagination with multiple pages."""
        mock_response_page1 = Mock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "data": [{"id": "1"}, {"id": "2"}],
            "links": {"next": "https://api.osf.io/v2/nodes?page=2"},
        }

        mock_response_page2 = Mock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = {
            "data": [{"id": "3"}, {"id": "4"}],
            "links": {},
        }

        mock_request.side_effect = [mock_response_page1, mock_response_page2]

        client = OSFAPIClient(token="test_token")
        items = list(client.get_paginated("/nodes"))

        assert len(items) == 4
        assert mock_request.call_count == 2

    @patch("dvc_osf.api.requests.Session.request")
    def test_pagination_empty_results(self, mock_request):
        """Test pagination with empty results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [],
            "links": {},
        }
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        items = list(client.get_paginated("/nodes"))

        assert len(items) == 0


class TestContextManager:
    """Tests for context manager support."""

    def test_context_manager(self):
        """Test using client as context manager."""
        with OSFAPIClient(token="test_token") as client:
            assert isinstance(client, OSFAPIClient)
            assert client.session is not None

    @patch("dvc_osf.api.requests.Session.close")
    def test_context_manager_closes_session(self, mock_close):
        """Test that context manager closes session."""
        with OSFAPIClient(token="test_token"):
            pass

        mock_close.assert_called_once()


class TestErrorMessageExtraction:
    """Tests for extracting error messages from API responses."""

    @patch("dvc_osf.api.requests.Session.request")
    def test_extract_error_from_errors_array(self, mock_request):
        """Test extracting error message from errors array."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": [{"detail": "Invalid request parameters"}]
        }
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        with pytest.raises(OSFAPIError) as exc_info:
            client.get("/test")

        assert "Invalid request parameters" in str(exc_info.value)

    @patch("dvc_osf.api.requests.Session.request")
    def test_extract_error_from_detail_field(self, mock_request):
        """Test extracting error message from detail field."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Resource not found"}
        mock_request.return_value = mock_response

        client = OSFAPIClient(token="test_token")
        with pytest.raises(OSFNotFoundError) as exc_info:
            client.get("/test")

        assert "Resource not found" in str(exc_info.value)
