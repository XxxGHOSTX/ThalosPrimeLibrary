"""Thalos NEXUS — Determinism Spine.

Manages the four canonical output files that anchor every evolution run to a
deterministic, replayable record:

- ``repro_manifest.json``  — reproducibility manifest (seed, config_hash, …)
- ``event_log.jsonl``      — append-only, JSONL, hash-chained event log
- ``gate_results.json``    — serialised gate execution results
- ``artifacts.json``       — artifact inventory

Control Plane boundary: this module owns output-file lifecycle only.
No gate execution or data-plane logic belongs here.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_REPRO_SCHEMA_VERSION = "1.0"
_GATE_RESULTS_SCHEMA_VERSION = "1.0"


def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def _sha256_hex(data: str) -> str:
    """Return the SHA-256 hex digest of *data* encoded as UTF-8."""
    return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class ReproManifest:
    """Reproducibility manifest written to ``repro_manifest.json``.

    All fields are required; every field is serialised verbatim.

    Deterministic fields used for replay identity:
        ``seed``, ``config_hash``, ``thalos_nexus_version``, ``genome_hash``.

    Observability-only fields (NOT used in replay comparison):
        ``created_at``, ``python_version``, ``platform`` — wall-clock/environment metadata.
    """

    schema_version: str
    seed: int
    config_hash: str
    thalos_nexus_version: str
    python_version: str
    platform: str
    created_at: str
    genome_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "config_hash": self.config_hash,
            "thalos_nexus_version": self.thalos_nexus_version,
            "python_version": self.python_version,
            "platform": self.platform,
            "created_at": self.created_at,
            "genome_hash": self.genome_hash,
        }


# ---------------------------------------------------------------------------
# DeterminismSpine
# ---------------------------------------------------------------------------


class DeterminismSpine:
    """Owns and manages all four determinism-output files for one evolution run.

    Parameters
    ----------
    output_dir:
        Directory in which all output files are created.  Created if absent.

    """

    REPRO_MANIFEST_FILENAME = "repro_manifest.json"
    EVENT_LOG_FILENAME = "event_log.jsonl"
    GATE_RESULTS_FILENAME = "gate_results.json"
    ARTIFACTS_FILENAME = "artifacts.json"

    def __init__(self, output_dir: str | Path) -> None:
        """Initialise the spine, creating *output_dir* if necessary."""
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._prev_event_hash: str = ""
        self._event_sequence: int = 0

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    @property
    def output_dir(self) -> Path:
        """Absolute path to the output directory."""
        return self._output_dir

    def _path(self, filename: str) -> Path:
        return self._output_dir / filename

    # ------------------------------------------------------------------
    # repro_manifest.json
    # ------------------------------------------------------------------

    def write_repro_manifest(
        self,
        seed: int,
        config_hash: str,
        version: str,
        genome_hash: str,
    ) -> Path:
        """Write ``repro_manifest.json`` and return its path.

        Parameters
        ----------
        seed:
            Deterministic integer seed used for this run.
        config_hash:
            SHA-256 hex digest of the run configuration.
        version:
            ``thalos_nexus`` package version string.
        genome_hash:
            SHA-256 hex digest of the genome bundle.

        Returns
        -------
        Path
            Path to the written file.

        """
        manifest = ReproManifest(
            schema_version=_REPRO_SCHEMA_VERSION,
            seed=seed,
            config_hash=config_hash,
            thalos_nexus_version=version,
            python_version=sys.version,
            platform=platform.platform(),
            created_at=_utc_now(),
            genome_hash=genome_hash,
        )
        path = self._path(self.REPRO_MANIFEST_FILENAME)
        path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # event_log.jsonl
    # ------------------------------------------------------------------

    def emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Append a hash-chained event to ``event_log.jsonl``.

        Each event carries:

        - ``seq``        — monotonically increasing sequence number
        - ``event_type`` — caller-supplied string
        - ``data``       — caller-supplied payload
        - ``prev_hash``  — SHA-256 of the previous event's deterministic fields
          (or ``""`` for first event)
        - ``event_hash`` — SHA-256 of this event's deterministic fields
          (seq, event_type, data, prev_hash)
        - ``timestamp``  — UTC ISO-8601 (observability metadata; NOT included
          in hash computation — timestamps never affect replay identity)

        Parameters
        ----------
        event_type:
            Short string identifying the event kind.
        data:
            Arbitrary key/value payload for this event.

        """
        event: dict[str, Any] = {
            "seq": self._event_sequence,
            "event_type": event_type,
            "data": data,
            "prev_hash": self._prev_event_hash,
        }
        # Hash only deterministic fields (seq, event_type, data, prev_hash).
        # The timestamp is observability metadata and is intentionally excluded
        # from the hash chain so replay produces the same hash chain regardless
        # of wall-clock time.
        event_json = json.dumps(event, separators=(",", ":"), sort_keys=True)
        event_hash = _sha256_hex(event_json)
        event["event_hash"] = event_hash
        event["timestamp"] = _utc_now()  # Added after hashing; not part of chain
        self._prev_event_hash = event_hash
        self._event_sequence += 1

        line = json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n"
        log_path = self._path(self.EVENT_LOG_FILENAME)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    # ------------------------------------------------------------------
    # gate_results.json
    # ------------------------------------------------------------------

    def write_gate_results(self, results: dict[str, Any]) -> Path:
        """Write ``gate_results.json`` and return its path.

        Parameters
        ----------
        results:
            Dictionary conforming to the ``gate_results`` JSON schema.

        Returns
        -------
        Path
            Path to the written file.

        """
        if "schema_version" not in results:
            results = {"schema_version": _GATE_RESULTS_SCHEMA_VERSION, **results}
        path = self._path(self.GATE_RESULTS_FILENAME)
        path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # artifacts.json
    # ------------------------------------------------------------------

    def write_artifacts(self, artifacts: list[dict[str, Any]]) -> Path:
        """Write ``artifacts.json`` and return its path.

        Parameters
        ----------
        artifacts:
            List of artifact descriptor dictionaries.

        Returns
        -------
        Path
            Path to the written file.

        """
        payload = {
            "schema_version": "1.0",
            "created_at": _utc_now(),
            "artifacts": artifacts,
        }
        path = self._path(self.ARTIFACTS_FILENAME)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Convenience: list all spine-managed paths
    # ------------------------------------------------------------------

    def all_output_paths(self) -> list[Path]:
        """Return paths for all four managed files that currently exist."""
        names = [
            self.REPRO_MANIFEST_FILENAME,
            self.EVENT_LOG_FILENAME,
            self.GATE_RESULTS_FILENAME,
            self.ARTIFACTS_FILENAME,
        ]
        return [self._path(n) for n in names if self._path(n).exists()]
