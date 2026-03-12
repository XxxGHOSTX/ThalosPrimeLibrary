"""Schema drift detection for infra-synthesis.

Compares a serialised schema snapshot stored at deploy time against a
*live_state* dict supplied by the caller (e.g. returned by an inventory
API).  Drift is reported as a structured result — no auto-remediation.

Data Plane helper: stateless comparison, no I/O side effects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DriftResult:
    """Result of a drift-detection comparison.

    Attributes:
        drifted: True when the live state diverges from the snapshot.
        diff: Structured diff produced by DeepDiff (empty dict when no drift).
        summary: Human-readable summary string.

    """

    drifted: bool
    diff: dict[str, Any]
    summary: str


class DriftDetector:
    """Detects configuration drift between a schema snapshot and live state.

    Uses DeepDiff for structural comparison.  Both sides must be plain
    Python dicts (as produced by :class:`SchemaLoader` or a live inventory
    API).
    """

    def detect(
        self,
        snapshot: dict[str, Any],
        live_state: dict[str, Any],
    ) -> DriftResult:
        """Compare *snapshot* to *live_state* and report drift.

        Args:
            snapshot: Previously persisted schema snapshot.
            live_state: Current live infrastructure state as a dict.

        Returns:
            DriftResult describing any differences found.

        """
        try:
            from deepdiff import DeepDiff
        except ImportError as exc:
            msg = "deepdiff package is required for drift detection: pip install deepdiff"
            raise ImportError(msg) from exc

        raw_diff = DeepDiff(snapshot, live_state, ignore_order=True)
        diff_dict: dict[str, Any] = raw_diff.to_dict() if raw_diff else {}
        drifted = bool(diff_dict)

        if drifted:
            change_count = sum(len(v) if isinstance(v, dict) else 1 for v in diff_dict.values())
            summary = f"Drift detected: {change_count} change(s) found between snapshot and live state"
            logger.warning(summary)
        else:
            summary = "No drift: live state matches snapshot"
            logger.debug(summary)

        return DriftResult(drifted=drifted, diff=diff_dict, summary=summary)


__all__ = ["DriftDetector", "DriftResult"]
