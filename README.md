# ThalosPrimeLibrary
The brain

## Overview
ThalosPrime Library provides a Python package structure that allows importing from your local ThalosPrimeLibraryOfBabel directory.

## Installation

### For Development
```bash
pip install -e .
```

### For Production
```bash
pip install .
```

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
1. Using the `custom_path` parameter in `setup_local_imports()`
2. Modifying the `DEFAULT_LOCAL_LIBRARY_PATH` in `thalos_prime/config.py`

## Example

See `example_usage.py` for a complete working example.

```bash
python example_usage.py
```

## Requirements

- Python 3.7+

## License

MIT License - See LICENSE file for details
