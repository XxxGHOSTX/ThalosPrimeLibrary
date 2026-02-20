"""Tests for Library of Sense code generation components."""

from __future__ import annotations

from thalos_prime.library_of_sense.code_generation.validator import CodeValidator
from thalos_prime.library_of_sense.code_generation.generator import FunctionSpec, CodeGenerator
from thalos_prime.library_of_sense.code_generation.executor import CodeExecutor


# ---------------------------------------------------------------------------
# CodeValidator
# ---------------------------------------------------------------------------


class TestCodeValidator:
    def test_validate_syntax_valid(self) -> None:
        validator = CodeValidator()
        result = validator.validate_syntax("x = 1 + 2\n")
        assert result.valid is True

    def test_validate_syntax_invalid(self) -> None:
        validator = CodeValidator()
        result = validator.validate_syntax("def broken(:\n")
        assert result.valid is False

    def test_validate_has_docstrings_present(self) -> None:
        validator = CodeValidator()
        source = '''
def greet():
    """Say hello."""
    pass
'''
        result = validator.validate_has_docstrings(source)
        assert result.valid is True

    def test_validate_has_docstrings_missing(self) -> None:
        validator = CodeValidator()
        source = "def greet():\n    pass\n"
        result = validator.validate_has_docstrings(source)
        assert result.valid is False

    def test_count_functions(self) -> None:
        validator = CodeValidator()
        source = "def a(): pass\ndef b(): pass\n"
        assert validator.count_functions(source) == 2

    def test_count_functions_empty(self) -> None:
        validator = CodeValidator()
        assert validator.count_functions("x = 1\n") == 0


# ---------------------------------------------------------------------------
# CodeGenerator
# ---------------------------------------------------------------------------


class TestCodeGenerator:
    def test_generate_function_basic(self) -> None:
        gen = CodeGenerator()
        spec = FunctionSpec(name="add", params=["a", "b"], return_type="int", docstring="Add.")
        source = gen.generate_function(spec)
        assert "def add" in source
        assert "Add." in source

    def test_generate_class(self) -> None:
        gen = CodeGenerator()
        methods = [FunctionSpec(name="run", docstring="Run it.")]
        source = gen.generate_class("MyClass", "A class.", methods)
        assert "class MyClass" in source
        assert "def run" in source

    def test_validate_generated_valid(self) -> None:
        gen = CodeGenerator()
        spec = FunctionSpec(name="hello", docstring="Hello.")
        source = gen.generate_function(spec)
        result = gen.validate_generated(source)
        assert result.valid is True

    def test_parse_and_describe(self) -> None:
        gen = CodeGenerator()
        source = '''
def my_func():
    """Does something."""
    pass
'''
        descriptions = gen.parse_and_describe(source)
        assert any("my_func" in d for d in descriptions)


# ---------------------------------------------------------------------------
# CodeExecutor
# ---------------------------------------------------------------------------


class TestCodeExecutor:
    def test_execute_success(self) -> None:
        executor = CodeExecutor(timeout=5.0)
        result = executor.execute('print("hello")\n')
        assert result.success is True
        assert "hello" in result.stdout

    def test_execute_return_code_nonzero(self) -> None:
        executor = CodeExecutor(timeout=5.0)
        result = executor.execute("import sys; sys.exit(1)\n")
        assert result.return_code != 0
        assert result.success is False

    def test_execute_timeout(self) -> None:
        executor = CodeExecutor(timeout=0.1)
        result = executor.execute("import time; time.sleep(10)\n")
        assert result.timed_out is True
        assert result.success is False
