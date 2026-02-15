"""Tests for OSF configuration module."""

from dvc_osf.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_api_base_url(self):
        """Test default API base URL."""
        assert Config.API_BASE_URL == "https://api.osf.io/v2"

    def test_default_timeout(self):
        """Test default timeout."""
        assert Config.DEFAULT_TIMEOUT == 30

    def test_default_max_retries(self):
        """Test default max retries."""
        assert Config.MAX_RETRIES == 3

    def test_default_retry_backoff(self):
        """Test default retry backoff."""
        assert Config.RETRY_BACKOFF == 2.0

    def test_default_chunk_size(self):
        """Test default chunk size."""
        assert Config.CHUNK_SIZE == 8192

    def test_default_connection_pool_size(self):
        """Test default connection pool size."""
        assert Config.CONNECTION_POOL_SIZE == 10

    def test_default_provider(self):
        """Test default storage provider."""
        assert Config.DEFAULT_PROVIDER == "osfstorage"

    def test_min_project_id_length(self):
        """Test minimum project ID length."""
        assert Config.MIN_PROJECT_ID_LENGTH == 5

    def test_env_var_api_url(self, monkeypatch):
        """Test API URL override via environment variable."""
        monkeypatch.setenv("OSF_API_URL", "https://test.osf.io/v2")
        # Need to reload the module to pick up env var
        import importlib

        from dvc_osf import config

        importlib.reload(config)
        assert config.Config.API_BASE_URL == "https://test.osf.io/v2"

        # Restore original
        importlib.reload(config)

    def test_env_var_timeout(self, monkeypatch):
        """Test timeout override via environment variable."""
        monkeypatch.setenv("OSF_TIMEOUT", "60")
        import importlib

        from dvc_osf import config

        importlib.reload(config)
        assert config.Config.DEFAULT_TIMEOUT == 60

        # Restore original
        importlib.reload(config)

    def test_env_var_max_retries(self, monkeypatch):
        """Test max retries override via environment variable."""
        monkeypatch.setenv("OSF_MAX_RETRIES", "5")
        import importlib

        from dvc_osf import config

        importlib.reload(config)
        assert config.Config.MAX_RETRIES == 5

        # Restore original
        importlib.reload(config)

    def test_env_var_retry_backoff(self, monkeypatch):
        """Test retry backoff override via environment variable."""
        monkeypatch.setenv("OSF_RETRY_BACKOFF", "3.0")
        import importlib

        from dvc_osf import config

        importlib.reload(config)
        assert config.Config.RETRY_BACKOFF == 3.0

        # Restore original
        importlib.reload(config)

    def test_env_var_chunk_size(self, monkeypatch):
        """Test chunk size override via environment variable."""
        monkeypatch.setenv("OSF_CHUNK_SIZE", "16384")
        import importlib

        from dvc_osf import config

        importlib.reload(config)
        assert config.Config.CHUNK_SIZE == 16384

        # Restore original
        importlib.reload(config)

    def test_env_var_pool_size(self, monkeypatch):
        """Test connection pool size override via environment variable."""
        monkeypatch.setenv("OSF_POOL_SIZE", "20")
        import importlib

        from dvc_osf import config

        importlib.reload(config)
        assert config.Config.CONNECTION_POOL_SIZE == 20

        # Restore original
        importlib.reload(config)
