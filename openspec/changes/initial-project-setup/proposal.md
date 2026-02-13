## Why

The dvc-osf project needs a solid foundation with modern Python packaging and development tooling to support efficient development. This establishes the project structure, configures dual dependency management (uv and poetry for different use cases), and sets up development tooling for testing, linting, and code quality.

## What Changes

- Create core package structure (`dvc_osf/`) with proper module organization
- Configure `pyproject.toml` with project metadata, dependencies, and DVC/fsspec entry points
- Add support for both uv (fast, modern) and poetry (traditional, feature-rich) dependency managers
- Set up development tooling: pytest, black, isort, flake8, mypy, pre-commit
- Create initial package modules: filesystem, api, auth, utils, exceptions, config
- Configure testing infrastructure with pytest and coverage reporting
- Add `.gitignore`, `.pre-commit-config.yaml`, and other essential project files
- Create initial documentation structure (README.md, CONTRIBUTING.md, etc.)

## Capabilities

### New Capabilities

- `package-structure`: Core Python package layout with `dvc_osf/` directory and essential modules
- `dependency-management`: Dual support for uv and poetry with `pyproject.toml` configuration
- `development-tooling`: Testing (pytest), linting (flake8), formatting (black, isort), type checking (mypy)
- `build-configuration`: Modern Python packaging with entry points for DVC and fsspec
- `git-configuration`: Git ignore patterns and pre-commit hooks for code quality
- `documentation-structure`: README, CONTRIBUTING, and docs/ directory scaffolding

### Modified Capabilities

<!-- No existing capabilities are being modified - this is the initial setup -->

## Impact

**New Files Created**:
- `dvc_osf/__init__.py`, `filesystem.py`, `api.py`, `auth.py`, `utils.py`, `exceptions.py`, `config.py`
- `pyproject.toml` (single source of truth for both uv and poetry)
- `uv.lock` and `poetry.lock` (dependency lock files)
- `.gitignore`, `.pre-commit-config.yaml`, `pytest.ini`
- `tests/` directory with `conftest.py` and initial test files
- `README.md`, `CONTRIBUTING.md`, `LICENSE`, `CHANGELOG.md`
- `.github/workflows/` for CI configuration

**Development Environment**:
- Developers can choose between uv (faster) or poetry (more features)
- Both tools will use the same `pyproject.toml` for consistency
- Pre-commit hooks will enforce code quality standards

**Dependencies**:
- Core: dvc-objects, requests, fsspec
- Development: pytest, black, isort, flake8, mypy, pre-commit
