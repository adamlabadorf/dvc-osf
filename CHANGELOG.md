# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Phase 3: Write Operations

- **Complete Write Operation Support**
  - File upload operations: `put_file()`, `put()` with streaming for large files
  - File deletion: `rm()`, `rm_file()` with recursive support
  - Directory operations: `mkdir()`, `rmdir()` (no-op per OSF virtual directories)
  - Write mode file handles: `open(mode='wb')` with `OSFWriteFile` class
  - Automatic file versioning on overwrites (OSF native behavior)
  
- **Upload Features**
  - Streaming uploads for large files (>5MB default) with configurable chunk size
  - MD5 checksum verification for upload integrity
  - Progress callback support: `callback(bytes_uploaded, total_bytes)`
  - Configurable upload timeout (default: 300 seconds)
  - Memory-efficient single-request streaming (OSF API constraint)
  
- **Error Handling for Write Operations**
  - New exception types: `QuotaExceededError`, `FileLockedError`, `VersionConflictError`, `InsufficientStorageError`, `UploadError`
  - Detailed error messages with remediation suggestions
  - Bytes uploaded tracking in upload-related exceptions
  - Smart retry logic (retry transient errors, skip version conflicts)
  
- **Upload Utilities**
  - `compute_upload_checksum()` - MD5 computation during uploads
  - `chunk_file()` - Generator for streaming file data in chunks
  - `format_bytes()` - Human-readable byte counts for error messages
  - `get_file_size()` - Extract size from file-like objects
  - `determine_upload_strategy()` - Choose single vs chunked upload
  - `ProgressTracker` class - Manage upload progress callbacks
  
- **Configuration Options**
  - `OSF_UPLOAD_CHUNK_SIZE` - Chunk size for streaming uploads (default: 5MB)
  - `OSF_UPLOAD_TIMEOUT` - Timeout for upload operations (default: 300s)
  - `OSF_WRITE_BUFFER_SIZE` - Buffer size for write file objects (default: 8KB)
  
- **Testing - Phase 3**
  - 240 total unit tests with 73% coverage for write operations
  - 18 integration tests (11 write-specific, 7 roundtrip tests)
  - Roundtrip tests: small files, large files (6MB), special characters, binary data, empty files
  - All integration tests passing (100% pass rate)
  - Error scenario coverage: quota exceeded, file locked, version conflicts, integrity errors

### Added - Phase 1: Read Operations

- **Core OSF Filesystem Implementation (Phase 1 - Read-Only)**
  - Complete OSF API v2 client with authentication, retry logic, and rate limiting
  - OSF filesystem with read-only operations: `exists()`, `ls()`, `info()`, `open()`, `get_file()`
  - Streaming file downloads with chunked reading for memory efficiency
  - MD5 checksum verification during file downloads
  - Connection pooling and HTTP session management
  - Exponential backoff retry logic for transient failures
  - Smart rate limit handling with `Retry-After` header support
  - Comprehensive error handling with custom exception hierarchy
  
- **Authentication**
  - Multi-source token retrieval (explicit parameter, DVC config, environment variable)
  - Personal Access Token (PAT) support
  - Token validation and secure handling (never logged)
  
- **Path Handling**
  - OSF URL parsing: `osf://PROJECT_ID/PROVIDER/PATH` format
  - Project ID validation
  - Default provider support (`osfstorage`)
  - Path normalization and manipulation utilities
  
- **Configuration**
  - Environment variable support for all client settings
  - Configurable timeouts, retries, chunk sizes, and connection pools
  - Smart defaults optimized for typical use cases
  
- **Testing - Phase 1**
  - 168 unit tests with 84% code coverage
  - 14 integration tests with real OSF project
  - Comprehensive mocking of OSF API responses
  - Test fixtures for common scenarios
  - Integration test infrastructure with automatic skipping when credentials unavailable
  
- **Documentation**
  - Complete configuration guide with all options documented
  - Troubleshooting section for common issues
  - Examples for programmatic use and fsspec integration
  - Integration test setup documentation

### Changed
- Updated package dependencies: added `urllib3>=1.26.0`, `requests-cache>=1.0.0` (optional)
- Enhanced README with write operation examples and full read/write capability documentation
- Improved error messages for better debugging with upload-specific context
- Enhanced exception hierarchy with upload-specific errors and attributes

### Fixed
- OSF API file lookups now correctly search parent directories (OSF doesn't support direct path queries)
- Download links now use `files.osf.io` endpoint with Bearer auth (not `osf.io/download`)
- Root directory queries handle list responses correctly
- Upload operations correctly use single-request streaming (OSF doesn't support multi-request chunked uploads)

### Fixed
- OSF API file lookups now correctly search parent directories (OSF doesn't support direct path queries)
- Download links now use `files.osf.io` endpoint with Bearer auth (not `osf.io/download`)
- Root directory queries handle list responses correctly

### Technical Details
- **Architecture**: Extends `dvc_objects.fs.base.ObjectFileSystem`
- **API**: Uses OSF API v2 (`https://api.osf.io/v2`)
- **Authentication**: Bearer token in Authorization header
- **Streaming**: 8KB default chunk size, configurable via `OSF_CHUNK_SIZE`
- **Retries**: 3 attempts with 2x exponential backoff by default
- **Checksums**: MD5 verification on all downloads

### Limitations (Current)
- osfstorage provider only (add-on providers planned for future)
- Subdirectory uploads not yet implemented (root-level uploads fully supported)
- Append operations not supported (OSF API constraint)
- Sequential operations (no parallelization yet)
- No resume capability for interrupted uploads/downloads

## [0.1.0] - 2026-02-13

### Added
- Initial release
- Basic project scaffolding
- DVC and fsspec entry points configuration
- OSFFileSystem placeholder implementation
- OSF API client placeholder
- Authentication handling structure
- Custom exception classes
- Utility functions for OSF URL handling
- Configuration management

### Notes
- This is an alpha release with placeholder implementations
- Actual OSF filesystem operations not yet implemented
- Focus is on establishing project structure and development workflow
