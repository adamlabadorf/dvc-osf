# Integration Tests for dvc-osf

This directory contains integration tests that interact with a real OSF project.

## Setup

### 1. Create an OSF Test Project

1. Go to https://osf.io and log in
2. Create a new project (e.g., "dvc-osf-test")
3. Note your project ID (it's in the URL: `osf.io/PROJECT_ID`)

### 2. Generate a Personal Access Token (PAT)

1. Go to https://osf.io/settings/tokens/
2. Click "Create token"
3. Give it a descriptive name (e.g., "dvc-osf integration tests")
4. Select scopes: `osf.full_read` (or broader if testing writes later)
5. Save the token securely

### 3. Upload a Test File (Optional but Recommended)

1. In your OSF test project, go to Files → osfstorage
2. Upload a small text file named `test_file.txt` with some content (e.g., "Hello from OSF!")
3. This file will be used for read/download tests

### 4. Set Environment Variables

Export the following environment variables before running integration tests:

```bash
export OSF_TEST_TOKEN="your_personal_access_token_here"
export OSF_TEST_PROJECT_ID="your_project_id"  # e.g., "abc12"
export OSF_TEST_FILE="test_file.txt"  # optional, name of test file you uploaded
```

## Running Integration Tests

### Run all integration tests:

```bash
pytest tests/integration/ -v -m integration
```

### Run specific integration test:

```bash
pytest tests/integration/test_osf_read.py::TestOSFFileSystemIntegration::test_ls_root_directory -v
```

### Run all tests (unit + integration):

```bash
pytest tests/ -v
```

Note: Integration tests are automatically skipped if `OSF_TEST_TOKEN` and `OSF_TEST_PROJECT_ID` are not set.

## What's Tested

The integration tests verify:

1. **Initialization**: Creating an OSFFileSystem with real credentials
2. **exists()**: Checking if files and directories exist
3. **ls()**: Listing directory contents (with and without detail)
4. **info()**: Getting file metadata
5. **open()**: Opening and reading file contents
6. **get_file()**: Downloading files with checksum verification
7. **Error handling**: Invalid project IDs, missing files, bad tokens

## Test Structure

- `test_osf_read.py`: Main integration test file
  - `TestOSFFileSystemIntegration`: Tests with real OSF project
  - `TestOSFFileSystemEdgeCases`: Error handling and edge cases

## Cleanup

Integration tests only perform read operations, so no cleanup is needed. Your OSF project remains unchanged.

## Troubleshooting

### Tests are skipped
- Make sure `OSF_TEST_TOKEN` and `OSF_TEST_PROJECT_ID` environment variables are set
- Run: `echo $OSF_TEST_TOKEN` to verify

### Authentication errors
- Verify your token is valid at https://osf.io/settings/tokens/
- Make sure token has `osf.full_read` scope
- Token should not have leading/trailing whitespace

### File not found errors
- If testing file operations, make sure you uploaded `test_file.txt` to your project
- Set `OSF_TEST_FILE` environment variable to match your uploaded filename
- File should be in osfstorage (not a third-party add-on)

### API errors
- OSF API might be temporarily down - try again later
- Check OSF status at https://twitter.com/OSFramework
- Rate limiting: If you run tests frequently, you may hit rate limits

## Security Notes

**Never commit your OSF token to version control!**

- Use environment variables only
- Add `.env` to `.gitignore` if using dotenv
- Revoke and regenerate tokens if accidentally exposed
- Use a dedicated test account and test project for integration testing
