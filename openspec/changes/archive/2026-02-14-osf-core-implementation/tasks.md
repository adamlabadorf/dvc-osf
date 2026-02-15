# Implementation Tasks

## 1. Update Dependencies and Configuration

- [x] 1.1 Add `requests>=2.28.0` to pyproject.toml dependencies
- [x] 1.2 Add `urllib3>=1.26.0` to pyproject.toml dependencies
- [x] 1.3 Add `dvc-objects>=5.0.0` to pyproject.toml dependencies
- [x] 1.4 Add `requests-cache>=1.0.0` to pyproject.toml optional dependencies under 'cache' group
- [x] 1.5 Run `uv lock` to update uv.lock with new dependencies
- [x] 1.6 Run `poetry lock` to update poetry.lock with new dependencies
- [x] 1.7 Verify entry points in pyproject.toml reference OSFFileSystem correctly

## 2. Implement Exception Hierarchy

- [x] 2.1 Define `OSFException` base class in exceptions.py
- [x] 2.2 Define `OSFAuthenticationError(OSFException, PermissionError)` for auth failures
- [x] 2.3 Define `OSFNotFoundError(OSFException, FileNotFoundError)` for 404 errors
- [x] 2.4 Define `OSFPermissionError(OSFException, PermissionError)` for 403 errors
- [x] 2.5 Define `OSFConnectionError(OSFException, ConnectionError)` for network errors
- [x] 2.6 Define `OSFRateLimitError(OSFException, ConnectionError)` for rate limiting
- [x] 2.7 Define `OSFAPIError(OSFException)` for general API errors
- [x] 2.8 Define `OSFIntegrityError(OSFException)` for checksum mismatches
- [x] 2.9 Add `retryable` attribute to exception classes (True for transient errors)
- [x] 2.10 Add `status_code` and `response` attributes to API error classes

## 3. Implement Configuration Module

