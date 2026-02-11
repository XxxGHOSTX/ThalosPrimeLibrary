"""
Tests for the configuration module
"""

import sys
import os
import pytest
from pathlib import Path
from thalos_prime.config import LibraryConfig, get_config, setup_local_imports


def test_library_config_default_path(monkeypatch):
    """Test that LibraryConfig has the correct default path"""
    # Clear the environment variable to test the actual default
    monkeypatch.delenv('THALOS_LIBRARY_PATH', raising=False)
    
    # Import fresh to get the default without env var
    from importlib import reload
    import thalos_prime.config as config_module
    reload(config_module)
    
    config = config_module.LibraryConfig()
    expected_path = r"C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel"
    assert config.get_local_library_path() == expected_path


def test_library_config_with_env_var(monkeypatch):
    """Test that LibraryConfig respects the environment variable"""
    custom_path = "/custom/env/path"
    monkeypatch.setenv('THALOS_LIBRARY_PATH', custom_path)
    
    # Import fresh to get the value from env var
    from importlib import reload
    import thalos_prime.config as config_module
    reload(config_module)
    
    config = config_module.LibraryConfig()
    assert config.get_local_library_path() == custom_path


def test_library_config_custom_path():
    """Test that LibraryConfig accepts a custom path"""
    custom_path = r"C:\Custom\Path"
    config = LibraryConfig(local_library_path=custom_path)
    assert config.get_local_library_path() == custom_path


def test_library_config_set_path():
    """Test that LibraryConfig can change paths"""
    config = LibraryConfig()
    new_path = r"C:\New\Path"
    config.set_local_library_path(new_path)
    assert config.get_local_library_path() == new_path


def test_get_config_singleton():
    """Test that get_config returns the same instance"""
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2


def test_setup_imports_nonexistent_path():
    """Test that setup_imports handles nonexistent paths gracefully"""
    # Use a path that definitely doesn't exist
    result = setup_local_imports(custom_path="/nonexistent/path/12345")
    # Should return False for nonexistent path but not crash
    assert result is False


def test_setup_imports_with_temp_directory(tmp_path):
    """Test that setup_imports successfully adds an existing path"""
    # Create a temporary directory that exists
    test_path = str(tmp_path)
    
    # Get the initial sys.path length
    initial_path_count = len(sys.path)
    
    # Set up imports with the temporary path
    result = setup_local_imports(custom_path=test_path)
    
    # Should return True and add the path to sys.path
    assert result is True
    assert test_path in sys.path or str(Path(test_path).resolve()) in sys.path


def test_library_config_added_to_path_flag():
    """Test that the _added_to_path flag works correctly"""
    config = LibraryConfig()
    assert config._added_to_path is False
    
    # After changing path, flag should reset
    config.set_local_library_path("new_path")
    assert config._added_to_path is False
