# Changelog

All notable changes to dvc-osf are documented here.

## [1.0.4] - 2026-03-09

### Fixed
- Checksum mismatch after upload (got `d41d8cd98f00b204e9800998ecf8427e`, the
  empty-file MD5): `upload_file()` was passing a generator from `_stream_upload`
  through `_request()`'s retry loop. On retry the generator was already exhausted,
  so an empty body was sent to WaterButler. Fix: bypass `_request()` for uploads
  and rewind the file object between attempts so every attempt sends the full body.

## [1.0.3] - 2026-03-07 / 2026-03-08

### Fixed
- `_get_kwargs_from_urls()` no longer returns `path` in its result dict.
  DVC calls `Remote(name, fs_path, fs, **config)` with `fs_path` extracted
  separately via `_strip_protocol()`; having `path` in `**config` as well
  caused `TypeError: Remote.__init__() got multiple values for argument 'path'`
- Updated unit test assertions for `_get_kwargs_from_urls` to reflect the
  above behaviour change

### Changed
- Added pre-push hook that runs unit tests (157 tests) before every `git push`
  Integration tests (requiring OSF credentials) remain CI-only

## [1.0.2] - 2026-03-02

### Fixed
- Resolved all mypy type errors in source package
- Added mypy to pre-commit hooks (scoped to `dvc_osf/`, using `dvc-objects` in isolated env)
- Set `warn_unused_ignores = false` to handle cross-environment differences in dvc-objects stub availability
- Added `.flake8` config to align line length with black (88 chars)
- Fixed `OSFClient` → `OSFAPIClient` rename in test conftest

## [1.0.1] - 2026-03-02

### Fixed
- CI: `uv sync --extra test` so pytest is actually installed in GitHub Actions
- CI: use `astral-sh/setup-uv@v5` action; drop Python 3.8, add 3.13 to matrix
- Tests: skip DVC-fork-dependent e2e tests when standard DVC is installed
- Tests: fix `tomllib` import for Python 3.9/3.10 (stdlib only in 3.11+)
- Tests: update `path_to_api_url` assertions to expect trailing slash

## [1.0.0] - 2026-03-02

First stable release. `dvc push`, `dvc pull`, and `dvc status` work
against OSF remotes for projects of any size.

### Features
- Full `dvc push` / `dvc pull` / `dvc status` support against OSF storage
- Content-addressed storage layout (`files/md5/ab/hash`) with automatic
  intermediate directory creation (OSF does not auto-create nested paths)
- ID-based directory navigation: walks OSF's internal file-ID tree instead
  of constructing path URLs (nested path URLs return 404 on OSF's API)
- Streaming uploads and downloads for memory efficiency
- MD5 checksum verification after every upload
- Pagination support throughout (large directories with >10 entries)
- `REMOTE_CONFIG` schema discovery for DVC's plugin entry-point system
  (requires `adamlabadorf/dvc` fork until upstream PR #10994 merges)
- `dvc remote add`, `dvc remote modify`, `dvc version` all show `osf`

### Installation

```bash
# Install dvc-osf
pip install git+https://github.com/adamlabadorf/dvc-osf.git

# Configure a remote
dvc remote add myremote osf://YOUR_PROJECT_ID/osfstorage
dvc remote modify myremote token YOUR_OSF_PAT
dvc remote default myremote
```

### Known limitations
- Requires the `adamlabadorf/dvc` fork (`feature/plugin-schema-discovery`
  branch) for `osf` to appear in `dvc remote add` tab-completion and
  schema validation. Standard DVC works for push/pull without the fork.
- No true multi-part chunked upload (OSF/WaterButler does not support it);
  large files are streamed in a single PUT request.

### Bug fixes (relative to 0.x development)
- Fixed HTTP 500 from OSF when pushing to nested content-addressed paths
- Fixed `IndexError: tuple index out of range` during `dvc push` status check
  (`find()` infinite recursion with string prefix parameter)
- Fixed `AttributeError: 'OSFFileSystem' object has no attribute 'async_impl'`
  when pushing many files in parallel
- Fixed `AttributeError: property 'fs' has no setter` during fsspec init
- Fixed pagination in `rm()`, `_get_upload_url()`, `ls()`, `info()`, `open()`
- Fixed `_strip_protocol()` to handle list inputs (DVC passes lists during push)
- Fixed `exists()` to return `list[bool]` when called with a list of paths
