# Development Guide

## Development Setup

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed development setup instructions.

## Quick Start

```bash
# Clone repository
git clone https://github.com/dvc-osf/dvc-osf.git
cd dvc-osf

# Install with uv
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

## Architecture Overview

### Core Components

- **filesystem.py**: OSFFileSystem implementation (extends `ObjectFileSystem`)
- **api.py**: OSF API client for HTTP operations
- **auth.py**: Authentication handling
- **config.py**: Configuration management
- **utils.py**: Utility functions
- **exceptions.py**: Custom exception classes

### Design Principles

- **DVC Integration**: Implements `ObjectFileSystem` interface
- **fsspec Compatibility**: Works with fsspec-based tools
- **OSF API v2**: Uses OSF REST API for all operations
- **Error Handling**: Comprehensive exception hierarchy
- **Type Safety**: Full type hints throughout codebase

## Testing

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=dvc_osf

# Specific test file
uv run pytest tests/test_filesystem.py

# Skip integration tests
uv run pytest -m "not integration"
```

### Test Structure

- **Unit tests**: Test individual components
- **Integration tests**: Test OSF API integration (requires credentials)
- **Fixtures**: Shared test fixtures in `conftest.py`

### Writing Tests

```python
import pytest
from dvc_osf.filesystem import OSFFileSystem

def test_filesystem_init(osf_token, osf_project_id):
    """Test filesystem initialization."""
    fs = OSFFileSystem(token=osf_token, project_id=osf_project_id)
    assert fs.token == osf_token
```

## Code Quality

### Formatting and Linting

```bash
# Format code
uv run black dvc_osf tests

# Sort imports
uv run isort dvc_osf tests

# Lint code
uv run flake8 dvc_osf tests

# Type check
uv run mypy dvc_osf
```

### Pre-commit Hooks

Pre-commit hooks automatically run on `git commit`:

- Trailing whitespace removal
- End-of-file fixer
- YAML/TOML validation
- Black formatting
- isort import sorting
- Flake8 linting
- Mypy type checking

## Dependency Management

### With uv

```bash
# Add dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update dependencies
uv sync --upgrade
```

### With poetry

```bash
# Add dependency
poetry add package-name

# Add dev dependency
poetry add --group dev package-name

# Update dependencies
poetry update
```

## Release Process

1. Update version in `dvc_osf/__init__.py`
2. Update CHANGELOG.md
3. Commit changes
4. Create git tag: `git tag v0.x.0`
5. Push tag: `git push origin v0.x.0`

## Debugging

### Local Testing with OSF

For integration testing with real OSF:

1. Create a test project on OSF
2. Generate a personal access token
3. Set environment variables:
   ```bash
   export OSF_TOKEN=your_token
   export OSF_PROJECT_ID=your_project_id
   ```
4. Run integration tests:
   ```bash
   uv run pytest -m integration
   ```

### Logging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

## Resources

- [DVC Documentation](https://dvc.org/doc)
- [OSF API Documentation](https://developer.osf.io/)
- [fsspec Documentation](https://filesystem-spec.readthedocs.io/)
- [dvc-objects](https://github.com/iterative/dvc-objects)
