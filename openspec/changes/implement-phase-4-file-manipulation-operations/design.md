## Context

The dvc-osf plugin currently has partial file manipulation support:
- **Implemented**: `rm()`, `rm_file()`, and `rmdir()` methods for deletion
- **Missing**: `cp()` for copying and `mv()` for moving/renaming files
- **API Client**: Already has `delete()` method, but lacks dedicated copy/move methods

The OSF API (via WaterButler) provides several approaches for file operations:
1. **Native WaterButler operations**: Direct API endpoints for copy/move (if available)
2. **Fallback approach**: Download source → upload to destination → optionally delete source

Current architecture:
- `OSFFileSystem` extends `ObjectFileSystem` from dvc-objects
- `OSFAPIClient` handles all HTTP communication with OSF API
- Path resolution converts DVC paths to OSF API URLs
- Existing `put_file()` and `get_file()` methods provide upload/download primitives

DVC requires these operations for:
- `dvc push`: May need to reorganize files
- `dvc pull`: May need to move files between cache locations
- `dvc gc`: Needs to delete unused files
- Manual file management through DVC commands

## Goals / Non-Goals

**Goals:**
- Implement `cp()` method for copying files within OSF storage
- Implement `mv()` method for moving/renaming files within OSF storage
- Ensure copy and move operations work correctly with OSF's file structure
- Provide atomic or near-atomic operations where possible
- Support batch operations for efficiency
- Maintain consistency with existing delete operations
- Handle OSF-specific constraints (virtual directories, file IDs)

**Non-Goals:**
- Cross-project copying (only within same OSF project/component)
- Cross-provider copying (only within same storage provider, e.g., osfstorage)
- Directory-level operations beyond recursive file operations (OSF has virtual directories)
- Version control or file history management (out of scope for Phase 4)
- Optimized multi-threaded batch operations (can be added in Phase 6)

## Decisions

### Decision 1: Copy Implementation Strategy

**Choice**: Use download-then-upload fallback approach initially, with hooks for native API operations in future.

**Rationale**:
- OSF/WaterButler API documentation for native copy operations is limited
- Download-then-upload is guaranteed to work and is straightforward
- Can leverage existing `get_file()` and `put_file()` methods
- Maintains data integrity with checksum verification
- Can be optimized later with native API calls without changing interface

**Alternatives Considered**:
- Native WaterButler copy API: More efficient but documentation unclear, risk of incompatibility
- HTTP redirect-based copy: May not be supported by OSF for same-storage copies

**Implementation**:
```python
def cp(self, path1: str, path2: str, **kwargs: Any) -> None:
    # 1. Verify source exists and get metadata
    # 2. Download source to temp file
    # 3. Upload temp file to destination
    # 4. Verify checksums match
    # 5. Clean up temp file
```

### Decision 2: Move Implementation Strategy

**Choice**: Implement move as copy-then-delete with best-effort atomicity.

**Rationale**:
- OSF WaterButler move/rename API endpoints are not well-documented
- Copy-then-delete is reliable and builds on existing operations
- Provides clear failure modes (file may be duplicated but not lost)
- Can detect and handle failures at each step
- Matches semantics of other DVC remote storage backends

**Alternatives Considered**:
- Native WaterButler move API: May not exist or be reliable
- Rename-only operation: Would be faster but likely not supported for all paths

**Implementation**:
```python
def mv(self, path1: str, path2: str, **kwargs: Any) -> None:
    # 1. Copy source to destination (using cp())
    # 2. Verify copy succeeded
    # 3. Delete source file
    # 4. If delete fails, log warning but don't fail (copy succeeded)
```

**Atomicity considerations**:
- Not fully atomic - copy and delete are separate operations
- Risk: Failure between copy and delete leaves duplicate file
- Mitigation: This is acceptable for DVC use cases (cleanup can happen later)
- Trade-off: Reliability over atomicity given OSF API constraints

### Decision 3: Path Resolution and Validation

**Choice**: Reuse existing `_resolve_path()` method and add validation for same-project/provider constraints.

**Rationale**:
- Consistent with existing read/write/delete operations
- OSF file operations are file-ID based, requiring path-to-ID resolution
- Cross-project operations are complex and out of scope
- Validation prevents user errors and provides clear error messages

**Implementation**:
```python
# In cp() and mv():
src_project, src_provider, src_path = self._resolve_path(path1)
dst_project, dst_provider, dst_path = self._resolve_path(path2)

if src_project != dst_project:
    raise OSFOperationNotSupportedError("Cross-project copy not supported")
if src_provider != dst_provider:
    raise OSFOperationNotSupportedError("Cross-provider copy not supported")
```

### Decision 4: Error Handling

**Choice**: Add new exception types and use specific errors for manipulation operations.

**New Exceptions**:
- `OSFConflictError`: Destination file already exists (when overwrite=False)
- `OSFOperationNotSupportedError`: Operation not supported by OSF or this implementation

