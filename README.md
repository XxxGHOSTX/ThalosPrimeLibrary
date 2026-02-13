# ThalosPrimeLibrary
The brain

## Overview
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

## API Server

Access interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
python -m pytest tests -v

# Run with coverage
python -m pytest tests --cov=thalos_prime
```

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Implementation details
- [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) - System verification

## Requirements

- Python 3.7+ (3.11+ recommended)
- See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed prerequisites

## License

MIT License - See LICENSE file for details