- [x] 3.1 Create `Config` class in config.py with API_BASE_URL constant (default: https://api.osf.io/v2)
- [x] 3.2 Add DEFAULT_TIMEOUT constant (default: 30 seconds)
- [x] 3.3 Add MAX_RETRIES constant (default: 3)
- [x] 3.4 Add RETRY_BACKOFF constant (default: 2.0 for exponential backoff)
- [x] 3.5 Add CHUNK_SIZE constant (default: 8192 bytes)
- [x] 3.6 Add CONNECTION_POOL_SIZE constant (default: 10)
- [x] 3.7 Support environment variable overrides (OSF_API_URL, OSF_TIMEOUT, OSF_MAX_RETRIES, etc.)

## 4. Implement Path Handling Utilities

- [x] 4.1 Create `parse_osf_url()` function in utils.py to parse osf://PROJECT_ID/PROVIDER/PATH format
- [x] 4.2 Implement project ID validation (alphanumeric, minimum 5 characters)
- [x] 4.3 Implement default storage provider ('osfstorage') when not specified
- [x] 4.4 Create `normalize_path()` function to remove leading/trailing slashes and collapse multiple slashes
- [x] 4.5 Create `join_path()` function to join path components correctly
- [x] 4.6 Create `path_to_api_url()` function to convert (project_id, provider, path) to OSF API endpoint
- [x] 4.7 Implement URL encoding for special characters while preserving forward slashes
- [x] 4.8 Create `serialize_path()` function to convert internal representation back to osf:// URL
- [x] 4.9 Add path component extraction utilities (get_filename, get_directory, get_parent)
- [x] 4.10 Validate OSF URL scheme and raise ValueError for invalid formats

## 5. Implement Authentication Module

- [x] 5.1 Create `get_token()` function in auth.py to retrieve token from multiple sources
- [x] 5.2 Implement token retrieval from function parameter (highest priority)
- [x] 5.3 Implement token retrieval from DVC config (medium priority)
- [x] 5.4 Implement token retrieval from OSF_TOKEN environment variable (lowest priority)
- [x] 5.5 Create `validate_token()` function to check token format (non-empty string)
- [x] 5.6 Add logic to never log or expose tokens in error messages
- [x] 5.7 Create helper to format Bearer token header: 'Authorization: Bearer <token>'
- [x] 5.8 Raise OSFAuthenticationError with helpful message when token is missing or invalid

## 6. Implement OSF API Client

- [x] 6.1 Create `OSFAPIClient` class in api.py with initialization for base_url and token
- [x] 6.2 Create requests.Session in __init__ for connection pooling
- [x] 6.3 Configure HTTPAdapter with connection pool size and retry settings
- [x] 6.4 Implement `_request()` method for common request logic with timeout and headers
- [x] 6.5 Implement `get()` method for HTTP GET requests with query parameter support
- [x] 6.6 Implement `post()` method for HTTP POST requests with JSON payload
- [x] 6.7 Implement `put()` method for HTTP PUT requests with file streaming
- [x] 6.8 Implement `delete()` method for HTTP DELETE requests
- [x] 6.9 Implement `_handle_response()` method to map status codes to exceptions
- [x] 6.10 Map 400 → OSFAPIError, 401 → OSFAuthenticationError, 403 → OSFPermissionError, 404 → OSFNotFoundError, 429 → OSFRateLimitError
- [x] 6.11 Map 500/502/503 → OSFAPIError with retryable=True
- [x] 6.12 Extract error messages from response JSON when available
- [x] 6.13 Implement retry logic with exponential backoff for transient failures
- [x] 6.14 Implement special rate limit handling: check Retry-After header and use longer backoff
- [x] 6.15 Implement `download_file()` method with streaming support (stream=True)
- [x] 6.16 Implement `get_paginated()` method to automatically fetch all pages (follow links.next)
- [x] 6.17 Add `close()` method to close the session
- [x] 6.18 Add context manager support (__enter__ and __exit__)

## 7. Implement File-Like Object for Streaming

- [x] 7.1 Create `OSFFile` class in filesystem.py as file-like object wrapper
- [x] 7.2 Implement `read(size=-1)` method to read from streaming response
- [x] 7.3 Implement `readline()` method for text mode
- [x] 7.4 Implement `__iter__()` and `__next__()` for line iteration
- [x] 7.5 Implement `seek(offset, whence=0)` method (limited support for forward seeks)
- [x] 7.6 Implement `tell()` method to return current position
- [x] 7.7 Implement `close()` method to release response resources
- [x] 7.8 Add context manager support (__enter__ and __exit__)
- [x] 7.9 Track bytes read for position tracking
- [x] 7.10 Support both binary and text modes (decode UTF-8 in text mode)

## 8. Implement OSFFileSystem Class

- [x] 8.1 Create `OSFFileSystem` class in filesystem.py extending ObjectFileSystem
- [x] 8.2 Implement `__init__()` to parse osf:// URL and initialize API client
- [x] 8.3 Set protocol class attribute to 'osf'
- [x] 8.4 Store project_id, provider, and base_path from URL parsing
- [x] 8.5 Implement `_resolve_path()` helper to convert relative paths to (project_id, provider, path) tuples
- [x] 8.6 Implement `exists(path)` method by calling OSF API files endpoint and checking for 404
- [x] 8.7 Implement `ls(path, detail=False)` method to list directory contents via API
- [x] 8.8 Handle pagination in ls() for directories with many files
- [x] 8.9 Return detailed metadata when detail=True, just names/paths when detail=False
- [x] 8.10 Implement `info(path)` method to get file metadata (name, size, type, modified, checksum)
- [x] 8.11 Parse OSF API response to extract relevant metadata fields
- [x] 8.12 Implement `open(path, mode='rb')` method for reading files
- [x] 8.13 Raise NotImplementedError for write modes (w, wb, a, ab)
- [x] 8.14 Return OSFFile instance for read operations with streaming
- [x] 8.15 Implement `get_file(rpath, lpath)` method to download file to local path
- [x] 8.16 Stream download in chunks to avoid memory issues
- [x] 8.17 Compute MD5 checksum during download
- [x] 8.18 Verify checksum against OSF metadata after download
- [x] 8.19 Raise OSFIntegrityError if checksum mismatch
- [x] 8.20 Create parent directories for local path if they don't exist
- [x] 8.21 Implement `_strip_protocol()` static method to remove osf:// prefix from URLs

## 9. Write Unit Tests

- [x] 9.1 Write tests for exception classes in test_exceptions.py (inheritance, attributes)
- [x] 9.2 Write tests for config module in test_config.py (constants, env var overrides)
- [x] 9.3 Write tests for path parsing in test_utils.py (parse_osf_url, normalize_path, join_path)
- [x] 9.4 Write tests for path validation in test_utils.py (invalid project IDs, malformed URLs)
- [x] 9.5 Write tests for path to API URL conversion in test_utils.py
- [x] 9.6 Write tests for token retrieval in test_auth.py (parameter, env var, DVC config)
- [x] 9.7 Write tests for token validation in test_auth.py (empty, invalid format)
- [x] 9.8 Write tests for API client initialization in test_api.py
- [x] 9.9 Mock requests.Session and test HTTP method implementations (get, post, put, delete)
- [x] 9.10 Test status code to exception mapping in test_api.py
- [x] 9.11 Test retry logic with mocked transient failures (500, 502, 503, connection errors)
- [x] 9.12 Test rate limit handling with mocked 429 responses and Retry-After header
- [x] 9.13 Test pagination logic with mocked paginated responses
- [x] 9.14 Write tests for OSFFile class in test_filesystem.py (read, seek, tell, close)
- [x] 9.15 Write tests for OSFFileSystem.exists() with mocked API responses
- [x] 9.16 Write tests for OSFFileSystem.ls() with mocked directory listings
- [x] 9.17 Write tests for OSFFileSystem.info() with mocked file metadata
- [x] 9.18 Write tests for OSFFileSystem.open() with mocked file content
- [x] 9.19 Write tests for OSFFileSystem.get_file() with mocked downloads and checksum verification
- [x] 9.20 Create mock API response fixtures in tests/fixtures/ directory
- [x] 9.21 Achieve >80% code coverage across all modules (84% achieved)

## 10. Write Integration Tests

- [x] 10.1 Create test_osf_read.py in tests/integration/ directory
- [x] 10.2 Add pytest marker for integration tests: @pytest.mark.integration
- [x] 10.3 Skip integration tests if OSF_TEST_TOKEN environment variable not set
- [x] 10.4 Test OSFFileSystem initialization with real OSF project
- [x] 10.5 Test exists() on real OSF files and directories
- [x] 10.6 Test ls() on real OSF directories
- [x] 10.7 Test info() on real OSF files
- [x] 10.8 Test open() and read from real OSF files
- [x] 10.9 Test get_file() download from real OSF project
- [x] 10.10 Test error scenarios (invalid project ID, missing file, invalid token)
- [x] 10.11 Document OSF test project setup in tests/integration/README.md

## 11. Update Documentation

- [x] 11.1 Update README.md with usage examples for OSF remote configuration
- [x] 11.2 Document osf:// URL format in docs/configuration.md
- [x] 11.3 Document authentication setup (OSF_TOKEN env var, DVC remote config) in docs/configuration.md
- [x] 11.4 Document supported operations (exists, ls, info, open, get_file) in docs/configuration.md
- [x] 11.5 Document limitations (read-only, no write operations, osfstorage only) in README.md
- [x] 11.6 Add troubleshooting section for common errors (auth failures, network issues) in docs/configuration.md
- [x] 11.7 Update CHANGELOG.md with new functionality

## 12. Verify and Test

- [x] 12.1 Run all unit tests: `pytest tests/ -v --cov=dvc_osf --cov-report=term-missing`
- [x] 12.2 Verify code coverage is >80%
- [x] 12.3 Run integration tests with test OSF project: `pytest tests/integration/ -v -m integration`
- [x] 12.4 Run type checking: `mypy dvc_osf/`
- [x] 12.5 Run linting: `flake8 dvc_osf/`
- [x] 12.6 Run code formatting: `black dvc_osf/ tests/` and verify no changes needed
- [x] 12.7 Run import sorting: `isort dvc_osf/ tests/` and verify no changes needed
- [x] 12.8 Test package build: `uv build` and verify success
- [x] 12.9 Test package installation: `pip install -e .` and verify OSFFileSystem can be imported
- [x] 12.10 Test DVC integration manually: configure OSF remote and try `dvc pull` on test data
- [x] 12.11 Verify entry points are registered: check `fsspec.get_filesystem_class('osf')`
- [x] 12.12 Run pre-commit hooks: `pre-commit run --all-files`
