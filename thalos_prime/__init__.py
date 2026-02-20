"""ThalosPrime Library - Main Package.

This package provides:
- Deterministic page generation (lob_babel_generator)
- Query to address enumeration (lob_babel_enumerator)
- Enhanced coherence scoring (lob_decoder)
- Configuration and import management (config)
"""

__version__ = "0.1.0"
__author__ = "ThalosPrime"

# Library of Babel endpoints
LIBRARY_OF_BABEL_BASE_URL = "https://libraryofbabel.info"
LIBRARY_OF_BABEL_SEARCH_URL = f"{LIBRARY_OF_BABEL_BASE_URL}/search.html"
LIBRARY_OF_BABEL_SEARCH_API = f"{LIBRARY_OF_BABEL_BASE_URL}/search.cgi"

# This allows importing from the local ThalosPrimeLibraryOfBabel
import os
import sys

# Get the local library path from environment variable or use default
# Users can set THALOS_LIBRARY_PATH environment variable to customize
LOCAL_LIBRARY_PATH = os.getenv(
    "THALOS_LIBRARY_PATH",
    r"C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel",
)

# Add to path if the directory exists and is not already in sys.path
if os.path.exists(LOCAL_LIBRARY_PATH) and LOCAL_LIBRARY_PATH not in sys.path:
    sys.path.insert(0, LOCAL_LIBRARY_PATH)


def get_babel_endpoints() -> dict[str, str]:
    """Return the canonical Library of Babel endpoints used by Thalos Prime."""
    return {
        "base": LIBRARY_OF_BABEL_BASE_URL,
        "search_html": LIBRARY_OF_BABEL_SEARCH_URL,
        "search_api": LIBRARY_OF_BABEL_SEARCH_API,
    }

# Re-export synthesis helpers
from thalos_prime.lob_babel_enumerator import (
    BabelEnumerator,
    enumerate_addresses,
    query_to_addresses,
)

# Export main components for easy access
from thalos_prime.lob_babel_generator import (
    BabelGenerator,
    address_to_page,
    normalize_text,
    text_to_address,
)
from thalos_prime.lob_decoder import (
    BabelDecoder,
    CoherenceScore,
    DecodedPage,
    decode_page,
    score_coherence,
)

from .synthesis import deep_synthesis

__all__ = [
    # Library of Babel endpoints
    "LIBRARY_OF_BABEL_BASE_URL",
    "LIBRARY_OF_BABEL_SEARCH_API",
    "LIBRARY_OF_BABEL_SEARCH_URL",
    "LOCAL_LIBRARY_PATH",
    # Decoder
    "BabelDecoder",
    # Enumerator
    "BabelEnumerator",
    # Generator
    "BabelGenerator",
    "CoherenceScore",
    "DecodedPage",
    "__author__",
    # Version info
    "__version__",
    "address_to_page",
    "decode_page",
    # Synthesis
    "deep_synthesis",
    "enumerate_addresses",
    "get_babel_endpoints",
    "normalize_text",
    "query_to_addresses",
    "score_coherence",
    "text_to_address",
]
