"""Schema version registry for infra-synthesis.

Stores versioned schema snapshots to a JSON file so that every historical
version of the schema can be retrieved and compared.

Data Plane: JSON persistence only.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"


class SchemaVersionRegistry:
    """Appends schema versions to a JSON registry file.

    Each entry records a version tag, timestamp, and the full schema dict.
    Entries are stored as a JSON array (appended in memory, written on each
    call to :meth:`register`).

    Args:
        registry_path: Path to the JSON registry file.

    """

    def __init__(self, registry_path: str | Path = ".thalos_schema_versions.json") -> None:
        """Initialise the registry.

        Args:
            registry_path: Filesystem path for the JSON registry file.

        """
        self._path = Path(registry_path)
        self._entries: list[dict[str, Any]] = self._load_existing()

    def _load_existing(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text(encoding=_ENCODING))
        if not isinstance(data, list):
            msg = f"Schema version registry '{self._path}' is not a JSON array"
            raise TypeError(msg)
        return data

    def register(self, version: str, schema: dict[str, Any]) -> None:
        """Append *schema* to the registry under *version*.

        Args:
            version: Semver or arbitrary version tag (e.g. ``"1.0.0"``).
            schema: Validated schema dict.

        """
        entry: dict[str, Any] = {
            "version": version,
            "registered_at": datetime.now(UTC).isoformat(),
            "schema": schema,
        }
        self._entries.append(entry)
        self._path.write_text(
            json.dumps(self._entries, indent=2, sort_keys=True), encoding=_ENCODING
        )
        logger.info("SchemaVersionRegistry: registered version '%s'", version)

    def get(self, version: str) -> dict[str, Any] | None:
        """Return the schema stored under *version*, or ``None``.

        Args:
            version: Version tag to look up.

        Returns:
            Schema dict, or ``None`` if not found.

        """
        for entry in self._entries:
            if entry.get("version") == version:
                return entry.get("schema")
        return None

    def list_versions(self) -> list[str]:
        """Return all registered version tags in registration order.

        Returns:
            List of version strings.

        """
        return [e["version"] for e in self._entries]


__all__ = ["SchemaVersionRegistry"]
