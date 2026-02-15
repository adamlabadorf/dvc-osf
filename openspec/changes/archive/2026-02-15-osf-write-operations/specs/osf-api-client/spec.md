# OSF API Client Specification

## Purpose

Provides an HTTP client for interacting with the OSF (Open Science Framework) API, including authentication, request/response handling, error handling, connection pooling, retry logic, and streaming support.

## MODIFIED Requirements

### Requirement: HTTP PUT requests
The system SHALL support HTTP PUT requests to OSF API endpoints for updating resources and uploading files.

#### Scenario: PUT request for file upload
- **WHEN** client makes a PUT request with file data
- **THEN** the system SHALL stream the file content in the request body

#### Scenario: PUT request with metadata
- **WHEN** client makes a PUT request with metadata updates
- **THEN** the system SHALL serialize the metadata as JSON in the request body

#### Scenario: PUT request with chunked data
- **WHEN** client makes a PUT request for chunk upload
- **THEN** the system SHALL stream the chunk data without loading entire file into memory

#### Scenario: PUT request with progress tracking
- **WHEN** client makes a PUT request with large file and callback
- **THEN** the system SHALL invoke callback periodically during upload

#### Scenario: PUT request timeout for uploads
- **WHEN** client makes a PUT request for file upload
- **THEN** the system SHALL use upload timeout (default 300 seconds) instead of default request timeout

### Requirement: HTTP DELETE requests
The system SHALL support HTTP DELETE requests to OSF API endpoints for deleting resources.

#### Scenario: Successful DELETE request
- **WHEN** client makes a DELETE request to a valid resource
- **THEN** the system SHALL return success (no exception raised)

#### Scenario: DELETE non-existent resource
- **WHEN** client makes a DELETE request to a non-existent resource
- **THEN** the system SHALL raise OSFNotFoundError

#### Scenario: DELETE without permissions
- **WHEN** client makes a DELETE request without proper permissions
- **THEN** the system SHALL raise OSFPermissionError

### Requirement: Automatic retry for transient failures
The system SHALL automatically retry requests that fail due to transient errors.

#### Scenario: Retry on connection error
- **WHEN** a request fails with a connection error
- **THEN** the system SHALL retry up to the configured maximum (default: 3 times)

#### Scenario: Retry with exponential backoff
- **WHEN** a request is retried
- **THEN** the system SHALL wait progressively longer between retries (exponential backoff factor: 2.0)

#### Scenario: Retry on 500 error
- **WHEN** API returns 500 status code
- **THEN** the system SHALL retry the request up to the maximum retry count

#### Scenario: Retry on 502 error
- **WHEN** API returns 502 status code
- **THEN** the system SHALL retry the request up to the maximum retry count

#### Scenario: Retry on 503 error
- **WHEN** API returns 503 status code
- **THEN** the system SHALL retry the request up to the maximum retry count

#### Scenario: No retry on client errors except rate limits
- **WHEN** API returns 4xx status code (except 429)
- **THEN** the system SHALL NOT retry and SHALL raise an exception immediately

#### Scenario: No retry on 409 conflict
- **WHEN** API returns 409 Conflict status code
- **THEN** the system SHALL NOT retry and SHALL raise an exception immediately

#### Scenario: Retry exhausted
- **WHEN** all retry attempts are exhausted
- **THEN** the system SHALL raise the last encountered exception

## ADDED Requirements

### Requirement: File upload streaming
The system SHALL support streaming file uploads without loading entire files into memory.

#### Scenario: Stream file during PUT
- **WHEN** uploading file via PUT request
- **THEN** the system SHALL read and send file in configurable chunks

#### Scenario: Stream from file object
- **WHEN** PUT request includes file-like object
- **THEN** the system SHALL stream from the object without loading all data

#### Scenario: Upload with progress callback
- **WHEN** uploading with callback parameter
- **THEN** the system SHALL invoke callback with (bytes_sent, total_bytes) periodically

### Requirement: Chunked upload support
The system SHALL support uploading files in chunks for large file handling.

#### Scenario: Upload chunk to OSF
- **WHEN** upload_chunk() is called with chunk data
- **THEN** the system SHALL send chunk data via PUT request

#### Scenario: Track chunk upload progress
- **WHEN** uploading chunks
- **THEN** the system SHALL track bytes uploaded per chunk

#### Scenario: Retry failed chunk upload
- **WHEN** chunk upload fails with retryable error
- **THEN** the system SHALL retry that specific chunk

### Requirement: Upload timeout configuration
The system SHALL support separate timeout values for upload operations.

#### Scenario: Use upload timeout for PUT requests
- **WHEN** making PUT request for file upload
- **THEN** the system SHALL use upload_timeout parameter (default 300s)

#### Scenario: Configurable upload timeout
- **WHEN** client is initialized with custom upload_timeout
- **THEN** the system SHALL use that timeout for upload operations

#### Scenario: Fall back to default timeout
- **WHEN** PUT request is not a file upload
- **THEN** the system SHALL use default request timeout (30s)

### Requirement: Upload error handling
The system SHALL handle upload-specific errors appropriately.

#### Scenario: Map 413 to quota exceeded error
- **WHEN** API returns 413 Payload Too Large during upload
- **THEN** the system SHALL raise OSFQuotaExceededError

#### Scenario: Handle upload interruption
- **WHEN** upload is interrupted by network error
- **THEN** the system SHALL raise OSFConnectionError and mark as retryable

#### Scenario: Handle file size mismatches
- **WHEN** uploaded size doesn't match expected size
- **THEN** the system SHALL include size information in error message

### Requirement: DELETE request error handling
The system SHALL handle deletion-specific errors appropriately.

#### Scenario: Map 404 during delete
- **WHEN** DELETE request returns 404
- **THEN** the system SHALL raise OSFNotFoundError

#### Scenario: Map 403 during delete
- **WHEN** DELETE request returns 403
- **THEN** the system SHALL raise OSFPermissionError

#### Scenario: Map 409 during delete
- **WHEN** DELETE request returns 409
- **THEN** the system SHALL raise OSFAPIError indicating conflict

### Requirement: Request payload size tracking
The system SHALL track request payload sizes for monitoring and error reporting.

#### Scenario: Track upload size
- **WHEN** uploading file data
- **THEN** the system SHALL track total bytes sent

#### Scenario: Include size in error messages
- **WHEN** upload fails
- **THEN** error message SHALL include bytes uploaded before failure
