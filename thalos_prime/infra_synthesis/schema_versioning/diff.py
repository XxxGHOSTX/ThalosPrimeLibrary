"""Schema diff module for infra-synthesis.

Uses DeepDiff to compute structural differences between two schema dicts.
Intended for use with :class:`SchemaVersionRegistry` to track how schemas
evolve between versions.

Data Plane helper: pure comparison; no I/O side effects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SchemaDiff:
    """Result of comparing two schema versions.

    Attributes:
        changed: True when the schemas differ.
        diff: Raw DeepDiff output dict.
        summary: Human-readable one-line summary.

    """

    changed: bool
    diff: dict[str, Any]
    summary: str


def compute_diff(old: dict[str, Any], new: dict[str, Any]) -> SchemaDiff:
    """Compute the structural difference between *old* and *new* schemas.

    Args:
        old: Previous schema version dict.
        new: New schema version dict.

    Returns:
        :class:`SchemaDiff` describing the changes.

    Raises:
        ImportError: When ``deepdiff`` is not installed.

    """
    try:
        from deepdiff import DeepDiff
    except ImportError as exc:
        msg = "deepdiff package is required for schema diff: pip install deepdiff"
        raise ImportError(msg) from exc

    raw = DeepDiff(old, new, ignore_order=True)
    diff_dict: dict[str, Any] = raw.to_dict() if raw else {}
    changed = bool(diff_dict)

    if changed:
        change_count = sum(
            len(v) if isinstance(v, dict) else 1 for v in diff_dict.values()
        )
        summary = f"Schema changed: {change_count} change(s)"
    else:
        summary = "Schema unchanged"

    logger.debug("compute_diff: %s", summary)
    return SchemaDiff(changed=changed, diff=diff_dict, summary=summary)


__all__ = ["SchemaDiff", "compute_diff"]
