# OSF API Client Delta Specification (Phase 4)

## Purpose

Extends the OSF API Client with additional HTTP operations needed for file manipulation (copy and move operations), building on the existing GET, POST, PUT, DELETE support.

## ADDED Requirements

### Requirement: High-level file operation methods
The system SHALL provide high-level methods for common file manipulation operations.

#### Scenario: Copy file via download-upload
- **WHEN** copy_file() method is called with source and destination paths
- **THEN** the system SHALL download source file and upload to destination

#### Scenario: Move file via copy-delete
- **WHEN** move_file() method is called with source and destination paths
- **THEN** the system SHALL copy the file and then delete the source

#### Scenario: Delete file via DELETE request
- **WHEN** delete_file() method is called with a file path
- **THEN** the system SHALL make a DELETE request to the file's delete URL

### Requirement: File metadata retrieval for operations
The system SHALL provide methods to retrieve file metadata needed for manipulation operations.

#### Scenario: Get file delete URL
- **WHEN** preparing to delete a file
- **THEN** the system SHALL retrieve the file's delete URL from its metadata

#### Scenario: Get file upload URL for copy destination
- **WHEN** preparing to copy a file
- **THEN** the system SHALL determine the appropriate upload URL for the destination path

#### Scenario: Verify file after copy
- **WHEN** copy operation completes
- **THEN** the system SHALL retrieve destination file metadata to verify the operation

## MODIFIED Requirements

### Requirement: HTTP DELETE requests
The system SHALL support HTTP DELETE requests to OSF API endpoints for deleting resources with enhanced file-specific handling.

#### Scenario: Successful DELETE request
- **WHEN** client makes a DELETE request to a valid resource
- **THEN** the system SHALL return success (no exception raised)

#### Scenario: DELETE non-existent resource
- **WHEN** client makes a DELETE request to a non-existent resource
- **THEN** the system SHALL raise OSFNotFoundError

#### Scenario: DELETE with permission error
- **WHEN** client makes a DELETE request but lacks permissions
- **THEN** the system SHALL raise OSFPermissionError

#### Scenario: DELETE with file lock
- **WHEN** client makes a DELETE request on a locked file
- **THEN** the system SHALL raise OSFFileLockedError
