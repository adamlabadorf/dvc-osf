## ADDED Requirements

### Requirement: Single pyproject.toml configuration
The project SHALL use a single `pyproject.toml` file that works with both uv and poetry dependency managers.

#### Scenario: File uses PEP 621 project section
- **WHEN** `pyproject.toml` is examined
- **THEN** it contains a `[project]` section with standard metadata fields

#### Scenario: Both uv and poetry can read the configuration
- **WHEN** either `uv sync` or `poetry install` is executed
- **THEN** dependencies are resolved successfully without errors

### Requirement: Core dependencies are specified
The project SHALL declare core runtime dependencies in the `[project]` dependencies section.

#### Scenario: Required packages are listed
- **WHEN** `pyproject.toml` is examined
- **THEN** it lists `dvc-objects>=5.0.0`, `requests>=2.28.0`, and `fsspec>=2023.1.0`

### Requirement: Development dependencies are optional
The project SHALL declare development dependencies in `[project.optional-dependencies]` under a `dev` group.

#### Scenario: Dev dependencies include testing tools
- **WHEN** the dev dependencies are examined
- **THEN** they include pytest, pytest-cov, pytest-mock

#### Scenario: Dev dependencies include code quality tools
- **WHEN** the dev dependencies are examined
- **THEN** they include black, isort, flake8, mypy

#### Scenario: Dev dependencies include pre-commit
- **WHEN** the dev dependencies are examined
- **THEN** they include pre-commit

### Requirement: Both tools generate lock files
The project SHALL support both `uv.lock` and `poetry.lock` files for reproducible installs.

#### Scenario: uv generates lock file
- **WHEN** `uv sync` is executed
- **THEN** a `uv.lock` file is created or updated

#### Scenario: Poetry generates lock file
- **WHEN** `poetry install` is executed
- **THEN** a `poetry.lock` file is created or updated

### Requirement: Python version constraint is specified
The project SHALL specify minimum and maximum Python versions in `pyproject.toml`.

#### Scenario: Minimum Python 3.8 is required
- **WHEN** `pyproject.toml` is examined
- **THEN** `requires-python` is set to `">=3.8"`

### Requirement: Build system is configured
The project SHALL specify a PEP 517-compliant build system in `pyproject.toml`.

#### Scenario: Build backend is specified
- **WHEN** `pyproject.toml` is examined
- **THEN** it contains a `[build-system]` section with `requires` and `build-backend` fields

#### Scenario: setuptools is configured as backend
- **WHEN** the build backend is examined
- **THEN** it is set to `"setuptools.build_meta"`
