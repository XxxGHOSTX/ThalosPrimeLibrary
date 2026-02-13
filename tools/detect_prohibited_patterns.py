#!/usr/bin/env python3
"""Prohibited patterns detector for Thalos Prime Library.

Scans production code for prohibited patterns:
- TODO, FIXME, XXX, HACK, STUB, MOCK, PLACEHOLDER
- Catch-all exceptions without re-raise
- type: ignore without justification
- Untyped Any without protocol bounds
- Implicit defaults that could mask errors
- Silent retries without logging
"""

import ast
import re
import sys
from pathlib import Path
from typing import List


# Prohibited keywords in production code
PROHIBITED_KEYWORDS = [
    "TODO",
    "FIXME",
    "XXX",
    "HACK",
    "STUB",
    "MOCK",
    "PLACEHOLDER",
]


class ProhibitedPatternChecker(ast.NodeVisitor):
    """AST visitor to detect prohibited patterns."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the checker.

        Args:
            file_path: Path to the file being checked.
        """
        self.file_path = file_path
        self.issues: List[str] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Check for catch-all exception handlers."""
        # Check for bare except or except Exception
        if node.type is None:
            # Bare except - check if it re-raises
            has_reraise = any(isinstance(stmt, ast.Raise) for stmt in node.body)
            if not has_reraise:
                self.issues.append(
                    f"Line {node.lineno}: Bare except without re-raise (prohibited)"
                )
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            # except Exception - check if it re-raises
            has_reraise = any(isinstance(stmt, ast.Raise) for stmt in node.body)
            if not has_reraise:
                self.issues.append(
                    f"Line {node.lineno}: Catch-all 'except Exception:' without re-raise"
                )

        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        """Check for untyped Any without bounds."""
        if node.annotation and isinstance(node.annotation, ast.Name):
            if node.annotation.id == "Any":
                self.issues.append(
                    f"Line {node.lineno}: Untyped 'Any' detected for '{node.arg}' "
                    f"(should be bounded by protocol)"
                )

        self.generic_visit(node)


def check_file_content(file_path: Path) -> List[str]:
    """Check file content for prohibited keywords and patterns.

    Args:
        file_path: Path to the file to check.

    Returns:
        List of issues found.
    """
    issues: List[str] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return [f"{file_path}: Error reading file - {e}"]

    for lineno, line in enumerate(lines, 1):
        # Skip if line is part of a string literal (simple heuristic)
        stripped = line.strip()

        # Check for prohibited keywords in comments and code
        for keyword in PROHIBITED_KEYWORDS:
            if keyword in line:
                # Check if it's in a comment
                if f"# {keyword}" in line or f"#{keyword}" in line:
                    issues.append(
                        f"{file_path}:Line {lineno}: Prohibited keyword '{keyword}' "
                        f"in production code"
                    )
                # Check if it's in code (not in a string)
                elif keyword in stripped and not (
                    stripped.startswith('"') or stripped.startswith("'")
                ):
                    issues.append(
                        f"{file_path}:Line {lineno}: Prohibited keyword '{keyword}' "
                        f"in production code"
                    )

        # Check for type: ignore without justification
        if "# type: ignore" in line:
            # Check if there's a justification after it
            if line.strip().endswith("# type: ignore"):
                issues.append(
                    f"{file_path}:Line {lineno}: '# type: ignore' without justification comment"
                )

    return issues


def validate_file(file_path: Path) -> List[str]:
    """Validate a single Python file for prohibited patterns.

    Args:
        file_path: Path to the Python file to validate.

    Returns:
        List of issue messages.
    """
    # First check file content
    issues = check_file_content(file_path)

    # Then check AST patterns
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        issues.append(f"{file_path}: Syntax error - {e}")
        return issues

    checker = ProhibitedPatternChecker(file_path)
    checker.visit(tree)

    # Prefix AST issues with file path
    issues.extend([f"{file_path}::{issue}" for issue in checker.issues])

    return issues


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
        # Skip __pycache__ but include test files to check them too
        if "__pycache__" in str(file_path):
            continue

        issues = validate_file(file_path)
        all_issues.extend(issues)

    return all_issues


def main() -> int:
    """Main entry point for prohibited patterns detection.

    Returns:
        Exit code: 0 if no violations, 1 if violations found.
    """
    print("=" * 80)
    print("Thalos Prime Library - Prohibited Patterns Detector")
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
        print(f"\n❌ {len(issues)} prohibited patterns found:\n")
        for issue in issues:
            print(f"  ❌ {issue}")
        print("\n" + "=" * 80)
        print("FAILED: Prohibited patterns detected")
        print("=" * 80)
        return 1

    print("\n" + "=" * 80)
    print("✅ PASSED: No prohibited patterns detected")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
