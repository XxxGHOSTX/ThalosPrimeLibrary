"""Local JSON-on-disk state backend for infra-synthesis.

Persists schema snapshots as individual JSON files under a configurable
directory.  Each snapshot is written atomically: written to a temp file
then renamed to prevent partial writes.

Data Plane implementation: file I/O only.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from thalos_prime.infra_synthesis.state.backend import StateBackend

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"


class LocalStateBackend(StateBackend):
    r"""JSON-file-based implementation of :class:`StateBackend`.

    Each snapshot is stored as ``<root_dir>/<key>.json``.  Key characters
    unsafe for filenames (``/``, ``\\``, ``:``) are replaced with ``_``.

    Args:
        root_dir: Directory where snapshot files are stored.  Created on
                  first use if it does not already exist.

    """

    def __init__(self, root_dir: str | Path = ".thalos_state") -> None:
        """Initialise the backend with *root_dir*.

        Args:
            root_dir: Filesystem path to the snapshot storage directory.

        """
        self._root = Path(root_dir)

    def _key_to_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self._root / f"{safe}.json"

    def _ensure_dir(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, state: dict[str, Any]) -> None:
        """Atomically persist *state* under *key*.

        Args:
            key: Snapshot identifier.
            state: JSON-serialisable dict.

        """
        self._ensure_dir()
        target = self._key_to_path(key)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self._root, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding=_ENCODING) as fh:
                json.dump(state, fh, indent=2, sort_keys=True)
            Path(tmp_path).replace(target)
        except (OSError, TypeError, ValueError):
            # Remove partial temp file on any error.
            Path(tmp_path).unlink(missing_ok=True)
            raise
        logger.debug("LocalStateBackend: saved snapshot '%s' -> '%s'", key, target)

    def load(self, key: str) -> dict[str, Any] | None:
        """Load snapshot for *key*, returning ``None`` if absent.

        Args:
            key: Snapshot identifier.

        Returns:
            Stored dict or ``None``.

        """
        path = self._key_to_path(key)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding=_ENCODING))
        if not isinstance(data, dict):
            msg = f"Snapshot file '{path}' does not contain a JSON object"
            raise TypeError(msg)
        return data

    def delete(self, key: str) -> None:
        """Delete snapshot for *key* (no-op if absent).

        Args:
            key: Snapshot identifier.

        """
        self._key_to_path(key).unlink(missing_ok=True)
        logger.debug("LocalStateBackend: deleted snapshot '%s'", key)

    def list_keys(self) -> list[str]:
        """Return sorted list of all stored snapshot keys.

        Returns:
            List of key strings derived from filenames.

        """
        if not self._root.exists():
            return []
        return sorted(p.stem for p in self._root.glob("*.json"))


__all__ = ["LocalStateBackend"]
