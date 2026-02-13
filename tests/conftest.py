"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def osf_token():
    """Provide a test OSF token."""
    return "test_token_12345"


@pytest.fixture
def osf_project_id():
    """Provide a test OSF project ID."""
    return "test_project_abc123"


@pytest.fixture
def mock_osf_client(osf_token):
    """Provide a mock OSF API client for testing."""
    from dvc_osf.api import OSFClient

    client = OSFClient(token=osf_token)
    return client


@pytest.fixture
def mock_osf_filesystem(osf_token, osf_project_id):
    """Provide a mock OSF filesystem for testing."""
    from dvc_osf.filesystem import OSFFileSystem

    fs = OSFFileSystem(token=osf_token, project_id=osf_project_id)
    return fs


@pytest.fixture
def sample_file_metadata():
    """Provide sample file metadata from OSF API."""
    return {
        "data": {
            "id": "file123",
            "type": "files",
            "attributes": {
                "name": "test.txt",
                "size": 1024,
                "path": "/test.txt",
                "materialized_path": "/test.txt",
            },
        }
    }


@pytest.fixture
def sample_project_metadata():
    """Provide sample project metadata from OSF API."""
    return {
        "data": {
            "id": "proj123",
            "type": "nodes",
            "attributes": {
                "title": "Test Project",
                "description": "A test project",
                "public": True,
            },
        }
    }
