## Context

Phase 1 of dvc-osf established a read-only OSF filesystem integration, implementing the `OSFFileSystem` class that extends `ObjectFileSystem` from dvc-objects. The current implementation includes:

- **Existing Architecture**: `OSFFileSystem` delegates to `OSFAPIClient` for all HTTP interactions with OSF API v2
- **Authentication**: Token-based auth via `get_token()` supporting DVC config, env vars, and direct parameters
- **Read Operations**: `exists()`, `ls()`, `info()`, `open()`, `get_file()` with streaming downloads
- **Error Handling**: Custom exception hierarchy mapping HTTP status codes to semantic errors
- **Retry Logic**: Exponential backoff for transient failures (500, 502, 503, network errors)
- **Checksum Verification**: MD5 checksums computed during downloads and verified against OSF metadata

The OSF API v2 uses a RESTful JSON API structure where:
- Files are represented as resources with attributes (name, size, checksum, links)
- File operations require navigating links (e.g., `links.upload` for uploads, `links.delete` for deletions)
- Directories don't exist as first-class entities; they're inferred from file paths
- File versioning is automatic: OSF creates new versions on overwrites

**Stakeholders**: Data scientists using DVC with OSF storage, OSF platform maintainers, dvc-osf contributors

**Constraints**:
- Must maintain compatibility with existing read-only operations
- OSF API rate limits (more restrictive for write operations)
- OSF storage quotas vary by account type
- OSF only supports `osfstorage` provider (no add-on storage in Phase 2)
- Must follow fsspec/dvc-objects filesystem interface conventions

## Goals / Non-Goals

**Goals:**
- Enable `dvc push` to upload versioned data to OSF storage
- Support standard DVC write workflows (`dvc add` + `dvc push`)
- Handle large file uploads efficiently with chunking and streaming
- Provide upload progress tracking for visibility
- Detect and handle file conflicts appropriately
- Maintain consistency with OSF's file versioning model
- Preserve existing error handling and retry patterns
- Achieve >80% test coverage including integration tests

