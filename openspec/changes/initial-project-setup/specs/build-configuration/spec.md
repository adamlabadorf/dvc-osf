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

### Requirement: Entry points are registered
The project SHALL register filesystem entry points for both fsspec and DVC.

#### Scenario: fsspec entry point is registered
- **WHEN** `pyproject.toml` is examined
- **THEN** it contains an entry in `[project.entry-points."fsspec.specs"]` mapping `osf` to `dvc_osf.filesystem:OSFFileSystem`

#### Scenario: DVC entry point is registered
- **WHEN** `pyproject.toml` is examined
- **THEN** it contains an entry in `[project.entry-points."dvc.fs"]` mapping `osf` to `dvc_osf.filesystem:OSFFileSystem`

#### Scenario: Entry points enable plugin discovery
- **WHEN** the package is installed
- **THEN** DVC and fsspec can discover the OSF filesystem plugin

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
