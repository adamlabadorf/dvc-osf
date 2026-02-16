# dvc-osf

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)

Open Science Framework (OSF) storage plugin for Data Version Control (DVC).

## About

**dvc-osf** is a DVC plugin that enables seamless integration between [Data Version Control (DVC)](https://dvc.org) and the [Open Science Framework (OSF)](https://osf.io). This plugin allows data scientists and researchers to version control their datasets on OSF storage while leveraging DVC's powerful data management capabilities.

### What is OSF?

The [Open Science Framework](https://osf.io) is a free, open-source platform for organizing and sharing research activities, documentation, code, and data in a transparent and FAIR (Findable, Accessible, Interoperable, Reusable) way. OSF provides:

- Free storage for research data and materials
- Project organization and collaboration tools
- Version control and provenance tracking
- DOI minting for persistent citations
- Integration with other research tools and platforms
- Support for open and transparent science practices

### What is DVC?

[Data Version Control (DVC)](https://dvc.org) brings software engineering best practices to data science and machine learning projects. DVC allows you to:

- Version control large datasets efficiently
- Track experiments and model performance
- Share and reproduce ML pipelines
- Collaborate on data-driven projects
- Store data on various remote storage backends

### Why dvc-osf?

This plugin bridges the gap between DVC's powerful data versioning capabilities and OSF's commitment to open science:

- **Open Science Compliance**: Store your versioned data on a platform designed for open, transparent research
- **FAIR Data Principles**: Leverage OSF's infrastructure to make your data Findable, Accessible, Interoperable, and Reusable
- **Free Storage**: Utilize OSF's free storage for academic and research projects
- **Collaboration**: Share data with collaborators through OSF's project management features
- **Reproducibility**: Combine DVC's reproducibility features with OSF's persistent storage and citation capabilities
- **Integration**: Seamlessly integrate with the broader OSF ecosystem of research tools

## Features

- **Full DVC remote storage support for OSF** (Phase 4 - current implementation)
- ✅ **Read Operations**:
  - Download versioned data from OSF storage
  - List and query files on OSF storage
  - Streaming downloads for large files with checksum verification
- ✅ **Write Operations**:
  - Upload files to OSF storage (`dvc push`)
  - Delete files from OSF storage
  - Automatic file versioning on overwrites
  - Streaming uploads for large files with progress tracking
  - MD5 checksum verification for data integrity
- ✅ **File Manipulation Operations** (Phase 4 - NEW):
  - Copy files and directories within OSF storage
  - Move/rename files and directories
  - Batch copy, move, and delete operations
  - Checksum verification during copy operations
  - Progress callbacks for batch operations
- Authentication via OSF personal access tokens
- Support for OSF projects and components
- Automatic retry logic with exponential backoff for network resilience
- Compatible with DVC's caching features

### Current Limitations

- ❌ OSF add-on storage providers (osfstorage only)
- ❌ Cross-project or cross-provider file operations
- ❌ Append operations (not supported by OSF API)
- ⚠️ Directory operations limited by OSF API (nested directory creation not supported)

## Installation

You can install **dvc-osf** via pip:

```bash
pip install dvc-osf
```

Or install from source:

```bash
git clone https://github.com/YOUR_USERNAME/dvc-osf.git
cd dvc-osf
pip install -e .
```

## Requirements

- Python 3.8 or higher
- DVC 2.0 or higher
- An OSF account and personal access token

## Usage

### 1. Create an OSF Personal Access Token

1. Log in to [OSF](https://osf.io)
2. Go to Settings → Personal Access Tokens
3. Create a new token with appropriate scopes:
   - `osf.full_read` - Required for downloading data
   - `osf.full_write` - Required for uploading data
4. Save the token securely

### 2. Configure DVC Remote

Add an OSF remote to your DVC project:

```bash
# Configure OSF remote with project ID
dvc remote add -d myosf osf://PROJECT_ID/osfstorage

# Set your OSF access token (option 1: DVC config)
dvc remote modify myosf token YOUR_OSF_TOKEN

# Or use environment variable (option 2)
export OSF_TOKEN=YOUR_OSF_TOKEN
```

**URL Format:** `osf://PROJECT_ID/PROVIDER/PATH`

Where:
- `PROJECT_ID` is your OSF project identifier (found in the OSF project URL, e.g., "abc123")
- `PROVIDER` is the storage provider (use `osfstorage` for OSF's native storage)
- `PATH` (optional) is a subdirectory within the storage

**Examples:**
```bash
# Root of osfstorage
osf://abc123/osfstorage

# Specific directory
osf://abc123/osfstorage/data

# With environment variable for token
export OSF_TOKEN="your_token_here"
dvc remote add -d myosf osf://abc123/osfstorage
```

### 3. Use DVC as Normal

Once configured, use DVC commands for **both reading and writing data to/from OSF**:

```bash
# Track data with DVC
dvc add data/train.csv

# Push data to OSF
dvc push

# Pull data from OSF
dvc pull

# Check remote status
dvc status -r myosf

# List remote files (if DVC supports it)
dvc list osf://abc123/osfstorage
```

### Example Workflow (Full Read/Write Support)

```bash
# Initialize DVC in your project
dvc init

# Add OSF remote (ensure token has write permissions)
dvc remote add -d osf-storage osf://abc123/osfstorage
dvc remote modify osf-storage token $OSF_TOKEN

# Track your data with DVC
dvc add data/train.csv data/model.pkl

# Push data to OSF
dvc push

# Commit the .dvc files to git
git add data/train.csv.dvc data/model.pkl.dvc .gitignore
git commit -m "Track training data and model on OSF"
git push

# On another machine, pull the data
git pull
dvc pull
```

### Upload Progress Tracking

For large file uploads, you can track progress programmatically:

```python
from dvc_osf.filesystem import OSFFileSystem

fs = OSFFileSystem(token="your_token")

def progress_callback(bytes_uploaded, total_bytes):
    percent = (bytes_uploaded / total_bytes) * 100
    print(f"Upload progress: {percent:.1f}%")

# Upload with progress tracking
fs.put_file(
    "local_file.dat", 
    "osf://abc123/osfstorage/remote_file.dat",
    callback=progress_callback
)
```

### File Manipulation Operations (Phase 4 - NEW)

The plugin now supports copy, move, and delete operations directly on OSF storage:

#### Copy Files

```python
from dvc_osf.filesystem import OSFFileSystem

fs = OSFFileSystem("osf://abc123/osfstorage", token="your_token")

# Copy a single file
fs.cp("source_file.csv", "backup/source_file.csv")

# Copy with overwrite control
fs.cp("file.csv", "existing_file.csv", overwrite=False)  # Raises error if exists

# Copy a directory recursively
fs.cp("data_folder", "backup/data_folder", recursive=True)
```

#### Move/Rename Files

```python
# Move a file to a different location
fs.mv("old_location/file.csv", "new_location/file.csv")

# Rename a file
fs.mv("old_name.csv", "new_name.csv")

# Move a directory recursively
fs.mv("old_folder", "new_folder", recursive=True)
```

#### Batch Operations

For efficient bulk operations:

```python
# Batch copy multiple files
copy_pairs = [
    ("data1.csv", "backup/data1.csv"),
    ("data2.csv", "backup/data2.csv"),
    ("data3.csv", "backup/data3.csv"),
]

result = fs.batch_copy(copy_pairs)
print(f"Copied {result['successful']} files, {result['failed']} failed")

# Batch move with progress callback
def progress(current, total, path, operation):
    print(f"{operation}: {current}/{total} - {path}")

move_pairs = [
    ("temp1.csv", "archive/temp1.csv"),
    ("temp2.csv", "archive/temp2.csv"),
]

result = fs.batch_move(move_pairs, callback=progress)

# Batch delete files
files_to_delete = ["temp1.csv", "temp2.csv", "temp3.csv"]
result = fs.batch_delete(files_to_delete)
print(f"Deleted {result['successful']} files")
```

#### Important Notes on File Operations

- **Same project only**: Copy and move operations only work within the same OSF project and storage provider
- **Checksum verification**: Copy operations automatically verify data integrity using checksums
- **Non-atomic moves**: Move operations use copy-then-delete strategy for reliability (not atomic)
- **Batch error handling**: Batch operations collect all errors and continue processing remaining files
- **No overwrite by default**: Copy operations overwrite by default; use `overwrite=False` to prevent

## Configuration Options

Environment variables for customizing OSF client behavior:

### Read/Download Configuration

```bash
# OSF API endpoint (default: https://api.osf.io/v2)
export OSF_API_URL=https://api.osf.io/v2

# Request timeout in seconds (default: 30)
export OSF_TIMEOUT=60

# Maximum retry attempts (default: 3)
export OSF_MAX_RETRIES=5

# Retry backoff multiplier (default: 2.0)
export OSF_RETRY_BACKOFF=2.0

# Download chunk size in bytes (default: 8192)
export OSF_CHUNK_SIZE=16384

# Connection pool size (default: 10)
export OSF_POOL_SIZE=20
```

### Write/Upload Configuration

```bash
# Upload chunk size for streaming large files (default: 5MB / 5242880 bytes)
export OSF_UPLOAD_CHUNK_SIZE=10485760  # 10MB

# Upload timeout in seconds (default: 300)
export OSF_UPLOAD_TIMEOUT=600  # 10 minutes for very large files

# Write buffer size for file objects (default: 8192 bytes)
export OSF_WRITE_BUFFER_SIZE=16384
```

## Troubleshooting

### Authentication Errors

**Problem:** "Authentication failed. Check your OSF token."

**Solutions:**
- Verify your token is valid at https://osf.io/settings/tokens/
- Ensure token has `osf.full_read` scope for downloads
- Ensure token has `osf.full_write` scope for uploads
- Check that token isn't expired
- Make sure there's no whitespace in the token string

### Upload Errors

**Problem:** "Failed to upload file to OSF"

**Solutions:**
- Verify your token has `osf.full_write` scope
- Check that you have write permissions for the OSF project
- Ensure you're not exceeding OSF storage quotas
- Try increasing upload timeout: `export OSF_UPLOAD_TIMEOUT=600`
- Check file size limits (OSF supports files up to 5GB)

### Quota Exceeded Errors

**Problem:** "Storage quota exceeded"

**Solutions:**
- Check your OSF project storage usage at the project settings page
- Delete unnecessary files from OSF to free up space
- Contact OSF support for quota increases if needed
- Consider using OSF's add-on storage providers (future feature)

### Checksum Verification Errors

**Problem:** "Checksum mismatch after upload"

**Solutions:**
- This usually indicates network corruption - the plugin will automatically retry
- Check your network connection stability
- Try uploading again - transient network issues often resolve on retry
- If persistent, try reducing chunk size: `export OSF_UPLOAD_CHUNK_SIZE=1048576`

### File Not Found Errors

**Problem:** Files exist on OSF but aren't found by the plugin

**Solutions:**
- Verify the project ID is correct (check OSF project URL)
- Ensure you're using `osfstorage` as the provider
- Check that files are in the osfstorage provider (not add-on storage)
- Verify you have read permissions for the OSF project

### Network/Connection Errors

**Problem:** "Failed to connect to OSF"

**Solutions:**
- Check your internet connection
- Verify OSF isn't experiencing downtime: https://twitter.com/OSFramework
- Try increasing timeout: `export OSF_TIMEOUT=120`
- Check if you're behind a proxy that might block OSF API access

### Rate Limiting

**Problem:** "OSF API rate limit exceeded"

**Solutions:**
- Wait for the rate limit to reset (plugin auto-retries with backoff)
- Reduce concurrent operations
- The plugin automatically handles rate limiting with exponential backoff

### File Locking Errors

**Problem:** "File is locked by another process"

**Solutions:**
- Wait for the other operation to complete
- Check OSF web interface to see if file is being processed
- This is usually temporary - retry after a few moments

### Copy/Move Operation Errors (Phase 4)

**Problem:** "Cross-project copy not supported" or "Cross-provider copy not supported"

**Solutions:**
- Copy and move operations only work within the same OSF project
- Ensure both source and destination paths use the same project ID
- Both paths must use the same storage provider (e.g., both `osfstorage`)
- To move files between projects, download and re-upload manually

**Problem:** "Destination exists" during copy/move operations

**Solutions:**
- For copy: Use `overwrite=True` parameter: `fs.cp(src, dst, overwrite=True)`
- For move: Delete the destination file first, or choose a different destination
- Check if destination exists before operation: `if not fs.exists(dst): fs.cp(src, dst)`

**Problem:** Batch operations report partial failures

**Solutions:**
- Check the `errors` list in the result dictionary for specific failure reasons
- Batch operations continue on errors - review the result to see which files succeeded
- Common causes: source file not found, permission denied, network errors
- Retry failed operations individually for more detailed error messages

**Problem:** "Source not found" during copy/move

**Solutions:**
- Verify the source file exists: `fs.exists("path/to/file")`
- Check for typos in the file path
- Ensure you have read permissions for the source file
- List directory contents to confirm file name: `fs.ls("directory")`

**Problem:** Copy operation succeeds but checksums don't match

**Solutions:**
- The operation will automatically fail with an integrity error
- This indicates data corruption during transfer
- Retry the operation - transient network issues often resolve
- Check network stability if the problem persists

## Architecture

**dvc-osf** follows the standard DVC plugin architecture:

- Subclasses `dvc_objects.fs.base.ObjectFileSystem` from the [dvc-objects](https://github.com/iterative/dvc-objects) package
- Implements the required filesystem operations (read, write, list, copy, delete)
- Interacts with OSF through the [OSF API v2](https://developer.osf.io/)
- Provides authentication and connection management
- Handles file transfer operations with proper error handling and retries

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/dvc-osf.git
cd dvc-osf

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=dvc_osf --cov-report=html

# Run specific test file
pytest tests/test_filesystem.py
```

### Code Quality

This project uses:
- `black` for code formatting
- `isort` for import sorting
- `flake8` for linting
- `mypy` for type checking
- `pre-commit` for automated checks

Run checks manually:

```bash
# Format code
black dvc_osf tests

# Sort imports
isort dvc_osf tests

# Run linter
flake8 dvc_osf tests

# Run type checker
mypy dvc_osf
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please ensure:
- All tests pass
- Code follows the project's style guidelines
- Documentation is updated as needed
- Commit messages are clear and descriptive

## Testing

The test suite includes:
- Unit tests for filesystem operations
- Integration tests with OSF API (mocked and real)
- Tests for authentication and error handling
- Tests for edge cases and error conditions

## License

Distributed under the Apache 2.0 License. See `LICENSE` file for more information.

## Support

- **Documentation**: [Link to full documentation]
- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/dvc-osf/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/dvc-osf/discussions)
- **DVC Community**: [DVC Discord](https://dvc.org/chat)
- **OSF Support**: [OSF Help](https://help.osf.io)

## Related Projects

- [DVC](https://github.com/iterative/dvc) - Data Version Control
- [dvc-objects](https://github.com/iterative/dvc-objects) - DVC filesystem abstractions
- [dvc-s3](https://github.com/iterative/dvc-s3) - DVC plugin for AWS S3
- [dvc-gs](https://github.com/iterative/dvc-gs) - DVC plugin for Google Cloud Storage
- [OSF API Documentation](https://developer.osf.io/) - Official OSF API docs

## Acknowledgments

- The [DVC team](https://github.com/iterative/dvc/graphs/contributors) for creating an excellent data versioning tool
- The [OSF team](https://osf.io/team/) for building a platform that supports open science
- All contributors to this project

## Citation

If you use dvc-osf in your research, please cite:

```bibtex
@software{dvc_osf,
  title = {dvc-osf: Open Science Framework plugin for Data Version Control},
  author = {[Your Name/Organization]},
  year = {2026},
  url = {https://github.com/YOUR_USERNAME/dvc-osf}
}
```

## Roadmap

### Completed Phases

- ✅ **Phase 1**: Basic read operations and authentication
- ✅ **Phase 2**: Advanced read features (streaming, caching, error handling)
- ✅ **Phase 3**: Write operations (upload, delete, checksums)
- ✅ **Phase 4**: File manipulation operations (copy, move, batch operations)

### Future Phases

### Phase 5 (In Progress)
- [ ] Parallel upload/download for multiple files
- [ ] Resume interrupted uploads
- [ ] Performance optimizations for batch operations

### Phase 6 (Planned)
- [ ] Subdirectory management (explicit folder creation)
- [ ] Support for OSF add-on storage providers
- [ ] Integration with OSF DOI minting
- [ ] Advanced metadata handling

## FAQ

**Q: Do I need an OSF account to use this plugin?**  
A: Yes, you need an OSF account and a personal access token.

**Q: Is OSF storage free?**  
A: Yes, OSF provides free storage for research projects, with reasonable usage limits.

**Q: Can I use this with private OSF projects?**  
A: Yes, the plugin works with both public and private OSF projects, as long as you have the appropriate access permissions.

**Q: Can I upload data to OSF with this plugin?**  
A: Yes! Phase 3 includes full write operation support. Use `dvc push` to upload data to OSF. Make sure your token has the `osf.full_write` scope.

**Q: Does the plugin handle large file uploads?**  
A: Yes, the plugin uses streaming uploads for large files (>5MB by default), which keeps memory usage low and provides progress tracking. You can configure the chunk size with `OSF_UPLOAD_CHUNK_SIZE`.

**Q: What happens when I upload a file that already exists on OSF?**  
A: OSF automatically creates a new version of the file. The plugin doesn't delete old versions - you can access them through the OSF web interface.

**Q: Does this support OSF add-on storage providers (like Dropbox, Google Drive)?**  
A: Not currently. The plugin supports `osfstorage` only. Add-on provider support is planned for future releases.

**Q: Can I copy or move files between different OSF projects?**  
A: No, copy and move operations only work within the same OSF project and storage provider. To transfer files between projects, download from one project and upload to another.

**Q: Are move operations atomic on OSF?**  
A: No, move operations use a copy-then-delete strategy for reliability. If the delete fails after a successful copy, the source file may remain (creating a duplicate). This prioritizes data safety over atomicity.

**Q: How do I copy multiple files efficiently?**  
A: Use the `batch_copy()` method which handles multiple files in one operation and provides detailed results. Batch operations are more efficient than individual copy operations and provide progress tracking.

**Q: What happens if a file copy fails in the middle?**  
A: The plugin verifies checksums after each copy. If data corruption is detected, the operation fails with an integrity error, and you can safely retry. The destination file will not be left in a corrupted state.

---

Made with ❤️ for open science and reproducible research
