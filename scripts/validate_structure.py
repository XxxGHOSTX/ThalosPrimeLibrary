"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.

Validates the ThalosPrime repository structure for compliance.
"""

import sys
from pathlib import Path

REQUIRED_PATHS = [
    "core/base_engine.py",
    "core/utilities.py",
    "core/README.md",
    "system/orchestrator.py",
    "services/control_plane/seed_manager.py",
    "services/discovery_sentinel/scanner.py",
    "services/artifact_engine/repair_logic.py",
    "STATELOG/.gitkeep",
    "pyproject.toml",
    "requirements.txt",
    ".github/copilot-instructions.md",
    "registry/manifest.yml",
    "docs/platform/ARCHITECTURE.md",
    "docs/GOVERNANCE.md",
]

IP_HEADER = "Copyright © 2026 Tony Ray Macier III"


def validate(root: Path = Path(".")) -> bool:
    """Validate that all required paths exist and contain the IP header.

    Args:
        root: Repository root directory.

    Returns:
        True if all checks pass, False otherwise.
    """
    errors = []
    for rel_path in REQUIRED_PATHS:
        full = root / rel_path
        if not full.exists():
            errors.append(f"MISSING: {rel_path}")
        elif full.suffix in (".py", ".ts", ".md") and IP_HEADER not in full.read_text(encoding="utf-8"):
            errors.append(f"MISSING IP HEADER: {rel_path}")

    if errors:
        print("Validation FAILED:")
        for e in errors:
            print(f"  {e}")
        return False
    print("Validation PASSED: All required paths and IP headers present.")
    return True


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    sys.exit(0 if validate(root) else 1)
