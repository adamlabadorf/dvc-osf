"""Configuration management for DVC-OSF."""

import os


class Config:
    """Configuration constants for OSF API client and filesystem."""

    # OSF API configuration
    API_BASE_URL = os.getenv("OSF_API_URL", "https://api.osf.io/v2")

    # Request timeout in seconds
    DEFAULT_TIMEOUT = int(os.getenv("OSF_TIMEOUT", "30"))

    # Retry configuration
    MAX_RETRIES = int(os.getenv("OSF_MAX_RETRIES", "3"))
    RETRY_BACKOFF = float(os.getenv("OSF_RETRY_BACKOFF", "2.0"))

    # Streaming configuration
    CHUNK_SIZE = int(os.getenv("OSF_CHUNK_SIZE", "8192"))

    # Connection pooling
    CONNECTION_POOL_SIZE = int(os.getenv("OSF_POOL_SIZE", "10"))

    # Storage provider default
    DEFAULT_PROVIDER = "osfstorage"

    # Minimum project ID length
    MIN_PROJECT_ID_LENGTH = 5
