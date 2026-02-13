# Installation Guide

## Prerequisites

- Python 3.8 or higher
- pip, uv, or poetry package manager
- OSF account (create at https://osf.io)
- OSF personal access token

## Installation Methods

### Using pip

```bash
pip install dvc-osf
```

### Using uv (recommended)

```bash
uv pip install dvc-osf
```

### Using poetry

```bash
poetry add dvc-osf
```

### From Source

```bash
git clone https://github.com/dvc-osf/dvc-osf.git
cd dvc-osf
pip install -e .
```

## Verification

Verify the installation:

```bash
python -c "import dvc_osf; print(dvc_osf.__version__)"
```

## Next Steps

- See [Configuration](configuration.md) for setup instructions
- See [README](../README.md) for usage examples
