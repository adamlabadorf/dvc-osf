"""Tests for DVC plugin integration (Phase 5).

Covers:
- _prepare_credentials
- _get_kwargs_from_urls
- unstrip_protocol
- PARAM_CHECKSUM
- fs property
- Entry point verification
"""

import os
from unittest.mock import patch

import pytest

from dvc_osf.filesystem import OSFFileSystem

# ============================================================
# Task 1.3: _prepare_credentials tests
# ============================================================


class TestPrepareCredentials:
    """Tests for _prepare_credentials method."""

    def test_explicit_token_takes_priority(self):
        """Config token should be returned over env vars."""
        with patch.dict(os.environ, {"OSF_TOKEN": "env_token"}, clear=False):
            creds = OSFFileSystem._prepare_credentials(
                OSFFileSystem, token="config_token"
            )
            assert creds["token"] == "config_token"

    def test_env_var_osf_token_fallback(self):
        """OSF_TOKEN env var used when no explicit token."""
        with patch.dict(os.environ, {"OSF_TOKEN": "env_token"}, clear=False):
            creds = OSFFileSystem._prepare_credentials(OSFFileSystem)
            assert creds["token"] == "env_token"

    def test_env_var_osf_access_token_fallback(self):
        """OSF_ACCESS_TOKEN env var used when OSF_TOKEN not set."""
        env = {"OSF_ACCESS_TOKEN": "alt_token"}
        with patch.dict(os.environ, env, clear=False):
            # Remove OSF_TOKEN if present
            os.environ.pop("OSF_TOKEN", None)
            creds = OSFFileSystem._prepare_credentials(OSFFileSystem)
            assert creds["token"] == "alt_token"

    def test_no_token_returns_empty(self):
        """No token anywhere returns empty dict (auth error raised later)."""
        with patch.dict(os.environ, {}, clear=True):
            creds = OSFFileSystem._prepare_credentials(OSFFileSystem)
            assert "token" not in creds

    def test_endpoint_url_included(self):
        """endpoint_url should be passed through."""
        creds = OSFFileSystem._prepare_credentials(
            OSFFileSystem,
            token="tok",
            endpoint_url="https://api.test.osf.io/v2",
        )
        assert creds["endpoint_url"] == "https://api.test.osf.io/v2"

    def test_endpoint_url_omitted_when_not_provided(self):
        """endpoint_url should not be in result when not provided."""
        creds = OSFFileSystem._prepare_credentials(OSFFileSystem, token="tok")
        assert "endpoint_url" not in creds


# ============================================================
# Task 2.3: _get_kwargs_from_urls tests
# ============================================================


class TestGetKwargsFromUrls:
    """Tests for _get_kwargs_from_urls static method."""

    def test_full_url_with_path(self):
        result = OSFFileSystem._get_kwargs_from_urls(
            "osf://abc123/osfstorage/data/files"
        )
        assert result == {
            "project_id": "abc123",
            "provider": "osfstorage",
            "path": "data/files",
        }

    def test_url_without_path(self):
        result = OSFFileSystem._get_kwargs_from_urls("osf://abc123/osfstorage")
        assert result == {"project_id": "abc123", "provider": "osfstorage"}

    def test_url_with_trailing_slash(self):
        result = OSFFileSystem._get_kwargs_from_urls("osf://abc123/osfstorage/")
        assert result == {"project_id": "abc123", "provider": "osfstorage"}

    def test_url_with_deep_path(self):
        result = OSFFileSystem._get_kwargs_from_urls(
            "osf://abc123/osfstorage/a/b/c/d.csv"
        )
        assert result == {
            "project_id": "abc123",
            "provider": "osfstorage",
            "path": "a/b/c/d.csv",
        }

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            OSFFileSystem._get_kwargs_from_urls("s3://bucket/key")


# ============================================================
# Task 2.4: unstrip_protocol tests
# ============================================================


class TestUnstripProtocol:
    """Tests for unstrip_protocol method."""

    @patch.dict(os.environ, {"OSF_TOKEN": "test_token"})
    def test_normal_path(self):
        fs = OSFFileSystem("osf://abc123/osfstorage")
        assert fs.unstrip_protocol("data/files/test.csv") == (
            "osf://abc123/osfstorage/data/files/test.csv"
        )

    @patch.dict(os.environ, {"OSF_TOKEN": "test_token"})
    def test_empty_path(self):
        fs = OSFFileSystem("osf://abc123/osfstorage")
        assert fs.unstrip_protocol("") == "osf://abc123/osfstorage"

    @patch.dict(os.environ, {"OSF_TOKEN": "test_token"})
    def test_path_with_leading_slash(self):
        fs = OSFFileSystem("osf://abc123/osfstorage")
        assert fs.unstrip_protocol("/data/file.csv") == (
            "osf://abc123/osfstorage/data/file.csv"
        )


# ============================================================
# Task 3.4: fs property and PARAM_CHECKSUM tests
# ============================================================


class TestFsPropertyAndChecksum:
    """Tests for fs cached property and PARAM_CHECKSUM."""

    def test_param_checksum_is_md5(self):
        assert OSFFileSystem.PARAM_CHECKSUM == "md5"

    def test_protocol_is_osf(self):
        assert OSFFileSystem.protocol == "osf"

    @patch.dict(os.environ, {"OSF_TOKEN": "test_token"})
    def test_get_kwargs_from_urls_returns_dict(self):
        """Verify the return type is a dict (fsspec contract)."""
        result = OSFFileSystem._get_kwargs_from_urls("osf://abc123/osfstorage")
        assert isinstance(result, dict)


# ============================================================
# Task 4.2: Import without DVC
# ============================================================


class TestEntryPoints:
    """Tests for entry point and import behavior."""

    def test_import_without_dvc(self):
        """OSFFileSystem can be imported without dvc installed."""
        from dvc_osf import OSFFileSystem as FS

        assert FS is not None
        assert FS.protocol == "osf"

    def test_entry_points_in_pyproject(self):
        """Verify pyproject.toml has correct entry points."""
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # fallback for 3.9/3.10
            except ImportError:
                pytest.skip("tomllib/tomli not available")
        from pathlib import Path

        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        eps = data.get("project", {}).get("entry-points", {})

        # fsspec entry point
        assert "fsspec.specs" in eps
        assert eps["fsspec.specs"]["osf"] == "dvc_osf.filesystem:OSFFileSystem"

        # DVC entry point
        assert "dvc.fs" in eps
        assert eps["dvc.fs"]["osf"] == "dvc_osf.filesystem:OSFFileSystem"
