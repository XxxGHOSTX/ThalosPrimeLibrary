"""ActiveInferenceEngine — Data Plane component for action selection.

Implements the deterministic free-energy proxy to select the next Action
that minimally contradicts the current belief graph while maximally
progressing toward ACTIVE goals.

Data Plane component — no lifecycle or coordination logic.
"""

from __future__ import annotations

from hashlib import sha256

from thalos_prime.agency.schema import (
    AGENCY_SCHEMA_VERSION,
    Action,
    Goal,
    GoalStatus,
    WorldState,
)
from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph

_LOW_CONFIDENCE_THRESHOLD = 0.5
_MIN_ENTITY_EDGES = 2


def _action_id(action_type: str, params: dict[str, str], timestep: int) -> str:
    sorted_params = "|".join(f"{k}={v}" for k, v in sorted(params.items()))
    return sha256(f"{action_type}:{sorted_params}:{timestep}".encode()).hexdigest()


def _goal_relevance(action: Action, goal: Goal) -> float:
    """Fraction of goal key words present in action expected_outcome."""
    goal_words = set(goal.goal_text.lower().split())
    outcome_words = set(action.expected_outcome.lower().split())
    if not goal_words:
        return 0.0
    return len(goal_words & outcome_words) / len(goal_words)


def _goal_cost(action: Action, goals: list[Goal]) -> float:
    """1 - max(priority * relevance) over ACTIVE goals; lower = better."""
    active = [g for g in goals if g.status == GoalStatus.ACTIVE]
    if not active:
        return 1.0
    max_val = max(g.priority * _goal_relevance(action, g) for g in active)
    return 1.0 - max_val


def _surprise_cost(action: Action, graph: KnowledgeGraph) -> float:
    """1 - mean(edge weight for edges reachable from action entities).

    Lower = action is consistent with existing beliefs.
    """
    if graph.edge_count == 0:
        return 1.0
    outcome_words = action.expected_outcome.lower().split()
    entity_ids: list[str] = []
    for word in outcome_words:
        node = graph.find_entity_by_name(word)
        if node:
            entity_ids.append(node.id)

    if not entity_ids:
        return 1.0

    weights: list[float] = []
    for eid in entity_ids:
        for _, edge_attrs in graph.neighbors_of(eid):
            weights.append(float(edge_attrs.get("weight", 0.0)))

    if not weights:
        return 1.0
    return 1.0 - (sum(weights) / len(weights))


def _free_energy_proxy(action: Action, state: WorldState, graph: KnowledgeGraph) -> float:
    """Compute deterministic free-energy proxy for an action."""
    return _goal_cost(action, state.active_goals) + _surprise_cost(action, graph)


def _generate_candidates(
    state: WorldState,
    graph: KnowledgeGraph,
    max_candidates: int,
) -> list[Action]:
    """Generate candidate actions from goals, predictions, and graph gaps."""
    candidates: list[Action] = []

    # One "reason" action per ACTIVE goal
    for goal in state.active_goals:
        if goal.status != GoalStatus.ACTIVE:
            continue
        action_type = "reason"
        params: dict[str, str] = {"goal_id": goal.id}
        action = Action(
            id=_action_id(action_type, params, state.timestep),
            action_type=action_type,
            params=params,
            expected_outcome=goal.goal_text,
            actual_outcome=None,
            timestep=state.timestep,
            version=AGENCY_SCHEMA_VERSION,
        )
        candidates.append(action)

    # One "verify" action per low-confidence prediction
    for pred in state.prediction_log:
        if isinstance(pred.confidence, float) and pred.confidence < _LOW_CONFIDENCE_THRESHOLD:
            action_type = "verify"
            params = {"prediction_id": pred.id}
            action = Action(
                id=_action_id(action_type, params, state.timestep),
                action_type=action_type,
                params=params,
                expected_outcome=pred.prediction_text,
                actual_outcome=None,
                timestep=state.timestep,
                version=AGENCY_SCHEMA_VERSION,
            )
            candidates.append(action)

    # One "ingest" action per EntityNode with few incoming edges
    for nid, attrs in sorted(graph._graph.nodes(data=True), key=lambda x: str(x[0])):
        if attrs.get("node_type") != "entity":
            continue
        if graph._graph.in_degree(nid) < _MIN_ENTITY_EDGES:
            canonical = str(attrs.get("canonical_name", str(nid)))
            action_type = "ingest"
            params = {"entity": canonical}
            action = Action(
                id=_action_id(action_type, params, state.timestep),
                action_type=action_type,
                params=params,
                expected_outcome=f"more context about {canonical}",
                actual_outcome=None,
                timestep=state.timestep,
                version=AGENCY_SCHEMA_VERSION,
            )
            candidates.append(action)

    # Deduplicate by id, sort: free_energy DESC inverted (lower = better) → id ASC
    seen: set[str] = set()
    unique: list[Action] = []
    for c in candidates:
        if c.id not in seen:
            seen.add(c.id)
            unique.append(c)

    unique.sort(key=lambda a: (_free_energy_proxy(a, state, graph), a.id))
    return unique[:max_candidates]


class ActiveInferenceEngine:
    """Data Plane engine that selects the next action via free-energy proxy.

    step(world_state) → Action
    """

    def __init__(self, max_candidate_actions: int = 10) -> None:
        """Initialize the engine.

        Args:
            max_candidate_actions: Maximum candidates to evaluate per step.

        """
        self.max_candidate_actions = max_candidate_actions

    def step(self, state: WorldState, graph: KnowledgeGraph) -> Action:
        """Select the next best action.

        Args:
            state: Current WorldState.
            graph: Current belief graph.

        Returns:
            The selected Action (lowest free-energy proxy).

        """
        candidates = _generate_candidates(state, graph, self.max_candidate_actions)

        if not candidates:
            # No candidates — emit a no-op query action
            noop: dict[str, str] = {}
            return Action(
                id=_action_id("query", noop, state.timestep),
                action_type="query",
                params=noop,
                expected_outcome="no active goals or predictions",
                actual_outcome=None,
                timestep=state.timestep,
                version=AGENCY_SCHEMA_VERSION,
            )

        # Best action = lowest free_energy_proxy; tie-break: lexicographically smallest id
        return min(candidates, key=lambda a: (_free_energy_proxy(a, state, graph), a.id))
