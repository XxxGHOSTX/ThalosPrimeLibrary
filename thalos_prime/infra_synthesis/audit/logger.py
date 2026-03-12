"""Structured audit logger for infra-synthesis.

Appends JSON lines to an audit log file.  Each line is a self-contained
structured record with timestamp, actor, action, and arbitrary metadata.

Control Plane: audit trail only; no computational logic.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"


class AuditLogger:
    """Appends structured JSON-line audit records to a log file.

    Each record contains:
    * ``timestamp`` — ISO-8601 UTC.
    * ``actor``     — Identity of the principal performing the action.
    * ``action``    — Short string describing the action (e.g. ``"build"``).
    * ``metadata``  — Arbitrary dict with additional context.

    Args:
        log_path: Path to the audit log file (created / appended on write).

    """

    def __init__(self, log_path: str | Path = "audit.log") -> None:
        """Initialise with *log_path*.

        Args:
            log_path: Filesystem path to the append-only audit log.

        """
        self._path = Path(log_path)

    def log(
        self,
        actor: str,
        action: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a structured audit record.

        Args:
            actor: Identity of the principal (e.g. username or service name).
            action: Short action description (e.g. ``"deploy"``, ``"build"``).
            metadata: Optional additional context dict.

        """
        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor,
            "action": action,
            "metadata": metadata or {},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding=_ENCODING) as fh:
            fh.write(json.dumps(record) + "\n")
        logger.debug(
            "AuditLogger: actor='%s' action='%s' metadata_keys=%s",
            actor,
            action,
            list((metadata or {}).keys()),
        )

    def read_all(self) -> list[dict[str, Any]]:
        """Read all audit records from the log file.

        Returns:
            List of parsed record dicts in append order.

        """
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding=_ENCODING).splitlines()
        return [json.loads(line) for line in lines if line.strip()]


__all__ = ["AuditLogger"]
