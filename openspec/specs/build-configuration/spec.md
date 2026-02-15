## ADDED Requirements

### Requirement: Package metadata is complete
The `pyproject.toml` SHALL include complete package metadata in the `[project]` section.

#### Scenario: Required metadata fields are present
- **WHEN** `pyproject.toml` is examined
- **THEN** it includes `name`, `version`, `description`, `authors`, `license`, `readme`, and `requires-python`

#### Scenario: Package name is dvc-osf
- **WHEN** the package name is checked
- **THEN** it is set to `"dvc-osf"`

#### Scenario: License is specified
- **WHEN** license information is checked
- **THEN** it specifies the Apache 2.0 license

### Requirement: Entry points are configured for plugin discovery
The project's pyproject.toml SHALL configure entry points for both fsspec and DVC plugin discovery with complete OSFFileSystem implementation.

#### Scenario: fsspec entry point exists
- **WHEN** pyproject.toml is examined
- **THEN** it contains '[project.entry-points."fsspec.specs"]' section with 'osf = "dvc_osf.filesystem:OSFFileSystem"'

#### Scenario: DVC entry point exists
- **WHEN** pyproject.toml is examined
- **THEN** it contains '[project.entry-points."dvc.fs"]' section with 'osf = "dvc_osf.filesystem:OSFFileSystem"'

#### Scenario: Entry points reference implemented class
- **WHEN** entry points are loaded
- **THEN** they reference the fully implemented OSFFileSystem class, not a placeholder

#### Scenario: fsspec can discover OSF filesystem
- **WHEN** fsspec registry is queried
- **THEN** 'osf' protocol is registered and points to OSFFileSystem

#### Scenario: DVC can discover OSF filesystem
- **WHEN** DVC loads filesystem plugins
- **THEN** 'osf' remote type is available and points to OSFFileSystem

### Requirement: Build system uses modern standards
The project SHALL use PEP 517/518 build system configuration.

#### Scenario: Build system is declared
- **WHEN** `pyproject.toml` is examined
- **THEN** it contains a `[build-system]` section

#### Scenario: Setuptools is specified as build backend
- **WHEN** build backend is checked
- **THEN** it is set to `"setuptools.build_meta"`

#### Scenario: Build dependencies are listed
- **WHEN** build requirements are checked
- **THEN** they include `"setuptools>=61.0"` and `"wheel"`

### Requirement: Package discovery is configured
The project SHALL configure setuptools to discover the dvc_osf package.

#### Scenario: Package discovery uses find directive
- **WHEN** `pyproject.toml` is examined
- **THEN** it contains `[tool.setuptools.packages.find]` configuration

#### Scenario: Only dvc_osf package is included
- **WHEN** package discovery configuration is checked
- **THEN** it includes the dvc_osf package and excludes tests

### Requirement: Dynamic version is configured
The project SHALL use dynamic versioning from `dvc_osf.__init__.py`.

#### Scenario: Version is marked as dynamic
- **WHEN** `pyproject.toml` is examined
- **THEN** `"version"` is listed in the `dynamic` field

#### Scenario: Version source is specified
- **WHEN** setuptools dynamic configuration is examined
- **THEN** version is configured to read from `"dvc_osf.__version__"`

### Requirement: Package is installable in editable mode
The project SHALL support editable/development installation.

#### Scenario: Editable install with uv works
- **WHEN** `uv pip install -e .` is executed
- **THEN** the package is installed in editable mode

#### Scenario: Editable install with poetry works
- **WHEN** `poetry install` is executed
- **THEN** the package is installed in editable mode

#### Scenario: Changes to source reflect immediately
- **WHEN** source code is modified in editable mode
- **THEN** changes are immediately available when importing the package

### Requirement: Core dependencies are declared
The pyproject.toml SHALL include all core dependencies required for OSF functionality.

#### Scenario: requests is in dependencies
- **WHEN** pyproject.toml [project.dependencies] is examined
- **THEN** it includes 'requests>=2.28.0'

#### Scenario: urllib3 is in dependencies
- **WHEN** pyproject.toml [project.dependencies] is examined
- **THEN** it includes 'urllib3>=1.26.0'

#### Scenario: dvc-objects is in dependencies
- **WHEN** pyproject.toml [project.dependencies] is examined
- **THEN** it includes 'dvc-objects>=5.0.0'

### Requirement: Optional dependencies are declared
The pyproject.toml SHALL include optional dependencies for enhanced functionality.

#### Scenario: Cache optional dependency group exists
- **WHEN** pyproject.toml [project.optional-dependencies] is examined
- **THEN** it includes a 'cache' group with 'requests-cache>=1.0.0'

### Requirement: Package can be built with new dependencies
The package SHALL build successfully with all new dependencies included.

#### Scenario: Build with uv succeeds
- **WHEN** 'uv build' command is executed
- **THEN** package builds without errors

#### Scenario: Build with poetry succeeds
- **WHEN** 'poetry build' command is executed
- **THEN** package builds without errors

#### Scenario: Built wheel includes all dependencies
- **WHEN** built wheel metadata is examined
- **THEN** it declares all core dependencies
