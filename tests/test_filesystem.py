"""Tests for OSFFileSystem class."""

import pytest

from dvc_osf.filesystem import OSFFileSystem


def test_osf_filesystem_init(osf_token, osf_project_id):
    """Test OSFFileSystem initialization."""
    fs = OSFFileSystem(token=osf_token, project_id=osf_project_id)
    assert fs.token == osf_token
    assert fs.project_id == osf_project_id


def test_osf_filesystem_protocol():
    """Test that OSFFileSystem has correct protocol."""
    assert OSFFileSystem.protocol == "osf"


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_filesystem_open():
    """Test opening files on OSF."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_filesystem_ls():
    """Test listing directory contents on OSF."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_filesystem_info():
    """Test getting file/directory info on OSF."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_filesystem_mkdir():
    """Test creating directories on OSF."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_filesystem_rm():
    """Test removing files/directories on OSF."""
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_osf_filesystem_exists():
    """Test checking if path exists on OSF."""
    pass
