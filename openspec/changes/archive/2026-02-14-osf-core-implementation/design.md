## Context

**Current State**: The dvc-osf project has a complete package structure with placeholder implementations. All foundational infrastructure (build config, testing, linting, CI/CD) is in place, but the core OSF integration does not exist yet.

**Background**: DVC requires filesystem plugins to extend `dvc_objects.fs.base.ObjectFileSystem` and implement a standard set of filesystem operations. OSF provides a REST API (v2) for file operations, but it has its own conventions for project/storage hierarchies and file access patterns that need to be abstracted into a filesystem interface.

**Constraints**:
- Must maintain Python 3.8+ compatibility
- Must implement the `ObjectFileSystem` abstract interface from dvc-objects
- Must register via both `fsspec.specs` and `dvc.fs` entry points
- Must handle OSF's rate limiting (documented but limits not publicly specified)
- Must work with OSF's specific URL structure: project IDs, storage providers, file paths
- Must support OSF's authentication via Personal Access Tokens (PAT)

**Stakeholders**: Researchers using DVC for data versioning who want to store data on OSF for open science practices.

## Goals / Non-Goals

**Goals:**
- Implement read-only filesystem operations (exists, ls, info, open for reading, get_file)
- Provide a robust OSF API client with proper authentication, error handling, and retries
- Parse and validate `osf://` URLs correctly
- Stream large files efficiently without loading entire files into memory
- Verify file integrity with checksums
- Achieve >80% code coverage with unit and integration tests
- Provide clear error messages for common failure scenarios

**Non-Goals:**
- Write operations (put, mkdir, cp, mv, rm) - deferred to future phase
- OSF file versioning support - deferred to future phase
- Support for OSF add-on storage providers (Dropbox, Google Drive, etc.) - MVP focuses on osfstorage only
- Advanced caching strategies - basic implementation only
- Parallel downloads - sequential downloads for MVP
- Resume capability for interrupted downloads - full re-download for MVP
- GUI or CLI tools beyond DVC integration - standard DVC commands only

## Decisions

### 1. API Client Architecture

**Decision**: Create a separate `OSFAPIClient` class in `api.py` rather than embedding API logic directly in `OSFFileSystem`.

**Rationale**:
- Separation of concerns: filesystem abstraction vs. HTTP client logic
- Easier testing: can mock the API client independently
- Reusability: API client can be used by other components
- Cleaner error handling: API-specific errors handled at API layer

**Alternatives Considered**:
- **Embed API calls in filesystem class**: Would mix concerns and make testing harder
- **Use existing osfclient library**: Not maintained, doesn't match our needs, adds unnecessary dependency

### 2. Authentication Strategy

**Decision**: Use session-based authentication with a single PAT stored in DVC remote config or environment variable.

**Rationale**:
- OSF API uses bearer token authentication (simple and stateless)
- DVC has built-in credential management for remotes
- Follows DVC conventions for other remotes (S3, GCS, etc.)
- No need for OAuth flows or token refresh (PATs are long-lived)

**Alternatives Considered**:
- **OAuth2 flow**: Too complex for CLI tool, requires browser interaction
- **Username/password**: Not supported by OSF API v2, less secure than PAT

### 3. Path Resolution Strategy

**Decision**: Parse `osf://PROJECT_ID/STORAGE_PROVIDER/PATH` format and maintain internal path representation as `(project_id, provider, path)` tuple.

**Rationale**:
- OSF API requires project ID and provider for all file operations
- Separating these components early simplifies API calls
- Allows validation at parse time rather than during operations
- Matches OSF's actual data model (projects contain storage providers contain files)

**Path Format**:
```
osf://abc123/osfstorage/data/dataset.csv
     |       |           |
     |       |           +-- File path within storage
     |       +-------------- Storage provider (default: osfstorage)
     +---------------------- OSF project/component ID
```

**Alternatives Considered**:
- **Flat path string**: Would require parsing for every API call, error-prone
- **Include OSF domain in URL**: Unnecessary, api.osf.io is the only production endpoint

### 4. Error Handling Strategy

