# Changelog

All notable changes to dvc-osf are documented here.

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
