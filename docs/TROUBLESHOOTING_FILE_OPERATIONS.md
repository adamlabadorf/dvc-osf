# Troubleshooting File Operations (Copy/Move/Delete)

This guide covers common issues and solutions for Phase 4 file manipulation operations in dvc-osf.

## Table of Contents

- [Copy Operations](#copy-operations)
- [Move Operations](#move-operations)
- [Batch Operations](#batch-operations)
- [General Issues](#general-issues)
- [Best Practices](#best-practices)

## Copy Operations

### Error: "Cross-project copy not supported"

**Cause:** Attempting to copy files between different OSF projects.

**Example:**
```python
# This will fail
fs.cp(
    "osf://project1/osfstorage/file.csv",
    "osf://project2/osfstorage/file.csv"
)
```

**Solution:**
Copy and move operations only work within the same OSF project. To transfer files between projects:

1. Download from source project
2. Upload to destination project

```python
# Download from project1
fs1 = OSFFileSystem("osf://project1/osfstorage", token=token)
fs1.get_file("file.csv", "/tmp/file.csv")

# Upload to project2
fs2 = OSFFileSystem("osf://project2/osfstorage", token=token)
fs2.put_file("/tmp/file.csv", "file.csv")
```

### Error: "Cross-provider copy not supported"

**Cause:** Attempting to copy files between different storage providers (e.g., osfstorage to github).

**Solution:**
All file operations must use the same storage provider. Ensure both source and destination use `osfstorage`.

### Error: "Destination exists"

**Cause:** Trying to copy to a location where a file already exists with `overwrite=False`.

**Example:**
```python
# This will fail if destination.csv already exists
fs.cp("source.csv", "destination.csv", overwrite=False)
```

**Solutions:**

**Option 1:** Allow overwriting (default behavior)
```python
fs.cp("source.csv", "destination.csv", overwrite=True)  # or omit overwrite parameter
```

**Option 2:** Check existence first
```python
if not fs.exists("destination.csv"):
    fs.cp("source.csv", "destination.csv")
else:
    print("Destination already exists")
```

**Option 3:** Use a different destination
```python
import time
unique_name = f"destination_{int(time.time())}.csv"
fs.cp("source.csv", unique_name)
```

### Error: "Source not found"

**Cause:** The source file doesn't exist or path is incorrect.

**Solutions:**

**Check if file exists:**
```python
if fs.exists("source.csv"):
    fs.cp("source.csv", "destination.csv")
else:
    print("Source file not found")
```

**List directory contents:**
```python
files = fs.ls("directory")
print("Available files:", files)
```

**Verify path format:**
```python
# Correct - relative path from filesystem root
fs.cp("data/file.csv", "backup/file.csv")

# Incorrect - absolute OSF URL in path
# fs.cp("osf://abc123/osfstorage/file.csv", "backup/file.csv")  # Wrong!
```

### Error: "Checksum mismatch after copy"

**Cause:** Data corruption occurred during the copy operation.

**What it means:**
The plugin automatically verifies that the copied file has the same checksum as the source. This error means the verification failed.

**Solutions:**

1. **Retry the operation** - Transient network issues often resolve:
```python
import time
for attempt in range(3):
    try:
        fs.cp("large_file.dat", "backup/large_file.dat")
        break
    except OSFIntegrityError:
        if attempt < 2:
            print(f"Retry {attempt + 1}/3...")
            time.sleep(2)
        else:
            raise
```

2. **Check network stability** - Frequent checksum errors indicate network problems

3. **Try smaller chunks** - Reduce upload chunk size:
```bash
export OSF_UPLOAD_CHUNK_SIZE=1048576  # 1MB instead of default 5MB
```

### Copying Directories

**Issue:** Directory copy with `recursive=True` skips or fails

**Cause:** OSF API limitations with nested directory creation

**Solution:**
The plugin will copy all files within a directory, but deeply nested directories may have limitations. For best results:

```python
# Copy a directory and its contents
fs.cp("source_dir", "dest_dir", recursive=True)

# If this fails, copy files individually
source_files = fs.ls("source_dir", detail=False)
for file_path in source_files:
    filename = file_path.split("/")[-1]
    fs.cp(file_path, f"dest_dir/{filename}")
```

## Move Operations

### Error: "Source not deleted after move"

**Cause:** Move uses copy-then-delete strategy. If delete fails, source remains.

**What it means:**
The file was successfully copied to the destination, but the source couldn't be deleted. You now have two copies.

**Solutions:**

1. **Manual cleanup:**
```python
# Check if move succeeded by checking destination
if fs.exists("destination.csv"):
    # Destination exists, try deleting source
    try:
        fs.rm_file("source.csv")
    except Exception as e:
        print(f"Could not delete source: {e}")
```

2. **Use copy + manual delete for critical operations:**
```python
# First copy
fs.cp("important.csv", "backup/important.csv")

# Verify copy succeeded
if fs.exists("backup/important.csv"):
    # Then delete original
    fs.rm_file("important.csv")
```

### Error: "Move failed during copy phase"

**Cause:** Copy operation failed (see copy operation errors above).

**What it means:**
The move operation failed before the source was deleted. Your source file is still intact.

**Solution:**
Fix the underlying copy error (see Copy Operations section above) and retry.

### Moving Large Files

**Issue:** Move operations timeout for large files

**Solution:**
Increase timeout and use progress tracking:

```bash
export OSF_UPLOAD_TIMEOUT=1800  # 30 minutes
```

```python
def progress(current, total, path, op):
    percent = (current / total) * 100
    print(f"{op}: {percent:.1f}% - {path}")

# Move large file with monitoring
fs.mv("large_dataset.dat", "archive/large_dataset.dat")
```

## Batch Operations

### Partial Failures in Batch Operations

**Issue:** Some files succeed, others fail in batch operations

**Example:**
```python
result = fs.batch_copy([
    ("file1.csv", "backup/file1.csv"),
    ("missing.csv", "backup/missing.csv"),  # This will fail
    ("file3.csv", "backup/file3.csv"),
])

print(result)
# {
#   'total': 3,
#   'successful': 2,
#   'failed': 1,
#   'errors': [('missing.csv', 'Source not found: missing.csv')]
# }
```

**Solution:**
Batch operations are designed to continue on errors. Check the result and retry failed operations:

```python
result = fs.batch_copy(copy_pairs)

if result['failed'] > 0:
    print(f"Failed operations: {result['errors']}")

    # Retry failed operations
    for source, error in result['errors']:
        print(f"Retrying {source}: {error}")
        # Handle specific error or retry
```

### Batch Operation Performance

**Issue:** Batch operations are slow

**Current Limitation:**
Phase 4 implements sequential batch operations. Files are processed one at a time.

**Workaround:**
For now, batch operations provide progress tracking but not parallel processing:

```python
def progress(current, total, path, operation):
    elapsed = time.time() - start_time
    rate = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / rate if rate > 0 else 0
    print(f"{operation}: {current}/{total} ({eta:.0f}s remaining)")

start_time = time.time()
result = fs.batch_copy(pairs, callback=progress)
```

**Future:** Phase 5 will add parallel processing for better performance.

### Empty Batch Operations

**Error:** "Cannot perform batch operation on empty list"

**Cause:** Provided an empty list to batch operation.

**Solution:**
Check list is not empty before calling batch operations:

```python
files_to_delete = []  # Empty list

if files_to_delete:
    result = fs.batch_delete(files_to_delete)
else:
    print("No files to delete")
```

### Duplicate Destinations in Batch

**Error:** "Duplicate destinations found in batch operation"

**Cause:** Multiple source files map to the same destination.

**Example:**
```python
# This will fail - both map to same destination
fs.batch_copy([
    ("dir1/file.csv", "backup/file.csv"),
    ("dir2/file.csv", "backup/file.csv"),  # Duplicate destination!
])
```

**Solution:**
Ensure all destination paths are unique:

```python
import os

copy_pairs = []
for source in sources:
    # Create unique destination using source path
    basename = os.path.basename(source)
    dirname = os.path.dirname(source).replace("/", "_")
    dest = f"backup/{dirname}_{basename}"
    copy_pairs.append((source, dest))

result = fs.batch_copy(copy_pairs)
```

## General Issues

### Permission Denied

**Error:** "Permission denied for OSF operation"

**Cause:** Token lacks required permissions.

**Solution:**

1. **Check token scopes:**
   - Copy/move/delete require `osf.full_write` scope
   - Visit https://osf.io/settings/tokens/ to verify

2. **Check project permissions:**
   - Ensure you have write access to the project
   - Admin or contributor role required for write operations

3. **Regenerate token if needed:**
```python
# Test token permissions
fs = OSFFileSystem("osf://abc123/osfstorage", token=token)
try:
    fs.ls("")  # Read operation
    print("Read access: ✓")
except Exception as e:
    print(f"Read access: ✗ ({e})")

try:
    # Try creating a test file
    fs.put_file("/tmp/test.txt", "test.txt")
    fs.rm_file("test.txt")
    print("Write access: ✓")
except Exception as e:
    print(f"Write access: ✗ ({e})")
```

### Rate Limiting

**Error:** "OSF API rate limit exceeded"

**Cause:** Too many API requests in a short time.

**Solution:**
The plugin automatically retries with exponential backoff. For large batch operations:

```python
import time

# Process in smaller batches with delays
batch_size = 10
for i in range(0, len(all_pairs), batch_size):
    batch = all_pairs[i:i + batch_size]
    result = fs.batch_copy(batch)
    print(f"Batch {i//batch_size + 1}: {result['successful']} succeeded")

    # Delay between batches
    if i + batch_size < len(all_pairs):
        time.sleep(5)
```

### Quota Exceeded

**Error:** "Storage quota exceeded"

**Cause:** OSF project has reached storage limit.

**Solution:**

1. **Check project storage:**
   - Visit project settings on OSF web interface
   - Review storage usage

2. **Clean up unnecessary files:**
```python
# List all files
files = fs.ls("", detail=True)

# Sort by size
files.sort(key=lambda x: x.get('size', 0), reverse=True)

# Review large files
for file in files[:10]:
    print(f"{file['name']}: {file['size'] / 1024 / 1024:.1f} MB")
```

3. **Contact OSF support** for quota increase if needed

## Best Practices

### Pre-Operation Checks

Always verify conditions before operations:

```python
def safe_copy(fs, source, destination, overwrite=False):
    """Safe copy with pre-checks."""
    # Check source exists
    if not fs.exists(source):
        raise ValueError(f"Source not found: {source}")

    # Check destination
    if fs.exists(destination) and not overwrite:
        raise ValueError(f"Destination exists: {destination}")

    # Perform copy
    fs.cp(source, destination, overwrite=overwrite)

    # Verify success
    if fs.exists(destination):
        print(f"✓ Copied {source} → {destination}")
    else:
        raise RuntimeError("Copy verification failed")
```

### Batch Operation Error Handling

```python
def robust_batch_copy(fs, pairs, max_retries=3):
    """Batch copy with retry logic."""
    result = fs.batch_copy(pairs)

    # Retry failed operations
    retry_pairs = [(src, dst) for src, _ in result['errors']]
    retry_count = 0

    while retry_pairs and retry_count < max_retries:
        retry_count += 1
        print(f"Retry {retry_count}: {len(retry_pairs)} files")

        result = fs.batch_copy(retry_pairs)
        retry_pairs = [(src, dst) for src, _ in result['errors']]

    return result
```

### Progress Monitoring

```python
class ProgressTracker:
    def __init__(self, total):
        self.start_time = time.time()
        self.total = total

    def __call__(self, current, total, path, operation):
        elapsed = time.time() - self.start_time
        rate = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / rate if rate > 0 else 0

        percent = (current / total) * 100
        print(f"\r{operation}: {current}/{total} ({percent:.1f}%) "
              f"ETA: {eta:.0f}s - {path}", end="")

        if current == total:
            print()  # New line when complete

# Use with batch operations
tracker = ProgressTracker(len(pairs))
result = fs.batch_copy(pairs, callback=tracker)
```

### Atomic-Like Operations

For critical data, implement verification:

```python
def atomic_like_move(fs, source, destination):
    """Move with verification and rollback capability."""
    # Step 1: Copy
    fs.cp(source, destination)

    # Step 2: Verify copy succeeded
    if not fs.exists(destination):
        raise RuntimeError("Copy verification failed")

    # Step 3: Verify checksums match (if available)
    src_info = fs.info(source)
    dst_info = fs.info(destination)

    if 'checksum' in src_info and 'checksum' in dst_info:
        if src_info['checksum'] != dst_info['checksum']:
            # Rollback - delete bad destination
            fs.rm_file(destination)
            raise RuntimeError("Checksum mismatch - copy failed")

    # Step 4: Delete source
    try:
        fs.rm_file(source)
    except Exception as e:
        # Source delete failed but copy succeeded
        # Log warning but don't fail
        print(f"Warning: Could not delete source {source}: {e}")
        print(f"Destination {destination} is valid. Manual cleanup needed.")
```

## Getting Help

If you encounter issues not covered here:

1. **Check the logs:** Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Verify API status:** Check https://twitter.com/OSFramework for OSF service status

3. **Report issues:** Open an issue at https://github.com/YOUR_USERNAME/dvc-osf/issues with:
   - Error message and stack trace
   - Minimal code to reproduce
   - OSF project ID (if not sensitive)
   - Plugin version: `pip show dvc-osf`

4. **Community support:**
   - DVC Discord: https://dvc.org/chat
   - OSF Help: https://help.osf.io
