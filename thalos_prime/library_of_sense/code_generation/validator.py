"""Library of Sense - Code Validator.

Validates Python code syntax and structure using the ast module,
checking for syntax errors and structural compliance.
"""

from __future__ import annotations

import ast
import logging

from thalos_prime.library_of_sense.core.interfaces import ValidationResult

logger = logging.getLogger(__name__)


class CodeValidator:
    """Validates Python source code for syntax correctness and basic structural compliance."""

    def validate_syntax(self, source: str) -> ValidationResult:
        """Validate Python syntax by attempting to parse with ast.

        Args:
            source: Python source code string.

        Returns:
            ValidationResult with parse result.

        """
        try:
            ast.parse(source)
        except SyntaxError as exc:
            return ValidationResult(
                valid=False,
                message=f"Syntax error at line {exc.lineno}: {exc.msg}",
                details={"line": str(exc.lineno), "offset": str(exc.offset)},
            )
        return ValidationResult(valid=True, message="Syntax valid")

    def validate_has_docstrings(self, source: str) -> ValidationResult:
        """Check that all top-level public functions and classes have docstrings.

        Args:
            source: Python source code string.

        Returns:
            ValidationResult indicating docstring compliance.

        """
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return ValidationResult(
                valid=False,
                message=f"Cannot parse for docstring check: {exc}",
            )

        missing: list[str] = [
            f"{type(node).__name__} '{node.name}' at line {node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            and not node.name.startswith("_")
            and not ast.get_docstring(node)
        ]

        if missing:
            return ValidationResult(
                valid=False,
                message=f"Missing docstrings: {', '.join(missing)}",
                details={"missing": str(missing)},
            )
        return ValidationResult(valid=True, message="All public symbols have docstrings")

    def count_functions(self, source: str) -> int:
        """Count the number of function definitions in source code.

        Args:
            source: Python source code string.

        Returns:
            Number of function definitions found.

        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return 0
        return sum(
            1 for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )


__all__ = ["CodeValidator"]
