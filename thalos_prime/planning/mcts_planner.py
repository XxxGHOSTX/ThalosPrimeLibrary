"""Thalos Prime - Monte Carlo Tree Search (MCTS) Planner.

Control Plane component that implements MCTS with UCB1 selection policy,
deterministic seeded rollouts, backpropagation, and configurable simulation
policies for autonomous planning.

Control Plane boundary: coordinates planning strategy only.
No data-plane retrieval or computational work belongs here.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)

# UCB1 exploration constant (sqrt(2) is theoretically optimal)
DEFAULT_EXPLORATION_CONSTANT = math.sqrt(2.0)


@dataclass
class MCTSNode:
    """A node in the MCTS search tree.

    Attributes:
        state: String representation of the current state/action.
        visits: Number of times this node has been visited during search.
        total_reward: Cumulative reward accumulated across all simulations.
        children: Ordered list of child nodes (expanded actions).
        parent_state: State string of the parent node (empty for root).
        depth: Depth of this node in the search tree (root = 0).
        seed: Deterministic seed used for rollouts from this node.

    """

    state: str
    visits: int = 0
    total_reward: float = 0.0
    children: list[MCTSNode] = field(default_factory=list)
    parent_state: str = ""
    depth: int = 0
    seed: int = 0

    @property
    def mean_reward(self) -> float:
        """Average reward per visit.

        Returns:
            Mean reward, or 0.0 if unvisited.

        """
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    def to_dict(self) -> dict[str, object]:
        """Serialize node to dictionary.

        Returns:
            Dictionary representation of this MCTS node.

        """
        return {
            "state": self.state,
            "visits": self.visits,
            "total_reward": self.total_reward,
            "mean_reward": self.mean_reward,
            "depth": self.depth,
            "seed": self.seed,
            "children_count": len(self.children),
        }


@dataclass
class MCTSResult:
    """Result from an MCTS planning run.

    Attributes:
        best_action: The highest-scoring immediate action from root.
        best_path: Sequence of actions along the best path.
        root: The root MCTSNode with full tree statistics.
        iterations_run: Number of MCTS iterations performed.
        total_simulations: Total rollout simulations executed.

    """

    best_action: str
    best_path: list[str]
    root: MCTSNode
    iterations_run: int
    total_simulations: int

    def to_dict(self) -> dict[str, object]:
        """Serialize result to dictionary.

        Returns:
            Dictionary representation of this result.

        """
        return {
            "best_action": self.best_action,
            "best_path": self.best_path,
            "iterations_run": self.iterations_run,
            "total_simulations": self.total_simulations,
            "root_visits": self.root.visits,
        }


class MCTSPlanner(BaseLifecycleComponent):
    """Monte Carlo Tree Search planner with UCB1 selection.

    Uses seeded random for determinism: identical (state, seed, iterations)
    inputs always produce identical search trees and action selections.
    Configurable action generator and reward evaluator allow plugging in
    domain-specific simulation policies.
    """

    def __init__(
        self,
        component_seed: int = 0,
        exploration_constant: float = DEFAULT_EXPLORATION_CONSTANT,
    ) -> None:
        """Initialize the MCTS planner.

        Args:
            component_seed: Seed for the component lifecycle.
            exploration_constant: UCB1 exploration-exploitation tradeoff
                parameter. Higher values favor exploration.

        """
        super().__init__("MCTSPlanner", seed=component_seed)
        self._exploration_constant = exploration_constant
        self._plan_count: int = 0
        self._total_iterations: int = 0

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize planner state."""
        self._plan_count = 0
        self._total_iterations = 0
        self._initialized = True
        self._emit_event("initialize", "MCTS planner ready")

    def validate(self) -> ValidationResult:
        """Validate planner configuration.

        Returns:
            ValidationResult indicating whether the planner is ready.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="MCTSPlanner not initialized; call initialize() first",
            )
        if self._exploration_constant < 0:
            return ValidationResult(
                valid=False,
                message=(
                    f"Invalid exploration_constant: {self._exploration_constant}. "
                    f"Must be >= 0."
                ),
            )
        return ValidationResult(
            valid=True,
            message=(
                f"MCTSPlanner ready: plans={self._plan_count} "
                f"iterations={self._total_iterations}"
            ),
        )

    def operate(self) -> None:
        """Log current planner statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"plans={self._plan_count} iterations={self._total_iterations}",
        )

    def reconcile(self) -> None:
        """Reconcile planner state; fix negative counters."""
        self._plan_count = max(self._plan_count, 0)
        self._total_iterations = max(self._total_iterations, 0)
        self._emit_event(
            "reconcile",
            f"plans={self._plan_count} iterations={self._total_iterations}",
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize planner state.

        Returns:
            Dict with component name, seed, and counters.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "exploration_constant": self._exploration_constant,
            "plan_count": self._plan_count,
            "total_iterations": self._total_iterations,
        }
        self._emit_event("checkpoint", f"plans={self._plan_count}")
        return state

    def terminate(self) -> None:
        """Reset planner state."""
        self._plan_count = 0
        self._total_iterations = 0
        self._initialized = False
        self._emit_event("terminate", "planner cleared")

    # ------------------------------------------------------------------
    # MCTS core algorithm
    # ------------------------------------------------------------------

    def search(
        self,
        root_state: str,
        action_generator: Callable[[str], list[str]],
        reward_evaluator: Callable[[str], float],
        iterations: int = 100,
        max_depth: int = 10,
        seed: int = 42,
    ) -> MCTSResult:
        """Run MCTS from a root state for a given number of iterations.

        Deterministic: identical parameters always produce identical results.

        Args:
            root_state: String representation of the initial state.
            action_generator: Function that generates possible actions from a state.
                Returns a list of action/state strings.
            reward_evaluator: Function that evaluates a terminal state and returns
                a reward in [0.0, 1.0].
            iterations: Number of MCTS iterations to run.
            max_depth: Maximum depth for rollout simulations.
            seed: Deterministic seed for this search run.

        Returns:
            MCTSResult with the best action, path, and search statistics.

        """
        rng = random.Random(seed)  # noqa: S311  # nosec B311
        root = MCTSNode(state=root_state, depth=0, seed=seed)

        total_simulations = 0
        for _ in range(iterations):
            # Selection
            node = self._select(root, rng)
            # Expansion
            if node.visits > 0 and node.depth < max_depth:
                node = self._expand(node, action_generator, rng)
            # Rollout
            reward = self._simulate(node, reward_evaluator, action_generator, max_depth, rng)
            total_simulations += 1
            # Backpropagation
            self._backpropagate(node, reward, root)

        self._plan_count += 1
        self._total_iterations += iterations

        best_action, best_path = self._extract_best(root)
        self._emit_event(
            "search",
            f"root={root_state!r} iterations={iterations} best={best_action!r}",
        )
        return MCTSResult(
            best_action=best_action,
            best_path=best_path,
            root=root,
            iterations_run=iterations,
            total_simulations=total_simulations,
        )

    def _ucb1_score(self, node: MCTSNode, parent_visits: int) -> float:
        """Compute UCB1 score for node selection.

        Args:
            node: The child node to score.
            parent_visits: Total visits of the parent node.

        Returns:
            UCB1 score combining exploitation and exploration.

        """
        if node.visits == 0:
            return float("inf")
        exploitation = node.mean_reward
        exploration = self._exploration_constant * math.sqrt(
            math.log(parent_visits) / node.visits
        )
        return exploitation + exploration

    def _select(self, node: MCTSNode, rng: random.Random) -> MCTSNode:
        """Select a leaf node using UCB1 tree policy.

        Args:
            node: Current node to select from.
            rng: Seeded random instance (unused here but passed for consistency).

        Returns:
            Selected leaf node for expansion.

        """
        _ = rng  # UCB1 is deterministic given visit counts
        current = node
        while current.children:
            best_score = -1.0
            best_child = current.children[0]
            for child in current.children:
                score = self._ucb1_score(child, current.visits)
                if score > best_score:
                    best_score = score
                    best_child = child
            current = best_child
        return current

    def _expand(
        self,
        node: MCTSNode,
        action_generator: Callable[[str], list[str]],
        rng: random.Random,
    ) -> MCTSNode:
        """Expand a leaf node by generating child actions.

        Args:
            node: The leaf node to expand.
            action_generator: Function generating possible actions.
            rng: Seeded random instance.

        Returns:
            One of the newly created child nodes.

        """
        if node.children:
            return node
        actions = action_generator(node.state)
        if not actions:
            return node
        child_seed_base = rng.randint(0, 2**31 - 1)
        for i, action in enumerate(actions):
            child = MCTSNode(
                state=action,
                parent_state=node.state,
                depth=node.depth + 1,
                seed=child_seed_base + i,
            )
            node.children.append(child)
        # Return first unvisited child
        return node.children[0]

    def _simulate(
        self,
        node: MCTSNode,
        reward_evaluator: Callable[[str], float],
        action_generator: Callable[[str], list[str]],
        max_depth: int,
        rng: random.Random,
    ) -> float:
        """Run a random rollout simulation from the given node.

        Args:
            node: Starting node for simulation.
            reward_evaluator: Evaluates terminal states for reward.
            action_generator: Generates possible actions for rollout.
            max_depth: Maximum rollout depth.
            rng: Seeded random instance.

        Returns:
            Reward value from the rollout in [0.0, 1.0].

        """
        current_state = node.state
        current_depth = node.depth
        while current_depth < max_depth:
            actions = action_generator(current_state)
            if not actions:
                break
            current_state = rng.choice(actions)
            current_depth += 1
        return reward_evaluator(current_state)

    def _backpropagate(
        self,
        node: MCTSNode,
        reward: float,
        root: MCTSNode,
    ) -> None:
        """Backpropagate reward from leaf to root through the tree.

        Uses parent_state matching to trace path back to root.

        Args:
            node: The leaf node where simulation ended.
            reward: The reward to propagate.
            root: The root node of the search tree.

        """
        # Build index: state -> node for path tracing
        path = self._trace_path(node, root)
        for path_node in path:
            path_node.visits += 1
            path_node.total_reward += reward

    def _trace_path(self, leaf: MCTSNode, root: MCTSNode) -> list[MCTSNode]:
        """Trace path from root to leaf using BFS.

        Args:
            leaf: The target leaf node.
            root: The root node.

        Returns:
            List of nodes from leaf to root (inclusive).

        """
        # Build parent map via BFS
        parent_map: dict[str, MCTSNode | None] = {root.state: None}
        queue: list[MCTSNode] = [root]
        target_node: MCTSNode | None = None

        while queue:
            current = queue.pop(0)
            if current is leaf:
                target_node = current
                break
            for child in current.children:
                if child.state not in parent_map:
                    parent_map[child.state] = current
                    queue.append(child)

        # Trace back from leaf to root
        path: list[MCTSNode] = []
        current_node: MCTSNode | None = target_node if target_node is not None else leaf
        while current_node is not None:
            path.append(current_node)
            parent = parent_map.get(current_node.state)
            current_node = parent

        return path

    def _extract_best(self, root: MCTSNode) -> tuple[str, list[str]]:
        """Extract the best action and path from the search tree.

        Selects the child with the highest visit count (most robust selection).

        Args:
            root: Root of the MCTS tree.

        Returns:
            Tuple of (best immediate action, full best path).

        """
        if not root.children:
            return root.state, [root.state]

        best_child = max(root.children, key=lambda c: c.visits)
        best_action = best_child.state

        # Follow most-visited path
        path = [root.state]
        current = root
        while current.children:
            best = max(current.children, key=lambda c: c.visits)
            path.append(best.state)
            current = best

        return best_action, path

    def best_action(self, root: MCTSNode) -> str:
        """Get the best immediate action from a completed search tree.

        Args:
            root: Root node of a completed MCTS search.

        Returns:
            The state string of the most-visited child.

        """
        if not root.children:
            return root.state
        return max(root.children, key=lambda c: c.visits).state

    @property
    def plan_count(self) -> int:
        """Number of search runs completed."""
        return self._plan_count

    @property
    def total_iterations(self) -> int:
        """Total MCTS iterations across all search runs."""
        return self._total_iterations


__all__ = ["MCTSNode", "MCTSPlanner", "MCTSResult"]
