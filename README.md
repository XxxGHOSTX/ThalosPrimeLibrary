# ThalosPrimeLibrary
The brain

## Overview
ThalosPrime Library provides a Python package structure that allows importing from your local ThalosPrimeLibraryOfBabel directory.
It is aligned with the canonical Library of Babel domain at https://libraryofbabel.info (not thelibraryofbabel.com).
The structured search endpoints used by ThalosPrime are:
- Human-readable search UI: https://libraryofbabel.info/search.html
- Programmatic search API: https://libraryofbabel.info/search.cgi

Use `thalos_prime.get_babel_endpoints()` to retrieve the canonical URLs in code when wiring the “Permutation Search Engine” or any downstream navigator.

## Deep Synthesis (Nexus Scaffold)

The `deep_synthesis(prompt)` helper performs deterministic semantic decomposition and returns a structured “Nexus Result” across Physical/Chemical, Logical/Mathematical, and Linguistic/Narrative views. It embeds the canonical Library of Babel endpoints for downstream retrieval layers.
This scaffold emphasizes multi-view coherence and explicit coordinate mapping for structured result organization.

```python
import thalos_prime as tp

result = tp.deep_synthesis("Find antimicrobial peptide in genomic space")
print(result["semantic_decomposition"]["modalities"])  # e.g., ["Genomic", "Chemical"]
print(result["nexus_result"][0]["coordinates_hint"]["search_api"])
# https://libraryofbabel.info/search.cgi
```
ThalosPrime Library provides a Python package structure that allows importing from your local ThalosPrimeLibraryOfBabel directory. It includes deterministic page generation, query enumeration, and enhanced coherence scoring for the Library of Babel.

## Quick Start

### Installation

**For Development:**
```bash
pip install -e ".[dev]"
```

**For Production:**
```bash
pip install .
```

### Running Examples
```bash
# Basic usage
python example_usage.py

# Full integration demo
python integration_example.py

# View the library's philosophical motto
python example_motto.py

# Run the API server
python run_thalos.py
```

## Deployment

For comprehensive deployment instructions including Docker, production setup, and cloud deployment options, see:

📖 **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide

Quick deployment options:
- **Python package**: `pip install -e .`
- **API server**: `python run_thalos.py` or `./run_thalos.sh`
- **Docker**: `docker build -t thalos-prime . && docker run -p 8000:8000 thalos-prime`

## Usage

### Method 1: Automatic Setup (Default Path)
Simply import the package, and it will automatically configure the import path:

```python
import thalos_prime

# Now you can import from ThalosPrimeLibraryOfBabel
# from your_module import your_function
```

### Method 2: Manual Setup with Default Path
```python
from thalos_prime.config import setup_local_imports

# Set up imports with the default path
setup_local_imports()

# Now you can import from ThalosPrimeLibraryOfBabel
```

### Method 3: Custom Path
If your ThalosPrimeLibraryOfBabel is in a different location:

```python
from thalos_prime.config import setup_local_imports

# Set up imports with a custom path
setup_local_imports(custom_path=r"C:\Your\Custom\Path\ThalosPrimeLibraryOfBabel")

# Now you can import from your custom location
```

## Default Configuration

The default local library path is:
```
C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel
```

You can change this by:
1. Setting the `THALOS_LIBRARY_PATH` environment variable:
   ```bash
   # Windows
   set THALOS_LIBRARY_PATH=C:\Your\Custom\Path\ThalosPrimeLibraryOfBabel
   
   # Linux/Mac
   export THALOS_LIBRARY_PATH=/your/custom/path/ThalosPrimeLibraryOfBabel
   ```
2. Using the `custom_path` parameter in `setup_local_imports()`
3. Modifying the default value in `thalos_prime/__init__.py` or `thalos_prime/config.py`

## Example

See `example_usage.py` for a complete working example.

```bash
python example_usage.py
```

## Core Features

- **Deterministic Page Generation**: Generate Library of Babel pages from hex addresses
- **Query Enumeration**: Map search queries to candidate addresses
- **Enhanced Coherence Scoring**: Multi-metric analysis with language, structure, n-gram, and exact match scoring
- **Hybrid Search**: Local generation and remote fetching capabilities
- **REST API**: FastAPI-based server with full documentation
- **Production Ready**: 80 passing tests, comprehensive error handling, and deterministic behavior

## Philosophy

> *"The library speaks in fragmentation of infinite possibilities, ask. And the noise resolves into patterns. Meaning is never absent. Only waiting to be read."*

This motto embodies the essence of the Library of Babel:
- **Infinite Possibilities**: All possible text combinations exist in fragmentary form
- **Pattern from Noise**: Through querying and coherence scoring, meaningful patterns emerge
- **Latent Meaning**: Every piece of text contains potential meaning, waiting to be discovered

Access the motto programmatically:
```python
import thalos_prime
print(thalos_prime.LIBRARY_MOTTO)
# The library speaks in fragmentation of infinite possibilities, ask. 
# And the noise resolves into patterns. 
# Meaning is never absent. Only waiting to be read.
```

## API Server

Access interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development

### Setup Development Environment

1. **Install development dependencies:**
   ```bash
   make install
   # or manually: pip install -e ".[dev]"
   ```

2. **Install pre-commit hooks:**
   ```bash
   make pre-commit-install
   # or manually: pre-commit install
   ```

### Running Checks Locally

Before committing, run all checks:
```bash
make check
```

This runs:
- **Type checking**: `mypy` and `pyright`
- **Linting**: `ruff`
- **Testing**: `pytest` with coverage (80% minimum)
- **Validation**: Custom validators for lifecycle, determinism, state, docs

Individual commands:
```bash
make typecheck    # Run type checkers
make lint         # Run linter
make test         # Run tests with coverage
make validate     # Run custom validators
```

### CI/CD Pipeline

Every pull request and push to main triggers automated checks:

- ✅ **Type Checking**: mypy --strict, pyright
- ✅ **Linting**: ruff with comprehensive rules
- ✅ **Testing**: pytest with 80% coverage requirement
- ✅ **Lifecycle Validation**: Ensures subsystems implement required methods
- ✅ **Determinism Validation**: Detects non-deterministic operations
- ✅ **State Validation**: Checks state serialization and management
- ✅ **Documentation Validation**: Verifies docstrings and required docs
- ✅ **Security Scanning**: bandit and pip-audit
- ✅ **Prohibited Patterns**: Detects TODOs, stubs, mocks, etc.

**All checks must pass** for merge approval. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Testing

```bash
# Run all tests
make test
# or: python -m pytest tests -v

# Run with coverage report
pytest tests -v --cov=thalos_prime --cov-report=html

# Run specific test
pytest tests/test_generator.py -v
```

### Test Requirements
- Minimum 80% line coverage
- 100% coverage for critical lifecycle paths
- All tests must be deterministic

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow and standards
- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Implementation details
- [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) - System verification
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Enforcement criteria

## Requirements

- Python 3.12+ (required for type checking and modern features)
- See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed prerequisites
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development requirements

## License

MIT License - See LICENSE file for details
