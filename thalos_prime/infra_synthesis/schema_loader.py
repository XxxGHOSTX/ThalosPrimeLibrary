"""Safe YAML schema loader for infra-synthesis.

Data Plane helper: pure I/O with no lifecycle state.
Uses yaml.safe_load to prevent arbitrary code execution from untrusted schemas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class SchemaLoadError(Exception):
    """Raised when a schema file cannot be loaded or parsed."""


class SchemaLoader:
    """Loads and parses infrastructure schema YAML files.

    All loading is performed with yaml.safe_load to prevent code injection.
    Binary or multi-document YAML is rejected deterministically.
    """

    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        """Load a YAML schema from *path* and return as a plain dict.

        Args:
            path: Filesystem path to the YAML file.

        Returns:
            Parsed schema as a nested dictionary.

        Raises:
            SchemaLoadError: When the file does not exist, cannot be read,
                             is not valid YAML, or does not contain a mapping.

        """
        schema_path = Path(path)
        if not schema_path.exists():
            msg = f"Schema file not found: {schema_path}"
            raise SchemaLoadError(msg)
        if not schema_path.is_file():
            msg = f"Schema path is not a file: {schema_path}"
            raise SchemaLoadError(msg)

        try:
            raw = schema_path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Cannot read schema file '{schema_path}': {exc}"
            raise SchemaLoadError(msg) from exc

        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            msg = f"YAML parse error in '{schema_path}': {exc}"
            raise SchemaLoadError(msg) from exc

        if not isinstance(data, dict):
            msg = (
                f"Schema '{schema_path}' must be a YAML mapping at the top level; "
                f"got {type(data).__name__}"
            )
            raise SchemaLoadError(msg)

        logger.debug("Schema loaded from '%s' (%d top-level keys)", schema_path, len(data))
        return data


__all__ = ["SchemaLoadError", "SchemaLoader"]
