## Context

This is the initial setup for the dvc-osf project, a Python plugin that integrates DVC (Data Version Control) with OSF (Open Science Framework). The project currently has only a PROJECT_DESCRIPTION.md file and needs a complete project structure with modern Python packaging tooling.

**Current State**: Empty repository with only documentation

**Constraints**:
- Must support Python 3.8+ (per project requirements)
- Must integrate with DVC's plugin system via entry points
- Must follow modern Python packaging best practices (PEP 517/518)
- Development team wants flexibility in dependency management tools

**Stakeholders**:
- Developers who will implement the dvc-osf functionality
- Research community who will use the plugin
- DVC and OSF ecosystems

## Goals / Non-Goals

**Goals:**
- Create a well-organized package structure that's easy to navigate and extend
- Support both uv and poetry as dependency managers with a single source of truth
- Establish code quality standards through automated tooling
- Enable immediate development with proper testing infrastructure
- Configure entry points for DVC and fsspec plugin discovery
- Provide clear documentation structure for contributors

**Non-Goals:**
- Implementation of actual OSF filesystem functionality (future work)
- Complete documentation content (only structure)
- CI/CD pipeline implementation (basic structure only)
- Performance optimization or advanced features

## Decisions

### 1. Single `pyproject.toml` for Both uv and Poetry

**Decision**: Use one `pyproject.toml` that works with both uv and poetry, rather than maintaining separate configuration files.

**Rationale**: 
- Both tools support PEP 621 standard `[project]` section
- Poetry has improved PEP 621 support (poetry 1.5+)
- Reduces duplication and maintenance burden
- Ensures dependency consistency across tools

**Alternatives Considered**:
- Separate files (pyproject.toml + poetry-specific config): Rejected due to duplication
- Only uv: Rejected because poetry is widely established in Python ecosystem
- Only poetry: Rejected because uv is significantly faster for operations

**Implementation**:
- Use `[project]` section for core metadata (PEP 621)
- Use `[project.optional-dependencies]` for dev dependencies
- Add `[tool.poetry]` section only for poetry-specific config if needed
- Both tools will generate their own lock files (uv.lock, poetry.lock)

### 2. Package Structure: Flat Module Organization

**Decision**: Use a flat module structure within `dvc_osf/` rather than nested subpackages.

**Rationale**:
- Project is small to medium size at this phase
- Flat structure is easier to navigate
- Can refactor into subpackages later if needed
- Aligns with project description structure

**Structure**:
```
dvc_osf/
├── __init__.py          # Version, public API
├── filesystem.py        # OSFFileSystem class
├── api.py              # OSF API client
├── auth.py             # Authentication handling
├── utils.py            # Utility functions
├── exceptions.py       # Custom exceptions
└── config.py           # Configuration management
```

**Alternatives Considered**:
- Nested structure (dvc_osf/core/, dvc_osf/api/): Rejected as premature for initial setup
- Monolithic single file: Rejected for maintainability

### 3. Development Tools: Industry Standard Stack

**Decision**: Use pytest, black, isort, flake8, mypy, and pre-commit.

**Rationale**:
- These are industry-standard, well-supported tools
- Aligns with DVC project's own tooling
- Good IDE/editor integration
- Pre-commit ensures standards are enforced before commit

**Configuration**:
- Black with 88-character line length (default)
- isort with black-compatible profile
- flake8 with max-line-length=88, ignore E203/W503 for black compatibility
- mypy with strict mode (can relax if needed)
- Pre-commit hooks for all formatters/linters

**Alternatives Considered**:
- Ruff (modern all-in-one): Considered but sticking with established tools for now
- Pylint: Rejected as more opinionated than flake8

### 4. Entry Points: Dual Registration

**Decision**: Register the filesystem with both `fsspec.specs` and `dvc.fs` entry points.

**Rationale**:
- `fsspec.specs` allows direct fsspec usage
- `dvc.fs` is the official DVC plugin system
- Both registrations ensure maximum compatibility
- No downsides to dual registration

