## ADDED Requirements

### Requirement: Gitignore excludes Python artifacts
The project SHALL include a `.gitignore` file that excludes Python build and runtime artifacts.

#### Scenario: Python cache directories are ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes patterns for `__pycache__/`, `*.py[cod]`, and `*$py.class`

#### Scenario: Virtual environments are ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes patterns for `venv/`, `env/`, `.venv/`, and common virtualenv names

#### Scenario: Build artifacts are ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes patterns for `build/`, `dist/`, `*.egg-info/`, and `.eggs/`

### Requirement: Gitignore excludes dependency lock files
The project SHALL ignore dependency manager lock files except those intended for version control.

#### Scenario: Poetry lock file is tracked
- **WHEN** `.gitignore` is examined
- **THEN** `poetry.lock` is NOT in the ignore list

#### Scenario: UV lock file is tracked
- **WHEN** `.gitignore` is examined
- **THEN** `uv.lock` is NOT in the ignore list

### Requirement: Gitignore excludes IDE and editor files
The project SHALL ignore common IDE and editor configuration files.

#### Scenario: VSCode settings are ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes `.vscode/` (or only tracks selected files)

#### Scenario: PyCharm settings are ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes `.idea/`

#### Scenario: System files are ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes `.DS_Store` and `Thumbs.db`

### Requirement: Gitignore excludes test and coverage artifacts
The project SHALL ignore test-related temporary files and coverage reports.

#### Scenario: Coverage files are ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes `.coverage`, `.coverage.*`, `htmlcov/`, and `coverage.xml`

#### Scenario: Pytest cache is ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes `.pytest_cache/`

#### Scenario: Mypy cache is ignored
- **WHEN** `.gitignore` is examined
- **THEN** it includes `.mypy_cache/`

### Requirement: Pre-commit hooks are configured
The project SHALL include a `.pre-commit-config.yaml` file with code quality hooks.

#### Scenario: Pre-commit config exists
- **WHEN** `.pre-commit-config.yaml` is checked
- **THEN** the file exists in the repository root

#### Scenario: Black hook is configured
- **WHEN** `.pre-commit-config.yaml` is examined
- **THEN** it includes a hook for black formatter

#### Scenario: isort hook is configured
- **WHEN** `.pre-commit-config.yaml` is examined
- **THEN** it includes a hook for isort import sorting

#### Scenario: Flake8 hook is configured
- **WHEN** `.pre-commit-config.yaml` is examined
- **THEN** it includes a hook for flake8 linting

#### Scenario: Trailing whitespace hook is included
- **WHEN** `.pre-commit-config.yaml` is examined
- **THEN** it includes standard hooks for trailing whitespace and end-of-file fixes

### Requirement: Git configuration supports both lock files
The project SHALL track both `uv.lock` and `poetry.lock` in version control.

#### Scenario: Lock files are committed
- **WHEN** lock files are generated
- **THEN** they can be added and committed to git

#### Scenario: Lock files enable reproducible installs
- **WHEN** a developer clones the repository
- **THEN** they can install exact dependency versions using either lock file
