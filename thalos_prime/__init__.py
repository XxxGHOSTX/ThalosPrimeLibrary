"""
ThalosPrime Library - Main Package

This package provides:
- Deterministic page generation (lob_babel_generator)
- Query to address enumeration (lob_babel_enumerator)
- Enhanced coherence scoring (lob_decoder)
- Configuration and import management (config)
"""

from typing import Dict

__version__ = "0.1.0"
__author__ = "ThalosPrime"

# Philosophical motto
LIBRARY_MOTTO = (
    "The library speaks In fragmentation of infinite possibilities, ask. "
    "And the noice turns resolves into patterns. Meaning is never absent. "
    "Only waiting to be read."
)

# Library of Babel endpoints
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


def get_babel_endpoints() -> Dict[str, str]:
    """Return the canonical Library of Babel endpoints used by Thalos Prime."""
    return {
        "base": LIBRARY_OF_BABEL_BASE_URL,
        "search_html": LIBRARY_OF_BABEL_SEARCH_URL,
        "search_api": LIBRARY_OF_BABEL_SEARCH_API,
    }

# Re-export synthesis helpers
from .synthesis import deep_synthesis  # noqa: E402,F401
# Export main components for easy access
from thalos_prime.lob_babel_generator import (
    BabelGenerator,
    address_to_page,
    text_to_address,
    normalize_text
)

from thalos_prime.lob_babel_enumerator import (
    BabelEnumerator,
    enumerate_addresses,
    query_to_addresses
)

from thalos_prime.lob_decoder import (
    BabelDecoder,
    CoherenceScore,
    DecodedPage,
    score_coherence,
    decode_page
)

__all__ = [
    # Version info
    '__version__',
    '__author__',
    'LIBRARY_MOTTO',
    'LOCAL_LIBRARY_PATH',
    
    # Library of Babel endpoints
    'LIBRARY_OF_BABEL_BASE_URL',
    'LIBRARY_OF_BABEL_SEARCH_URL',
    'LIBRARY_OF_BABEL_SEARCH_API',
    'get_babel_endpoints',
    
    # Generator
    'BabelGenerator',
    'address_to_page',
    'text_to_address',
    'normalize_text',
    
    # Enumerator
    'BabelEnumerator',
    'enumerate_addresses',
    'query_to_addresses',
    
    # Decoder
    'BabelDecoder',
    'CoherenceScore',
    'DecodedPage',
    'score_coherence',
    'decode_page',
    
    # Synthesis
    'deep_synthesis',
]
