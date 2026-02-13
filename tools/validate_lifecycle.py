#!/usr/bin/env python3
"""Lifecycle validator for Thalos Prime Library.

Validates that all subsystem classes implement required lifecycle methods:
- initialize()
- validate()
- operate()
- reconcile()
- checkpoint()
- terminate()

All methods must have explicit type annotations.
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


REQUIRED_LIFECYCLE_METHODS: Set[str] = {
    "initialize",
    "validate",
    "operate",
    "reconcile",
    "checkpoint",
    "terminate",
}


class LifecycleValidator(ast.NodeVisitor):
    """AST visitor to validate lifecycle methods in classes."""

    def __init__(self) -> None:
        """Initialize the validator."""
        self.classes: Dict[str, Dict[str, bool | None]] = {}
        self.current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition and check for lifecycle methods."""
        self.current_class = node.name
        self.classes[node.name] = {method: None for method in REQUIRED_LIFECYCLE_METHODS}

        # Check methods in this class
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_name = item.name
                if method_name in REQUIRED_LIFECYCLE_METHODS:
                    # Check if method has return type annotation
                    has_return_annotation = item.returns is not None
                    self.classes[node.name][method_name] = has_return_annotation

        self.generic_visit(node)
        self.current_class = None


def is_subsystem_class(class_name: str, methods: Dict[str, bool | None]) -> bool:
    """Determine if a class should be considered a subsystem.

    A class is considered a subsystem if:
    - It has at least one lifecycle method
    - Its name contains keywords like Manager, Controller, Service, etc.
    """
    lifecycle_keywords = ["manager", "controller", "service", "handler", "processor"]
    name_lower = class_name.lower()

    # Check if any lifecycle method is present
    has_lifecycle_method = any(methods.values())

    # Check if name suggests it's a subsystem
    has_subsystem_name = any(keyword in name_lower for keyword in lifecycle_keywords)

    return has_lifecycle_method or has_subsystem_name


def validate_file(file_path: Path) -> Tuple[List[str], int]:
    """Validate a single Python file for lifecycle compliance.

    Args:
        file_path: Path to the Python file to validate.

    Returns:
        Tuple of (list of error messages, number of subsystem classes found).
    """
    errors: List[str] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except SyntaxError as e:
        errors.append(f"{file_path}: Syntax error - {e}")
        return errors, 0

    validator = LifecycleValidator()
    validator.visit(tree)

    subsystem_count = 0

    for class_name, methods in validator.classes.items():
        if not is_subsystem_class(class_name, methods):
            continue

        subsystem_count += 1
        missing_methods: List[str] = []
        methods_without_types: List[str] = []

        for method_name in REQUIRED_LIFECYCLE_METHODS:
            method_value = methods[method_name]
            if method_value is None:
                # Method doesn't exist
                missing_methods.append(method_name)
            elif method_value is False:
                # Method exists but without return type annotation
                methods_without_types.append(method_name)

        if missing_methods:
            errors.append(
                f"{file_path}::{class_name}: Missing lifecycle methods: "
                f"{', '.join(missing_methods)}"
            )

        if methods_without_types:
            errors.append(
                f"{file_path}::{class_name}: Methods without return type annotation: "
                f"{', '.join(methods_without_types)}"
            )

    return errors, subsystem_count


def validate_directory(directory: Path) -> Tuple[List[str], int]:
    """Validate all Python files in a directory.

    Args:
        directory: Path to directory to scan.

    Returns:
        Tuple of (list of all errors, total subsystem count).
    """
    all_errors: List[str] = []
    total_subsystems = 0

    python_files = sorted(directory.rglob("*.py"))

    for file_path in python_files:
        # Skip test files and __pycache__
        if "__pycache__" in str(file_path) or file_path.name.startswith("test_"):
            continue

        errors, subsystem_count = validate_file(file_path)
        all_errors.extend(errors)
        total_subsystems += subsystem_count

    return all_errors, total_subsystems


def main() -> int:
    """Main entry point for lifecycle validation.

    Returns:
        Exit code: 0 if no violations, 1 if violations found.
    """
    print("=" * 80)
    print("Thalos Prime Library - Lifecycle Validator")
    print("=" * 80)

    # Get the repository root
    repo_root = Path(__file__).parent.parent
    thalos_prime_dir = repo_root / "thalos_prime"

    if not thalos_prime_dir.exists():
        print(f"Error: Directory {thalos_prime_dir} does not exist")
        return 1

    print(f"\nScanning directory: {thalos_prime_dir}")
    print("-" * 80)

    errors, subsystem_count = validate_directory(thalos_prime_dir)

    print(f"\nFound {subsystem_count} subsystem classes")

    if errors:
        print(f"\n{len(errors)} lifecycle violations found:\n")
        for error in errors:
            print(f"  ❌ {error}")
        print("\n" + "=" * 80)
        print("FAILED: Lifecycle validation failed")
        print("=" * 80)
        return 1

    print("\n" + "=" * 80)
    print("✅ PASSED: All subsystem classes have required lifecycle methods")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
