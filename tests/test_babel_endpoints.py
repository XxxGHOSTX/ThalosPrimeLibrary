"""
Tests for Library of Babel endpoint helpers
"""

import thalos_prime


def test_babel_endpoint_constants() -> None:
    """Verify Library of Babel endpoint constants"""
    assert thalos_prime.LIBRARY_OF_BABEL_BASE_URL == "https://libraryofbabel.info"
    assert thalos_prime.LIBRARY_OF_BABEL_SEARCH_URL == "https://libraryofbabel.info/search.html"
    assert thalos_prime.LIBRARY_OF_BABEL_SEARCH_API == "https://libraryofbabel.info/search.cgi"


def test_get_babel_endpoints() -> None:
    """Verify get_babel_endpoints returns expected mapping"""
    endpoints = thalos_prime.get_babel_endpoints()
    assert endpoints["base"] == thalos_prime.LIBRARY_OF_BABEL_BASE_URL
    assert endpoints["search_html"] == thalos_prime.LIBRARY_OF_BABEL_SEARCH_URL
    assert endpoints["search_api"] == thalos_prime.LIBRARY_OF_BABEL_SEARCH_API
