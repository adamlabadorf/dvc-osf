# OSF Chunked Upload Specification

## Purpose

Provides chunked/multipart upload support for efficiently uploading large files to OSF without loading entire files into memory, with configurable chunk sizes and progress tracking.

## ADDED Requirements

### Requirement: Automatic chunking for large files
The system SHALL automatically use chunked uploads for files exceeding the chunk threshold.

#### Scenario: Small file uses single PUT
- **WHEN** uploading file smaller than chunk threshold (5MB default)
- **THEN** the system SHALL upload in a single PUT request

#### Scenario: Large file uses chunked upload
- **WHEN** uploading file larger than or equal to chunk threshold
- **THEN** the system SHALL split upload into multiple chunks

#### Scenario: Threshold configurable via environment
- **WHEN** OSF_UPLOAD_CHUNK_SIZE environment variable is set
- **THEN** the system SHALL use that value as the chunk threshold

### Requirement: Chunk size configuration
The system SHALL support configurable chunk sizes for uploads.

#### Scenario: Default chunk size
- **WHEN** no chunk size is configured
- **THEN** the system SHALL use 5MB (5242880 bytes) as default chunk size

#### Scenario: Custom chunk size via environment
- **WHEN** OSF_UPLOAD_CHUNK_SIZE is set to custom value (e.g., "10MB")
- **THEN** the system SHALL parse and use that chunk size

#### Scenario: Minimum chunk size
- **WHEN** configured chunk size is less than 1MB
- **THEN** the system SHALL use 1MB as minimum (to avoid excessive API calls)

#### Scenario: Maximum chunk size
- **WHEN** configured chunk size exceeds reasonable limits
- **THEN** the system SHALL cap at maximum (e.g., 100MB) to avoid memory issues

### Requirement: Sequential chunk upload
The system SHALL upload chunks sequentially to OSF.

#### Scenario: Upload chunks in order
- **WHEN** large file is uploaded
- **THEN** the system SHALL send chunks in sequential order (chunk 1, 2, 3, ...)

#### Scenario: Track chunk progress
- **WHEN** uploading chunks
- **THEN** the system SHALL track which chunks have been uploaded successfully

#### Scenario: Each chunk independent request
- **WHEN** uploading chunks
- **THEN** each chunk SHALL be sent as a separate HTTP PUT request

### Requirement: Chunk streaming from disk
The system SHALL stream chunks from disk without loading entire file into memory.

#### Scenario: Read chunk from file
- **WHEN** uploading a chunk
- **THEN** the system SHALL read only that chunk's bytes from disk

#### Scenario: Memory usage bounded by chunk size
- **WHEN** uploading large file (e.g., 10GB)
- **THEN** memory usage SHALL not exceed chunk size (e.g., 5MB) regardless of file size

#### Scenario: Release chunk memory after upload
- **WHEN** chunk upload completes
- **THEN** the system SHALL release that chunk's memory before reading next chunk

### Requirement: Chunk retry on failure
The system SHALL retry individual chunks on transient failures.

#### Scenario: Retry failed chunk
- **WHEN** chunk upload fails with retryable error (500, connection error)
- **THEN** the system SHALL retry uploading that specific chunk

#### Scenario: Retry with backoff
- **WHEN** chunk fails and is retried
- **THEN** the system SHALL use exponential backoff between retries

#### Scenario: Continue after successful retry
- **WHEN** failed chunk is retried successfully
- **THEN** the system SHALL continue with next chunk

#### Scenario: Abort after max retries
- **WHEN** chunk fails repeatedly exceeding max retries
- **THEN** the system SHALL abort the entire upload and raise exception

### Requirement: Progress callbacks during chunked upload
The system SHALL invoke progress callbacks after each chunk upload.

#### Scenario: Callback after each chunk
- **WHEN** chunk upload completes
- **THEN** the system SHALL call progress callback with (bytes_uploaded_so_far, total_bytes)

