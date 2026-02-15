# OSF Filesystem Write Operations Specification

## Purpose

Provides write operations for OSF storage, including file uploads, directory creation, file deletion, streaming uploads, chunked transfers, and progress tracking for large files.

## ADDED Requirements

### Requirement: Upload file from local path
The system SHALL provide a put_file() method to upload files from local filesystem to OSF.

#### Scenario: Upload small file successfully
- **WHEN** put_file(local_path, remote_path) is called with a file smaller than chunk threshold
- **THEN** the system SHALL upload the file to OSF in a single PUT request

#### Scenario: Upload large file with chunking
- **WHEN** put_file(local_path, remote_path) is called with a file larger than chunk threshold (5MB)
- **THEN** the system SHALL upload the file in chunks using multiple PUT requests

#### Scenario: Upload to non-existent path
- **WHEN** put_file() is called with a remote path in a non-existent directory
- **THEN** the system SHALL create the directory implicitly and upload the file

#### Scenario: Upload overwrites existing file
- **WHEN** put_file() is called with a remote path that already exists
- **THEN** the system SHALL overwrite the file and create a new OSF version

#### Scenario: Upload from non-existent local file
- **WHEN** put_file() is called with a local path that does not exist
- **THEN** the system SHALL raise FileNotFoundError

#### Scenario: Upload with progress callback
- **WHEN** put_file() is called with a callback parameter
- **THEN** the system SHALL call the callback periodically with bytes_uploaded and total_bytes

### Requirement: Upload file from file-like object
The system SHALL provide a put() method to upload data from file-like objects or buffers.

#### Scenario: Upload from file object
- **WHEN** put(file_obj, remote_path) is called with an open file object
- **THEN** the system SHALL read from the file object and upload to OSF

#### Scenario: Upload from BytesIO buffer
- **WHEN** put() is called with a BytesIO or similar buffer object
- **THEN** the system SHALL upload the buffer contents to OSF

#### Scenario: Upload from stream
- **WHEN** put() is called with a streaming object
- **THEN** the system SHALL stream the data to OSF without loading entirely into memory

#### Scenario: Upload with unknown size
- **WHEN** put() is called with a stream that doesn't provide size information
- **THEN** the system SHALL upload the data successfully, reading until EOF

### Requirement: Create directories
The system SHALL provide a mkdir() method to create directories in OSF.

#### Scenario: Create directory
- **WHEN** mkdir(path) is called
- **THEN** the system SHALL succeed without error (OSF creates directories implicitly)

#### Scenario: Create nested directories
- **WHEN** mkdir(path, create_parents=True) is called with nested path
- **THEN** the system SHALL succeed without error (OSF handles path creation)

#### Scenario: Create directory that already exists
- **WHEN** mkdir() is called on an existing directory path
- **THEN** the system SHALL succeed without error (idempotent operation)

### Requirement: Delete files
The system SHALL provide rm() and rm_file() methods to delete files from OSF.

#### Scenario: Delete existing file
- **WHEN** rm(path) is called on an existing file
- **THEN** the system SHALL permanently delete the file from OSF

#### Scenario: Delete non-existent file
- **WHEN** rm(path) is called on a non-existent file
- **THEN** the system SHALL raise OSFNotFoundError

#### Scenario: Delete file without permissions
- **WHEN** rm(path) is called on a file without delete permissions
- **THEN** the system SHALL raise OSFPermissionError

#### Scenario: Delete file with rm_file()
- **WHEN** rm_file(path) is called on a file
- **THEN** the system SHALL delete the file (alias for rm())

### Requirement: Remove directories
The system SHALL provide an rmdir() method to remove directories from OSF.

#### Scenario: Remove empty directory
- **WHEN** rmdir(path) is called
- **THEN** the system SHALL succeed without error (OSF has no explicit directories)

#### Scenario: Remove non-empty directory
- **WHEN** rmdir(path) is called on a path containing files
- **THEN** the system SHALL succeed without error (OSF directories are virtual)

#### Scenario: Remove directory recursively
- **WHEN** rm(path, recursive=True) is called on a directory
- **THEN** the system SHALL delete all files under that path prefix

### Requirement: Upload checksum computation
The system SHALL compute checksums during uploads for integrity verification.

#### Scenario: Compute MD5 during upload
- **WHEN** file is uploaded via put_file() or put()
- **THEN** the system SHALL compute MD5 checksum incrementally during streaming

#### Scenario: Verify uploaded checksum
- **WHEN** upload completes
- **THEN** the system SHALL retrieve file metadata from OSF and compare checksums

#### Scenario: Checksum match after upload
- **WHEN** computed checksum matches OSF's computed checksum
- **THEN** the system SHALL consider the upload successful

#### Scenario: Checksum mismatch after upload
- **WHEN** computed checksum does not match OSF's checksum
- **THEN** the system SHALL raise OSFIntegrityError and mark upload as failed

