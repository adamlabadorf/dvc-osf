# Contributing to DVC-OSF

Thank you for considering contributing to dvc-osf! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Either `uv` or `poetry` for dependency management

### Setup with uv (recommended)

```bash
# Clone the repository
git clone https://github.com/dvc-osf/dvc-osf.git
cd dvc-osf

# Install uv if you haven't already
pip install uv

# Create virtual environment and install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Setup with poetry

```bash
# Clone the repository
git clone https://github.com/dvc-osf/dvc-osf.git
cd dvc-osf

# Install poetry if you haven't already
pip install poetry

# Install dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install
```

## Development Workflow

### Running Tests

```bash
# With uv
uv run pytest

# With poetry
poetry run pytest

# Run with coverage
uv run pytest --cov=dvc_osf --cov-report=html
```

### Code Formatting and Linting

This project uses several tools to maintain code quality:

- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Code linting
- **mypy**: Type checking

```bash
# Format code
uv run black dvc_osf tests

# Sort imports
uv run isort dvc_osf tests

# Run linter
uv run flake8 dvc_osf tests

# Run type checker
uv run mypy dvc_osf
```

Pre-commit hooks will automatically run these tools before each commit.

### Running Pre-commit Checks

```bash
# Run all pre-commit hooks on all files
uv run pre-commit run --all-files

# Skip pre-commit hooks for a specific commit (use sparingly)
git commit --no-verify
```

## Making Changes

### Branching Strategy

- Create a new branch for each feature or bug fix
- Use descriptive branch names: `feature/add-xyz`, `fix/issue-123`
- Keep branches focused on a single concern

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense: "Add", "Fix", "Update", "Remove"
- Reference issues when applicable: "Fix authentication error (#42)"

### Pull Request Process

1. **Create your branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes**
   - Write code following project style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests and checks**
   ```bash
   uv run pytest
   uv run pre-commit run --all-files
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add amazing feature"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a Pull Request**
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure CI checks pass

## Testing Guidelines

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the package structure: `test_filesystem.py` for `filesystem.py`
- Use descriptive test names: `test_osf_filesystem_lists_files_correctly`
- Use pytest fixtures from `conftest.py` for common setup

### Test Categories

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test interaction with OSF API (mark with `@pytest.mark.integration`)
- **Slow tests**: Mark long-running tests with `@pytest.mark.slow`

### Running Specific Tests

```bash
# Run a specific test file
uv run pytest tests/test_filesystem.py

# Run a specific test
uv run pytest tests/test_filesystem.py::test_osf_filesystem_init

# Skip integration tests
uv run pytest -m "not integration"
```

## Code Style Guidelines

### Python Style

- Follow PEP 8 (enforced by flake8)
- Use type hints for function signatures
- Maximum line length: 88 characters (black default)
- Use docstrings for all public functions and classes

### Docstring Format

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    More detailed description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this is raised
    """
    pass
```

## Dependency Management

### Adding Dependencies

**With uv:**
```bash
# Add a production dependency
uv add package-name

# Add a development dependency
uv add --dev package-name
```

**With poetry:**
```bash
# Add a production dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name
```

### Updating Dependencies

```bash
# With uv
uv sync --upgrade

# With poetry
poetry update
```

## Documentation

### Updating Documentation

- Keep README.md up to date with new features
- Update docstrings when modifying functions
- Add examples for new functionality
- Update CHANGELOG.md for notable changes

## Release Process

(For maintainers only)

1. Update version in `dvc_osf/__init__.py`
2. Update CHANGELOG.md
3. Create a git tag: `git tag v0.x.0`
4. Push tag: `git push origin v0.x.0`
5. GitHub Actions will handle the release

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Chat**: Join the DVC Discord

## Code of Conduct

Be respectful and inclusive. We're all here to support open science and reproducible research.

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
