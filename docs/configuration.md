# Configuration Guide

This guide covers all configuration options and usage details for dvc-osf.

## OSF URL Format

The dvc-osf plugin uses a URL format to specify OSF resources:

```
osf://PROJECT_ID/PROVIDER/PATH
```

### Components

- **PROJECT_ID** (required): Your OSF project identifier
  - Found in the OSF project URL: `https://osf.io/PROJECT_ID`
  - Example: `abc123`, `3eugf`
  - Must be at least 5 alphanumeric characters

- **PROVIDER** (required): Storage provider name
  - Use `osfstorage` for OSF's native storage
  - Other providers (Dropbox, Google Drive, etc.) not yet supported in Phase 1

- **PATH** (optional): Directory path within the storage provider
  - Relative path to a subdirectory
  - Example: `data/training`, `experiments/2024`
  - Omit for root directory

### Examples

```bash
# Root of osfstorage provider
osf://abc123/osfstorage

# Specific directory in osfstorage
osf://abc123/osfstorage/data

# Nested directory path
osf://abc123/osfstorage/experiments/2024/model-v1
```

## Authentication Setup

### Method 1: DVC Remote Configuration (Recommended)

Store your OSF token in DVC's remote configuration:

```bash
# Add remote
dvc remote add -d myosf osf://PROJECT_ID/osfstorage

# Store token in DVC config
dvc remote modify myosf token YOUR_TOKEN_HERE
```

This stores the token in `.dvc/config` (for team) or `.dvc/config.local` (for personal use).

**For team repos:** Use `.dvc/config.local` to avoid committing tokens to git:

```bash
dvc remote modify --local myosf token YOUR_TOKEN_HERE
```

### Method 2: Environment Variable

Set the `OSF_TOKEN` environment variable:

```bash
# Linux/macOS
export OSF_TOKEN="your_token_here"

# Windows (Command Prompt)
set OSF_TOKEN=your_token_here

# Windows (PowerShell)
$env:OSF_TOKEN="your_token_here"
```

Add to your shell profile for persistence:

```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export OSF_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

### Method 3: Direct Parameter (For Scripts)

Pass the token directly when initializing the filesystem:

```python
from dvc_osf.filesystem import OSFFileSystem

fs = OSFFileSystem("osf://abc123/osfstorage", token="your_token_here")
```

### Token Priority Order

When multiple sources provide a token, the plugin uses this priority:

1. **Explicit parameter** (highest priority - for programmatic use)
2. **DVC config** (medium priority - team/project configuration)
3. **Environment variable** (lowest priority - personal/system-wide)

## Creating an OSF Personal Access Token

1. Log in to [OSF](https://osf.io)
2. Go to **Settings** → **Personal Access Tokens**
3. Click **"Create token"**
4. Configure the token:
   - **Name**: Give it a descriptive name (e.g., "dvc-osf-project-alpha")
   - **Scopes**: Select `osf.full_read` (write operations require additional scopes in Phase 2)
5. Click **"Create token"** and copy the token immediately
6. Store the token securely (you won't be able to see it again)

### Token Security Best Practices

- ⚠️ **Never commit tokens to git**
- ⚠️ **Use `.dvc/config.local` for personal tokens**
- ⚠️ **Rotate tokens regularly**
- ⚠️ **Use minimal scopes required** (`osf.full_read` for Phase 1)
- ⚠️ **Revoke unused tokens** at https://osf.io/settings/tokens/

## Supported Operations

### Phase 1 (Current) - Read-Only Operations

| Operation | DVC Command | Status | Description |
|-----------|-------------|--------|-------------|
| **exists()** | `dvc status` | ✅ Supported | Check if file/directory exists |
| **ls()** | `dvc list` | ✅ Supported | List directory contents |
| **info()** | - | ✅ Supported | Get file metadata (size, checksum, modified date) |
| **open()** | `dvc get` | ✅ Supported | Read file contents with streaming |
| **get_file()** | `dvc pull` | ✅ Supported | Download file with checksum verification |

### Phase 2 (Planned) - Write Operations

| Operation | DVC Command | Status | Description |
|-----------|-------------|--------|-------------|
| **put()** | - | ❌ Not yet | Upload file data |
| **put_file()** | `dvc push` | ❌ Not yet | Upload file from local path |
| **mkdir()** | - | ❌ Not yet | Create directory |
| **rm()** | - | ❌ Not yet | Delete file or directory |
| **cp()** | - | ❌ Not yet | Copy within OSF storage |
| **mv()** | - | ❌ Not yet | Move/rename within OSF storage |

## Current Limitations

### Read-Only Mode

Phase 1 is intentionally read-only to validate the architecture before adding write complexity:

- ✅ **Download data from OSF** with `dvc pull`
- ✅ **Query and list files** on OSF
- ✅ **Verify checksums** during downloads
- ❌ **Cannot upload** with `dvc push` (upload via OSF web interface instead)
- ❌ **Cannot modify files** on OSF through the plugin

### Storage Provider Support

- ✅ **osfstorage** - OSF's native storage (fully supported)
- ❌ **Add-on providers** - Dropbox, Google Drive, Box, etc. (not yet supported)

### File Operations

- ✅ **Streaming downloads** - Large files handled efficiently
- ✅ **Checksum verification** - MD5 hashes verified automatically
- ❌ **Resume downloads** - Interrupted downloads restart from beginning
- ❌ **Parallel downloads** - Files downloaded sequentially

## Environment Variables

Customize the OSF client behavior with these environment variables:

### API Configuration

```bash
# OSF API base URL (default: https://api.osf.io/v2)
export OSF_API_URL=https://api.osf.io/v2
```

Use for testing against staging environments or custom OSF instances.

### Timeout and Retry Settings

```bash
# Request timeout in seconds (default: 30)
export OSF_TIMEOUT=60

