"""WorldModel — wraps the belief graph and implements the update protocol.

The WorldModel holds a reference to the KnowledgeGraph (belief_graph) and
manages WorldState updates, goal evaluation, and prediction generation.

Data Plane component — no lifecycle or coordination logic.
"""

from __future__ import annotations

from hashlib import sha256

from thalos_prime.agency.goal_evaluator import GoalEvaluator
from thalos_prime.agency.prediction_engine import PredictionEngine
from thalos_prime.agency.schema import (
    AGENCY_SCHEMA_VERSION,
    Goal,
    GoalStatus,
    WorldState,
)
from thalos_prime.graph_rag.control_plane import GraphRAGControlPlane
from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph
from thalos_prime.ingest import CanonicalArtifact


def _world_state_id(seed: int, timestep: int, config_hash: str) -> str:
    return sha256(f"{seed}:{timestep}:{config_hash}".encode()).hexdigest()


class WorldModel:
    """Data Plane component that manages the belief graph and WorldState.

    Update protocol (called after new evidence arrives):
        1. Ingest evidence into belief_graph via GraphRAGControlPlane.
        2. Increment timestep.
        3. Re-evaluate all ACTIVE Goals.
        4. Generate new Predictions.
        5. Update WorldState.
    """

    def __init__(
        self,
        graph_cp: GraphRAGControlPlane,
        seed: int,
        config_hash: str,
    ) -> None:
        """Initialize the WorldModel.

        Args:
            graph_cp: The GraphRAGControlPlane for belief graph ingestion.
            seed: Deterministic seed.
            config_hash: Stable config hash for state ID derivation.

        """
        self._graph_cp = graph_cp
        self._seed = seed
        self._config_hash = config_hash
        self._evaluator = GoalEvaluator()
        self._predictor = PredictionEngine()

        self.state = WorldState(
            id=_world_state_id(seed, 0, config_hash),
            seed=seed,
            timestep=0,
            config_hash=config_hash,
        )

    @property
    def belief_graph(self) -> KnowledgeGraph:
        """Return the current belief graph."""
        return self._graph_cp.graph

    def update(self, artifact: CanonicalArtifact) -> WorldState:
        """Update the world model with a new evidence artifact.

        Args:
            artifact: New evidence to incorporate.

        Returns:
            Updated WorldState.

        """
        # Step 1 — ingest into belief graph
        self._graph_cp.operate([artifact])

        # Step 2 — increment timestep
        new_timestep = self.state.timestep + 1

        # Step 3 — re-evaluate goals
        updated_goals: list[Goal] = []
        for goal in self.state.active_goals:
            new_status = self._evaluator.evaluate(goal, self.belief_graph)
            updated_goals.append(
                Goal(
                    id=goal.id,
                    goal_text=goal.goal_text,
                    priority=goal.priority,
                    status=new_status,
                    created_at=goal.created_at,
                    version=AGENCY_SCHEMA_VERSION,
                )
            )

        # Step 4 — generate predictions
        new_predictions = self._predictor.generate(
            self.belief_graph, self._seed, new_timestep
        )

        # Step 5 — build new WorldState
        self.state = WorldState(
            id=_world_state_id(self._seed, new_timestep, self._config_hash),
            seed=self._seed,
            timestep=new_timestep,
            config_hash=self._config_hash,
            active_goals=updated_goals,
            action_history=list(self.state.action_history),
            prediction_log=new_predictions,
        )
        return self.state

    def add_goal(self, goal_text: str, priority: float = 0.5) -> Goal:
        """Add a new ACTIVE Goal to the world state.

        Args:
            goal_text: Description of the goal.
            priority: Priority in [0.0, 1.0].

        Returns:
            The created Goal.

        """
        goal_id = sha256(
            f"{goal_text}:{self.state.timestep}".encode()
        ).hexdigest()
        goal = Goal(
            id=goal_id,
            goal_text=goal_text,
            priority=max(0.0, min(1.0, priority)),
            status=GoalStatus.ACTIVE,
            created_at=self.state.timestep,
            version=AGENCY_SCHEMA_VERSION,
        )
        self.state.active_goals.append(goal)
        return goal
