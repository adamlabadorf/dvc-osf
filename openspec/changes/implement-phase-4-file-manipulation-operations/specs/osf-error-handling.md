# OSF Error Handling Delta Specification (Phase 4)

## Purpose

Extends the OSF error handling system with new exception types for file manipulation operations (conflict errors, unsupported operations).

## ADDED Requirements

### Requirement: Conflict error handling
The system SHALL raise OSFConflictError when file operations encounter conflicts.

#### Scenario: Destination file exists on copy without overwrite
- **WHEN** copying a file and destination exists with overwrite=False
- **THEN** the system SHALL raise OSFConflictError inheriting from FileExistsError

#### Scenario: Destination file exists on move
- **WHEN** moving a file and destination already exists
- **THEN** the system SHALL raise OSFConflictError with message indicating conflicting destination

#### Scenario: Conflict error includes paths
- **WHEN** OSFConflictError is raised
- **THEN** the exception SHALL include both source and destination paths in the message

### Requirement: Operation not supported error handling
The system SHALL raise OSFOperationNotSupportedError for operations that cannot be performed.

#### Scenario: Cross-project operation attempt
- **WHEN** attempting to copy or move files across different OSF projects
- **THEN** the system SHALL raise OSFOperationNotSupportedError with message explaining the limitation

#### Scenario: Cross-provider operation attempt
- **WHEN** attempting to copy or move files across different storage providers
- **THEN** the system SHALL raise OSFOperationNotSupportedError with message explaining the limitation

#### Scenario: Directory copy without recursive flag
- **WHEN** attempting to copy a directory with recursive=False
- **THEN** the system SHALL raise OSFOperationNotSupportedError with message suggesting recursive=True

#### Scenario: Operation not supported error includes suggestion
- **WHEN** OSFOperationNotSupportedError is raised
- **THEN** the exception message SHALL include guidance on what operations are supported

### Requirement: Enhanced permission error context
The system SHALL provide detailed context for permission errors during file manipulation.

#### Scenario: Permission denied on copy destination
- **WHEN** copy fails due to insufficient write permissions on destination
- **THEN** the system SHALL raise OSFPermissionError with message indicating destination path and required permission

#### Scenario: Permission denied on delete
- **WHEN** delete fails due to insufficient permissions
- **THEN** the system SHALL raise OSFPermissionError with message indicating file path and delete permission requirement

#### Scenario: Permission denied on move source
- **WHEN** move fails due to insufficient read or delete permissions on source
- **THEN** the system SHALL raise OSFPermissionError indicating which permission is missing

### Requirement: Batch operation error aggregation
The system SHALL support aggregating multiple errors from batch operations.

#### Scenario: Collect multiple file operation errors
- **WHEN** batch operation encounters multiple failures
- **THEN** the system SHALL provide a way to access all individual errors

#### Scenario: Batch error summary
- **WHEN** batch operation fails for some files
- **THEN** the error SHALL include count of successes and failures

#### Scenario: Preserve individual error details
- **WHEN** batch operation errors are aggregated
- **THEN** each individual error SHALL retain its path, operation, and specific error type