# Maximum retry attempts for transient failures (default: 3)
export OSF_MAX_RETRIES=5

# Exponential backoff multiplier (default: 2.0)
# Delay = RETRY_BACKOFF ^ attempt_number
export OSF_RETRY_BACKOFF=3.0
```

### Performance Tuning

```bash
# Download chunk size in bytes (default: 8192)
# Larger chunks = fewer API calls, more memory usage
export OSF_CHUNK_SIZE=16384

# HTTP connection pool size (default: 10)
# More connections = more concurrent requests
export OSF_POOL_SIZE=20
```

## Error Handling

The plugin includes comprehensive error handling with automatic retries:

### Automatic Retries

The following errors trigger automatic retry with exponential backoff:

- **Network errors** - Connection failures, timeouts
- **Server errors** - 500, 502, 503, 504 status codes
- **Rate limiting** - 429 status code (uses `Retry-After` header if present)

### Non-Retryable Errors

These errors fail immediately without retry:

- **Authentication errors** (401) - Invalid or expired token
- **Permission errors** (403) - Insufficient permissions
- **Not found errors** (404) - File or project doesn't exist
- **Client errors** (400) - Invalid request format

### Custom Exception Types

```python
from dvc_osf.exceptions import (
    OSFAuthenticationError,  # 401 - invalid token
    OSFPermissionError,       # 403 - insufficient permissions
    OSFNotFoundError,         # 404 - resource not found
    OSFRateLimitError,        # 429 - rate limit exceeded
    OSFConnectionError,       # Network/connection issues
    OSFIntegrityError,        # Checksum mismatch
    OSFAPIError,              # General API errors
)
```

## Troubleshooting

### Common Issues

#### 1. "Authentication failed. Check your OSF token."

**Cause:** Invalid, expired, or missing token

**Solutions:**
- Verify token at https://osf.io/settings/tokens/
- Check token has `osf.full_read` scope
- Ensure no whitespace in token string
- Try regenerating the token

#### 2. "Resource not found on OSF"

**Cause:** Invalid project ID or file path

**Solutions:**
- Verify project ID from OSF project URL
- Ensure you have read access to the project
- Check file exists in `osfstorage` (not add-on storage)
- Verify path capitalization and spelling

#### 3. "Permission denied for OSF operation"

**Cause:** Insufficient permissions for the project

**Solutions:**
- Verify you're a contributor on the OSF project
- Check project isn't private (if using public access)
- Ensure token has appropriate scopes

#### 4. "Failed to connect to OSF"

**Cause:** Network connectivity issues

**Solutions:**
- Check internet connection
- Verify OSF isn't down: https://twitter.com/OSFramework
- Check firewall/proxy settings
- Try increasing timeout: `export OSF_TIMEOUT=120`

#### 5. "Checksum mismatch"

**Cause:** File corruption during download

**Solutions:**
- Retry the download (plugin will re-download)
- Check network stability
- Report persistent issues to OSF support

### Getting Help

If you encounter issues not covered here:

1. Check [GitHub Issues](https://github.com/YOUR_USERNAME/dvc-osf/issues)
2. Search [DVC Community Forum](https://discuss.dvc.org/)
3. Open a new issue with:
   - Error message (with tokens redacted)
   - OSF project ID (if public)
   - Python and dvc-osf versions
   - Minimal reproduction steps

## Advanced Usage

### Programmatic Access

Use the filesystem directly in Python:

```python
from dvc_osf.filesystem import OSFFileSystem

# Initialize filesystem
fs = OSFFileSystem("osf://abc123/osfstorage", token="your_token")

# Check if file exists
exists = fs.exists("data/file.csv")

# List directory
files = fs.ls("data", detail=True)

# Get file metadata
info = fs.info("data/file.csv")
print(f"Size: {info['size']} bytes")
print(f"MD5: {info['checksum']}")

# Read file
with fs.open("data/file.csv", "rb") as f:
    content = f.read()

# Download file
fs.get_file("data/remote.csv", "local.csv")
```

### Integration with fsspec

The OSF filesystem is registered with fsspec:

```python
import fsspec

# Access via fsspec
fs = fsspec.filesystem("osf", token="your_token")
fs.ls("osf://abc123/osfstorage/")
```

## See Also

- [OSF API Documentation](https://developer.osf.io/)
- [DVC User Guide](https://dvc.org/doc/user-guide)
- [DVC Remote Storage](https://dvc.org/doc/command-reference/remote)