#### Scenario: Callback provides accurate progress
- **WHEN** 3 out of 5 chunks uploaded
- **THEN** callback SHALL report approximately 60% progress (3 * chunk_size / total_size)

#### Scenario: Final callback at 100%
- **WHEN** last chunk uploads successfully
- **THEN** callback SHALL be invoked with (total_bytes, total_bytes)

### Requirement: Chunked upload checksum computation
The system SHALL compute checksum across all chunks.

#### Scenario: Stream checksum during chunking
- **WHEN** uploading chunks
- **THEN** the system SHALL update running MD5 hash with each chunk's data

#### Scenario: Final checksum after all chunks
- **WHEN** all chunks uploaded
- **THEN** the system SHALL finalize checksum and verify against OSF metadata

#### Scenario: Checksum failure aborts upload
- **WHEN** final checksum doesn't match OSF's checksum
- **THEN** the system SHALL raise OSFIntegrityError

### Requirement: Chunk boundary alignment
The system SHALL handle chunk boundaries correctly.

#### Scenario: Split file on chunk boundaries
- **WHEN** file size is not evenly divisible by chunk size
- **THEN** the system SHALL upload last chunk with remaining bytes (< chunk size)

#### Scenario: Single byte last chunk
- **WHEN** file size is (chunk_size * N) + 1
- **THEN** the system SHALL upload final chunk with 1 byte

#### Scenario: Exact multiple of chunk size
- **WHEN** file size is exact multiple of chunk size
- **THEN** the system SHALL NOT create empty final chunk

### Requirement: Chunked upload performance
The system SHALL optimize chunked uploads for performance.

#### Scenario: Minimize API overhead
- **WHEN** uploading large files
- **THEN** chunk size SHALL be large enough to minimize API call overhead (default 5MB)

#### Scenario: Balance memory and speed
- **WHEN** chunk size is configured
- **THEN** it SHALL balance memory usage (smaller better) vs upload speed (larger better)

### Requirement: Chunked upload error details
The system SHALL provide clear error messages for chunk failures.

#### Scenario: Report failed chunk number
- **WHEN** chunk upload fails
- **THEN** error message SHALL include which chunk failed (e.g., "Chunk 3 of 10 failed")

#### Scenario: Report bytes uploaded before failure
- **WHEN** upload fails mid-chunks
- **THEN** error message SHALL indicate how many bytes were successfully uploaded

### Requirement: OSF API chunk upload protocol
The system SHALL use OSF API v2's chunked upload mechanism correctly.

#### Scenario: Use file upload endpoint
- **WHEN** uploading chunks
- **THEN** the system SHALL use the OSF file's upload URL from metadata

#### Scenario: Send proper headers for chunks
- **WHEN** uploading each chunk
- **THEN** the system SHALL include appropriate Content-Length and Content-Type headers

#### Scenario: Handle OSF chunk responses
- **WHEN** OSF responds to chunk upload
- **THEN** the system SHALL verify 200/201 status before proceeding to next chunk

### Requirement: Chunk upload timeout handling
The system SHALL handle timeouts appropriately for chunks.

#### Scenario: Per-chunk timeout
- **WHEN** uploading a chunk
- **THEN** the system SHALL use upload timeout (default 300s) per chunk

#### Scenario: Large files don't timeout
- **WHEN** uploading very large file (e.g., 1GB) in 5MB chunks
- **THEN** total upload time CAN exceed single timeout (timeout applies per chunk)

#### Scenario: Timeout resets between chunks
- **WHEN** chunk completes
- **THEN** timeout timer SHALL reset for next chunk

### Requirement: No resumable uploads in Phase 2
The system SHALL NOT support resuming interrupted uploads.

#### Scenario: Upload interruption requires restart
- **WHEN** chunked upload is interrupted mid-way
- **THEN** the system SHALL NOT resume from last successful chunk (Phase 2 limitation)

#### Scenario: Future enhancement documented
- **WHEN** upload is interrupted
- **THEN** user MUST restart entire upload (documentation SHALL note this as future enhancement)
