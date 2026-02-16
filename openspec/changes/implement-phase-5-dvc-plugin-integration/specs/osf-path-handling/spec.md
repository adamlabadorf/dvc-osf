## MODIFIED Requirements

### Requirement: _get_kwargs_from_urls parses osf:// URLs
The static method `_get_kwargs_from_urls` SHALL parse `osf://PROJECT_ID/PROVIDER[/PATH]` URLs and return a dict with `project_id`, `provider`, and optionally `path` keys.

#### Scenario: Parse full URL with path
- **WHEN** `_get_kwargs_from_urls("osf://abc123/osfstorage/data/files")` is called
- **THEN** the result is `{"project_id": "abc123", "provider": "osfstorage", "path": "data/files"}`

#### Scenario: Parse URL without path
- **WHEN** `_get_kwargs_from_urls("osf://abc123/osfstorage")` is called
- **THEN** the result is `{"project_id": "abc123", "provider": "osfstorage"}`

#### Scenario: Parse URL with trailing slash
- **WHEN** `_get_kwargs_from_urls("osf://abc123/osfstorage/")` is called
- **THEN** the result is `{"project_id": "abc123", "provider": "osfstorage"}`

### Requirement: unstrip_protocol reconstructs osf:// URLs
The `unstrip_protocol` method SHALL reconstruct a full `osf://` URL from an internal path, using the instance's `project_id` and `provider`.

#### Scenario: Reconstruct URL from internal path
- **WHEN** `unstrip_protocol("data/files/test.csv")` is called on an instance with `project_id="abc123"` and `provider="osfstorage"`
- **THEN** the result is `"osf://abc123/osfstorage/data/files/test.csv"`

#### Scenario: Reconstruct URL from root path
- **WHEN** `unstrip_protocol("")` is called on an instance with `project_id="abc123"` and `provider="osfstorage"`
- **THEN** the result is `"osf://abc123/osfstorage"`
