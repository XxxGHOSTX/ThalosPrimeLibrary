"""
Tests for the main package
"""

from typing import Any
import os
import pytest
import thalos_prime


def test_package_version() -> None:
    """Test that the package has a version"""
    assert hasattr(thalos_prime, '__version__')
    assert thalos_prime.__version__ == "0.1.0"


def test_package_author() -> None:
    """Test that the package has an author"""
    assert hasattr(thalos_prime, '__author__')
    assert thalos_prime.__author__ == "ThalosPrime"


def test_library_of_babel_base_url() -> None:
    """Ensure the canonical Library of Babel domain is correct"""
    assert hasattr(thalos_prime, 'LIBRARY_OF_BABEL_BASE_URL')
    assert thalos_prime.LIBRARY_OF_BABEL_BASE_URL == "https://libraryofbabel.info"


def test_library_of_babel_search_url() -> None:
    """Ensure the structured search endpoint is exposed"""
    assert hasattr(thalos_prime, 'LIBRARY_OF_BABEL_SEARCH_URL')
    assert thalos_prime.LIBRARY_OF_BABEL_SEARCH_URL == "https://libraryofbabel.info/search.html"


def test_library_of_babel_search_api() -> None:
    """Ensure the programmatic search endpoint is exposed"""
    assert hasattr(thalos_prime, 'LIBRARY_OF_BABEL_SEARCH_API')
    assert thalos_prime.LIBRARY_OF_BABEL_SEARCH_API == "https://libraryofbabel.info/search.cgi"


def test_get_babel_endpoints() -> None:
    """Ensure endpoint helper returns all canonical URLs"""
    endpoints = thalos_prime.get_babel_endpoints()
    assert endpoints["base"] == "https://libraryofbabel.info"
    assert endpoints["search_html"] == "https://libraryofbabel.info/search.html"
    assert endpoints["search_api"] == "https://libraryofbabel.info/search.cgi"


def test_deep_synthesis_structure() -> None:
    """Deep synthesis returns semantic decomposition and nexus views"""
    result = thalos_prime.deep_synthesis("Find antimicrobial peptide in genomic space")
    assert "semantic_decomposition" in result
    assert "nexus_result" in result
    assert any("Genomic" in m for m in result["semantic_decomposition"]["modalities"])
    views = {block["view"] for block in result["nexus_result"]}
    assert views == {"Physical/Chemical", "Logical/Mathematical", "Linguistic/Narrative"}
    coordinates = result["nexus_result"][0]["coordinates_hint"]
    assert coordinates["search_api"] == "https://libraryofbabel.info/search.cgi"


def test_package_local_library_path(monkeypatch: Any) -> None:
    """Test that the package defines LOCAL_LIBRARY_PATH"""
    # Clear any environment variable to test the default
    monkeypatch.delenv('THALOS_LIBRARY_PATH', raising=False)
    
    # Import fresh to get the default
    from importlib import reload
    reload(thalos_prime)
    
    assert hasattr(thalos_prime, 'LOCAL_LIBRARY_PATH')
    expected_path = r"C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel"
    assert thalos_prime.LOCAL_LIBRARY_PATH == expected_path


def test_package_local_library_path_with_env_var(monkeypatch: Any) -> None:
    """Test that the package respects THALOS_LIBRARY_PATH environment variable"""
    custom_path = "/custom/env/path"
    monkeypatch.setenv('THALOS_LIBRARY_PATH', custom_path)
    
    # Import fresh to get the value from env var
    from importlib import reload
    reload(thalos_prime)
    
    assert thalos_prime.LOCAL_LIBRARY_PATH == custom_path
