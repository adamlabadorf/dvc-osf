## MODIFIED Requirements

### Requirement: Token resolution priority chain
The authentication system SHALL resolve OSF tokens in the following priority order:
1. Explicit `token` parameter passed to the constructor (from DVC remote config)
2. `OSF_TOKEN` environment variable
3. `OSF_ACCESS_TOKEN` environment variable (alternate name)

The first non-empty value found SHALL be used. If no token is found, operations requiring authentication SHALL raise `OSFAuthenticationError`.

#### Scenario: Token from DVC config takes priority over env var
- **WHEN** `OSFFileSystem` is created with `token="config_token"` and `OSF_TOKEN=env_token` is set
- **THEN** `config_token` is used for API authentication

#### Scenario: Env var used when no explicit token
- **WHEN** `OSFFileSystem` is created without a `token` parameter and `OSF_TOKEN=env_token` is set
- **THEN** `env_token` is used for API authentication

#### Scenario: No token available
- **WHEN** no token is provided via constructor or environment
- **THEN** `OSFAuthenticationError` is raised with a message explaining how to set a token

### Requirement: _prepare_credentials integrates with DVC credential flow
The `_prepare_credentials` method SHALL extract the `token` and `endpoint_url` from the config dict and return them as kwargs suitable for initializing the OSF API client.

#### Scenario: Credentials prepared from config
- **WHEN** `_prepare_credentials(token="abc", endpoint_url="https://api.test.osf.io/v2")` is called
- **THEN** the returned dict includes `{"token": "abc", "endpoint_url": "https://api.test.osf.io/v2"}`
