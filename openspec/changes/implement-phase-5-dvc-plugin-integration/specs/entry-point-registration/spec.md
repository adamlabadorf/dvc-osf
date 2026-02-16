## ADDED Requirements

### Requirement: Plugin discoverable via fsspec entry point
The package SHALL register an `fsspec.specs` entry point so that `fsspec.filesystem("osf")` resolves to `OSFFileSystem` after `pip install dvc-osf`.

#### Scenario: fsspec discovers the osf protocol
- **WHEN** `dvc-osf` is installed and `fsspec.filesystem("osf", token="...")` is called
- **THEN** an `OSFFileSystem` instance is returned

### Requirement: Plugin discoverable via DVC entry point
The package SHALL register a `dvc.fs` entry point so that DVC recognizes `osf://` URLs as valid remote schemes.

#### Scenario: DVC recognizes osf:// remote URL
- **WHEN** a user runs `dvc remote add myosf osf://abc123/osfstorage`
- **THEN** DVC accepts the remote configuration without errors

### Requirement: No additional DVC dependencies for core plugin
The plugin SHALL NOT require `dvc` as a runtime dependency. The `dvc-objects` package provides the filesystem base class. DVC itself is only needed for end-to-end testing.

#### Scenario: Import without DVC installed
- **WHEN** `dvc-osf` is installed in an environment without `dvc`
- **THEN** `from dvc_osf import OSFFileSystem` succeeds without import errors
