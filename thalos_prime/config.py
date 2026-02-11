"""
Configuration for ThalosPrime Library
Manages paths and import configurations
"""

import os
import sys
import logging
import warnings
from pathlib import Path

# Set up logger for this module
logger = logging.getLogger(__name__)


class LibraryConfig:
    """Configuration class for managing library paths and imports"""
    
    # Default local library path (Windows) - can be overridden via THALOS_LIBRARY_PATH env var
    DEFAULT_LOCAL_LIBRARY_PATH = os.getenv(
        'THALOS_LIBRARY_PATH',
        r"C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel"
    )
    
    def __init__(self, local_library_path=None):
        """
        Initialize the library configuration
        
        Args:
            local_library_path: Optional custom path to the local library.
                               If not provided, uses the default path.
        """
        self.local_library_path = local_library_path or self.DEFAULT_LOCAL_LIBRARY_PATH
        self._added_to_path = False
    
    def setup_imports(self):
        """
        Set up the import paths to include the local library
        
        Returns:
            bool: True if the path was added successfully, False otherwise
        """
        if self._added_to_path:
            return True
        
        # Convert to Path object for better path handling
        lib_path = Path(self.local_library_path)
        
        # Check if path exists
        if not lib_path.exists():
            warnings.warn(
                f"Local library path does not exist: {lib_path}\n"
                f"You can set the THALOS_LIBRARY_PATH environment variable or "
                f"call setup_local_imports() with a custom path.",
                UserWarning,
                stacklevel=2
            )
            logger.warning("Local library path does not exist: %s", lib_path)
            return False
        
        # Add to sys.path if not already present
        lib_path_str = str(lib_path.resolve())
        if lib_path_str not in sys.path:
            sys.path.insert(0, lib_path_str)
            self._added_to_path = True
            logger.info("Added to Python path: %s", lib_path_str)
            return True
        
        self._added_to_path = True
        return True
    
    def get_local_library_path(self):
        """Get the configured local library path"""
        return self.local_library_path
    
    def set_local_library_path(self, path):
        """
        Set a new local library path
        
        Args:
            path: New path to the local library
        """
        self.local_library_path = path
        self._added_to_path = False


# Global configuration instance
_config = LibraryConfig()


def get_config():
    """Get the global configuration instance"""
    return _config


def setup_local_imports(custom_path=None):
    """
    Convenience function to set up local library imports
    
    Args:
        custom_path: Optional custom path to the local library
        
    Returns:
        bool: True if setup was successful
    """
    config = get_config()
    if custom_path:
        config.set_local_library_path(custom_path)
    return config.setup_imports()
