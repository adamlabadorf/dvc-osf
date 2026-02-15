## Why

Phase 1 established read-only OSF integration, enabling `dvc pull` operations. However, DVC's primary value proposition requires bidirectional data flow. Without write capabilities, users cannot use `dvc push` to version their data on OSF, forcing manual uploads through the web interface and breaking DVC's reproducible workflow. This change completes the core DVC-OSF integration by implementing write operations, enabling full data versioning workflows with OSF storage.

## What Changes

- Implement `put_file()` method in `OSFFileSystem` for uploading local files to OSF
- Implement `put()` method for uploading file-like objects with streaming
- Implement `mkdir()` method for creating directories on OSF
- Implement `rm()` and `rm_file()` methods for deleting files from OSF
- Implement `rmdir()` method for removing empty directories
- Add chunked upload support for large files (multipart uploads)
- Add upload progress tracking and callbacks
- Add conflict detection and handling for concurrent modifications
- Implement OSF file versioning support (create new versions on overwrites)
- Add upload checksum computation and verification
- Extend retry logic to cover upload operations
- Add write-specific error handling (quota exceeded, permission denied, etc.)
- Add unit tests for all write operations with mocked API responses
- Add integration tests for upload/download round-trips with real OSF projects
- Update documentation with write operation examples and `dvc push` workflows

## Capabilities

### New Capabilities

- `osf-filesystem-write`: Write operations (put_file, put, mkdir, rm, rmdir) with streaming, chunked uploads, and progress tracking
- `osf-file-versioning`: Support for OSF file versioning (create new versions on overwrites, query version history)
- `osf-upload-chunked`: Chunked/multipart upload support for large files with resumability
- `osf-conflict-handling`: Conflict detection and resolution strategies for concurrent modifications

### Modified Capabilities

- `osf-api-client`: Add POST/PUT/DELETE methods with file streaming, chunk uploads, and upload-specific retry logic
- `osf-filesystem-read`: Update base class integration to properly support both read and write modes
- `osf-error-handling`: Add write-specific exceptions (quota exceeded, file locked, version conflict)

## Impact

**Code Changes**:
- `dvc_osf/filesystem.py`: Add write methods (put_file, put, mkdir, rm, rmdir) (~400-500 lines added)
- `dvc_osf/api.py`: Add upload methods, chunked transfer support (~200-300 lines added)
- `dvc_osf/exceptions.py`: Add write-specific exceptions (OSFQuotaExceededError, OSFFileLockedError, OSFVersionConflictError) (~50-100 lines added)
- `dvc_osf/utils.py`: Add upload utilities (chunk splitter, progress tracker) (~100-150 lines added)
- `dvc_osf/config.py`: Add write-related constants (chunk sizes, upload timeouts) (~20-30 lines added)

**Test Changes**:
- `tests/test_filesystem.py`: Add write operation tests (~200-300 lines added)
- `tests/test_api.py`: Add upload and delete endpoint tests (~150-200 lines added)
- `tests/test_exceptions.py`: Add write-specific exception tests (~50 lines added)
- `tests/integration/test_osf_write.py`: Add integration tests for uploads and deletes (~200-300 lines new file)
- `tests/integration/test_osf_roundtrip.py`: Add round-trip tests (upload then download verification) (~150-200 lines new file)

**Dependencies**:
- No new dependencies required (requests already supports streaming uploads)
- Consider adding `tqdm` as optional dependency for progress bars (optional)

**Configuration**:
- Environment variables: Add `OSF_UPLOAD_CHUNK_SIZE` (default: 5MB), `OSF_UPLOAD_TIMEOUT` (default: 300 seconds)
- DVC remote configuration: No changes needed (existing token provides write access)

**External Systems**:
- Requires write permissions on OSF projects (token must have `osf.full_write` scope)
- OSF storage quota limits apply (varies by account type)
- OSF API rate limits apply to write operations (more restrictive than reads)

**Breaking Changes**:
- None. This is purely additive functionality.

**User Workflows**:
- Enables standard DVC workflows: `dvc add`, `dvc push`, `dvc checkout`
- Users can now version data bidirectionally with OSF
- Enables collaborative workflows where team members push/pull from shared OSF projects