**Decision**: Create custom exception hierarchy inheriting from built-in exceptions, with retry logic for transient failures.

**Exception Hierarchy**:
```
OSFException(Exception)
├── OSFAuthenticationError(OSFException, PermissionError)
├── OSFNotFoundError(OSFException, FileNotFoundError)
├── OSFPermissionError(OSFException, PermissionError)
├── OSFConnectionError(OSFException, ConnectionError)
├── OSFRateLimitError(OSFException, ConnectionError)
└── OSFAPIError(OSFException)
```

**Retry Strategy**:
- Automatic retry with exponential backoff for: 500, 502, 503, 504, connection errors
- Special handling for 429 (rate limit): exponential backoff with longer delays
- No retry for: 400, 401, 403, 404 (client errors that won't succeed on retry)
- Configurable max retries (default: 3) and timeout (default: 30s)

**Rationale**:
- Inheriting from built-in exceptions allows standard error handling patterns
- Retry logic handles transient network issues gracefully
- Rate limit handling prevents API abuse
- Clear exception types make debugging easier

**Alternatives Considered**:
- **Use generic exceptions**: Less informative, harder to handle specific cases
- **No retry logic**: Would fail on transient errors, poor user experience
- **Retry all errors**: Would waste time retrying client errors that won't succeed

### 5. File Streaming Strategy

**Decision**: Use `requests` with `stream=True` and yield chunks for file downloads. Implement checksums during streaming.

**Implementation**:
```python
def open(path, mode='rb'):
    response = api_client.download_file(path, stream=True)
    return StreamingFileObject(response, chunk_size=8192)
```

**Rationale**:
- Prevents loading entire files into memory
- Allows progress tracking (future enhancement)
- Matches how DVC handles large files
- Can compute checksums on-the-fly

**Alternatives Considered**:
- **Download to temp file first**: Wastes disk space, slower for large files
- **Load entire file into memory**: Fails for large files, high memory usage

### 6. Connection Pooling

**Decision**: Use `requests.Session` for connection pooling with `HTTPAdapter` for retry configuration.

**Configuration**:
- Pool size: 10 connections (balances performance with resource usage)
- Keep-alive: Enabled (reduces connection overhead for multiple operations)
- Retry configuration: Integrated with our custom retry strategy

**Rationale**:
- Reuses TCP connections for multiple requests
- Reduces latency for consecutive operations
- Built-in support in requests library
- Standard pattern for Python HTTP clients

**Alternatives Considered**:
- **No connection pooling**: Slower, more overhead for multiple operations
- **aiohttp for async**: More complex, not needed for MVP, DVC is synchronous

### 7. Checksum Strategy

**Decision**: Use MD5 checksums computed during streaming, compare with OSF-provided checksums from file metadata.

**Implementation**:
- Compute MD5 during download streaming
- Fetch expected checksum from OSF file metadata API
- Compare after download completes
- Raise `OSFIntegrityError` on mismatch

**Rationale**:
- OSF provides MD5 checksums in file metadata
- MD5 is fast and sufficient for integrity checking (not for security)
- Computing during streaming avoids second pass over data
- Matches DVC's checksum approach

**Alternatives Considered**:
- **SHA256**: More secure but slower, overkill for integrity checking
- **No verification**: Risks data corruption going undetected
- **Verify before download**: Can't detect corruption during transfer

### 8. Configuration Management

**Decision**: Use a `Config` class with constants for API endpoints, timeouts, retry settings. Support override via environment variables.

**Configuration Parameters**:
```python
class Config:
    API_BASE_URL = os.getenv('OSF_API_URL', 'https://api.osf.io/v2')
    DEFAULT_TIMEOUT = int(os.getenv('OSF_TIMEOUT', '30'))
    MAX_RETRIES = int(os.getenv('OSF_MAX_RETRIES', '3'))
    RETRY_BACKOFF = float(os.getenv('OSF_RETRY_BACKOFF', '2.0'))
    CHUNK_SIZE = int(os.getenv('OSF_CHUNK_SIZE', '8192'))
    CONNECTION_POOL_SIZE = int(os.getenv('OSF_POOL_SIZE', '10'))
```

**Rationale**:
- Centralized configuration is easier to maintain
- Environment variables allow testing and customization
- Default values work for most use cases
- Matches patterns from other DVC remotes

**Alternatives Considered**:
- **Hard-coded values**: Not flexible, hard to test
- **Config file**: Overkill for small set of parameters
- **DVC config only**: Need fallbacks for non-DVC usage

### 9. Testing Strategy

**Decision**: Three-tier testing: unit tests with mocks, integration tests with test OSF project, and type checking with mypy.

**Unit Tests**:
- Mock all OSF API responses using `responses` library
- Test each method in isolation
- Cover success and failure scenarios
- Target >80% code coverage

**Integration Tests**:
- Use real OSF test project (requires `OSF_TEST_TOKEN`)
- Skip if credentials not available (allows running in CI without secrets)
- Test round-trip operations (upload fixtures, download, verify)
- Use pytest markers: `@pytest.mark.integration`

**Type Checking**:
- Add type hints to all public APIs
- Run mypy in strict mode
- Helps catch errors early and improves IDE support

**Rationale**:
- Unit tests are fast and don't require external dependencies
- Integration tests catch real-world issues
- Type checking prevents common errors
- Matches project's existing testing strategy

**Alternatives Considered**:
- **Only integration tests**: Too slow, requires credentials, flaky
- **Only unit tests**: Misses real API behavior issues
- **VCR.py for recorded responses**: Complex, cassettes become stale

## Risks / Trade-offs

### Risk: OSF API Rate Limiting
**Impact**: Operations could fail if rate limit is hit
**Mitigation**:
- Implement exponential backoff for 429 responses
- Add configurable retry delays
- Document rate limit behavior in user guide
- Consider request caching in future phase

### Risk: OSF API Changes
**Impact**: Breaking changes in OSF API could break the plugin
**Mitigation**:
- Pin to OSF API v2 explicitly in all requests
- Monitor OSF API changelog
- Add integration tests to catch API changes early
- Version the plugin to allow users to pin to working version

### Risk: Large File Memory Usage
**Impact**: Very large files could cause memory issues
**Mitigation**:
- Use streaming for all file operations
- Process files in configurable chunks (default 8KB)
- Document memory usage characteristics
- Consider memory profiling in future optimization phase

### Risk: Network Failures During Download
**Impact**: Large downloads could fail partway through
**Mitigation**:
- Implement retry logic for transient failures
- Accept full re-download for MVP (no resume capability)
- Document limitation and add resume support in future phase
- DVC's cache layer provides some protection against re-downloads

### Risk: Authentication Token Security
**Impact**: Leaked tokens could compromise OSF projects
**Mitigation**:
- Document secure token storage practices
- Never log tokens
- Use DVC's credential management when possible
- Support environment variables as fallback
- Recommend minimum-scope tokens in documentation

### Trade-off: Read-Only Implementation
**Decision**: Implement only read operations in this phase
**Benefit**: Faster to implement, test, and validate
**Cost**: Can't use for `dvc push`, only `dvc pull`
**Justification**: De-risk the project by validating approach before adding write complexity

### Trade-off: Sequential Downloads
**Decision**: Download files one at a time (no parallelization)
**Benefit**: Simpler implementation, easier to debug
**Cost**: Slower for many small files
**Justification**: MVP focus, can optimize later based on real usage patterns

### Trade-off: OSFStorage Only
**Decision**: Support only osfstorage provider, not add-ons (Dropbox, etc.)
**Benefit**: Reduces complexity, focuses on core OSF functionality
**Cost**: Can't use add-on storage providers
**Justification**: Vast majority of OSF users use osfstorage, add-ons can be added later if needed

### Trade-off: MD5 Checksums
**Decision**: Use MD5 for integrity checking
**Benefit**: Fast, matches OSF's provided checksums
**Cost**: Not cryptographically secure (but not needed for integrity)
**Justification**: Sufficient for detecting corruption, matches OSF API capabilities
