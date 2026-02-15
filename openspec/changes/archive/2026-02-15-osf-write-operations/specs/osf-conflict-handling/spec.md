# OSF Conflict Handling Specification

## Purpose

Provides strategies for detecting and handling conflicts during concurrent modifications to OSF files, including conflict resolution through OSF's versioning system and appropriate error handling.

## ADDED Requirements

### Requirement: Leverage OSF versioning for conflict resolution
The system SHALL use OSF's automatic versioning as the primary conflict resolution strategy.

#### Scenario: Concurrent uploads create versions
- **WHEN** two clients upload to same file simultaneously
- **THEN** OSF SHALL accept both uploads and create separate versions

#### Scenario: Last write wins for latest version
- **WHEN** concurrent uploads complete
- **THEN** the last upload to finish SHALL be marked as the "latest" version

#### Scenario: Both uploads preserved
- **WHEN** concurrent conflict occurs
- **THEN** both uploaded contents SHALL be preserved in version history

### Requirement: No distributed locking
The system SHALL NOT implement file locking mechanisms.

#### Scenario: No lock acquisition before write
- **WHEN** uploading a file
- **THEN** the system SHALL NOT attempt to acquire a distributed lock

#### Scenario: OSF API provides no locking
- **WHEN** checking OSF API capabilities
- **THEN** OSF v2 API SHALL NOT provide lock/unlock endpoints

#### Scenario: Accept version-based conflicts
- **WHEN** writes conflict
- **THEN** the system SHALL rely on OSF's versioning rather than preventing conflicts

### Requirement: Conflict detection through metadata
The system SHALL detect potential conflicts by checking file metadata.

#### Scenario: Check if file exists before upload
- **WHEN** put_file() is called
- **THEN** the system MAY call exists() or info() to determine if file already exists

#### Scenario: Detect modification during upload
- **WHEN** uploading large file over extended time
- **THEN** the system SHALL NOT detect if another client modifies the file concurrently (limitation accepted)

### Requirement: Conflict behavior documentation
The system SHALL document conflict behavior clearly.

#### Scenario: Document version-based resolution
- **WHEN** user reads documentation
- **THEN** it SHALL explain that conflicts are resolved through versioning

#### Scenario: Document no locking
- **WHEN** user expects file locking
- **THEN** documentation SHALL clarify that OSF doesn't provide locking

#### Scenario: Document collaborative workflows
- **WHEN** multiple users work on same OSF project
- **THEN** documentation SHALL recommend coordination strategies (e.g., separate directories)

### Requirement: Consistent behavior with OSF web interface
The system SHALL behave consistently with OSF's web interface for conflicts.

#### Scenario: Same versioning behavior as web upload
- **WHEN** uploading via dvc-osf
- **THEN** version creation SHALL match what happens when uploading via OSF website

#### Scenario: Same conflict outcomes
- **WHEN** concurrent modifications occur
- **THEN** results SHALL be same as if both users uploaded via OSF web interface

### Requirement: Predictable conflict outcomes
The system SHALL ensure conflicts have predictable, documented outcomes.

#### Scenario: Overwrites always create versions
- **WHEN** file is overwritten
- **THEN** new version SHALL always be created (predictable behavior)

#### Scenario: No silent data loss
- **WHEN** conflict occurs
- **THEN** no uploaded data SHALL be lost (both versions preserved)

#### Scenario: Latest version deterministic
- **WHEN** conflict resolves
- **THEN** the "latest" version SHALL be the one that completed last (deterministic)

### Requirement: No conflict errors raised
The system SHALL NOT raise errors for version-based conflicts.

#### Scenario: Successful upload despite conflict
- **WHEN** uploading to file being modified by another client
- **THEN** the system SHALL complete upload successfully

#### Scenario: No 409 Conflict errors
- **WHEN** OSF handles concurrent uploads
- **THEN** the system SHALL NOT receive or raise 409 Conflict HTTP errors

### Requirement: Atomic operation boundary
The system SHALL consider each file upload as atomic from conflict perspective.

#### Scenario: File-level atomicity
- **WHEN** uploading a file
- **THEN** the entire file upload SHALL be atomic (not individual chunks from conflict perspective)

#### Scenario: No cross-file transactions
- **WHEN** uploading multiple files
- **THEN** each file upload SHALL be independent (no multi-file atomic transactions)

### Requirement: Checksum-based conflict avoidance
The system SHALL use checksums to avoid unnecessary uploads.

#### Scenario: Skip upload if checksum matches
- **WHEN** attempting to upload file with same content as current version
- **THEN** the system SHALL detect matching checksum and skip upload

#### Scenario: Different checksum triggers upload
- **WHEN** file content differs from current version
- **THEN** the system SHALL proceed with upload despite file existing

### Requirement: Conflict metadata in exceptions
The system SHALL provide conflict-related information in exceptions when applicable.

#### Scenario: Include current version in error
- **WHEN** operation fails due to conflict-related issue
- **THEN** exception SHALL include current version information if available

#### Scenario: Suggest checking version history
- **WHEN** unexpected file state encountered
- **THEN** error message SHALL suggest checking OSF version history

### Requirement: Rate limiting under conflict load
The system SHALL handle rate limiting that may occur during conflicts.

#### Scenario: Many concurrent operations trigger rate limits
- **WHEN** multiple clients upload simultaneously causing high API load
- **THEN** the system SHALL handle rate limit errors with backoff

#### Scenario: Retry after rate limit
- **WHEN** rate limited during conflict scenario
- **THEN** the system SHALL wait and retry according to rate limit policy

### Requirement: Conflict handling in DVC workflows
The system SHALL support DVC's conflict resolution through content addressing.

#### Scenario: DVC content-addressed storage avoids conflicts
- **WHEN** DVC pushes data
- **THEN** different file contents SHALL have different paths (no conflicts)

#### Scenario: Same content from multiple sources
- **WHEN** multiple DVC clients push same data (same hash)
- **THEN** the system SHALL recognize identical content and avoid redundant uploads

### Requirement: Directory-level conflict handling
The system SHALL handle directory operations considering conflicts.

#### Scenario: Multiple clients create same directory
- **WHEN** multiple clients call mkdir() for same path
- **THEN** both SHALL succeed (directories are virtual, no conflict)

#### Scenario: File operations in concurrent directory creation
- **WHEN** multiple clients upload to files in same new directory
- **THEN** all uploads SHALL succeed with directory created implicitly

### Requirement: Delete operation conflict handling
The system SHALL handle conflicts when files are deleted.

#### Scenario: Delete after concurrent modification
- **WHEN** file is deleted after another client modified it
- **THEN** deletion SHALL remove all versions (OSF behavior)

#### Scenario: Delete non-existent file
- **WHEN** attempting to delete file already deleted by another client
- **THEN** the system SHALL raise OSFNotFoundError

#### Scenario: Concurrent delete operations
- **WHEN** multiple clients attempt to delete same file
- **THEN** first deletion SHALL succeed, others SHALL raise OSFNotFoundError

### Requirement: Conflict behavior testing
The system SHALL include tests for conflict scenarios.

#### Scenario: Test concurrent upload simulation
- **WHEN** running test suite
- **THEN** it SHALL include tests simulating concurrent uploads

#### Scenario: Test version creation under conflicts
- **WHEN** testing conflict scenarios
- **THEN** tests SHALL verify that multiple versions are created

#### Scenario: Integration tests with real concurrency
- **WHEN** running integration tests
- **THEN** they SHALL include actual concurrent operations against test OSF project
