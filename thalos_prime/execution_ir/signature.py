"""Environment signature utilities for replay and determinism verification."""

from __future__ import annotations

import platform
import sys

from thalos_prime.execution_ir.hash import hash_dict


def get_env_signature() -> str:
    """Compute a deterministic hash of the current execution environment.

    The signature encodes Python version, platform, and sys.version_info
    to detect environment drift between runs.

    Returns:
        Hex SHA-256 digest uniquely identifying this environment.

    """
    vi = sys.version_info
    env_data: dict[str, object] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "version_info": {
            "major": vi.major,
            "minor": vi.minor,
            "micro": vi.micro,
            "releaselevel": vi.releaselevel,
            "serial": vi.serial,
        },
    }
    return hash_dict(env_data)


__all__ = ["get_env_signature"]
