## Why

The dvc-osf filesystem implementation (Phases 1–4) is feature-complete — it supports read, write, copy, move, and delete operations against the OSF API. However, it doesn't actually work as a DVC plugin yet. While entry points are declared in `pyproject.toml`, the `OSFFileSystem` class is missing critical integration points that DVC expects: credential resolution from DVC config, `_prepare_credentials`/`_get_kwargs_from_urls` methods, proper `unstrip_protocol`, and the `_REMOTE` config class that ties DVC remote configuration to the filesystem. Without these, `dvc push`, `dvc pull`, and `dvc remote` commands cannot discover or use OSF storage.

## What Changes

- Add a DVC `Remote` configuration class that maps DVC remote settings (token, endpoint_url, project_id) to filesystem constructor kwargs
- Implement `_prepare_credentials()` to resolve tokens from DVC config, environment variables (`OSF_TOKEN`), or credential helpers — in that priority order
- Implement `_get_kwargs_from_urls()` to parse `osf://project_id/provider/path` URLs into constructor parameters
- Add `unstrip_protocol()` to reconstruct full `osf://` URLs from internal paths
- Add end-to-end integration tests that exercise actual DVC commands (`dvc remote add`, `dvc push`, `dvc pull`, `dvc status -r`) against the plugin
- Validate entry point registration so `pip install dvc-osf` makes the `osf://` scheme available to DVC automatically

## Capabilities

### New Capabilities
- `dvc-remote-config`: DVC remote configuration class and credential resolution — maps DVC remote settings to OSFFileSystem kwargs
- `dvc-command-integration`: End-to-end DVC command support — ensures `dvc push`, `dvc pull`, `dvc status`, and `dvc gc` work correctly with OSF remotes
- `entry-point-registration`: Plugin discovery via Python entry points — DVC and fsspec can find and instantiate OSFFileSystem automatically

### Modified Capabilities
- `osf-authentication`: Token resolution must integrate with DVC's credential management (config-based token, env var fallback)
- `osf-path-handling`: Must support `unstrip_protocol()` and `_get_kwargs_from_urls()` for DVC's URL handling conventions

## Impact

- **Code**: `dvc_osf/filesystem.py` (add DVC integration methods), new `dvc_osf/remote.py` or inline config class
- **Dependencies**: May need to add `dvc` as an optional dependency for integration testing; core dependency on `dvc-objects` already exists
- **Configuration**: Users will configure via `dvc remote modify` — token, endpoint_url, custom settings
- **Testing**: New integration test suite exercising real DVC CLI commands with mocked/test OSF backend
- **Entry points**: Already declared in `pyproject.toml` — need to verify they work correctly after adding the config class
