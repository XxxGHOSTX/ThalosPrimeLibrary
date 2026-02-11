"""
Tests for the main package
"""

import thalos_prime


def test_package_version():
    """Test that the package has a version"""
    assert hasattr(thalos_prime, '__version__')
    assert thalos_prime.__version__ == "0.1.0"


def test_package_author():
    """Test that the package has an author"""
    assert hasattr(thalos_prime, '__author__')
    assert thalos_prime.__author__ == "ThalosPrime"


def test_package_local_library_path():
    """Test that the package defines LOCAL_LIBRARY_PATH"""
    assert hasattr(thalos_prime, 'LOCAL_LIBRARY_PATH')
    expected_path = r"C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel"
    assert thalos_prime.LOCAL_LIBRARY_PATH == expected_path
