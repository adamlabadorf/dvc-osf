# OSF Batch Operations Specification

## Purpose

Provides efficient batch operations for performing copy, move, or delete operations on multiple files, with error aggregation and progress tracking.

## ADDED Requirements

### Requirement: Batch copy operations
The system SHALL support copying multiple files efficiently in a single batch operation.

#### Scenario: Copy multiple files in batch
- **WHEN** batch copy is requested with a list of source-destination pairs
- **THEN** the system SHALL copy each file using the cp() method

#### Scenario: Batch copy with sequential processing
- **WHEN** batch copy operation executes
- **THEN** the system SHALL process files sequentially (not in parallel) for Phase 4

#### Scenario: Batch copy collects errors
- **WHEN** individual file copies fail during batch operation
- **THEN** the system SHALL collect errors and continue with remaining files

#### Scenario: Batch copy returns summary
- **WHEN** batch copy completes
- **THEN** the system SHALL return summary with successful count, failed count, and list of errors

### Requirement: Batch move operations
The system SHALL support moving multiple files efficiently in a single batch operation.

#### Scenario: Move multiple files in batch
- **WHEN** batch move is requested with a list of source-destination pairs
- **THEN** the system SHALL move each file using the mv() method

#### Scenario: Batch move handles partial failures
- **WHEN** some moves succeed and others fail in batch
- **THEN** the system SHALL complete all attempted moves and report which succeeded and which failed

#### Scenario: Batch move with delete warnings
- **WHEN** batch move has copy-succeeded-but-delete-failed cases
- **THEN** the system SHALL log warnings for each orphaned source file

### Requirement: Batch delete operations
The system SHALL support deleting multiple files efficiently in a single batch operation.

#### Scenario: Delete multiple files in batch
- **WHEN** batch delete is requested with a list of paths
- **THEN** the system SHALL delete each file using the rm_file() method

#### Scenario: Batch delete continues after failure
- **WHEN** individual file deletions fail during batch
- **THEN** the system SHALL continue attempting to delete remaining files

#### Scenario: Batch delete returns detailed results
- **WHEN** batch delete completes
- **THEN** the system SHALL return list of successfully deleted paths and list of failed paths with errors

### Requirement: Batch operation error handling
The system SHALL provide comprehensive error aggregation for batch operations.

#### Scenario: Collect all errors during batch
- **WHEN** multiple operations fail in a batch
- **THEN** the system SHALL collect all errors without stopping early

#### Scenario: Provide per-file error details
- **WHEN** batch operation completes with errors
- **THEN** the system SHALL include the file path and specific error for each failure

#### Scenario: Raise batch exception if all operations fail
- **WHEN** all files in a batch operation fail
- **THEN** the system SHALL raise an exception with aggregated error information

#### Scenario: Return success if any operations succeed
- **WHEN** some operations succeed in a batch even if others fail
- **THEN** the system SHALL return successfully with partial results and error details

### Requirement: Batch operation progress tracking
The system SHALL support basic progress tracking for batch operations.

#### Scenario: Track completed count
- **WHEN** batch operation is in progress
- **THEN** the system SHALL maintain count of completed operations

#### Scenario: Provide progress callback support
- **WHEN** batch operation is called with a progress callback
- **THEN** the system SHALL call the callback after each file operation with current progress

#### Scenario: Progress callback includes operation details
- **WHEN** progress callback is invoked
- **THEN** the system SHALL provide current file index, total files, current file path, and operation type

### Requirement: Batch operation validation
The system SHALL validate batch operation inputs before processing.

#### Scenario: Validate non-empty batch
- **WHEN** batch operation is called with empty file list
- **THEN** the system SHALL raise ValueError

#### Scenario: Validate all paths exist for batch move/copy
- **WHEN** batch operation includes source paths that don't exist
- **THEN** the system SHALL either validate all paths first or handle not-found errors per-file

#### Scenario: Validate no duplicate destinations
- **WHEN** batch operation includes duplicate destination paths
- **THEN** the system SHALL raise ValueError indicating conflicting destinations

### Requirement: Batch operation resource management
The system SHALL manage resources efficiently during batch operations.

#### Scenario: Reuse temp files for batch copy
- **WHEN** performing batch copy operations
- **THEN** the system SHALL clean up temp files after each individual copy

#### Scenario: Handle rate limiting in batch
- **WHEN** OSF rate limits are encountered during batch
- **THEN** the system SHALL use existing retry logic with exponential backoff

#### Scenario: Limit memory usage in batch
- **WHEN** processing batch operations
- **THEN** the system SHALL NOT load all file contents into memory simultaneously
