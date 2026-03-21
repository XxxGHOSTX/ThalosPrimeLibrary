"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.

Repository structure validator for ThalosPrime policy compliance.
"""

import sys
from pathlib import Path

REQUIRED_DIRS = [
    "core",
    "system",
    "experimental",
    "services",
    "infrastructure",
    "docs",
    "automation",
    "registry",
]
IP_HEADER = "Copyright © 2026 Tony Ray Macier III"


def validate_repo(root: Path) -> list[str]:
    """Validate repository structure and IP header compliance."""
    errors = []
    for d in REQUIRED_DIRS:
        if not (root / d).is_dir():
            errors.append(f"MISSING DIRECTORY: {d}/")

    for py_file in root.rglob("*.py"):
        if "node_modules" in str(py_file) or ".git" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            if IP_HEADER not in content:
                errors.append(f"MISSING IP HEADER: {py_file.relative_to(root)}")
        except (UnicodeDecodeError, OSError):
            pass
    return errors


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    errors = validate_repo(root)
    if errors:
        print("Policy violations found:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("Repository validation PASSED.")
