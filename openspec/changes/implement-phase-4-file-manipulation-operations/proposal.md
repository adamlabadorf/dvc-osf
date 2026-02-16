## Why

Phase 4 completes the core filesystem interface for the dvc-osf plugin by implementing file manipulation operations (copy, move, delete). These operations are required by DVC's filesystem abstraction layer and enable full DVC workflow support (push, pull, cleanup). Without these operations, users cannot manage their OSF storage or perform critical operations like removing outdated files or reorganizing datasets.

## What Changes

- Add `cp()` method to OSFFileSystem for copying files within OSF storage
- Add `mv()` method to OSFFileSystem for moving/renaming files within OSF
- Add `rm()` method to OSFFileSystem for deleting files and directories
- Add `rm_file()` method to OSFFileSystem for deleting individual files
- Extend OSFAPIClient with DELETE and PATCH/POST operations for file manipulation
- Implement batch operations for efficient multi-file operations
- Add comprehensive error handling for all manipulation operations (permission errors, not found, conflicts)
- Add integration tests covering all manipulation operations with various file sizes and scenarios
- Document operation semantics, edge cases, and OSF-specific limitations

## Capabilities

### New Capabilities
- `osf-filesystem-copy`: Copy files and directories within OSF storage using OSF API's copy endpoints
- `osf-filesystem-move`: Move and rename files and directories within OSF storage
- `osf-filesystem-delete`: Delete files and directories from OSF storage with proper cleanup
- `osf-batch-operations`: Perform efficient batch operations for copying, moving, or deleting multiple files

### Modified Capabilities
- `osf-api-client`: Add support for DELETE requests and file-to-file operations (copy/move via OSF API)
- `osf-error-handling`: Extend error handling to cover manipulation-specific errors (conflict on copy, permission denied on delete)

## Impact

**Code Impact**:
- `dvc_osf/filesystem.py`: Add cp(), mv(), rm(), rm_file() methods to OSFFileSystem class
- `dvc_osf/api.py`: Add delete_file(), copy_file(), move_file() methods to OSFAPIClient class
- `dvc_osf/exceptions.py`: Add OSFConflictError, OSFOperationNotSupportedError exceptions

**API Impact**:
- New OSF API endpoints used:
  - `DELETE /files/{file_id}/`: Delete file
  - OSF WaterButler endpoints for copy/move operations (if available)
  - Fallback: download + upload + delete for copy/move if native endpoints unavailable

**Dependencies**:
- Requires completed Phase 1 (core filesystem), Phase 2 (read operations), Phase 3 (write operations)
- No new external dependencies

**Testing Impact**:
- New integration tests requiring OSF test project with write permissions
- Tests must handle OSF-specific behaviors (eventual consistency, rate limits)
- Performance benchmarks for batch operations

**User Impact**:
- Enables full DVC workflow: `dvc push`, `dvc pull`, `dvc gc` (garbage collection)
- Users can manage OSF storage directly through DVC commands
- Provides complete parity with other DVC remote storage backends