**Configuration**:
```toml
[project.entry-points."fsspec.specs"]
osf = "dvc_osf.filesystem:OSFFileSystem"

[project.entry-points."dvc.fs"]
osf = "dvc_osf.filesystem:OSFFileSystem"
```

### 5. Testing Structure: Mirror Package Layout

**Decision**: Mirror the package structure in tests/ with test_ prefix.

**Structure**:
```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_filesystem.py    # Tests for filesystem.py
├── test_api.py          # Tests for api.py
├── test_auth.py         # Tests for auth.py
├── test_integration.py  # Integration tests
└── fixtures/            # Test data and mocks
```

**Rationale**:
- Easy to find tests corresponding to modules
- Standard pytest convention
- Separation of unit and integration tests

### 6. Version Management: Single Source in __init__.py

**Decision**: Define version in `dvc_osf/__init__.py` and import it in pyproject.toml using dynamic versioning.

**Rationale**:
- Version is accessible at runtime via `dvc_osf.__version__`
- Single source of truth principle
- Simpler than using version files or git tags for initial setup

**Implementation**:
```python
# dvc_osf/__init__.py
__version__ = "0.1.0"
```

```toml
# pyproject.toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "dvc_osf.__version__"}
```

**Alternatives Considered**:
- setuptools_scm (git-based): Rejected as overkill for initial setup
- Separate VERSION file: Rejected for simplicity

## Risks / Trade-offs

### Risk: Poetry and uv Lock File Divergence
**Description**: Different tools may resolve dependencies differently, leading to inconsistent environments.

**Mitigation**: 
- Document that developers should pick one tool and stick with it
- CI will use uv for speed, but test with both lock files periodically
- Keep dependency constraints specific enough to avoid ambiguity

### Risk: uv Adoption Uncertainty
**Description**: uv is relatively new; some developers may not want to adopt it yet.

**Mitigation**:
- Poetry remains fully supported as the stable option
- Document uv as optional but recommended
- Both tools use the same pyproject.toml, so switching is easy

### Trade-off: Flat Module Structure vs. Scalability
**Description**: Flat structure may need refactoring if project grows significantly.

**Mitigation**:
- Start simple, refactor when needed
- Python makes refactoring imports straightforward
- This is the right choice for current project size

### Risk: Pre-commit Hook Strictness
**Description**: Strict linting may slow down initial development.

**Mitigation**:
- Can disable pre-commit hooks locally if needed (`git commit --no-verify`)
- Start with reasonable defaults, adjust based on feedback
- Benefits (consistency, fewer review comments) outweigh costs

### Trade-off: Mypy Strict Mode
**Description**: Strict type checking may require significant type annotations upfront.

**Mitigation**:
- Can relax mypy settings initially if too restrictive
- Incremental adoption is possible
- Type hints improve code quality and IDE support long-term

## Migration Plan

**Initial Setup** (this change):
1. Create all files and directories
2. Initialize with basic content (mostly stubs)
3. Verify tools work: `pytest`, `black --check`, `mypy`
4. Commit and tag as v0.1.0-dev

**Verification Steps**:
- `uv sync` or `poetry install` succeeds
- `pytest` runs (even with no real tests yet)
- Pre-commit hooks install and run successfully
- Package can be imported: `python -c "import dvc_osf"`

**Rollback Strategy**: 
- N/A for initial setup (no existing state to roll back to)
- If issues arise, can delete and recreate files

## Open Questions

1. **Should we include sample test data in the repository initially?**
   - Lean toward yes for integration tests, but can add later
   
2. **What version constraints for dependencies?**
   - Propose: `dvc-objects>=5.0.0`, `requests>=2.28.0`, `fsspec>=2023.1.0`
   - Based on project requirements and stability

3. **Should we set up GitHub Actions CI in this change or separately?**
   - Propose: Create basic workflow files, but they can be refined later
   - Keeps this change focused on local development setup

4. **License choice?**
   - Project description mentions Apache 2.0
   - Confirm with stakeholders before finalizing