**Rationale**:
- Provides clear distinction between operation errors and API errors
- Matches DVC's expectation of specific filesystem errors
- Allows users to handle conflicts programmatically

**Implementation**:
- Check destination existence before copy/move
- Raise `OSFConflictError` if destination exists and overwrite not specified
- Wrap OSF API errors with context about which operation failed

### Decision 5: Batch Operations

**Choice**: Implement basic sequential batch operations for Phase 4, defer parallel optimization to Phase 6.

**Rationale**:
- Sequential operations are simpler and safer
- Matches pattern in existing `rm()` recursive implementation
- Parallel operations add complexity (connection pooling, rate limiting)
- Phase 6 is dedicated to performance optimization

**Implementation**:
```python
def cp(self, path1: str, path2: str, recursive: bool = False, **kwargs: Any) -> None:
    if recursive and self.info(path1)["type"] == "directory":
        items = self.ls(path1, detail=True)
        for item in items:
            src = item["name"]
            dst = path2 + src[len(path1):]
            self.cp(src, dst, recursive=True)
    else:
        # Single file copy
```

### Decision 6: Overwrite Behavior

**Choice**: Support `overwrite` parameter (default: True for consistency with other DVC remotes).

**Rationale**:
- DVC typically overwrites by default
- Provides safety option when needed
- Matches behavior of existing `put_file()` implementation

**Implementation**:
```python
def cp(self, path1: str, path2: str, overwrite: bool = True, **kwargs: Any) -> None:
    if not overwrite and self.exists(path2):
        raise OSFConflictError(f"Destination exists: {path2}")
    # ... proceed with copy
```

## Risks / Trade-offs

### Risk: Incomplete operation leaves duplicate or missing files
**Impact**: Medium - User may have duplicate files or orphaned data  
**Mitigation**: 
- Implement copy-then-delete for moves (copy failure is safe)
- Log all operations for troubleshooting
- Document behavior in docstrings
- Future: Add transaction log or cleanup utility

### Risk: Performance degradation with large files
**Impact**: High - Copy/move of large files will be slow (download + upload)  
**Mitigation**:
- Document performance characteristics
- Stream data through temp files (don't load in memory)
- Phase 6 will optimize with native API operations if available
- Provide progress callbacks for long operations

### Risk: OSF rate limiting on batch operations
**Impact**: Medium - Batch operations may hit rate limits  
**Mitigation**:
- Existing retry logic with exponential backoff handles this
- Sequential operations reduce concurrent request load
- Future: Add batch size configuration and throttling

### Risk: Cross-storage provider operations fail
**Impact**: Low - Users attempt cross-provider copies and get errors  
**Mitigation**:
- Validate paths before attempting operations
- Provide clear error messages with actionable guidance
- Document limitation in user-facing docs

### Risk: OSF virtual directories cause confusion
**Impact**: Low - Directory operations behave differently than local filesystem  
**Mitigation**:
- Document that OSF directories are virtual
- Copy/move operations work on files, recursively handle directories
- Consistent with existing `rm()` behavior

### Trade-off: Atomicity vs Reliability
**Choice**: Prioritize reliability over atomicity  
**Consequence**: Move operations are not atomic (file may be temporarily duplicated)  
**Justification**: OSF API doesn't provide atomic move; duplicate files are safer than data loss

### Trade-off: Performance vs Simplicity
**Choice**: Use download-upload fallback vs native API operations  
**Consequence**: Slower operations, more bandwidth usage  
**Justification**: Guaranteed correctness; performance optimization planned for Phase 6

## Migration Plan

**Phase 4 Implementation Steps**:
1. Add new exception types to `exceptions.py`
2. Implement `cp()` method in `OSFFileSystem` with tests
3. Implement `mv()` method in `OSFFileSystem` with tests
4. Add integration tests for copy/move operations
5. Update documentation with operation semantics

**Deployment**:
- No breaking changes to existing API
- New methods are additions to existing class
- Backward compatible with existing DVC workflows

**Rollback Strategy**:
- If critical bugs found, methods can be marked as experimental
- Users can continue using existing read/write/delete operations
- Git revert is straightforward (additive changes)

## Open Questions

1. **Native OSF API for copy/move**: Does WaterButler provide efficient copy/move endpoints? 
   - **Resolution path**: Research OSF WaterButler docs, test with OSF development instance
   - **Timeline**: Investigate during implementation, optimize in Phase 6 if available

2. **Progress reporting for long operations**: Should copy/move support progress callbacks?
   - **Resolution path**: Check if DVC passes callbacks to these methods
   - **Timeline**: Implement in Phase 4 if DVC provides callbacks, otherwise defer

3. **Handling of file metadata during copy**: Should we preserve timestamps, checksums?
   - **Resolution path**: Test what OSF preserves during upload
   - **Decision**: Copy data only, let OSF set new timestamps (standard behavior)

4. **Batch operation optimization**: What batch size is optimal for OSF API?
   - **Resolution path**: Performance testing in Phase 6
   - **Timeline**: Phase 4 uses sequential operations
