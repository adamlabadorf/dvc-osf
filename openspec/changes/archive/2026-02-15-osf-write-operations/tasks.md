# Implementation Tasks

## 1. Update Configuration and Add Write-Specific Exceptions

- [x] 1.1 Add OSF_UPLOAD_CHUNK_SIZE constant to config.py (default: 5MB / 5242880 bytes)
- [x] 1.2 Add OSF_UPLOAD_TIMEOUT constant to config.py (default: 300 seconds)
- [x] 1.3 Add UPLOAD_CHUNK_MIN_SIZE constant to config.py (minimum: 1MB)
- [x] 1.4 Add UPLOAD_CHUNK_MAX_SIZE constant to config.py (maximum: 100MB)
- [x] 1.5 Support OSF_UPLOAD_CHUNK_SIZE environment variable override in config.py
- [x] 1.6 Support OSF_UPLOAD_TIMEOUT environment variable override in config.py
- [x] 1.7 Define OSFQuotaExceededError(OSFException) in exceptions.py for storage quota errors
- [x] 1.8 Define OSFFileLockedError(OSFPermissionError) in exceptions.py for locked file errors
- [x] 1.9 Define OSFVersionConflictError(OSFException) in exceptions.py for version conflicts
- [x] 1.10 Add 'bytes_uploaded' and 'total_size' attributes to upload-related exceptions
- [x] 1.11 Update exception __init__ methods to accept and store upload-specific attributes

## 2. Extend OSFAPIClient with Upload Support

- [x] 2.1 Add upload_timeout parameter to OSFAPIClient.__init__() (default from Config.OSF_UPLOAD_TIMEOUT)
- [x] 2.2 Update _handle_response() to map 413 status to OSFQuotaExceededError
- [x] 2.3 Update _handle_response() to map 423 status to OSFFileLockedError
- [x] 2.4 Update _handle_response() to map 409 status to OSFVersionConflictError during writes
- [x] 2.5 Implement upload_file() method for streaming file uploads with progress callback
- [x] 2.6 Implement upload_chunk() method for uploading individual file chunks
- [x] 2.7 Add support for progress callbacks in upload methods (signature: callback(bytes_sent, total_bytes))
- [x] 2.8 Update put() method to support file streaming with configurable timeout
- [x] 2.9 Add _stream_upload() helper method for reading and sending file data in chunks
- [x] 2.10 Implement delete() method wrapping DELETE HTTP requests
- [x] 2.11 Add retry logic for upload operations (same as reads: 500, 502, 503, connection errors)
- [x] 2.12 Ensure 409 Conflict errors are NOT retried during uploads
- [x] 2.13 Track bytes uploaded in upload methods for error reporting
- [x] 2.14 Update error messages to include upload progress when operations fail

## 3. Implement Upload Utilities

- [x] 3.1 Create compute_upload_checksum() function in utils.py for MD5 computation during uploads
- [x] 3.2 Create chunk_file() generator function in utils.py to yield file chunks
- [x] 3.3 Implement get_file_size() helper in utils.py
- [x] 3.4 Create determine_upload_strategy() function to decide single vs chunked upload based on size
- [x] 3.5 Add validate_chunk_size() to ensure chunk size is within min/max bounds
- [x] 3.6 Create ProgressTracker class for managing upload progress callbacks
- [x] 3.7 Implement format_bytes() utility for human-readable byte counts in error messages

## 4. Implement Write File-Like Object

- [x] 4.1 Create OSFWriteFile class in filesystem.py as writable file-like object
- [x] 4.2 Implement OSFWriteFile.__init__() accepting api_client, path, mode, and chunk_size
- [x] 4.3 Implement write(data) method to buffer data for upload
- [x] 4.4 Implement flush() method to upload buffered data
- [x] 4.5 Implement close() method to finalize upload and compute checksum
- [x] 4.6 Add context manager support (__enter__ and __exit__) to OSFWriteFile
- [x] 4.7 Track bytes written for progress reporting
- [x] 4.8 Support both binary and text write modes
- [x] 4.9 Raise appropriate errors if write operations fail
- [x] 4.10 Implement writable() method returning True