**Non-Goals:**
- Support for OSF add-on storage providers (Dropbox, Google Drive, etc.) - deferred to Phase 3
- Resumable uploads (OSF API doesn't provide upload resume endpoints) - future enhancement
- Parallel/concurrent uploads for multiple files - DVC handles this at a higher level
- Custom conflict resolution strategies - use OSF's default versioning behavior
- Direct version management UI - rely on OSF web interface for version history
- File locking mechanisms - OSF doesn't provide distributed locks

## Decisions

### Decision 1: Upload Strategy - Single PUT vs Chunked Multipart

**Decision**: Implement a hybrid approach with automatic switching based on file size.

**Rationale**:
- **Small files (<5MB)**: Use single PUT request with `links.upload` from file metadata
  - Simpler, fewer API calls, lower overhead
  - OSF API accepts entire file in one request body
  - Sufficient for most DVC artifacts (model checkpoints, small datasets)

- **Large files (≥5MB)**: Use chunked uploads via multiple PUT requests
  - OSF API supports chunked uploads through range headers
  - Prevents memory exhaustion from loading entire file
  - Better progress tracking granularity
  - More resilient to network interruptions (can retry individual chunks)

- **Threshold configurable** via `OSF_UPLOAD_CHUNK_SIZE` environment variable

**Alternatives Considered**:
- Always single PUT: Memory issues with large files (10GB+ datasets)
- Always chunked: Unnecessary overhead for small files
- Streaming multipart: OSF API doesn't support standard multipart/form-data for uploads

**Implementation**:
```python
def put_file(self, lpath, rpath):
    file_size = os.path.getsize(lpath)
    if file_size < self.upload_chunk_size:
        return self._put_file_simple(lpath, rpath)
    else:
        return self._put_file_chunked(lpath, rpath)
```

---

### Decision 2: OSF File Versioning - Overwrite vs Version Creation

**Decision**: Always create new versions on overwrites (OSF default behavior).

**Rationale**:
- **Aligns with OSF's native behavior**: OSF automatically versions files on overwrites
- **Preserves data provenance**: Old versions remain accessible through OSF web interface
- **No version conflict errors**: Eliminates need for complex conflict resolution
- **DVC's model expects this**: DVC tracks content by hash, not by version number
- **Simplifies implementation**: No need to query existing versions before upload

**Alternatives Considered**:
- Delete then recreate: Loses version history, not aligned with open science principles
- Check-and-fail on conflicts: Requires additional API call, complicates user workflow
- Allow user to choose: Adds configuration complexity for minimal benefit

**Trade-off**: Storage usage increases with versions, but this is expected OSF behavior and manageable through OSF's web interface.

---

### Decision 3: Directory Creation - Explicit mkdir() vs Implicit

**Decision**: Implement `mkdir()` as a no-op that always succeeds.

**Rationale**:
- **OSF has no directory concept**: Directories are inferred from file paths (e.g., `data/train.csv` implies `data/` directory)
- **Directories created implicitly**: When uploading `path/to/file.txt`, OSF creates intermediate path components automatically
- **fsspec convention**: Many cloud storage filesystems implement mkdir() as no-op
- **DVC doesn't require mkdir**: DVC calls `put_file()` directly, creating directories implicitly

**Alternatives Considered**:
- Raise NotImplementedError: Would break fsspec contract expectations
- Create marker files: Unnecessary complexity, OSF doesn't need them
- Track directories in memory: No benefit since OSF doesn't have directories

**Implementation**:
```python
def mkdir(self, path, create_parents=True, **kwargs):
    """No-op: OSF creates directories implicitly."""
    return None
```

---

### Decision 4: File Deletion - Immediate vs Soft Delete

**Decision**: Implement immediate permanent deletion via OSF's DELETE endpoint.

**Rationale**:
- **DVC expects permanent deletion**: `dvc gc` (garbage collection) removes unreferenced data
- **OSF API provides DELETE**: Direct endpoint for removing files
- **Simpler implementation**: No need for trash/recycle bin logic
- **User can recover via OSF versions**: If file was modified (not deleted), versions exist

**Alternatives Considered**:
- Soft delete with trash: OSF API doesn't provide trash bin functionality
- Require confirmation: Adds friction, DVC already confirms dangerous operations
- No deletion support: Breaks DVC garbage collection workflows

**Trade-off**: Accidental deletions are permanent. Users should use OSF's version history or backup strategies.

---

### Decision 5: Upload Progress Tracking - Callback vs Event System

**Decision**: Implement optional callback parameter for progress updates.

**Rationale**:
- **Simple integration**: Single callback function passed to `put_file(callback=fn)`
- **Follows fsspec pattern**: Similar to `fsspec` and `dvc-objects` conventions
- **Flexible**: Caller can implement progress bars, logging, or ignore
- **Low overhead**: Only called during chunked uploads, not for small files

**Callback Signature**:
```python
def callback(bytes_uploaded: int, total_bytes: int) -> None:
    """Called periodically during upload."""
    pass
```

**Alternatives Considered**:
- Event system: Over-engineered for single progress use case
- Built-in progress bar: Couples implementation to specific UI library (tqdm)
- No progress tracking: Poor UX for large file uploads

**Implementation**: Call callback after each chunk upload in `_put_file_chunked()`.

---

### Decision 6: Error Handling - Retry Strategy for Uploads

**Decision**: Extend existing retry logic to uploads with stricter conditions.

**Rationale**:
- **Reuse existing framework**: Same exponential backoff as reads
- **Retry only idempotent failures**: 500, 502, 503, connection errors
- **Don't retry 4xx except rate limits**: 400/409 indicate client error, not transient
- **Special handling for 409 conflicts**: Could indicate version conflict, don't retry

**Retry Matrix**:
| Status Code | Retry? | Reason |
|-------------|--------|--------|
| 500, 502, 503 | Yes | Server transient failures |
| 429 (rate limit) | Yes | Wait for Retry-After header |
| 408 (timeout) | Yes | Network transient failure |
| 409 (conflict) | No | Likely version conflict, requires investigation |
| 400, 403, 404 | No | Client error, retry won't help |
| 413 (too large) | No | File exceeds quota, user action required |

**Alternatives Considered**:
- Retry all errors: Wastes time on permanent failures
- No retries on uploads: Poor reliability on flaky networks
- Infinite retries: Could hang indefinitely

---

### Decision 7: Checksum Verification - Upload Validation

**Decision**: Compute checksum during upload and verify against OSF response.

**Rationale**:
- **Data integrity**: Ensures uploaded data matches local file
- **Detects corruption**: Network issues, OSF storage errors
- **Aligns with downloads**: Symmetric verification on both directions
- **OSF provides checksums**: API returns MD5 in file metadata after upload

**Implementation Flow**:
1. Compute MD5 during upload streaming (no memory overhead)
2. After upload completes, call `info()` to get OSF's computed checksum
3. Compare checksums, raise `OSFIntegrityError` on mismatch
4. Automatic retry on integrity error (likely transient network corruption)

**Alternatives Considered**:
- No verification: Risk of silent data corruption
- Pre-compute checksum: Requires reading file twice (inefficient)
- Trust OSF: No way to detect client-side corruption before upload

## Risks / Trade-offs

### Risk 1: OSF Storage Quota Exceeded
**Risk**: User uploads large file exceeding OSF project storage quota.

**Impact**: Upload fails with 413 or similar error, user confused why.

**Mitigation**:
- Catch quota errors and raise descriptive `OSFQuotaExceededError`
- Error message includes link to OSF project settings to check quota
- Document quota limits in README troubleshooting section
- Consider pre-flight quota check (query project storage before upload) - but adds latency

---

### Risk 2: Network Interruption During Large Upload
**Risk**: Multi-GB upload interrupted mid-transfer, requiring restart from scratch.

**Impact**: Poor UX, wasted bandwidth, frustration with large datasets.

**Mitigation**:
- Retry logic handles transient interruptions (connection resets)
- Chunked uploads limit lost progress (only retry failed chunk)
- Document workaround: manually split large files and upload separately
- **Future enhancement**: Implement resumable uploads when OSF API supports it

**Trade-off Accepted**: First implementation won't support resumable uploads due to OSF API limitations. Users with unstable connections should use smaller files or upload via OSF web interface.

---

### Risk 3: Concurrent Modifications / Race Conditions
**Risk**: Multiple users upload to same file simultaneously, creating version conflicts.

**Impact**: Unpredictable final state, potential data loss if wrong version wins.

**Mitigation**:
- OSF handles this via versioning: both uploads succeed, creating separate versions
- Last upload becomes "latest" version, others remain in history
- Document this behavior in README (not truly atomic)
- **Non-goal**: Distributed locking (OSF doesn't provide primitives)

**Trade-off Accepted**: OSF's versioning model is "last write wins" with history. This is acceptable for DVC's use case (content-addressed storage), but users should coordinate writes in collaborative workflows.

---

### Risk 4: OSF API Rate Limiting More Aggressive for Writes
**Risk**: Bulk uploads trigger rate limits, slowing down `dvc push` significantly.

**Impact**: Poor performance, timeouts, failed uploads.

**Mitigation**:
- Respect Retry-After headers (already implemented for reads)
- Add exponential backoff on rate limit errors
- Document recommended batch sizes in README
- Consider adding `--jobs` parameter guidance (DVC controls parallelism)

**Trade-off Accepted**: OSF's rate limits are necessary for platform stability. Users with large datasets should expect longer upload times compared to commercial cloud providers.

---

### Risk 5: Incomplete Upload on Process Termination
**Risk**: User Ctrl+C during upload, leaving partial/corrupt file on OSF.

**Impact**: Inconsistent state, DVC can't verify file, confusion.

**Mitigation**:
- OSF API is atomic: upload either completes or fails, no partial writes
- If interrupted mid-request, OSF discards partial data
- Checksum verification catches any inconsistencies on retry
- **Future enhancement**: Signal handling for graceful cleanup

**Trade-off Accepted**: Interrupted uploads are safe (no corruption), but require re-upload from scratch. This is standard behavior for most cloud storage systems.

## Migration Plan

### Phase 2a: Write Operations Implementation (This Change)
1. Implement core write methods in `OSFFileSystem`
2. Add upload support to `OSFAPIClient`
3. Extend exception hierarchy with write-specific errors
4. Add comprehensive unit tests with mocked API responses
5. Add integration tests against test OSF project

### Phase 2b: Testing and Validation
1. Manual testing with real DVC projects and OSF storage
2. Performance testing with various file sizes (1KB to 1GB)
3. Failure mode testing (network interruptions, rate limits, quota exceeded)
4. Cross-platform testing (Linux, macOS, Windows)

### Phase 2c: Documentation and Release
1. Update README with `dvc push` examples
2. Add troubleshooting section for write operations
3. Update CHANGELOG with new capabilities
4. Tag release as v0.2.0 (minor version bump for new features)

### Rollback Strategy
- No rollback needed: Changes are purely additive, read operations unaffected
- If critical bug found: revert commits, release v0.1.1 (Phase 1 only)
- Users can pin to v0.1.x in dependencies if write operations problematic

### Deployment Considerations
- No server-side changes (pure client library)
- No database migrations
- No configuration changes required (optional env vars)
- Backward compatible with existing DVC remotes

## Open Questions

### Q1: Should we implement atomic move/rename operations?
**Status**: Open

**Discussion**: OSF API v2 doesn't have native move/rename endpoints. Could implement as copy + delete, but this breaks atomicity. DVC rarely uses move operations for remotes.

**Recommendation**: Defer to Phase 3 or future enhancement. Implement as NotImplementedError for now.

---

### Q2: How to handle OSF file versioning in DVC's content-addressed model?
**Status**: Open

**Discussion**: DVC stores files by content hash (e.g., `ab/cd1234.txt`). OSF versions don't map cleanly to this model. Should we expose version history to DVC?

**Recommendation**: Ignore version history in Phase 2. DVC always reads/writes "latest" version. Future enhancement could add version pinning.

---

### Q3: Should we support progress callbacks for read operations too?
**Status**: Open

**Discussion**: Phase 1 doesn't have progress tracking for downloads. Should we add symmetry?

**Recommendation**: Yes, but defer to separate change. Keep this change focused on write operations. File issue for future enhancement.

---

### Q4: What's the behavior for rmdir() on non-empty directories?
**Status**: Open

**Discussion**: Standard filesystem raises error if directory not empty. But OSF doesn't have real directories.

**Recommendation**: Implement `rmdir()` as no-op (succeeds regardless). Document that OSF doesn't have directory concept. Alternatively, check if path prefix has files and raise error for consistency.

---

### Q5: Should we implement `put()` distinct from `put_file()`?
**Status**: Open

**Discussion**: fsspec distinguishes `put_file(local_path, remote_path)` for files vs `put(file_obj, remote_path)` for file-like objects. Both needed?

**Recommendation**: Yes, implement both for fsspec compatibility. `put_file()` optimized for local files, `put()` handles streams/buffers. Share implementation via `_upload_data()` helper.
