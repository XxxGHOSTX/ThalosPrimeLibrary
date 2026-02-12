"""
ThalosPrime Library - Main Package
"""

__version__ = "0.1.0"
__author__ = "ThalosPrime"
LIBRARY_OF_BABEL_BASE_URL = "https://libraryofbabel.info"
LIBRARY_OF_BABEL_SEARCH_URL = f"{LIBRARY_OF_BABEL_BASE_URL}/search.html"
LIBRARY_OF_BABEL_SEARCH_API = f"{LIBRARY_OF_BABEL_BASE_URL}/search.cgi"

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


def get_babel_endpoints():
    """Return the canonical Library of Babel endpoints used by Thalos Prime."""
    return {
        "base": LIBRARY_OF_BABEL_BASE_URL,
        "search_html": LIBRARY_OF_BABEL_SEARCH_URL,
        "search_api": LIBRARY_OF_BABEL_SEARCH_API,
    }

# Re-export synthesis helpers
from .synthesis import deep_synthesis  # noqa: E402,F401
