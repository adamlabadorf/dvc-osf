# OSF Path Handling Specification

## ADDED Requirements

### Requirement: OSF URL parsing
The system SHALL parse OSF URLs in the format 'osf://PROJECT_ID/STORAGE_PROVIDER/PATH'.

#### Scenario: Parse basic OSF URL
- **WHEN** URL is 'osf://abc123/osfstorage/data.csv'
- **THEN** the system SHALL extract project_id='abc123', provider='osfstorage', path='data.csv'

#### Scenario: Parse OSF URL with nested path
- **WHEN** URL is 'osf://abc123/osfstorage/folder/subfolder/file.txt'
- **THEN** the system SHALL extract project_id='abc123', provider='osfstorage', path='folder/subfolder/file.txt'

#### Scenario: Parse OSF URL with root path
- **WHEN** URL is 'osf://abc123/osfstorage/'
- **THEN** the system SHALL extract project_id='abc123', provider='osfstorage', path=''

#### Scenario: Parse OSF URL without trailing slash
- **WHEN** URL is 'osf://abc123/osfstorage'
- **THEN** the system SHALL extract project_id='abc123', provider='osfstorage', path=''

### Requirement: Default storage provider
The system SHALL use 'osfstorage' as the default storage provider when not specified.

#### Scenario: URL without storage provider
- **WHEN** URL is 'osf://abc123/data.csv'
- **THEN** the system SHALL use provider='osfstorage' and path='data.csv'

#### Scenario: URL with only project ID
- **WHEN** URL is 'osf://abc123'
- **THEN** the system SHALL use provider='osfstorage' and path=''

### Requirement: OSF project ID validation
The system SHALL validate OSF project IDs for correct format.

#### Scenario: Valid alphanumeric project ID
- **WHEN** project_id contains only letters and numbers (e.g., 'abc123')
- **THEN** the system SHALL accept it as valid

#### Scenario: Valid project ID with minimum length
- **WHEN** project_id is at least 5 characters long
- **THEN** the system SHALL accept it as valid

#### Scenario: Invalid empty project ID
- **WHEN** project_id is empty or missing
- **THEN** the system SHALL raise ValueError with message 'OSF project ID cannot be empty'

#### Scenario: Invalid project ID with special characters
- **WHEN** project_id contains special characters other than letters and numbers
- **THEN** the system SHALL raise ValueError with message 'OSF project ID must contain only letters and numbers'

### Requirement: Path normalization
The system SHALL normalize file paths to ensure consistent handling.

#### Scenario: Remove leading slashes
- **WHEN** path starts with '/' (e.g., '/folder/file.txt')
- **THEN** the system SHALL normalize it to 'folder/file.txt'

#### Scenario: Remove trailing slashes from file paths
- **WHEN** path ends with '/' and refers to a file
- **THEN** the system SHALL remove the trailing slash

#### Scenario: Collapse multiple consecutive slashes
- **WHEN** path contains '//' (e.g., 'folder//file.txt')
- **THEN** the system SHALL normalize it to 'folder/file.txt'

#### Scenario: Resolve relative path components
- **WHEN** path contains './' or '../' components
- **THEN** the system SHALL resolve them to absolute paths or raise error if they escape root

### Requirement: Path joining
The system SHALL join path components correctly for OSF paths.

#### Scenario: Join base path and filename
- **WHEN** joining 'folder' and 'file.txt'
- **THEN** the system SHALL produce 'folder/file.txt'

#### Scenario: Join paths with existing slashes
- **WHEN** joining 'folder/' and 'file.txt'
- **THEN** the system SHALL produce 'folder/file.txt' (no double slash)

#### Scenario: Join empty path components
- **WHEN** joining '' and 'file.txt'
- **THEN** the system SHALL produce 'file.txt'

### Requirement: Path to OSF API endpoint conversion
The system SHALL convert filesystem paths to OSF API endpoint URLs.

#### Scenario: Convert project root to API endpoint
- **WHEN** path represents project root (project_id='abc123', provider='osfstorage', path='')
- **THEN** the system SHALL generate API URL 'https://api.osf.io/v2/nodes/abc123/files/osfstorage/'

#### Scenario: Convert file path to API endpoint
- **WHEN** path represents a file (project_id='abc123', provider='osfstorage', path='data.csv')
- **THEN** the system SHALL generate API URL 'https://api.osf.io/v2/nodes/abc123/files/osfstorage/data.csv'

#### Scenario: Convert nested path to API endpoint
- **WHEN** path is 'folder/subfolder/file.txt'
- **THEN** the system SHALL properly encode path segments and generate correct API URL

### Requirement: URL encoding for special characters
The system SHALL properly encode special characters in paths for API requests.

#### Scenario: Encode spaces in path
- **WHEN** path contains spaces (e.g., 'my file.txt')
- **THEN** the system SHALL encode it as 'my%20file.txt' in API URLs

#### Scenario: Encode special characters
- **WHEN** path contains special characters (e.g., 'file&name.txt')
- **THEN** the system SHALL properly URL-encode the characters

#### Scenario: Preserve forward slashes
- **WHEN** path contains forward slashes as separators
- **THEN** the system SHALL NOT encode them (keep as '/')

### Requirement: Path existence checking
The system SHALL provide utilities to check if paths represent valid OSF resources.

#### Scenario: Check if path is root
- **WHEN** path is empty string
- **THEN** the system SHALL identify it as representing the storage provider root

#### Scenario: Check if path is absolute
- **WHEN** path starts from the storage provider root
- **THEN** the system SHALL identify it as an absolute path (relative to the configured project and provider)

### Requirement: Path component extraction
The system SHALL extract specific components from OSF paths.

#### Scenario: Extract filename from path
- **WHEN** path is 'folder/subfolder/file.txt'
- **THEN** the system SHALL extract 'file.txt' as the filename

#### Scenario: Extract directory from path
- **WHEN** path is 'folder/subfolder/file.txt'
- **THEN** the system SHALL extract 'folder/subfolder' as the directory path

#### Scenario: Extract parent directory
- **WHEN** path is 'folder/subfolder/file.txt'
- **THEN** the system SHALL extract 'folder/subfolder' as the parent directory

### Requirement: Path comparison
The system SHALL provide utilities to compare OSF paths.

#### Scenario: Check if path is child of another
- **WHEN** comparing 'folder/file.txt' with 'folder/'
- **THEN** the system SHALL identify that 'folder/file.txt' is a child of 'folder/'

#### Scenario: Check if paths are equal
- **WHEN** comparing normalized paths
- **THEN** the system SHALL correctly identify equal paths regardless of trailing slashes

### Requirement: Invalid path handling
The system SHALL reject invalid OSF paths with clear error messages.

#### Scenario: Reject path with invalid scheme
- **WHEN** URL scheme is not 'osf://'
- **THEN** the system SHALL raise ValueError with message 'Invalid OSF URL scheme. Expected osf://'

#### Scenario: Reject malformed URL
- **WHEN** URL cannot be parsed as valid OSF format
- **THEN** the system SHALL raise ValueError with descriptive message about expected format

### Requirement: Path serialization
The system SHALL convert internal path representations back to OSF URL format.

#### Scenario: Serialize path components to URL
- **WHEN** internal path has project_id='abc123', provider='osfstorage', path='data.csv'
- **THEN** the system SHALL serialize it to 'osf://abc123/osfstorage/data.csv'

#### Scenario: Serialize root path to URL
- **WHEN** internal path has project_id='abc123', provider='osfstorage', path=''
- **THEN** the system SHALL serialize it to 'osf://abc123/osfstorage/'