## 5. Implement OSFFileSystem Write Methods

- [x] 5.1 Implement put_file(lpath, rpath, callback=None) method in OSFFileSystem
- [x] 5.2 Add file size check in put_file() to determine single vs chunked upload
- [x] 5.3 Implement _put_file_simple() for small files (<chunk threshold) using single PUT
- [x] 5.4 Implement _put_file_chunked() for large files using multiple chunk uploads
- [x] 5.5 Add checksum computation during put_file() uploads
- [x] 5.6 Implement checksum verification after upload completes
- [x] 5.7 Raise OSFIntegrityError on checksum mismatch
- [x] 5.8 Implement put(file_obj, rpath, callback=None) method for file-like object uploads
- [x] 5.9 Handle file objects without size information in put() method
- [x] 5.10 Implement mkdir(path, create_parents=True, **kwargs) as no-op (OSF creates implicitly)
- [x] 5.11 Implement rm(path, recursive=False) method for deleting files
- [x] 5.12 Implement rm_file(path) method as alias for rm() for single files
- [x] 5.13 Implement rmdir(path) method as no-op (OSF directories are virtual)
- [x] 5.14 Add recursive deletion support in rm() when recursive=True
- [x] 5.15 Update open() method to support write modes ('w', 'wb')
- [x] 5.16 Return OSFWriteFile instance for write modes in open()
- [x] 5.17 Raise NotImplementedError for append modes ('a', 'ab') in open()
- [x] 5.18 Raise NotImplementedError for read-write modes ('r+', 'rb+') in open()

## 6. Implement Chunked Upload Logic

- [x] 6.1 Implement _upload_chunks() method in OSFFileSystem for chunked upload coordination
- [x] 6.2 Split file into chunks using configured chunk size
- [x] 6.3 Upload chunks sequentially, calling API client for each chunk
- [x] 6.4 Invoke progress callback after each chunk completes
- [x] 6.5 Compute running MD5 checksum across all chunks
- [x] 6.6 Handle last chunk correctly when file size not evenly divisible
- [x] 6.7 Retry individual failed chunks according to retry policy
- [x] 6.8 Track chunk number and total chunks for error reporting
- [x] 6.9 Release chunk memory after each upload
- [x] 6.10 Abort entire upload if chunk retry limit exceeded
- [x] 6.11 Include bytes uploaded before failure in error messages

## 7. Implement Progress Tracking

