# Build Configuration - Delta Specification

## MODIFIED Requirements

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

## ADDED Requirements

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
