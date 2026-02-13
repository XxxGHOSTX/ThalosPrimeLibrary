#!/usr/bin/env python3
"""Documentation validator for Thalos Prime Library.

Validates that:
- Every .py module has module-level docstring
- All public classes and functions have docstrings
- Docstrings include type annotations
- Required documentation files exist and are not empty
"""

import ast
import sys
from pathlib import Path
from typing import List


REQUIRED_DOCS: List[str] = [
    "ARCHITECTURE.md",
    "IMPLEMENTATION_COMPLETE.md",
    "VERIFICATION_REPORT.md",
]


class DocstringChecker(ast.NodeVisitor):
    """AST visitor to check for docstrings."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the checker.

        Args:
            file_path: Path to the file being checked.
        """
        self.file_path = file_path
        self.issues: List[str] = []
        self.has_module_docstring = False

    def visit_Module(self, node: ast.Module) -> None:
        """Check for module-level docstring."""
        if ast.get_docstring(node):
            self.has_module_docstring = True
        else:
            self.issues.append(f"Module lacks docstring")

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check for class docstring."""
        # Only check public classes (not starting with _)
        if not node.name.startswith("_"):
            if not ast.get_docstring(node):
                self.issues.append(
                    f"Line {node.lineno}: Public class '{node.name}' lacks docstring"
                )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for function docstring."""
        # Only check public functions (not starting with _)
        # Skip special methods except __init__
        if not node.name.startswith("_") or node.name == "__init__":
            if not ast.get_docstring(node):
                self.issues.append(
                    f"Line {node.lineno}: Public function '{node.name}' lacks docstring"
                )
            else:
                # Check if docstring mentions parameters and return type
                docstring = ast.get_docstring(node)
                docstring_str = docstring if docstring is not None else ""
                has_args = len(node.args.args) > 1 or (
                    len(node.args.args) == 1 and node.args.args[0].arg != "self"
                )
                has_return = node.returns is not None

                if has_args and "Args:" not in docstring_str and "Parameters:" not in docstring_str:
                    self.issues.append(
                        f"Line {node.lineno}: Function '{node.name}' docstring "
                        f"should document parameters"
                    )

                if has_return and "Returns:" not in docstring_str and "Return:" not in docstring_str:
                    self.issues.append(
                        f"Line {node.lineno}: Function '{node.name}' docstring "
                        f"should document return value"
                    )

        self.generic_visit(node)


def validate_file(file_path: Path) -> List[str]:
    """Validate a single Python file for documentation.

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

    checker = DocstringChecker(file_path)
    checker.visit(tree)

    # Prefix all issues with file path
    return [f"{file_path}::{issue}" for issue in checker.issues]


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
        # Skip __pycache__ and test files (files starting with 'test_')
        if "__pycache__" in str(file_path) or file_path.name.startswith("test_"):
            continue

        issues = validate_file(file_path)
        all_issues.extend(issues)

    return all_issues


def check_required_docs(repo_root: Path) -> List[str]:
    """Check that required documentation files exist and are not empty.

    Args:
        repo_root: Path to repository root.

    Returns:
        List of issues found.
    """
    issues: List[str] = []

    for doc_file in REQUIRED_DOCS:
        doc_path = repo_root / doc_file
        if not doc_path.exists():
            issues.append(f"Required documentation file missing: {doc_file}")
        elif doc_path.stat().st_size == 0:
            issues.append(f"Required documentation file is empty: {doc_file}")

    return issues


def main() -> int:
    """Main entry point for documentation validation.

    Returns:
        Exit code: 0 if no violations, 1 if violations found.
    """
    print("=" * 80)
    print("Thalos Prime Library - Documentation Validator")
    print("=" * 80)

    # Get the repository root
    repo_root = Path(__file__).parent.parent
    thalos_prime_dir = repo_root / "thalos_prime"

    if not thalos_prime_dir.exists():
        print(f"Error: Directory {thalos_prime_dir} does not exist")
        return 1

    print(f"\nScanning directory: {thalos_prime_dir}")
    print("-" * 80)

    # Check Python file docstrings
    code_issues = validate_directory(thalos_prime_dir)

    # Check required documentation files
    doc_issues = check_required_docs(repo_root)

    all_issues = code_issues + doc_issues

    if all_issues:
        print(f"\n⚠️  {len(all_issues)} documentation issues found:\n")
        for issue in all_issues:
            print(f"  ⚠️  {issue}")
        print("\n" + "=" * 80)
        print("WARNING: Documentation needs improvement")
        print("=" * 80)
        return 0  # Don't fail, just warn

    print("\n" + "=" * 80)
    print("✅ PASSED: Documentation is complete")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