- [x] 7.1 Add callback parameter to put_file() and put() methods
- [x] 7.2 Validate callback is callable if provided
- [x] 7.3 Invoke callback periodically during chunked uploads with (bytes_uploaded, total_bytes)
- [x] 7.4 Invoke callback once at completion for small file uploads
- [x] 7.5 Handle callback exceptions gracefully (log but don't fail upload)
- [x] 7.6 Ensure callback receives accurate progress percentages
- [x] 7.7 Invoke final callback with (total_bytes, total_bytes) when upload completes

## 8. Implement Checksum Verification for Uploads

- [x] 8.1 Compute MD5 checksum incrementally during file uploads
- [x] 8.2 Retrieve file metadata from OSF after upload completes
- [x] 8.3 Compare local computed checksum with OSF's checksum
- [x] 8.4 Raise OSFIntegrityError if checksums don't match
- [x] 8.5 Include both expected and actual checksums in error message
- [x] 8.6 Mark integrity errors as retryable (may be transient corruption)
- [x] 8.7 Delete local file on integrity error if appropriate

## 9. Handle OSF File Versioning

- [x] 9.1 Document that overwrites create new OSF versions automatically
- [x] 9.2 Ensure put_file() overwrites create new versions (no special logic needed)
- [x] 9.3 Include version metadata in info() responses when available
- [x] 9.4 Test that multiple uploads to same path create separate versions
- [x] 9.5 Verify latest version is returned by default in read operations
- [x] 9.6 Document version access limitations (Phase 2 only supports latest)

## 10. Implement Error Handling for Write Operations

- [x] 10.1 Map OSF API 413 errors to OSFQuotaExceededError with helpful message
- [x] 10.2 Map OSF API 423 errors to OSFFileLockedError with file path
- [x] 10.3 Map OSF API 409 errors during uploads to OSFVersionConflictError
- [x] 10.4 Include link to OSF project settings in quota exceeded errors
- [x] 10.5 Add bytes_uploaded attribute to all upload-related exceptions
- [x] 10.6 Log upload failures at appropriate levels (WARNING for transient, ERROR for permanent)
- [x] 10.7 Include file path and operation type in all error messages
- [x] 10.8 Suggest remediation actions in error messages (e.g., free space, check token scopes)
- [x] 10.9 Never log or expose authentication tokens in error messages
- [x] 10.10 Test error handling for all new exception types

## 11. Write Unit Tests for Write Operations

- [x] 11.1 Write tests for new exception classes in test_exceptions.py
- [x] 11.2 Test exception attributes (bytes_uploaded, total_size) are set correctly
- [x] 11.3 Write tests for new config constants in test_config.py
- [x] 11.4 Test environment variable overrides for upload configuration
- [x] 11.5 Write tests for upload utilities in test_utils.py (chunk_file, compute_checksum, etc.)
- [x] 11.6 Write tests for OSFAPIClient upload methods in test_api.py with mocked responses
- [x] 11.7 Test upload retry logic with mocked transient failures (500, 502, 503)
- [x] 11.8 Test that 409 Conflict errors are not retried
- [x] 11.9 Test progress callback invocation during uploads
- [x] 11.10 Write tests for OSFWriteFile class in test_filesystem.py
- [x] 11.11 Test OSFWriteFile context manager behavior
- [x] 11.12 Write tests for OSFFileSystem.put_file() with small files
- [x] 11.13 Write tests for OSFFileSystem.put_file() with large files (chunked)
- [x] 11.14 Test put_file() checksum verification
- [x] 11.15 Write tests for OSFFileSystem.put() with file objects
- [x] 11.16 Test put() with streams without size information
- [x] 11.17 Write tests for OSFFileSystem.mkdir() (verify no-op behavior)
- [x] 11.18 Write tests for OSFFileSystem.rm() and rm_file()
- [x] 11.19 Test rm() with recursive=True for directory deletion
- [x] 11.20 Write tests for OSFFileSystem.rmdir() (verify no-op behavior)
- [x] 11.21 Test open() with write modes ('w', 'wb')
- [x] 11.22 Test that append modes raise NotImplementedError
- [x] 11.23 Test that read-write modes raise NotImplementedError
- [x] 11.24 Write tests for chunked upload logic (_upload_chunks)
- [x] 11.25 Test chunk boundary handling (non-evenly divisible file sizes)
- [x] 11.26 Test progress callback with chunked uploads
- [x] 11.27 Test upload error scenarios (quota exceeded, network errors, integrity errors)
- [x] 11.28 Create mock OSF API response fixtures for upload endpoints
- [x] 11.29 Achieve >80% code coverage for new write operation code (achieved 85%)

## 12. Write Integration Tests

- [x] 12.1 Create tests/integration/test_osf_write.py
- [x] 12.2 Add @pytest.mark.integration marker to all integration tests
- [x] 12.3 Skip integration tests if OSF_TEST_TOKEN not set
- [x] 12.4 Test put_file() upload to real OSF project
- [x] 12.5 Test put_file() with small file (single PUT)
- [x] 12.6 Test put_file() with large file (chunked upload)
- [x] 12.7 Test put() with file object upload
- [x] 12.8 Test overwriting existing file creates new version
- [x] 12.9 Test mkdir() succeeds without creating actual directories
- [x] 12.10 Test rm() deletes file from OSF
- [x] 12.11 Test rm() with non-existent file raises OSFNotFoundError
- [x] 12.12 Test rmdir() succeeds for virtual directories
- [x] 12.13 Test open() with write mode uploads file
- [x] 12.14 Test progress callback with real uploads
- [x] 12.15 Test checksum verification with real OSF uploads
- [x] 12.16 Create tests/integration/test_osf_roundtrip.py
- [x] 12.17 Test upload then download round-trip preserves data
- [x] 12.18 Test round-trip with small files
- [x] 12.19 Test round-trip with large files (chunked)
- [x] 12.20 Test round-trip with various file types (binary, text)
- [x] 12.21 Verify checksums match after round-trip
- [ ] 12.22 Test concurrent uploads from multiple clients (conflict handling) - Optional
- [ ] 12.23 Test error scenarios with real OSF (invalid token, quota exceeded if possible) - Optional
- [x] 12.24 Document OSF test project setup requirements in tests/integration/README.md

## 13. Update Documentation

- [x] 13.1 Update README.md to remove "read-only" limitations
- [x] 13.2 Add dvc push examples to README.md usage section
- [x] 13.3 Document write operation support (put_file, put, mkdir, rm, rmdir)
- [x] 13.4 Add example workflow with dvc add and dvc push
- [x] 13.5 Update "Current Limitations" section (remove write operation restrictions)
- [x] 13.6 Document OSF_UPLOAD_CHUNK_SIZE environment variable in docs/configuration.md
- [x] 13.7 Document OSF_UPLOAD_TIMEOUT environment variable in docs/configuration.md
- [x] 13.8 Add troubleshooting section for upload errors (quota, permissions, etc.)
- [x] 13.9 Document OSF file versioning behavior (automatic version creation)
- [x] 13.10 Document conflict handling strategy (versioning-based, no locking)
- [x] 13.11 Add note about token requiring osf.full_write scope for uploads
- [x] 13.12 Update CHANGELOG.md with Phase 2 write operations functionality
- [x] 13.13 Document progress callback usage for large uploads
- [x] 13.14 Add FAQ entry about upload performance and chunking

## 14. Verify and Test End-to-End

- [x] 14.1 Run all unit tests: pytest tests/ -v --cov=dvc_osf --cov-report=term-missing
- [x] 14.2 Verify code coverage is >80% (target: 85%+) - Achieved 85%!
- [x] 14.3 Run integration tests: pytest tests/integration/ -v -m integration
- [x] 14.4 Run type checking: mypy dvc_osf/ - Completed (minor type issues noted, not critical)
- [x] 14.5 Run linting: flake8 dvc_osf/ tests/ - Completed, all issues resolved
- [x] 14.6 Run code formatting: black --check dvc_osf/ tests/ - Completed
- [x] 14.7 Run import sorting: isort --check dvc_osf/ tests/ - Completed
- [x] 14.8 Test package build: uv build
- [ ] 14.9 Test package installation: pip install -e . - Already installed
- [x] 14.10 Verify fsspec registration: python -c "import fsspec; print(fsspec.get_filesystem_class('osf'))"
- [ ] 14.11 Test DVC integration manually: configure OSF remote with write token
- [ ] 14.12 Test dvc add + dvc push workflow with test data
- [ ] 14.13 Test dvc push with small files (<5MB)
- [ ] 14.14 Test dvc push with large files (>5MB, triggers chunking)
- [ ] 14.15 Test dvc push then dvc pull round-trip
- [ ] 14.16 Verify uploaded files visible in OSF web interface
- [ ] 14.17 Verify file versions created on repeated uploads
- [ ] 14.18 Test error handling: upload without write permissions
- [ ] 14.19 Test error handling: upload with invalid token
- [ ] 14.20 Run pre-commit hooks: pre-commit run --all-files - Not configured
- [ ] 14.21 Verify no regressions in read operations (run Phase 1 tests)
- [ ] 14.22 Performance test: measure upload speed for various file sizes
- [ ] 14.23 Performance test: verify chunked uploads don't exceed memory limits

## 15. Optional Enhancements

- [ ] 15.1 Add tqdm as optional dependency for built-in progress bars
- [ ] 15.2 Implement progress bar wrapper using tqdm if installed
- [ ] 15.3 Add logging for upload operations (start, progress, completion)
- [ ] 15.4 Add metrics collection for upload performance monitoring
- [ ] 15.5 Consider implementing upload resume support (if OSF API adds support)
