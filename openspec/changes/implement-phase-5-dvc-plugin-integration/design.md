## Context

dvc-osf has a fully working `OSFFileSystem` that can read, write, copy, move, and delete files on OSF. However, it doesn't integrate with DVC's plugin discovery and configuration system. The `FileSystem` base class from `dvc-objects` defines a specific contract:

- `_prepare_credentials(**config)` → returns kwargs for the underlying fsspec filesystem
- `_get_kwargs_from_urls(url)` → static method that parses protocol URLs into constructor kwargs
- `unstrip_protocol(path)` → reconstructs full `protocol://...` URLs from stripped paths
- `fs` cached property → returns the actual fsspec filesystem instance
- Entry points in `pyproject.toml` → how DVC/fsspec discovers the plugin

The existing code already declares entry points and has `protocol = "osf"` and `_strip_protocol`, but is missing `_prepare_credentials`, `_get_kwargs_from_urls`, `unstrip_protocol`, and the `fs` property integration.

## Goals / Non-Goals

**Goals:**
- Make `dvc push` / `dvc pull` / `dvc status -r` work with `osf://` remotes
- Integrate token resolution with DVC's `dvc remote modify` config flow
- Ensure the plugin is auto-discovered when installed via pip
- Add integration tests that exercise real DVC commands

**Non-Goals:**
- OAuth or interactive auth flows (token-only for now)
- Support for OSF add-on storage providers
- Parallel transfers (Phase 6)
- Custom DVC CLI commands or extensions

## Decisions

### 1. Inline integration vs. separate Remote class

**Decision:** Add methods directly to `OSFFileSystem` rather than creating a separate `Remote` class.

**Rationale:** Modern DVC plugins (post dvc-objects 5.x) use the `FileSystem` class as the single integration point. DVC discovers the filesystem via entry points and calls its methods directly. A separate `Remote` class is the old pattern. The base `FileSystem` class already defines the hooks we need (`_prepare_credentials`, `_get_kwargs_from_urls`). Adding them to `OSFFileSystem` is simpler and follows the current convention.

**Alternative considered:** Separate `dvc_osf/remote.py` with a `Remote` class wrapping the filesystem — rejected as unnecessary indirection for the current DVC architecture.

### 2. Token resolution in _prepare_credentials

**Decision:** `_prepare_credentials` checks `config.get("token")` first, then `os.environ.get("OSF_TOKEN")`, then `os.environ.get("OSF_ACCESS_TOKEN")`.

**Rationale:** This matches the existing `auth.get_token()` function's behavior but integrates it into DVC's credential flow. DVC passes `dvc remote modify` values through config kwargs, so checking config first ensures DVC config takes priority. The env var fallback is standard for CI/CD environments.

### 3. _get_kwargs_from_urls parsing strategy

**Decision:** Parse `osf://PROJECT_ID/PROVIDER[/PATH]` by splitting on `/` after stripping the protocol. First segment = project_id, second = provider, remainder = path.

**Rationale:** This matches the existing `parse_osf_url()` utility and the URL format documented in README. We reuse the existing parser rather than introducing a new one.

### 4. fs property implementation

**Decision:** The `OSFFileSystem` will serve as both the DVC `FileSystem` wrapper and the underlying fsspec filesystem. The `fs` cached property will return `self` since the class already implements all required fsspec methods.

**Rationale:** Unlike S3 (where DVC's FileSystem wraps `s3fs.S3FileSystem`), our class directly implements all operations. There's no separate fsspec filesystem to wrap. This is valid — the base class allows this pattern.

### 5. Integration test approach

**Decision:** Use pytest fixtures that create a temporary DVC repo, configure an OSF remote with a mocked/test API, and run actual DVC CLI commands via `subprocess`.

**Rationale:** End-to-end tests with real DVC commands catch integration issues that unit tests miss (entry point discovery, config parsing, command dispatching). Mocking the OSF API layer keeps tests fast and avoids needing real OSF credentials in CI.

## Risks / Trade-offs

- **[dvc-objects API stability]** The `FileSystem` base class API may change between dvc-objects versions. → Pin `dvc-objects>=5.0.0,<6.0.0` and test against multiple versions in CI.
- **[Content-addressable path layout]** DVC expects files stored at `files/md5/<2-char>/<rest>`. If our filesystem doesn't handle this path structure correctly (especially directory auto-creation), push/pull will fail silently. → Add specific tests for the hash path layout.
- **[Entry point caching]** pip/fsspec cache entry points. During development, changes to entry points may not take effect until reinstall. → Document `pip install -e .` requirement for development.
- **[Self-referential fs property]** Returning `self` from the `fs` property is unconventional. If the base class calls `self.fs.some_method()` expecting a different object, we could get infinite recursion. → Verify the base class call patterns; the existing code already works this way since it extends `ObjectFileSystem`.

## Open Questions

- Should we support `dvc remote modify myosf project_id abc123` as an alternative to embedding the project ID in the URL? (Leaning yes for flexibility, but not required for MVP)
- Does DVC's `gc` command need special handling, or does it work via the standard `rm`/`exists` methods? (Likely works out of the box — verify in integration tests)
