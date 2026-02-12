"""
ThalosPrime Library - Main Package
"""

__version__ = "0.1.0"
__author__ = "ThalosPrime"

# This allows importing from the local ThalosPrimeLibraryOfBabel
import sys
import os

# Get the local library path from environment variable or use default
# Users can set THALOS_LIBRARY_PATH environment variable to customize
LOCAL_LIBRARY_PATH = os.getenv(
    'THALOS_LIBRARY_PATH',
    r"C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel"
)

# Add to path if the directory exists and is not already in sys.path
if os.path.exists(LOCAL_LIBRARY_PATH) and LOCAL_LIBRARY_PATH not in sys.path:
    sys.path.insert(0, LOCAL_LIBRARY_PATH)
