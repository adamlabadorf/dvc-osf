"""Tests for OSF API client."""

import pytest

from dvc_osf.api import OSFClient


def test_osf_client_init(osf_token):
    """Test OSFClient initialization."""
    client = OSFClient(token=osf_token)
    assert client.token == osf_token
    assert "Authorization" in client.session.headers


def test_osf_client_base_url():
    """Test that OSFClient has correct base URL."""
    assert OSFClient.BASE_URL == "https://api.osf.io/v2/"


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_get():
    """Test GET request to OSF API."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_post():
    """Test POST request to OSF API."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_put():
    """Test PUT request to OSF API."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_delete():
    """Test DELETE request to OSF API."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_get_project():
    """Test getting project information."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_list_files():
    """Test listing files in project."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_upload_file():
    """Test uploading file to project."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_download_file():
    """Test downloading file from project."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_client_delete_file():
    """Test deleting file from project."""
    pass
