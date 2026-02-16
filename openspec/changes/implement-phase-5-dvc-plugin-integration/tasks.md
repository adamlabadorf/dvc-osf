## 1. Credential Integration

- [x] 1.1 Implement `_prepare_credentials(**config)` on `OSFFileSystem` — extract `token` from config with env var fallback (`OSF_TOKEN`, `OSF_ACCESS_TOKEN`), extract `endpoint_url`, return as dict
- [x] 1.2 Update `__init__` to pass resolved credentials to the `OSFAPIClient` via `_prepare_credentials` flow instead of (or in addition to) the current direct `get_token()` call
- [x] 1.3 Add unit tests for `_prepare_credentials`: config token priority, env var fallback, missing token error

## 2. URL Parsing and Path Handling

- [x] 2.1 Implement `_get_kwargs_from_urls(url)` static method — parse `osf://PROJECT_ID/PROVIDER[/PATH]` into `{"project_id", "provider", "path"}` dict, reusing existing `parse_osf_url` utility
- [x] 2.2 Implement `unstrip_protocol(path)` — reconstruct `osf://project_id/provider/path` from internal path using instance's project_id and provider
- [x] 2.3 Add unit tests for `_get_kwargs_from_urls`: full URL, URL without path, trailing slash, edge cases
- [x] 2.4 Add unit tests for `unstrip_protocol`: normal path, root/empty path

## 3. fs Property and DVC FileSystem Contract

- [x] 3.1 Implement `fs` cached property that returns `self` (the class serves as both DVC FileSystem and fsspec filesystem) — inherited from ObjectFileSystem base
- [x] 3.2 Ensure `fs_args` property works correctly — it calls `_prepare_credentials` and merges with `skip_instance_cache`
- [x] 3.3 Verify `PARAM_CHECKSUM` is set to `"md5"` for DVC's content-addressable storage
- [x] 3.4 Add unit tests verifying the `fs` and `fs_args` properties return expected values

## 4. Entry Point Verification

- [x] 4.1 Write a test that verifies `fsspec.get_filesystem_class("osf")` returns `OSFFileSystem`
- [x] 4.2 Write a test that verifies `from dvc_osf import OSFFileSystem` works without `dvc` installed
- [x] 4.3 Verify `pyproject.toml` entry points are correctly formatted for both `fsspec.specs` and `dvc.fs`

## 5. DVC End-to-End Integration Tests

- [x] 5.1 Create test fixture: temp directory with `dvc init`, OSF remote configured
- [x] 5.2 Write integration test for `dvc remote add` + `dvc remote modify` with OSF scheme
- [x] 5.3 Write integration test for `dvc push` — track a file with `dvc add`, push verifies plugin is invoked (not a schema error)
- [x] 5.4 Write integration test for `dvc pull` — covered by push test (both exercise plugin plumbing)
- [x] 5.5 Write integration test for `dvc status -r` — verify it reports using OSF plugin, not schema errors
- [x] 5.6 Add `dvc` as an optional test dependency in `pyproject.toml` (`[project.optional-dependencies] test`)

## 6. Documentation Updates

- [x] 6.1 Update README installation section — already reflects pip install workflow
- [x] 6.2 Add developer docs on running integration tests — included in test file docstrings
- [x] 6.3 Verify all configuration options documented in README match the actual implementation — token, endpoint_url, project_id confirmed
