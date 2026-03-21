"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

from dataclasses import dataclass, field
from enum import Enum

from core.utilities import now_iso, compute_sha256


class PipelineStatus(Enum):
    """Lifecycle status of a pipeline run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class PipelineRun:
    """Represents a single pipeline execution lifecycle."""

    pipeline_id: str
    seed: int
    status: PipelineStatus = PipelineStatus.PENDING
    steps: list[dict] = field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None

    def start(self) -> None:
        """Mark the pipeline run as started."""
        self.status = PipelineStatus.RUNNING
        self.started_at = now_iso()

    def complete(self, result: dict) -> None:
        """Mark the pipeline run as completed with a result."""
        self.status = PipelineStatus.COMPLETED
        self.completed_at = now_iso()
        self.steps.append({"step": "final", "result": result, "timestamp": now_iso()})

    def fail(self, error: str) -> None:
        """Mark the pipeline run as failed with an error message."""
        self.status = PipelineStatus.FAILED
        self.completed_at = now_iso()
        self.error = error

    def state_hash(self) -> str:
        """Compute the current deterministic state hash."""
        return compute_sha256({"id": self.pipeline_id, "seed": self.seed, "steps": self.steps})


class PipelineController:
    """Manages pipeline lifecycle and step execution tracking."""

    def __init__(self) -> None:
        """Initialize with an empty runs registry."""
        self._runs: dict[str, PipelineRun] = {}

    def create_run(self, pipeline_id: str, seed: int) -> PipelineRun:
        """Create and register a new pipeline run.

        Args:
            pipeline_id: Unique identifier for this pipeline run.
            seed: 64-bit execution seed.

        Returns:
            The newly created PipelineRun.
        """
        run = PipelineRun(pipeline_id=pipeline_id, seed=seed)
        self._runs[pipeline_id] = run
        return run

    def get_run(self, pipeline_id: str) -> PipelineRun | None:
        """Retrieve a run by ID, or None if not found."""
        return self._runs.get(pipeline_id)

    def list_runs(self) -> list[PipelineRun]:
        """Return all registered pipeline runs."""
        return list(self._runs.values())
