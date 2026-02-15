# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
  
- **Testing**
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
- Enhanced README with accurate Phase 1 limitations and capabilities
- Improved error messages for better debugging

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

### Limitations (Phase 1)
- Read-only operations only (write operations planned for Phase 2)
- osfstorage provider only (add-on providers planned for future)
- Sequential downloads (no parallelization yet)
- No resume capability for interrupted downloads

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
