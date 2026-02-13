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

- Full DVC remote storage support for OSF
- Upload and download versioned data to/from OSF storage
- List and manage files on OSF storage
- Copy operations within OSF storage
- Authentication via OSF personal access tokens
- Support for OSF projects and components
- Compatible with DVC's caching and optimization features

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
3. Create a new token with appropriate scopes (read/write access to your projects)
4. Save the token securely

### 2. Configure DVC Remote

Add an OSF remote to your DVC project:

```bash
# Configure OSF remote with project ID
dvc remote add -d myosf osf://PROJECT_ID/STORAGE_NAME

# Set your OSF access token
dvc remote modify myosf token YOUR_OSF_TOKEN
```

Where:
- `PROJECT_ID` is your OSF project identifier (found in the OSF project URL)
- `STORAGE_NAME` is the storage provider name configured in your OSF project (e.g., `osfstorage`)
- `YOUR_OSF_TOKEN` is your personal access token

### 3. Use DVC as Normal

Once configured, use DVC commands as you normally would:

```bash
# Add data to DVC tracking
dvc add data/dataset.csv

# Push data to OSF
dvc push

# Pull data from OSF
dvc pull

# Check remote status
dvc status -r myosf
```

### Example Workflow

```bash
# Initialize DVC in your project
dvc init

# Add OSF remote
dvc remote add -d osf-storage osf://abc123/osfstorage
dvc remote modify osf-storage token $OSF_TOKEN

# Track a dataset
dvc add data/train.csv

# Commit the .dvc file to git
git add data/train.csv.dvc .gitignore
git commit -m "Add training dataset"

# Push data to OSF
dvc push

# Share your project with collaborators
# They can now pull the data from OSF
dvc pull
```

## Configuration Options

Additional configuration options for the OSF remote:

```bash
# Set custom OSF API endpoint (for testing or private instances)
dvc remote modify myosf endpoint_url https://api.osf.io/v2

# Configure connection timeout
dvc remote modify myosf timeout 300

# Enable retry on failure
dvc remote modify myosf retry_count 3
```

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

Future enhancements may include:

- [ ] Support for OSF file versioning
- [ ] Integration with OSF project metadata
- [ ] Support for OSF add-on storage providers
- [ ] Batch upload/download optimizations
- [ ] Progress reporting for large transfers
- [ ] Support for OSF file previews and metadata
- [ ] Integration with OSF DOI minting

## FAQ

**Q: Do I need an OSF account to use this plugin?**  
A: Yes, you need an OSF account and a personal access token.

**Q: Is OSF storage free?**  
A: Yes, OSF provides free storage for research projects, with reasonable usage limits.

**Q: Can I use this with private OSF projects?**  
A: Yes, the plugin works with both public and private OSF projects, as long as you have the appropriate access permissions.

**Q: How do I migrate existing DVC data to OSF?**  
A: Configure the OSF remote and use `dvc push -r osf-remote` to upload your data to OSF.

**Q: What happens if I hit OSF storage limits?**  
A: OSF has generous storage limits for individual projects. If you need more storage, contact OSF support or consider organizing data across multiple projects.

**Q: Does this support OSF add-on storage providers (like Dropbox, Google Drive)?**  
A: Currently, the plugin focuses on native OSF storage. Support for add-on providers may be added in future versions.

---

Made with ❤️ for open science and reproducible research
