## ADDED Requirements

### Requirement: Single pyproject.toml configuration
The project SHALL use a single `pyproject.toml` file that works with both uv and poetry dependency managers.

#### Scenario: File uses PEP 621 project section
- **WHEN** `pyproject.toml` is examined
- **THEN** it contains a `[project]` section with standard metadata fields

#### Scenario: Both uv and poetry can read the configuration
- **WHEN** either `uv sync` or `poetry install` is executed
- **THEN** dependencies are resolved successfully without errors

### Requirement: Core dependencies are specified
The project SHALL declare core runtime dependencies in the `[project]` dependencies section.

#### Scenario: Required packages are listed
- **WHEN** `pyproject.toml` is examined
- **THEN** it lists `dvc-objects>=5.0.0`, `requests>=2.28.0`, and `fsspec>=2023.1.0`

### Requirement: Development dependencies are optional
The project SHALL declare development dependencies in `[project.optional-dependencies]` under a `dev` group.

#### Scenario: Dev dependencies include testing tools
- **WHEN** the dev dependencies are examined
- **THEN** they include pytest, pytest-cov, pytest-mock

#### Scenario: Dev dependencies include code quality tools
- **WHEN** the dev dependencies are examined
- **THEN** they include black, isort, flake8, mypy

#### Scenario: Dev dependencies include pre-commit
- **WHEN** the dev dependencies are examined
- **THEN** they include pre-commit

### Requirement: Both tools generate lock files
The project SHALL support both `uv.lock` and `poetry.lock` files for reproducible installs.

#### Scenario: uv generates lock file
- **WHEN** `uv sync` is executed
- **THEN** a `uv.lock` file is created or updated

#### Scenario: Poetry generates lock file
- **WHEN** `poetry install` is executed
- **THEN** a `poetry.lock` file is created or updated

### Requirement: Python version constraint is specified
The project SHALL specify minimum and maximum Python versions in `pyproject.toml`.

#### Scenario: Minimum Python 3.8 is required
- **WHEN** `pyproject.toml` is examined
- **THEN** `requires-python` is set to `">=3.8"`

### Requirement: Build system is configured
The project SHALL specify a PEP 517-compliant build system in `pyproject.toml`.

#### Scenario: Build backend is specified
- **WHEN** `pyproject.toml` is examined
- **THEN** it contains a `[build-system]` section with `requires` and `build-backend` fields

#### Scenario: setuptools is configured as backend
- **WHEN** the build backend is examined
- **THEN** it is set to `"setuptools.build_meta"`

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
