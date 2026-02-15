# Dependency Management - Delta Specification

## ADDED Requirements

### Requirement: HTTP client library dependency
The project SHALL include `requests` library as a core dependency for HTTP client functionality.

#### Scenario: Requests library is available
- **WHEN** package is installed
- **THEN** requests>=2.28.0 is installed as a dependency

#### Scenario: Requests library can be imported
- **WHEN** dvc_osf modules are imported
- **THEN** requests library can be imported without error

### Requirement: URL parsing library dependency
The project SHALL include `urllib3` library as a dependency for connection pooling.

#### Scenario: urllib3 library is available
- **WHEN** package is installed
- **THEN** urllib3>=1.26.0 is installed as a dependency

#### Scenario: urllib3 can be used for connection pooling
- **WHEN** OSFAPIClient creates connection pool
- **THEN** urllib3 library provides pooling functionality

### Requirement: DVC objects dependency
The project SHALL include `dvc-objects` library for filesystem abstraction base class.

#### Scenario: dvc-objects library is available
- **WHEN** package is installed
- **THEN** dvc-objects>=5.0.0 is installed as a dependency

#### Scenario: ObjectFileSystem can be imported
- **WHEN** filesystem.py imports base class
- **THEN** dvc_objects.fs.base.ObjectFileSystem can be imported without error

### Requirement: Optional caching dependency
The project MAY include `requests-cache` as an optional dependency for API response caching.

#### Scenario: requests-cache is in optional dependencies
- **WHEN** examining pyproject.toml optional dependencies
- **THEN** requests-cache>=1.0.0 is listed under [project.optional-dependencies.cache]

#### Scenario: Package works without requests-cache
- **WHEN** package is installed without optional dependencies
- **THEN** all core functionality works (caching is disabled)

### Requirement: Lock files include new dependencies
Both uv.lock and poetry.lock SHALL include the new core dependencies.

#### Scenario: uv.lock includes new dependencies
- **WHEN** uv.lock is examined
- **THEN** it includes entries for requests, urllib3, and dvc-objects

#### Scenario: poetry.lock includes new dependencies
- **WHEN** poetry.lock is examined
- **THEN** it includes entries for requests, urllib3, and dvc-objects

### Requirement: Dependency version constraints
The project SHALL specify minimum versions for core dependencies to ensure compatibility.

#### Scenario: requests minimum version
- **WHEN** pyproject.toml is examined
- **THEN** requests dependency specifies >=2.28.0

#### Scenario: urllib3 minimum version
- **WHEN** pyproject.toml is examined
- **THEN** urllib3 dependency specifies >=1.26.0

#### Scenario: dvc-objects minimum version
- **WHEN** pyproject.toml is examined
- **THEN** dvc-objects dependency specifies >=5.0.0

### Requirement: Python version compatibility
New dependencies SHALL be compatible with Python 3.8+.

#### Scenario: All dependencies support Python 3.8
- **WHEN** dependencies are resolved
- **THEN** all versions are compatible with Python 3.8 or higher
