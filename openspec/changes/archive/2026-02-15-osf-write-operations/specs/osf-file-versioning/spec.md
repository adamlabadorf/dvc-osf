# OSF File Versioning Specification

## Purpose

Provides support for OSF's native file versioning system, including automatic version creation on overwrites, version metadata retrieval, and integration with OSF's version history.

## ADDED Requirements

### Requirement: Automatic version creation on overwrite
The system SHALL create new file versions automatically when existing files are overwritten.

#### Scenario: Upload overwrites creates new version
- **WHEN** put_file() uploads to a path that already exists on OSF
- **THEN** OSF SHALL automatically create a new version and preserve the old version

#### Scenario: Multiple overwrites create multiple versions
- **WHEN** same file path is uploaded multiple times
- **THEN** OSF SHALL create a new version for each upload, maintaining version history

#### Scenario: Version numbers increment
- **WHEN** new version is created
- **THEN** OSF SHALL assign the next sequential version number

### Requirement: Version metadata access
The system SHALL provide access to file version metadata from OSF.

#### Scenario: Get current version number
- **WHEN** info() is called on a file with versions
- **THEN** the system SHALL include current version number in metadata if available

#### Scenario: Get version creation date
- **WHEN** querying file metadata
- **THEN** the system SHALL include when the current version was created

#### Scenario: Get version creator
- **WHEN** querying file metadata with version information
- **THEN** the system SHALL include user who created the current version if available

### Requirement: Always operate on latest version
The system SHALL default to operating on the latest version of files.

#### Scenario: Read from latest version
- **WHEN** open() or get_file() is called without version specifier
- **THEN** the system SHALL read from the most recent version

#### Scenario: Upload creates latest version
- **WHEN** put_file() uploads to existing file
- **THEN** the uploaded content SHALL become the new latest version

#### Scenario: Info returns latest version metadata
- **WHEN** info() is called on a file with multiple versions
- **THEN** the system SHALL return metadata for the latest version

### Requirement: Version history preservation
The system SHALL preserve version history through write operations.

#### Scenario: Overwrite preserves old versions
- **WHEN** file is overwritten multiple times
- **THEN** all previous versions SHALL remain accessible through OSF web interface

#### Scenario: Delete removes all versions
- **WHEN** rm() deletes a file
- **THEN** all versions of that file SHALL be removed (OSF behavior)

### Requirement: No explicit version pinning in Phase 2
The system SHALL NOT support reading specific version numbers in this phase.

#### Scenario: Cannot specify version number
- **WHEN** attempting to read a specific version (not latest)
- **THEN** the system SHALL NOT provide a mechanism for this (future enhancement)

#### Scenario: Version pinning deferred
- **WHEN** user needs to access old versions
- **THEN** they MUST use OSF web interface (Phase 2 limitation documented)

### Requirement: Version conflict handling
The system SHALL handle version-related conflicts gracefully.

#### Scenario: Concurrent uploads create separate versions
- **WHEN** two users upload to same file simultaneously
- **THEN** OSF SHALL create separate versions for both uploads (last write wins for "latest")

#### Scenario: No version lock required
- **WHEN** uploading to a file
- **THEN** the system SHALL NOT require acquiring a version lock (OSF handles conflicts)

### Requirement: Version checksums
The system SHALL use OSF's version-specific checksums for integrity.

#### Scenario: Each version has unique checksum
- **WHEN** new version is created with different content
- **THEN** OSF SHALL compute and store a unique checksum for that version

#### Scenario: Verify against version checksum
- **WHEN** downloading or uploading file
- **THEN** the system SHALL use the specific version's checksum for verification

### Requirement: Version size tracking
The system SHALL report size for the current version.

#### Scenario: Get current version size
- **WHEN** info() is called
- **THEN** the system SHALL return the size of the latest version

#### Scenario: Size changes between versions
- **WHEN** file content changes between versions
- **THEN** each version SHALL have its own size value

### Requirement: Version metadata in file listings
The system SHALL include version information when listing files.

#### Scenario: List files shows current version
- **WHEN** ls() is called with detail=True
- **THEN** each file entry SHALL include version metadata if available

#### Scenario: Version info in detailed listings
- **WHEN** ls() returns detailed file information
- **THEN** version number and modified date SHALL reflect the latest version

### Requirement: Integration with DVC's content-addressed storage
The system SHALL integrate OSF versioning with DVC's hash-based storage model.

#### Scenario: DVC stores by content hash
- **WHEN** DVC uploads file to OSF
- **THEN** the system SHALL use DVC's content hash as the path, and OSF versions track changes

#### Scenario: Same hash not reuploaded
- **WHEN** DVC attempts to push file with existing hash
- **THEN** the system SHALL skip upload if checksum matches (file already exists)

#### Scenario: Different content creates new path
- **WHEN** file content changes
- **THEN** DVC SHALL use a different hash path, creating a new file (not a version of old one)

### Requirement: Version behavior documentation
The system SHALL clearly document OSF versioning behavior for users.

#### Scenario: Document automatic versioning
- **WHEN** user reads documentation
- **THEN** it SHALL explain that overwrites create versions automatically

#### Scenario: Document version access limitations
- **WHEN** user needs to access old versions
- **THEN** documentation SHALL direct them to OSF web interface

#### Scenario: Document version and DVC interaction
- **WHEN** user integrates with DVC
- **THEN** documentation SHALL explain how DVC's content addressing interacts with OSF versions
