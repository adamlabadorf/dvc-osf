# OSF Error Handling Specification

## Purpose

Provides a comprehensive exception hierarchy and error handling mechanisms for OSF operations, including authentication, connection, API, permission, and integrity errors with appropriate retry logic and logging.

## ADDED Requirements

### Requirement: Quota exceeded error handling
The system SHALL raise OSFQuotaExceededError when storage quota limits are reached.

#### Scenario: Upload exceeds quota
- **WHEN** file upload fails due to storage quota limit
- **THEN** the system SHALL raise OSFQuotaExceededError inheriting from OSFException

#### Scenario: Quota error includes details
- **WHEN** OSFQuotaExceededError is raised
- **THEN** error message SHALL include information about quota limits and usage

#### Scenario: Quota error includes OSF project link
- **WHEN** quota exceeded
- **THEN** error message SHALL include link to OSF project settings for quota management

#### Scenario: Quota error not retryable
- **WHEN** OSFQuotaExceededError occurs
- **THEN** exception SHALL have retryable=False (user action required)

### Requirement: File locked error handling
The system SHALL raise OSFFileLockedError when attempting to modify locked files.

#### Scenario: Write to locked file
- **WHEN** attempting to upload or delete a locked file
- **THEN** the system SHALL raise OSFFileLockedError inheriting from OSFPermissionError

#### Scenario: Lock error includes file path
- **WHEN** OSFFileLockedError is raised
- **THEN** error message SHALL include the path to the locked file

#### Scenario: Lock error not retryable
- **WHEN** file is locked
- **THEN** exception SHALL have retryable=False (lock must be released first)

### Requirement: Version conflict error handling
The system SHALL raise OSFVersionConflictError for version-related conflicts.

#### Scenario: Version conflict detected
- **WHEN** API returns 409 Conflict for version issue
- **THEN** the system SHALL raise OSFVersionConflictError inheriting from OSFException

#### Scenario: Conflict error includes version info
- **WHEN** OSFVersionConflictError is raised
- **THEN** error message SHALL include current and attempted version information if available

#### Scenario: Conflict error not retryable
- **WHEN** version conflict occurs
- **THEN** exception SHALL have retryable=False (requires resolution)

### Requirement: Write-specific error attributes
The system SHALL include write-specific attributes in exceptions.

#### Scenario: Upload errors include bytes uploaded
- **WHEN** exception is raised during upload
- **THEN** exception SHALL include 'bytes_uploaded' attribute

#### Scenario: Upload errors include total size
- **WHEN** exception is raised during partial upload
- **THEN** exception SHALL include 'total_size' attribute

#### Scenario: Delete errors include resource type
- **WHEN** exception is raised during delete operation
- **THEN** exception SHALL indicate whether target was file or directory

### Requirement: HTTP error mapping for write operations
The system SHALL map HTTP status codes from write operations to appropriate exceptions.

#### Scenario: Map 413 to OSFQuotaExceededError
- **WHEN** API returns 413 Payload Too Large
- **THEN** the system SHALL raise OSFQuotaExceededError

#### Scenario: Map 409 for writes to OSFVersionConflictError
- **WHEN** API returns 409 Conflict during upload
- **THEN** the system SHALL raise OSFVersionConflictError

#### Scenario: Map 423 to OSFFileLockedError
- **WHEN** API returns 423 Locked
- **THEN** the system SHALL raise OSFFileLockedError

### Requirement: Error recovery for write operations
The system SHALL handle error recovery appropriately for write operations.

#### Scenario: Retry transient upload failures
- **WHEN** upload fails with 500/502/503 error
- **THEN** the system SHALL retry according to retry policy

#### Scenario: Do not retry quota errors
- **WHEN** upload fails with quota exceeded
- **THEN** the system SHALL NOT retry (user must free space)

#### Scenario: Do not retry conflict errors
- **WHEN** write operation returns conflict
- **THEN** the system SHALL NOT retry automatically

### Requirement: Write operation error logging
The system SHALL log write-specific errors appropriately.

#### Scenario: Log upload failures with size
- **WHEN** upload fails
- **THEN** log SHALL include file size and bytes uploaded

#### Scenario: Log delete operations
- **WHEN** delete operation fails
- **THEN** log SHALL include target path and operation type

#### Scenario: Log quota errors at WARNING level
- **WHEN** quota exceeded error occurs
- **THEN** system SHALL log at WARNING level (expected user issue)

### Requirement: Clear error messages for write operations
The system SHALL provide actionable error messages for write failures.

#### Scenario: Quota error suggests solutions
- **WHEN** OSFQuotaExceededError is raised
- **THEN** error message SHALL suggest freeing space or upgrading OSF account

#### Scenario: Upload failure suggests retry
- **WHEN** transient upload error occurs
- **THEN** error message SHALL indicate operation will be retried

#### Scenario: Permission error for writes
- **WHEN** write fails due to permissions
- **THEN** error message SHALL explain token needs write scope
