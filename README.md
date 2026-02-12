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
This scaffold is designed to be superior to standard AI outputs by enforcing multi-view coherence and explicit coordinate mapping.

```python
import thalos_prime as tp

result = tp.deep_synthesis("Find antimicrobial peptide in genomic space")
print(result["semantic_decomposition"]["modalities"])  # e.g., ["Genomic", "Chemical"]
print(result["nexus_result"][0]["coordinates_hint"]["search_api"])
# https://libraryofbabel.info/search.cgi
```

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

## Requirements

- Python 3.7+

## License

MIT License - See LICENSE file for details
