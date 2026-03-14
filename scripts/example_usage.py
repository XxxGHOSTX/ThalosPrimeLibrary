"""
Example usage of ThalosPrime Library with local imports
"""

# Method 1: Automatic setup via package import
import thalos_prime

# Method 2: Manual setup with default path
from thalos_prime.config import setup_local_imports
setup_local_imports()

# Method 3: Manual setup with custom path
# from thalos_prime.config import setup_local_imports
# setup_local_imports(custom_path=r"C:\Custom\Path\To\Library")

# Now you can import from the local ThalosPrimeLibraryOfBabel
# For example:
# from some_module_in_babel import some_function
# some_function()

print("ThalosPrime Library initialized successfully!")
print(f"Version: {thalos_prime.__version__}")

# Show the configuration
from thalos_prime.config import get_config
config = get_config()
print(f"Local library path: {config.get_local_library_path()}")
