"""Library of Sense - Code Generator.

Generates Python code templates and function stubs from specifications
using ast introspection and structured code building.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from thalos_prime.library_of_sense.code_generation.validator import CodeValidator

if TYPE_CHECKING:
    from thalos_prime.library_of_sense.core.interfaces import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class FunctionSpec:
    """Specification for generating a Python function."""

    name: str
    params: list[str] = field(default_factory=list)
    return_type: str = "None"
    docstring: str = ""
    body: str = "pass"
    is_method: bool = True

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this function specification.

        """
        return {
            "name": self.name,
            "params": list(self.params),
            "return_type": self.return_type,
            "docstring": self.docstring,
            "body": self.body,
            "is_method": self.is_method,
        }


class CodeGenerator:
    """Generates Python function templates from FunctionSpec descriptions.

    Uses ast to verify generated code and CodeValidator for structural checks.
    """

    def __init__(self) -> None:
        """Initialize the code generator with a validator."""
        self._validator = CodeValidator()

    def generate_function(self, spec: FunctionSpec) -> str:
        """Generate a Python function definition from a FunctionSpec.

        Args:
            spec: FunctionSpec describing the function to generate.

        Returns:
            Python source code string for the function.

        """
        params_str = ", ".join(spec.params) if spec.params else ""
        if spec.is_method:
            params_str = f"self, {params_str}" if params_str else "self"

        lines: list[str] = [
            f"def {spec.name}({params_str}) -> {spec.return_type}:",
        ]

        if spec.docstring:
            lines.append(f'    """{spec.docstring}"""')

        body_lines = spec.body.strip().splitlines()
        lines.extend(f"    {line}" for line in body_lines)

        return "\n".join(lines)

    def generate_class(
        self,
        class_name: str,
        docstring: str,
        methods: list[FunctionSpec],
    ) -> str:
        """Generate a Python class definition with specified methods.

        Args:
            class_name: Name for the generated class.
            docstring: Class-level docstring.
            methods: List of FunctionSpec for methods to generate.

        Returns:
            Python source code string for the class.

        """
        lines: list[str] = [
            f"class {class_name}:",
            f'    """{docstring}"""',
            "",
        ]
        for spec in methods:
            method_src = self.generate_function(spec)
            lines.extend(f"    {line}" for line in method_src.splitlines())
            lines.append("")

        return "\n".join(lines)

    def validate_generated(self, source: str) -> ValidationResult:
        """Validate generated source code for syntax correctness.

        Args:
            source: Generated Python source code string.

        Returns:
            ValidationResult from syntax validation.

        """
        return self._validator.validate_syntax(source)

    def parse_and_describe(self, source: str) -> list[str]:
        """Parse Python source and return descriptions of top-level entities.

        Args:
            source: Python source code string.

        Returns:
            List of description strings for top-level classes and functions.

        """
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return [f"Parse error: {exc}"]

        descriptions: list[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                doc = ast.get_docstring(node) or "(no docstring)"
                descriptions.append(f"function {node.name}: {doc[:60]}")
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or "(no docstring)"
                descriptions.append(f"class {node.name}: {doc[:60]}")
        return descriptions


__all__ = ["CodeGenerator", "FunctionSpec"]
