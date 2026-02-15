# Integration Tests for dvc-osf

This directory contains integration tests that interact with a real OSF project to verify both read and write operations.

## Setup

### 1. Create an OSF Test Project

1. Go to https://osf.io and log in
2. Create a new project (e.g., "dvc-osf-test")
3. Note your project ID (it's in the URL: `osf.io/PROJECT_ID`)

### 2. Generate a Personal Access Token (PAT)

1. Go to https://osf.io/settings/tokens/
2. Click "Create token"
3. Give it a descriptive name (e.g., "dvc-osf integration tests")
4. **IMPORTANT**: Select BOTH scopes:
   - `osf.full_read` - Required for download/read tests
   - `osf.full_write` - Required for upload/write tests
5. Save the token securely (you won't see it again!)

### 3. Set Environment Variables

Export the following environment variables before running integration tests:

```bash
export OSF_TEST_TOKEN="your_personal_access_token_here"
export OSF_TEST_PROJECT_ID="your_project_id"  # e.g., "abc12"
export OSF_TEST_PROVIDER="osfstorage"  # Optional, defaults to osfstorage
export OSF_TEST_FILE="test_file.txt"  # Optional, for specific read tests
```

**Alternative**: Use the encrypted credentials script (if you have GPG key):

```bash
. configure-test-project-env.sh
```

## Running Integration Tests

### Run all integration tests:

```bash
pytest tests/integration/ -v -m integration
```

### Run specific test files:

```bash
# Read operations only
pytest tests/integration/test_osf_read.py -v

# Write operations only
pytest tests/integration/test_osf_write.py -v

# Roundtrip tests (upload and download)
pytest tests/integration/test_osf_roundtrip.py -v
```

### Run specific test:

```bash
pytest tests/integration/test_osf_write.py::TestOSFWriteOperations::test_put_file_small -v
```

### Run with coverage:

```bash
pytest tests/integration/ -v -m integration --cov=dvc_osf --cov-report=html
```

Note: Integration tests are automatically skipped if `OSF_TEST_TOKEN` and `OSF_TEST_PROJECT_ID` are not set.

## What's Tested

### test_osf_read.py (Phase 1 - Read Operations)

1. **Initialization**: Creating an OSFFileSystem with real credentials
2. **exists()**: Checking if files and directories exist
3. **ls()**: Listing directory contents (with and without detail)
4. **info()**: Getting file metadata
5. **open()**: Opening and reading file contents
6. **get_file()**: Downloading files with checksum verification
7. **Error handling**: Invalid project IDs, missing files, bad tokens

### test_osf_write.py (Phase 3 - Write Operations)

1. **put_file()**: Uploading local files
   - Small files (< 5MB, single request)
   - Large files (> 5MB, streaming upload)
2. **put()**: Uploading file-like objects
3. **rm()**: Deleting files
4. **mkdir()/rmdir()**: Directory operations (no-ops per OSF design)
5. **open(mode='wb')**: Write mode file handles
6. **Progress callbacks**: Tracking upload progress
7. **Checksum verification**: MD5 integrity checks
8. **File versioning**: Overwrite behavior (automatic versioning)

### test_osf_roundtrip.py (Phase 3 - End-to-End)

1. **Upload → Download → Verify**: Full roundtrip cycle
2. **Small text files**: Basic text content preservation
3. **Large binary files**: 6MB+ files with chunked transfer
4. **Special characters**: UTF-8, emojis, international characters
5. **Empty files**: Zero-byte file handling
6. **Binary data**: All byte values (0-255) preservation
7. **Multiple cycles**: Repeated upload/download maintains integrity

## Test Structure

- `test_osf_read.py`: Read-only integration tests (Phase 1)
  - `TestOSFFileSystemIntegration`: Tests with real OSF project
  - `TestOSFFileSystemEdgeCases`: Error handling and edge cases

- `test_osf_write.py`: Write operation integration tests (Phase 3)
  - `TestOSFWriteOperations`: Upload, delete, and write mode tests

- `test_osf_roundtrip.py`: End-to-end roundtrip tests (Phase 3)
  - `TestOSFRoundtrip`: Upload/download cycle verification

## Cleanup

Write operation tests attempt to clean up uploaded files after each test. However:
- If tests fail mid-execution, some test files may remain on OSF
- Test files are named with predictable patterns (e.g., `test_upload_small_*.txt`)
- You can manually delete leftover test files from the OSF web interface
- Regular cleanup helps avoid storage quota issues

## Troubleshooting

### Tests are skipped
- Make sure `OSF_TEST_TOKEN` and `OSF_TEST_PROJECT_ID` environment variables are set
- Run: `echo $OSF_TEST_TOKEN` to verify
- Ensure variables are exported in the current shell session

### Authentication errors
- Verify your token is valid at https://osf.io/settings/tokens/
- Make sure token has BOTH `osf.full_read` AND `osf.full_write` scopes
- Token should not have leading/trailing whitespace
- Try generating a new token if issues persist

### Permission errors (403 Forbidden)
- Verify token has `osf.full_write` scope for upload tests
- Check that you have write permissions to the test project
- Ensure the project isn't read-only

### Quota exceeded errors (413)
- Check your OSF project storage usage at project settings
- Delete unnecessary files from OSF to free up space
- Contact OSF support for quota increases if needed

### File not found errors
- For read tests, make sure you uploaded `test_file.txt` to your project
- Set `OSF_TEST_FILE` environment variable to match your uploaded filename
- File should be in osfstorage (not a third-party add-on storage provider)

### Rate limiting (429 Too Many Requests)
- OSF API may temporarily rate limit excessive requests
- Wait a few minutes for rate limit to reset
- The plugin automatically retries with exponential backoff
- Consider running fewer tests at once during development

### API errors / Network issues
- OSF API might be temporarily down - try again later
- Check OSF status at https://twitter.com/OSFramework
- Verify your internet connection
- Try increasing timeout: `export OSF_TIMEOUT=120`

## Security Notes

**Never commit your OSF token to version control!**

- Use environment variables only
- Add `.env` to `.gitignore` if using dotenv
- Revoke and regenerate tokens if accidentally exposed
- Use a dedicated test account and test project for integration testing
- Integration tests clean up after themselves, but don't store sensitive data in test projects

## Performance Notes

- Integration tests make real API calls and can be slow
- Large file tests (6MB+) may take 1-2 minutes depending on your connection
- Roundtrip tests are comprehensive and may take several minutes
- Consider running integration tests separately from unit tests
- Use `-x` flag to stop on first failure during debugging

## CI/CD Integration

For continuous integration pipelines:

1. **Store credentials as encrypted secrets** in your CI system
2. **Run integration tests in a separate stage** after unit tests
3. **Allow integration test failures** (optional) to not block builds on OSF downtime
4. **Use caching** for dependencies to speed up test execution
5. **Limit frequency** - don't run on every commit (use nightly builds or manual triggers)

Example GitHub Actions:

```yaml
- name: Run Integration Tests
  env:
    OSF_TEST_TOKEN: ${{ secrets.OSF_TEST_TOKEN }}
    OSF_TEST_PROJECT_ID: ${{ secrets.OSF_TEST_PROJECT_ID }}
  run: |
    pytest tests/integration/ -v -m integration
  continue-on-error: true  # Optional: don't fail build on OSF issues
```
