# OSF Filesystem Copy Operations Specification

## Purpose

Provides copy operations for duplicating files and directories within OSF storage, supporting both single-file and recursive directory copying with checksum verification.

## ADDED Requirements

### Requirement: Copy single file within OSF storage
The system SHALL provide a cp() method to copy a file from one OSF path to another within the same project and storage provider.

#### Scenario: Copy file successfully
- **WHEN** cp() is called with valid source and destination paths
- **THEN** the system SHALL create a copy of the source file at the destination path

#### Scenario: Verify copied file integrity
- **WHEN** a file is copied
- **THEN** the system SHALL verify the destination file checksum matches the source file checksum

#### Scenario: Copy non-existent file
- **WHEN** cp() is called with a non-existent source path
- **THEN** the system SHALL raise OSFNotFoundError

#### Scenario: Copy to existing destination without overwrite
- **WHEN** cp() is called with an existing destination path and overwrite=False
- **THEN** the system SHALL raise OSFConflictError

#### Scenario: Copy to existing destination with overwrite
- **WHEN** cp() is called with an existing destination path and overwrite=True
- **THEN** the system SHALL replace the destination file with the source file

#### Scenario: Copy file preserves content
- **WHEN** a file is copied
- **THEN** the destination file SHALL contain identical content to the source file

### Requirement: Copy directory recursively
The system SHALL support recursive copying of directories and their contents.

#### Scenario: Copy directory with recursive flag
- **WHEN** cp() is called on a directory path with recursive=True
- **THEN** the system SHALL copy all files within the directory to the destination

#### Scenario: Copy directory without recursive flag
- **WHEN** cp() is called on a directory path with recursive=False
- **THEN** the system SHALL raise OSFOperationNotSupportedError

#### Scenario: Copy nested directory structure
- **WHEN** cp() is called on a directory with subdirectories and recursive=True
- **THEN** the system SHALL recursively copy all subdirectories and files preserving structure

#### Scenario: Copy empty directory
- **WHEN** cp() is called on an empty directory with recursive=True
- **THEN** the system SHALL complete successfully without copying any files

### Requirement: Validate copy operation constraints
The system SHALL validate that copy operations meet OSF constraints before attempting the copy.

#### Scenario: Cross-project copy attempt
- **WHEN** cp() is called with source and destination in different OSF projects
- **THEN** the system SHALL raise OSFOperationNotSupportedError with message explaining cross-project limitation

#### Scenario: Cross-provider copy attempt
- **WHEN** cp() is called with source and destination in different storage providers
- **THEN** the system SHALL raise OSFOperationNotSupportedError with message explaining cross-provider limitation

#### Scenario: Same-project same-provider copy
- **WHEN** cp() is called with source and destination in same project and provider
- **THEN** the system SHALL proceed with the copy operation

### Requirement: Handle copy operation failures gracefully
The system SHALL handle partial failures during copy operations and provide clear error reporting.

#### Scenario: Partial directory copy failure
- **WHEN** copying a directory recursively and a file copy fails
- **THEN** the system SHALL raise an exception indicating which file failed and how many files were copied successfully

#### Scenario: Insufficient permissions on destination
- **WHEN** cp() is called but user lacks write permissions on destination
- **THEN** the system SHALL raise OSFPermissionError

#### Scenario: Quota exceeded during copy
- **WHEN** cp() would exceed OSF storage quota
- **THEN** the system SHALL raise OSFQuotaExceededError

### Requirement: Copy operation implementation strategy
The system SHALL implement copy using download-then-upload approach with temp files.

#### Scenario: Copy downloads source to temp file
- **WHEN** cp() is called
- **THEN** the system SHALL download source file to a temporary location

#### Scenario: Copy uploads from temp file to destination
- **WHEN** source is downloaded to temp file
- **THEN** the system SHALL upload the temp file content to destination path

#### Scenario: Copy cleans up temp files
- **WHEN** copy operation completes (success or failure)
- **THEN** the system SHALL delete temporary files created during the operation

#### Scenario: Copy streams large files
- **WHEN** copying files larger than memory limits
- **THEN** the system SHALL stream data through temp files without loading entire file into memory
