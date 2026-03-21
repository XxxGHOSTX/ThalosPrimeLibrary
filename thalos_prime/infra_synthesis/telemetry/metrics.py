"""Telemetry metrics recorder for infra-synthesis.

Records named numeric measurements with timestamps and exports them to
a JSON file.  All operations are in-memory; export writes atomically.

Data Plane helper: no lifecycle state, no side effects beyond file export.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"


@dataclass
class MetricPoint:
    """A single named measurement.

    Attributes:
        name: Metric name (e.g. ``"artifacts_generated"``).
        value: Numeric measurement.
        ts: UTC timestamp of the measurement.

    """

    name: str
    value: float
    ts: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict.

        Returns:
            Dictionary with keys ``name``, ``value``, ``ts``.

        """
        return {"name": self.name, "value": self.value, "ts": self.ts.isoformat()}


class MetricsRecorder:
    """Records metric points and exports them to JSON.

    Usage::

        recorder = MetricsRecorder()
        recorder.record("artifacts_generated", 5)
        recorder.export(Path("dist/metrics.json"))

    """

    def __init__(self) -> None:
        """Initialise an empty metric store."""
        self._points: list[MetricPoint] = []

    def record(self, name: str, value: float, ts: datetime | None = None) -> None:
        """Append a new measurement.

        Args:
            name: Metric name.
            value: Numeric value.
            ts: Optional explicit timestamp (defaults to ``datetime.now(timezone.utc)``).

        """
        point = MetricPoint(
            name=name,
            value=value,
            ts=ts if ts is not None else datetime.now(UTC),
        )
        self._points.append(point)
        logger.debug("Metric recorded: %s=%.4g at %s", name, value, point.ts.isoformat())

    def export(self, path: Path) -> None:
        """Write all recorded metrics as a JSON array to *path*.

        Args:
            path: Destination file.  Parent directory must exist.

        """
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [p.to_dict() for p in self._points]
        path.write_text(json.dumps(data, indent=2), encoding=_ENCODING)
        logger.info("MetricsRecorder: exported %d points to '%s'", len(data), path)

    def all_points(self) -> list[MetricPoint]:
        """Return a copy of all recorded metric points.

        Returns:
            List of :class:`MetricPoint` in recording order.

        """
        return list(self._points)


__all__ = ["MetricPoint", "MetricsRecorder"]
