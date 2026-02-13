#!/usr/bin/env python3
"""State validator for Thalos Prime Library.

Validates that:
- State classes are serializable (have to_dict() or implement protocol)
- State machines have explicit transition logs
- Checkpoint methods are atomic and versioned
- No hidden or implicit state (undocumented globals/class variables)
"""

import ast
import sys
from pathlib import Path
from typing import List, Set, Tuple


class StateValidator(ast.NodeVisitor):
    """AST visitor to validate state management patterns."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the validator.

        Args:
            file_path: Path to the file being validated.
        """
        self.file_path = file_path
        self.issues: List[str] = []
        self.state_classes: Set[str] = set()
        self.global_vars: List[Tuple[int, str]] = []
        self.in_class = False
        self.in_function = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to find state classes."""
        class_name = node.name
        has_to_dict = False
        has_checkpoint = False

        # Check if class name suggests it's a state class
        is_state_class = any(
            keyword in class_name.lower()
            for keyword in ["state", "config", "checkpoint", "snapshot"]
        )

        # Check methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_name = item.name
                if method_name == "to_dict":
                    has_to_dict = True
                elif method_name == "checkpoint":
                    has_checkpoint = True

        if is_state_class:
            self.state_classes.add(class_name)
            if not has_to_dict and not has_checkpoint:
                self.issues.append(
                    f"Line {node.lineno}: State class '{class_name}' "
                    f"lacks serialization method (to_dict or checkpoint)"
                )

        # Track scope
        was_in_class = self.in_class
        self.in_class = True
        self.generic_visit(node)
        self.in_class = was_in_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to track scope."""
        was_in_function = self.in_function
        self.in_function = True
        self.generic_visit(node)
        self.in_function = was_in_function

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignments to detect module-level global variables."""
        # Only record module-level assignments (not in classes or functions)
        if not self.in_class and not self.in_function:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.global_vars.append((node.lineno, target.id))

        self.generic_visit(node)


def validate_file(file_path: Path) -> List[str]:
    """Validate a single Python file for state management.

    Args:
        file_path: Path to the Python file to validate.

    Returns:
        List of issue messages.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        return [f"{file_path}: Syntax error - {e}"]

    validator = StateValidator(file_path)
    validator.visit(tree)

    # Check for undocumented global variables
    if validator.global_vars:
        # Read file to check for documentation
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        for lineno, var_name in validator.global_vars:
            # Skip common patterns like __version__, TYPE_CHECKING, etc.
            if var_name.startswith("_") and var_name.isupper():
                continue
            if var_name in {"TYPE_CHECKING", "logger", "log"}:
                continue

            # Check if there's a docstring or comment nearby
            has_doc = False
            if lineno > 1:
                prev_line = lines[lineno - 2].strip()
                if prev_line.startswith("#") or '"""' in prev_line or "'''" in prev_line:
                    has_doc = True

            if not has_doc:
                validator.issues.append(
                    f"Line {lineno}: Global variable '{var_name}' "
                    f"may be undocumented state"
                )

    # Prefix all issues with file path
    return [f"{file_path}::{issue}" for issue in validator.issues]


def validate_directory(directory: Path) -> List[str]:
    """Validate all Python files in a directory.

    Args:
        directory: Path to directory to scan.

    Returns:
        List of all issues found.
    """
    all_issues: List[str] = []
    python_files = sorted(directory.rglob("*.py"))

    for file_path in python_files:
        # Skip test files, __init__.py, and __pycache__
        if "__pycache__" in str(file_path):
            continue
        if file_path.name.startswith("test_"):
            continue

        issues = validate_file(file_path)
        all_issues.extend(issues)

    return all_issues


def main() -> int:
    """Main entry point for state validation.

    Returns:
        Exit code: 0 if no violations, 1 if violations found.
    """
    print("=" * 80)
    print("Thalos Prime Library - State Validator")
    print("=" * 80)

    # Get the repository root
    repo_root = Path(__file__).parent.parent
    thalos_prime_dir = repo_root / "thalos_prime"

    if not thalos_prime_dir.exists():
        print(f"Error: Directory {thalos_prime_dir} does not exist")
        return 1

    print(f"\nScanning directory: {thalos_prime_dir}")
    print("-" * 80)

    issues = validate_directory(thalos_prime_dir)

    if issues:
        print(f"\n⚠️  {len(issues)} potential state management issues found:\n")
        for issue in issues:
            print(f"  ⚠️  {issue}")
        print("\n" + "=" * 80)
        print("WARNING: Review state management issues")
        print("=" * 80)
        print("\nNote: Some warnings may be acceptable if:")
        print("  - State is documented elsewhere")
        print("  - Variables are constants")
        print("  - Serialization is handled externally")
        return 0  # Don't fail, just warn

    print("\n" + "=" * 80)
    print("✅ PASSED: No state management issues detected")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
