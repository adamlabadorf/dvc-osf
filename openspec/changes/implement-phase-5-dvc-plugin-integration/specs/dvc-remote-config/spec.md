## ADDED Requirements

### Requirement: DVC remote configuration parsing
The `OSFFileSystem` class SHALL accept DVC remote configuration parameters (`token`, `endpoint_url`, `project_id`, `provider`) and use them to configure the underlying OSF API client. Configuration SHALL be passed through the standard `**kwargs` mechanism from `FileSystem.__init__`.

#### Scenario: Remote configured with token via dvc config
- **WHEN** a user runs `dvc remote modify myosf token MY_TOKEN`
- **THEN** the `OSFFileSystem` receives `token="MY_TOKEN"` in its config kwargs and uses it for API authentication

#### Scenario: Remote configured with custom endpoint
- **WHEN** a user runs `dvc remote modify myosf endpoint_url https://api.test.osf.io/v2`
- **THEN** the `OSFFileSystem` uses that endpoint for all API requests instead of the default

### Requirement: fs cached property returns fsspec-compatible filesystem
The `OSFFileSystem` SHALL implement the `fs` cached property that returns a properly configured `AbstractFileSystem` instance (itself, since it extends `ObjectFileSystem`). The `fs_args` property SHALL be populated via `_prepare_credentials` with the resolved authentication and configuration.

#### Scenario: fs property initializes with credentials
- **WHEN** `OSFFileSystem` is instantiated with a token in config
- **THEN** `fs_args` includes the resolved token and any endpoint configuration
