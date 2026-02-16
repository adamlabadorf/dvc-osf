# OSF Filesystem Move Operations Specification

## Purpose

Provides move and rename operations for relocating files and directories within OSF storage, implemented as copy-then-delete with best-effort atomicity.

## ADDED Requirements

### Requirement: Move single file within OSF storage
The system SHALL provide a mv() method to move or rename a file from one OSF path to another within the same project and storage provider.

#### Scenario: Move file successfully
- **WHEN** mv() is called with valid source and destination paths
- **THEN** the system SHALL move the file from source to destination path

#### Scenario: Source file removed after move
- **WHEN** a file is moved successfully
- **THEN** the system SHALL delete the source file

#### Scenario: Destination contains moved content
- **WHEN** a file is moved successfully
- **THEN** the destination file SHALL contain the same content as the original source file

#### Scenario: Move non-existent file
- **WHEN** mv() is called with a non-existent source path
- **THEN** the system SHALL raise OSFNotFoundError

#### Scenario: Move to existing destination
- **WHEN** mv() is called with an existing destination path
- **THEN** the system SHALL raise OSFConflictError

#### Scenario: Rename file in same directory
- **WHEN** mv() is called with source and destination in the same directory
- **THEN** the system SHALL rename the file to the new name

### Requirement: Move directory recursively
The system SHALL support recursive moving of directories and their contents.

#### Scenario: Move directory with recursive flag
- **WHEN** mv() is called on a directory path with recursive=True
- **THEN** the system SHALL move all files within the directory to the destination

#### Scenario: Move directory without recursive flag
- **WHEN** mv() is called on a directory path with recursive=False
- **THEN** the system SHALL raise OSFOperationNotSupportedError

#### Scenario: Move nested directory structure
- **WHEN** mv() is called on a directory with subdirectories and recursive=True
- **THEN** the system SHALL recursively move all subdirectories and files preserving structure

#### Scenario: Source directory empty after move
- **WHEN** a directory is moved successfully with recursive=True
- **THEN** the source directory SHALL no longer contain any files

### Requirement: Validate move operation constraints
The system SHALL validate that move operations meet OSF constraints before attempting the move.

#### Scenario: Cross-project move attempt
- **WHEN** mv() is called with source and destination in different OSF projects
- **THEN** the system SHALL raise OSFOperationNotSupportedError with message explaining cross-project limitation

#### Scenario: Cross-provider move attempt
- **WHEN** mv() is called with source and destination in different storage providers
- **THEN** the system SHALL raise OSFOperationNotSupportedError with message explaining cross-provider limitation

#### Scenario: Same-project same-provider move
- **WHEN** mv() is called with source and destination in same project and provider
- **THEN** the system SHALL proceed with the move operation

### Requirement: Handle move operation failures with partial completion
The system SHALL handle failures during move operations where copy succeeds but delete fails.

#### Scenario: Copy succeeds but delete fails
- **WHEN** destination copy succeeds but source deletion fails
- **THEN** the system SHALL log a warning but NOT raise an exception (move is functionally complete)

#### Scenario: Copy fails during move
- **WHEN** copying to destination fails
- **THEN** the system SHALL raise an exception and NOT attempt to delete the source file

#### Scenario: Insufficient permissions on destination
- **WHEN** mv() is called but user lacks write permissions on destination
- **THEN** the system SHALL raise OSFPermissionError before attempting any operation

#### Scenario: Insufficient permissions to delete source
- **WHEN** destination copy succeeds but user lacks delete permission on source
- **THEN** the system SHALL log warning about orphaned source file

### Requirement: Move operation atomicity characteristics
The system SHALL document and implement best-effort atomicity for move operations.

#### Scenario: Move is not fully atomic
- **WHEN** mv() is called
- **THEN** the system SHALL perform copy-then-delete as separate operations (not atomic)

#### Scenario: Temporary duplicate during move
- **WHEN** copy completes before delete
- **THEN** both source and destination files SHALL temporarily exist

#### Scenario: Move prioritizes data safety
- **WHEN** move operation encounters errors
- **THEN** the system SHALL prioritize not losing data over strict atomicity (duplicate better than loss)

### Requirement: Move operation implementation strategy
The system SHALL implement move as copy-then-delete using existing copy and delete methods.

#### Scenario: Move uses copy method
- **WHEN** mv() is called
- **THEN** the system SHALL use the cp() method to copy source to destination

#### Scenario: Move deletes source after copy
- **WHEN** copy succeeds
- **THEN** the system SHALL use rm() method to delete the source

#### Scenario: Move verifies copy before delete
- **WHEN** copy operation completes
- **THEN** the system SHALL verify copy succeeded before attempting source deletion
