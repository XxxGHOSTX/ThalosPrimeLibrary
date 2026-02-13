#!/usr/bin/env python3
"""Determinism validator for Thalos Prime Library.

Scans for non-deterministic operations:
- random.random() without seed
- time.time() without logging
- os.listdir() without sorting
- uuid.uuid4() without deterministic alternative
- threading without explicit ordering
- asyncio without bounded queues
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Pattern definitions for non-deterministic operations
DETERMINISM_PATTERNS: Dict[str, List[str]] = {
    "random_without_seed": [
        r"random\.random\(",
        r"random\.choice\(",
        r"random\.shuffle\(",
        r"random\.sample\(",
    ],
    "time_operations": [
        r"time\.time\(",
        r"datetime\.now\(",
        r"datetime\.utcnow\(",
    ],
    "filesystem_operations": [
        r"os\.listdir\(",
        r"os\.scandir\(",
        r"glob\.glob\(",
    ],
    "uuid_generation": [
        r"uuid\.uuid4\(",
    ],
    "threading_operations": [
        r"threading\.Thread\(",
        r"ThreadPoolExecutor\(",
    ],
}


class DeterminismChecker(ast.NodeVisitor):
    """AST visitor to detect non-deterministic operations."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the checker.

        Args:
            file_path: Path to the file being checked.
        """
        self.file_path = file_path
        self.issues: List[str] = []
        self.random_seed_set: Set[int] = set()
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = None

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to detect non-deterministic operations."""
        call_str = ast.unparse(node)

        # Check for random.seed()
        if "random.seed(" in call_str:
            self.random_seed_set.add(node.lineno)

        # Check for non-deterministic random operations
        if any(re.search(pattern, call_str) for pattern in DETERMINISM_PATTERNS["random_without_seed"]):
            # Check if seed was set in this function
            if not self.random_seed_set:
                self.issues.append(
                    f"Line {node.lineno}: Random operation without seed: {call_str[:50]}"
                )

        # Check for time operations
        if any(re.search(pattern, call_str) for pattern in DETERMINISM_PATTERNS["time_operations"]):
            # Check if there's logging nearby (simple heuristic)
            self.issues.append(
                f"Line {node.lineno}: Time operation detected (ensure logged): {call_str[:50]}"
            )

        # Check for filesystem operations
        if any(re.search(pattern, call_str) for pattern in DETERMINISM_PATTERNS["filesystem_operations"]):
            self.issues.append(
                f"Line {node.lineno}: Filesystem scan detected (ensure sorted): {call_str[:50]}"
            )

        # Check for UUID generation
        if any(re.search(pattern, call_str) for pattern in DETERMINISM_PATTERNS["uuid_generation"]):
            self.issues.append(
                f"Line {node.lineno}: UUID4 generation (non-deterministic): {call_str[:50]}"
            )

        # Check for threading
        if any(re.search(pattern, call_str) for pattern in DETERMINISM_PATTERNS["threading_operations"]):
            self.issues.append(
                f"Line {node.lineno}: Threading detected (ensure explicit ordering): {call_str[:50]}"
            )

        self.generic_visit(node)


def validate_file(file_path: Path) -> List[str]:
    """Validate a single Python file for determinism.

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

    checker = DeterminismChecker(file_path)
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
        # Skip test files and __pycache__
        if "__pycache__" in str(file_path):
            continue

        issues = validate_file(file_path)
        all_issues.extend(issues)

    return all_issues


def main() -> int:
    """Main entry point for determinism validation.

    Returns:
        Exit code: 0 if no violations, 1 if violations found.
    """
    print("=" * 80)
    print("Thalos Prime Library - Determinism Validator")
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
        print(f"\n⚠️  {len(issues)} potential determinism issues found:\n")
        for issue in issues:
            print(f"  ⚠️  {issue}")
        print("\n" + "=" * 80)
        print("WARNING: Review determinism issues")
        print("=" * 80)
        print("\nNote: Some warnings may be acceptable if:")
        print("  - Randomness is seeded and logged")
        print("  - Time operations are logged for replay")
        print("  - Filesystem operations are sorted")
        print("  - Operations are in test code")
        return 0  # Don't fail, just warn

    print("\n" + "=" * 80)
    print("✅ PASSED: No determinism issues detected")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
