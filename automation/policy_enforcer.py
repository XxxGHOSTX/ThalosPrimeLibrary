"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.

Policy enforcement for ThalosPrime governance rules.
"""

import ast
import sys
from pathlib import Path


def check_no_experimental_in_core(root: Path) -> list[str]:
    """Ensure no core/ or system/ module imports from experimental/."""
    violations = []
    for py_file in list((root / "core").rglob("*.py")) + list((root / "system").rglob("*.py")):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", "") or ""
                if "experimental" in module:
                    violations.append(
                        f"POLICY VIOLATION: {py_file} imports from experimental: {module}"
                    )
    return violations


def enforce(root: Path = Path(".")) -> bool:
    """Enforce governance policies. Returns True if all checks pass."""
    violations = check_no_experimental_in_core(root)
    if violations:
        for v in violations:
            print(v)
        return False
    print("Policy enforcement PASSED.")
    return True


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    sys.exit(0 if enforce(root) else 1)
