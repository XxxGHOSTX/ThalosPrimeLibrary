"""Tests for validation tools.

Tests the validators to ensure they correctly detect violations.
"""

import tempfile
from pathlib import Path


def test_lifecycle_validator_detects_missing_methods() -> None:
    """Test that lifecycle validator detects missing lifecycle methods."""
    from tools.validate_lifecycle import validate_file

    # Create a test file with a subsystem class missing lifecycle methods
    test_code = '''
class TestManager:
    """A test manager class."""

    def some_method(self):
        """Some method."""
        pass
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        errors, count = validate_file(test_file)
        assert count == 1, "Should detect one subsystem class"
        assert len(errors) > 0, "Should detect missing lifecycle methods"
        assert "Missing lifecycle methods" in errors[0]
    finally:
        test_file.unlink()


def test_lifecycle_validator_detects_methods_without_return_types() -> None:
    """Test that lifecycle validator detects methods without return type annotations."""
    from tools.validate_lifecycle import validate_file

    test_code = '''
class ConfigManager:
    """A config manager."""

    def initialize(self):
        """Initialize without return type."""
        pass
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        errors, count = validate_file(test_file)
        assert count == 1
        assert any("without return type annotation" in err for err in errors)
    finally:
        test_file.unlink()


def test_prohibited_patterns_detector_finds_todos() -> None:
    """Test that prohibited patterns detector finds TODO comments."""
    from tools.detect_prohibited_patterns import check_file_content

    test_code = '''
def some_function():
    # TODO: implement this later
    pass
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        issues = check_file_content(test_file)
        assert len(issues) > 0
        assert any("TODO" in issue for issue in issues)
    finally:
        test_file.unlink()


def test_prohibited_patterns_detector_finds_catch_all_exceptions() -> None:
    """Test that prohibited patterns detector finds catch-all exceptions."""
    from tools.detect_prohibited_patterns import validate_file

    test_code = '''
def some_function() -> None:
    try:
        x = 1 / 0
    except Exception:
        pass
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        issues = validate_file(test_file)
        assert len(issues) > 0
        assert any("Catch-all" in issue for issue in issues)
    finally:
        test_file.unlink()


def test_determinism_validator_detects_random_without_seed() -> None:
    """Test that determinism validator detects random operations without seed."""
    from tools.validate_determinism import validate_file

    test_code = '''
import random

def generate_value():
    return random.random()
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        issues = validate_file(test_file)
        assert len(issues) > 0
        assert any("Random operation without seed" in issue for issue in issues)
    finally:
        test_file.unlink()


def test_determinism_validator_detects_uuid4() -> None:
    """Test that determinism validator detects uuid4 generation."""
    from tools.validate_determinism import validate_file

    test_code = '''
import uuid

def generate_id():
    return uuid.uuid4()
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        issues = validate_file(test_file)
        assert len(issues) > 0
        assert any("UUID4 generation" in issue for issue in issues)
    finally:
        test_file.unlink()


def test_docs_validator_detects_missing_module_docstring() -> None:
    """Test that docs validator detects missing module docstring."""
    from tools.validate_docs import validate_file

    test_code = '''
def some_function():
    """A function."""
    pass
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        issues = validate_file(test_file)
        assert len(issues) > 0
        assert any("Module lacks docstring" in issue for issue in issues)
    finally:
        test_file.unlink()


def test_docs_validator_detects_missing_function_docstring() -> None:
    """Test that docs validator detects missing function docstring."""
    from tools.validate_docs import validate_file

    test_code = '''
"""Module docstring."""

def public_function():
    pass
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        issues = validate_file(test_file)
        assert len(issues) > 0
        assert any("lacks docstring" in issue for issue in issues)
    finally:
        test_file.unlink()


def test_state_validator_detects_missing_serialization() -> None:
    """Test that state validator detects state classes without serialization."""
    from tools.validate_state import validate_file

    test_code = '''
"""Module docstring."""

class ApplicationState:
    """Application state."""

    def __init__(self):
        self.data = {}
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()
        test_file = Path(f.name)

    try:
        issues = validate_file(test_file)
        assert len(issues) > 0
        assert any("lacks serialization method" in issue for issue in issues)
    finally:
        test_file.unlink()
