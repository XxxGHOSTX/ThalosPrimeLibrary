"""Thalos Prime - World Model Simulation.

Data Plane component that provides deterministic world-state prediction,
observation merging, and divergence scoring.

Data Plane boundary: simulation only — no lifecycle orchestration logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.library_of_sense.retrieval.knowledge_graph import GraphTriple
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)


@dataclass
class WorldState:
    """A snapshot of the world at a point in time.

    Attributes:
        entities: Mapping of entity name -> attribute dict.
        relations: List of GraphTriple relations between entities.
        timestamp: Logical clock value (integer, not wall clock).
        version: Monotonically increasing version counter.

    """

    entities: dict[str, dict[str, object]] = field(default_factory=dict)
    relations: list[GraphTriple] = field(default_factory=list)
    timestamp: int = 0
    version: int = 0

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this WorldState.

        """
        return {
            "entities": {k: dict(v) for k, v in self.entities.items()},
            "relations": [r.to_dict() for r in self.relations],
            "timestamp": self.timestamp,
            "version": self.version,
        }


class WorldModel(BaseLifecycleComponent):
    """Deterministic world-state simulator.

    Predicts next states from (state, action), merges observations into state,
    and computes divergence between two states. Identical inputs always produce
    identical outputs.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize the WorldModel.

        Args:
            seed: Deterministic seed for replay identification.

        """
        super().__init__("WorldModel", seed=seed)
        self._predict_count: int = 0
        self._observe_count: int = 0

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the world model and reset counters."""
        self._predict_count = 0
        self._observe_count = 0
        self._initialized = True
        self._emit_event("initialize", "counters reset, initialized=True")
        logger.debug("WorldModel initialized")

    def validate(self) -> ValidationResult:
        """Validate that the world model is ready.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="WorldModel not initialized; call initialize() first",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"WorldModel ready: predicts={self._predict_count} "
                f"observes={self._observe_count}"
            ),
        )

    def operate(self) -> None:
        """Log current statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"predicts={self._predict_count} observes={self._observe_count}",
        )

    def reconcile(self) -> None:
        """Reconcile counters to non-negative values."""
        self._predict_count = max(self._predict_count, 0)
        self._observe_count = max(self._observe_count, 0)
        self._emit_event(
            "reconcile",
            f"predicts={self._predict_count} observes={self._observe_count}",
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize world model state.

        Returns:
            Dict with component name, seed, and operation counters.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "predict_count": self._predict_count,
            "observe_count": self._observe_count,
        }
        self._emit_event("checkpoint", f"predicts={self._predict_count}")
        return state

    def terminate(self) -> None:
        """Reset world model state."""
        self._predict_count = 0
        self._observe_count = 0
        self._initialized = False
        self._emit_event("terminate", "counters reset, initialized=False")
        logger.debug("WorldModel terminated")

    # ------------------------------------------------------------------
    # Data Plane methods
    # ------------------------------------------------------------------

    def predict(self, state: WorldState, action: str) -> WorldState:
        """Predict the next world state given a current state and an action.

        Deterministic: identical (state, action) inputs produce identical output.
        Increments timestamp and version.

        Args:
            state: Current world state.
            action: Action string describing the transition.

        Returns:
            New WorldState with updated entities, incremented timestamp and version.

        """
        new_entities: dict[str, dict[str, object]] = {
            k: dict(v) for k, v in state.entities.items()
        }
        new_entities.setdefault("_action_log", {})
        action_log = new_entities["_action_log"]
        action_log[str(state.timestamp)] = action

        new_state = WorldState(
            entities=new_entities,
            relations=list(state.relations),
            timestamp=state.timestamp + 1,
            version=state.version + 1,
        )
        self._predict_count += 1
        logger.debug(
            "WorldModel.predict: action=%r ts=%d -> ts=%d",
            action,
            state.timestamp,
            new_state.timestamp,
        )
        return new_state

    def observe(
        self,
        state: WorldState,
        observation: dict[str, object],
    ) -> WorldState:
        """Update a world state with new observation data.

        Merges entity attributes and appends new relations. Increments version.

        Args:
            state: Current world state to update.
            observation: Dict mapping entity names to attribute dicts (nested),
                plus an optional ``"relations"`` key with list of GraphTriple dicts.

        Returns:
            New WorldState with merged entities and appended relations.

        """
        new_entities: dict[str, dict[str, object]] = {
            k: dict(v) for k, v in state.entities.items()
        }

        new_relations: list[GraphTriple] = list(state.relations)

        for key, value in observation.items():
            if key == "relations" and isinstance(value, list):
                new_relations.extend(
                    rel for rel in value if isinstance(rel, GraphTriple)
                )
            elif isinstance(value, dict):
                entity_attrs = new_entities.setdefault(key, {})
                entity_attrs.update(value)
            else:
                new_entities.setdefault(key, {})[key] = value

        new_state = WorldState(
            entities=new_entities,
            relations=new_relations,
            timestamp=state.timestamp,
            version=state.version + 1,
        )
        self._observe_count += 1
        logger.debug(
            "WorldModel.observe: %d new keys merged, version=%d",
            len(observation),
            new_state.version,
        )
        return new_state

    def divergence(self, state_a: WorldState, state_b: WorldState) -> float:
        """Compute divergence score between two world states.

        0.0 = identical, 1.0 = completely different.
        Based on entity key overlap and relation set overlap.

        Args:
            state_a: First world state.
            state_b: Second world state.

        Returns:
            Float in [0.0, 1.0] representing divergence.

        """
        keys_a = set(state_a.entities.keys())
        keys_b = set(state_b.entities.keys())
        all_keys = keys_a | keys_b
        if not all_keys:
            entity_divergence = 0.0
        else:
            common_keys = keys_a & keys_b
            entity_divergence = 1.0 - len(common_keys) / len(all_keys)

        def _triple_key(t: GraphTriple) -> tuple[str, str, str]:
            return (t.subject, t.predicate, t.obj)

        rels_a = {_triple_key(r) for r in state_a.relations}
        rels_b = {_triple_key(r) for r in state_b.relations}
        all_rels = rels_a | rels_b
        if not all_rels:
            relation_divergence = 0.0
        else:
            common_rels = rels_a & rels_b
            relation_divergence = 1.0 - len(common_rels) / len(all_rels)

        return (entity_divergence + relation_divergence) / 2.0


__all__ = ["WorldModel", "WorldState"]
