"""Storage path provider for serverless-safe path resolution."""

from __future__ import annotations

import os
from pathlib import Path


def get_storage_base_path() -> Path:
    """Return the appropriate base path for graph storage.

    Resolution order:
    1. ``/tmp/thalos_graphs`` when the ``VERCEL`` environment variable is set
       (serverless deployment).
    2. The path specified by ``THALOS_STORAGE_PATH`` environment variable.
    3. ``~/ThalosPrimeStorage`` in the user's home directory.

    Returns:
        Resolved base Path for all storage operations.

    """
    if os.environ.get("VERCEL"):
        return Path("/tmp/thalos_graphs")  # nosec B108 - intentional /tmp usage for serverless (Vercel) ephemeral storage
    env_path = os.environ.get("THALOS_STORAGE_PATH")
    if env_path:
        return Path(env_path)
    return Path.home() / "ThalosPrimeStorage"


__all__ = ["get_storage_base_path"]
