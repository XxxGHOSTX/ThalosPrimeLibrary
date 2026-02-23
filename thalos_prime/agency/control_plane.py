"""Agency Control Plane — lifecycle orchestration for thalos_prime.agency.

AgencyControlPlane owns the lifecycle of the WorldModel and
ActiveInferenceEngine.  It enforces the six required lifecycle methods
and emits structured JSONL events for every state transition.

Control Plane component — no computational work lives here.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from thalos_prime.agency.active_inference import ActiveInferenceEngine
from thalos_prime.agency.schema import (
    AGENCY_SCHEMA_VERSION,
    AGENCY_SEED_SALT,
    Action,
    GoalStatus,
    WorldState,
)
from thalos_prime.agency.world_model import WorldModel
from thalos_prime.graph_rag.control_plane import GraphRAGControlPlane
from thalos_prime.ingest import CanonicalArtifact


class AgencyError(Exception):
    """Raised when the Agency subsystem encounters an unrecoverable error."""


class AgencyControlPlane:
    """Lifecycle orchestrator for the Agency subsystem.

    Lifecycle:
        initialize() → validate() → operate() → reconcile()
        → checkpoint() → terminate()

    State surfaces:
        _world_model: WorldModel (Data Plane)
        _inference: ActiveInferenceEngine (Data Plane)
        last_action: most recently selected Action
    """

    def __init__(
        self,
        seed: int,
        workdir: str,
        graph_cp: GraphRAGControlPlane,
        config_hash: str = "default",
        *,
        max_candidate_actions: int = 10,
        goal_stagnation_timesteps: int = 10,
    ) -> None:
        """Initialize the Agency Control Plane.

        Args:
            seed: Deterministic seed (XOR-salted to agency seed).
            workdir: Working directory for logs and checkpoints.
            graph_cp: The GraphRAGControlPlane providing the belief graph.
            config_hash: Stable configuration hash.
            max_candidate_actions: Maximum actions evaluated per step.
            goal_stagnation_timesteps: Timesteps before stagnant goals abandoned.

        """
        self._seed = seed ^ AGENCY_SEED_SALT
        self._workdir = Path(workdir)
        self._graph_cp = graph_cp
        self._config_hash = config_hash
        self._max_candidate_actions = max_candidate_actions
        self._goal_stagnation_timesteps = goal_stagnation_timesteps

        self._world_model: WorldModel | None = None
        self._inference: ActiveInferenceEngine | None = None
        self._initialized: bool = False
        self._terminated: bool = False
        self._log_path: Path | None = None

        self.last_action: Action | None = None

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Set up WorldModel and ActiveInferenceEngine.

        Raises:
            AgencyError: On initialization failure.

        """
        self._workdir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._workdir / "agency_events.jsonl"

        self._world_model = WorldModel(
            graph_cp=self._graph_cp,
            seed=self._seed,
            config_hash=self._config_hash,
        )
        self._inference = ActiveInferenceEngine(
            max_candidate_actions=self._max_candidate_actions,
        )
        self._initialized = True
        self._emit("lifecycle.initialize", {"seed": self._seed})

    def validate(self) -> None:
        """Validate engine and world model readiness.

        Raises:
            AgencyError: If validation fails.

        """
        if not self._initialized:
            raise AgencyError("validate() called before initialize()")
        if self._world_model is None or self._inference is None:
            raise AgencyError("WorldModel or ActiveInferenceEngine not initialized")
        self._emit("lifecycle.validate", {
            "timestep": self._world_model.state.timestep,
            "active_goals": sum(
                1 for g in self._world_model.state.active_goals
                if g.status.value == "active"
            ),
        })

    def operate(self, artifact: CanonicalArtifact | None = None) -> Action:
        """Run one active-inference step.

        Args:
            artifact: Optional new evidence to update the world model.

        Returns:
            The selected Action.

        Raises:
            AgencyError: If operate() called before initialize()/validate().

        """
        if (
            not self._initialized
            or self._world_model is None
            or self._inference is None
        ):
            raise AgencyError("operate() called before initialize()/validate()")

        # Update world model with new evidence if provided
        if artifact is not None:
            self._world_model.update(artifact)

        # Select next action
        action = self._inference.step(
            self._world_model.state,
            self._world_model.belief_graph,
        )

        # Record action in history
        self._world_model.state.action_history.append(action)
        self.last_action = action

        self._emit("lifecycle.operate", {
            "timestep": self._world_model.state.timestep,
            "action_type": action.action_type,
            "action_id": action.id,
        })
        return action

    def reconcile(self) -> None:
        """Mark stagnant goals as ABANDONED and validate predictions.

        Raises:
            AgencyError: If not initialized.

        """
        if not self._initialized or self._world_model is None:
            raise AgencyError("reconcile() called before initialize()")

        current_ts = self._world_model.state.timestep
        abandoned_count = 0
        for goal in self._world_model.state.active_goals:
            age = current_ts - goal.created_at
            if goal.status == GoalStatus.ACTIVE and age >= self._goal_stagnation_timesteps:
                goal.status = GoalStatus.ABANDONED
                abandoned_count += 1

        self._emit("lifecycle.reconcile", {
            "goals_abandoned": abandoned_count,
            "timestep": current_ts,
        })

    def checkpoint(self) -> Path:
        """Serialize WorldState to an atomic JSONL snapshot.

        Returns:
            Path to the written checkpoint file.

        Raises:
            AgencyError: If not initialized.

        """
        if not self._initialized or self._world_model is None:
            raise AgencyError("checkpoint() called before initialize()")

        cp_dir = self._workdir / "agency_checkpoints"
        cp_dir.mkdir(exist_ok=True)
        ts = int(time.time() * 1000)
        cp_path = cp_dir / f"checkpoint_{ts}.json"

        state = self._world_model.state
        payload: dict[str, Any] = {
            "schema_version": AGENCY_SCHEMA_VERSION,
            "seed": self._seed,
            "config_hash": self._config_hash,
            "timestep": state.timestep,
            "state_id": state.id,
            "active_goal_count": len(state.active_goals),
            "action_history_count": len(state.action_history),
            "prediction_count": len(state.prediction_log),
        }
        tmp = cp_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(cp_path)

        self._emit("lifecycle.checkpoint", {"checkpoint_path": str(cp_path)})
        return cp_path

    def terminate(self) -> None:
        """Flush log and mark as terminated."""
        self._emit("lifecycle.terminate", {})
        self._terminated = True

    @property
    def world_state(self) -> WorldState | None:
        """Return the current WorldState, or None if not initialized."""
        if self._world_model is None:
            return None
        return self._world_model.state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append a structured JSONL event to the log."""
        event = {
            "timestamp_ns": time.time_ns(),
            "version": AGENCY_SCHEMA_VERSION,
            "seed": self._seed,
            "module": "agency",
            "event_type": event_type,
            "payload": payload,
        }
        if self._log_path is not None:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event) + "\n")
