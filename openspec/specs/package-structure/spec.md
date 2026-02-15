## ADDED Requirements

### Requirement: Core package directory exists
The project SHALL have a `dvc_osf/` directory at the repository root that contains the main Python package.

#### Scenario: Package is importable
- **WHEN** a user installs the package
- **THEN** they can import dvc_osf with `import dvc_osf`

### Requirement: Package includes version identifier
The package SHALL define a `__version__` attribute in `dvc_osf/__init__.py`.

#### Scenario: Version is accessible at runtime
- **WHEN** the package is imported
- **THEN** `dvc_osf.__version__` returns the current version string

### Requirement: Core modules are present
The package SHALL include the following modules in the `dvc_osf/` directory:
- `filesystem.py` - OSFFileSystem class and filesystem operations
- `api.py` - OSF API client
- `auth.py` - Authentication handling
- `utils.py` - Utility functions
- `exceptions.py` - Custom exception classes
- `config.py` - Configuration management

#### Scenario: All modules can be imported
- **WHEN** each module is imported individually
- **THEN** no ImportError is raised

### Requirement: Modules contain full implementations
Each core module SHALL contain full implementations of OSF functionality, not just placeholders.

#### Scenario: Filesystem module has complete OSFFileSystem class
- **WHEN** `filesystem.py` is examined
- **THEN** it contains a complete `OSFFileSystem` class that extends `dvc_objects.fs.base.ObjectFileSystem`

#### Scenario: API module has complete OSFAPIClient class
- **WHEN** `api.py` is examined
- **THEN** it contains a complete `OSFAPIClient` class with all HTTP methods, retry logic, and error handling

#### Scenario: Auth module has complete authentication implementation
- **WHEN** `auth.py` is examined
- **THEN** it contains complete PAT authentication handling and token management

#### Scenario: Utils module has path handling utilities
- **WHEN** `utils.py` is examined
- **THEN** it contains complete path parsing, URL handling, and helper functions

#### Scenario: Exceptions module defines full exception hierarchy
- **WHEN** `exceptions.py` is examined
- **THEN** it contains complete exception hierarchy (OSFException, OSFAuthenticationError, OSFNotFoundError, OSFPermissionError, OSFConnectionError, OSFRateLimitError, OSFAPIError, OSFIntegrityError)

#### Scenario: Config module has configuration constants
- **WHEN** `config.py` is examined
- **THEN** it contains complete configuration constants for API endpoints, timeouts, retry settings, and connection pooling

### Requirement: Tests directory mirrors package structure
The project SHALL have a `tests/` directory at the repository root with test files corresponding to each module.

#### Scenario: Test files exist for each module
- **WHEN** the tests directory is examined
- **THEN** it contains `test_filesystem.py`, `test_api.py`, `test_auth.py`, and other test files

#### Scenario: Conftest provides shared fixtures
- **WHEN** tests need shared fixtures
- **THEN** `tests/conftest.py` provides common test configuration

### Requirement: Package uses __init__ for public API
The `dvc_osf/__init__.py` file SHALL expose the public API of the package.

#### Scenario: Main classes are accessible from package root
- **WHEN** a user imports from dvc_osf
- **THEN** key classes like `OSFFileSystem` are accessible via `from dvc_osf import OSFFileSystem`

### Requirement: Modules implement read operations
The core modules SHALL implement read-only filesystem operations.

#### Scenario: Filesystem module implements exists()
- **WHEN** OSFFileSystem.exists() is called
- **THEN** it returns True/False based on whether path exists in OSF

#### Scenario: Filesystem module implements ls()
- **WHEN** OSFFileSystem.ls() is called
- **THEN** it returns a list of files and directories from OSF

#### Scenario: Filesystem module implements info()
- **WHEN** OSFFileSystem.info() is called
- **THEN** it returns file metadata dictionary from OSF

#### Scenario: Filesystem module implements open() for reading
- **WHEN** OSFFileSystem.open() is called with mode='rb'
- **THEN** it returns a file-like object for reading from OSF

#### Scenario: Filesystem module implements get_file()
- **WHEN** OSFFileSystem.get_file() is called
- **THEN** it downloads the file from OSF to local filesystem

### Requirement: Modules use dependency injection
The core modules SHALL use dependency injection for testability.

#### Scenario: OSFFileSystem accepts API client
- **WHEN** OSFFileSystem is instantiated
- **THEN** it can optionally accept an OSFAPIClient instance for testing

#### Scenario: API client accepts session
- **WHEN** OSFAPIClient is instantiated
- **THEN** it can optionally accept a requests.Session instance for testing