### Requirement: Upload progress tracking
The system SHALL support progress callbacks for monitoring upload operations.

#### Scenario: Progress callback during chunked upload
- **WHEN** large file is uploaded with callback parameter
- **THEN** the system SHALL invoke callback after each chunk with (bytes_uploaded, total_bytes)

#### Scenario: Progress callback signature
- **WHEN** callback is invoked
- **THEN** the system SHALL pass two integer arguments: bytes_uploaded and total_bytes

#### Scenario: Progress callback for small files
- **WHEN** small file (non-chunked) is uploaded with callback
- **THEN** the system SHALL invoke callback once at completion with (total_bytes, total_bytes)

#### Scenario: No callback provided
- **WHEN** upload operation is called without callback parameter
- **THEN** the system SHALL complete upload without invoking any callback

### Requirement: Upload retry logic
The system SHALL retry uploads on transient failures following the same strategy as reads.

#### Scenario: Retry on network error
- **WHEN** upload fails with connection error
- **THEN** the system SHALL retry up to maximum retry count (default: 3)

#### Scenario: Retry on 500 server error
- **WHEN** OSF API returns 500 during upload
- **THEN** the system SHALL retry with exponential backoff

#### Scenario: Retry on 503 service unavailable
- **WHEN** OSF API returns 503 during upload
- **THEN** the system SHALL retry with exponential backoff

#### Scenario: No retry on 400 bad request
- **WHEN** OSF API returns 400 during upload
- **THEN** the system SHALL raise OSFAPIError without retrying

#### Scenario: No retry on 409 conflict
- **WHEN** OSF API returns 409 conflict during upload
- **THEN** the system SHALL raise appropriate error without retrying

### Requirement: Upload streaming efficiency
The system SHALL upload files efficiently without loading entire files into memory.

#### Scenario: Stream large file upload
- **WHEN** uploading a file larger than available memory
- **THEN** the system SHALL stream the file in chunks without memory errors

#### Scenario: Configurable chunk size
- **WHEN** uploading large files
- **THEN** the system SHALL use configurable chunk size (default from OSF_UPLOAD_CHUNK_SIZE env var or 5MB)

#### Scenario: Read file in chunks
- **WHEN** put_file() uploads a large file
- **THEN** the system SHALL read from disk in chunks matching upload chunk size

### Requirement: Write mode validation
The system SHALL properly handle different file opening modes for write operations.

#### Scenario: Open file in write mode
- **WHEN** open(path, mode='wb') is called
- **THEN** the system SHALL return a writable file-like object for uploading

#### Scenario: Open file in text write mode
- **WHEN** open(path, mode='w') is called
- **THEN** the system SHALL return a writable text file-like object

#### Scenario: Open file in append mode
- **WHEN** open(path, mode='ab') is called
- **THEN** the system SHALL raise NotImplementedError (OSF doesn't support append)

#### Scenario: Write to opened file
- **WHEN** file is opened with write mode and write() is called
- **THEN** the system SHALL buffer the data and upload when file is closed

### Requirement: Atomic upload operations
The system SHALL ensure uploads are atomic from OSF API perspective.

#### Scenario: Upload succeeds completely or fails
- **WHEN** put_file() or put() is interrupted
- **THEN** the OSF SHALL NOT have a partial or corrupted file (OSF API guarantees atomicity)

#### Scenario: Upload interrupted by user
- **WHEN** user terminates process during upload
- **THEN** the OSF SHALL discard any partial upload data

#### Scenario: Upload network interruption
- **WHEN** network fails during upload
- **THEN** the system SHALL retry or fail cleanly without leaving partial files

### Requirement: Upload timeout configuration
The system SHALL support configurable timeouts for upload operations.

#### Scenario: Default upload timeout
- **WHEN** uploading without specifying timeout
- **THEN** the system SHALL use default upload timeout (300 seconds from OSF_UPLOAD_TIMEOUT)

#### Scenario: Custom upload timeout
- **WHEN** upload timeout is configured via environment variable
- **THEN** the system SHALL use the configured timeout value

#### Scenario: Upload timeout exceeded
- **WHEN** upload exceeds configured timeout
- **THEN** the system SHALL raise OSFConnectionError and may retry if retryable

### Requirement: Write operation error handling
The system SHALL handle write-specific errors appropriately.

#### Scenario: Quota exceeded during upload
- **WHEN** upload fails due to storage quota limits
- **THEN** the system SHALL raise OSFQuotaExceededError with descriptive message

#### Scenario: File locked during operation
- **WHEN** attempting to modify a locked file
- **THEN** the system SHALL raise OSFFileLockedError if OSF returns such status

#### Scenario: Insufficient permissions for upload
- **WHEN** attempting to upload without write permissions
- **THEN** the system SHALL raise OSFPermissionError

#### Scenario: Invalid file path
- **WHEN** upload is called with invalid path characters
- **THEN** the system SHALL raise ValueError with message about invalid path
