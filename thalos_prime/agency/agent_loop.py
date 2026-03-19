"""Thalos Prime - Agent Reasoning Loop.

Control Plane component that orchestrates a full neuro-symbolic agent cycle:
plan → predict → act → observe → update beliefs. Ties together the
TreeOfThoughtsPlanner, WorldModel, BeliefTracker, and ActionExecutor into
a deterministic perceive-plan-act loop.

Control Plane boundary: coordinates lifecycle and state transitions only.
Delegates all computational work to Data Plane sub-components.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from thalos_prime.agency.action_executor import ActionExecutor, ActionResult
from thalos_prime.agency.belief_tracker import BeliefEntry, BeliefTracker
from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent
from thalos_prime.planning.tree_of_thoughts import TreeOfThoughtsPlanner
from thalos_prime.simulation.world_model import WorldModel, WorldState

logger = logging.getLogger(__name__)


@dataclass
class AgentStepResult:
    """Result of a single agent reasoning step.

    Attributes:
        step: Zero-based step index.
        chosen_action: The action selected by the planner.
        action_result: Result from executing the chosen action.
        world_state: World state after observation.
        belief_hash: State hash of beliefs after this step.
        timestamp: ISO-8601 timestamp of this step.

    """

    step: int
    chosen_action: str
    action_result: ActionResult
    world_state: WorldState
    belief_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this step result.

        """
        return {
            "step": self.step,
            "chosen_action": self.chosen_action,
            "action_result": self.action_result.to_dict(),
            "world_state": self.world_state.to_dict(),
            "belief_hash": self.belief_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentResult:
    """Result of a complete agent reasoning cycle.

    Attributes:
        query: The original query that initiated the cycle.
        steps: Ordered list of AgentStepResult for each step taken.
        final_answer: Synthesized final answer from belief state.
        total_steps: Number of steps executed.
        final_belief_hash: State hash of beliefs after the cycle.

    """

    query: str
    steps: list[AgentStepResult]
    final_answer: str
    total_steps: int
    final_belief_hash: str

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this agent result.

        """
        return {
            "query": self.query,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "total_steps": self.total_steps,
            "final_belief_hash": self.final_belief_hash,
        }


class AgentLoop(BaseLifecycleComponent):
    """Control Plane agent that orchestrates perceive-plan-act cycles.

    Composes TreeOfThoughtsPlanner, WorldModel, BeliefTracker, and
    ActionExecutor into a deterministic reasoning loop. Given a query
    the agent:

    1. Plans candidate reasoning paths (TreeOfThoughtsPlanner).
    2. Selects the best path and extracts the next action.
    3. Predicts the next world state (WorldModel).
    4. Executes the action (ActionExecutor).
    5. Observes the result and updates beliefs (BeliefTracker).
    6. Repeats until max_steps or convergence.
    """

    def __init__(
        self,
        planner: TreeOfThoughtsPlanner,
        world_model: WorldModel,
        belief_tracker: BeliefTracker,
        action_executor: ActionExecutor,
        seed: int = 0,
    ) -> None:
        """Initialize the agent loop with sub-components.

        Args:
            planner: TreeOfThoughtsPlanner for reasoning path generation.
            world_model: WorldModel for state prediction.
            belief_tracker: BeliefTracker for belief state management.
            action_executor: ActionExecutor for action execution.
            seed: Deterministic seed for the agent cycle.

        """
        super().__init__("AgentLoop", seed=seed)
        self._planner = planner
        self._world_model = world_model
        self._belief_tracker = belief_tracker
        self._action_executor = action_executor
        self._step_count: int = 0
        self._cycle_count: int = 0

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the agent loop and all sub-components."""
        self._planner.initialize()
        self._world_model.initialize()
        self._belief_tracker.initialize()
        self._action_executor.initialize()
        self._step_count = 0
        self._cycle_count = 0
        self._initialized = True
        self._emit_event("initialize", "all sub-components initialized")
        logger.debug("AgentLoop initialized")

    def validate(self) -> ValidationResult:
        """Validate that all sub-components are ready.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="AgentLoop not initialized; call initialize() first",
            )
        sub_results = [
            self._planner.validate(),
            self._world_model.validate(),
            self._belief_tracker.validate(),
            self._action_executor.validate(),
        ]
        invalid = [r for r in sub_results if not r.valid]
        if invalid:
            messages = "; ".join(r.message for r in invalid)
            return ValidationResult(
                valid=False,
                message=f"Sub-component validation failed: {messages}",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"AgentLoop ready: steps={self._step_count} cycles={self._cycle_count}"
            ),
        )

    def operate(self) -> None:
        """Log current statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"steps={self._step_count} cycles={self._cycle_count}",
        )

    def reconcile(self) -> None:
        """Reconcile counters and delegate to sub-components."""
        self._step_count = max(self._step_count, 0)
        self._cycle_count = max(self._cycle_count, 0)
        self._planner.reconcile()
        self._world_model.reconcile()
        self._belief_tracker.reconcile()
        self._action_executor.reconcile()
        self._emit_event(
            "reconcile",
            f"steps={self._step_count} cycles={self._cycle_count}",
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize agent loop state including sub-component checkpoints.

        Returns:
            Dict with component name, seed, counters, and sub-checkpoints.

        """
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "step_count": self._step_count,
            "cycle_count": self._cycle_count,
            "planner": self._planner.checkpoint(),
            "world_model": self._world_model.checkpoint(),
            "belief_tracker": self._belief_tracker.checkpoint(),
            "action_executor": self._action_executor.checkpoint(),
        }
        self._emit_event("checkpoint", f"steps={self._step_count}")
        return state

    def terminate(self) -> None:
        """Reset agent loop state and terminate sub-components."""
        self._planner.terminate()
        self._world_model.terminate()
        self._belief_tracker.terminate()
        self._action_executor.terminate()
        self._step_count = 0
        self._cycle_count = 0
        self._initialized = False
        self._emit_event("terminate", "all sub-components terminated")
        logger.debug("AgentLoop terminated")

    # ------------------------------------------------------------------
    # Agent reasoning methods
    # ------------------------------------------------------------------

    def step(
        self,
        query: str,
        world_state: WorldState,
        step_index: int = 0,
        seed: int = 42,
    ) -> AgentStepResult:
        """Execute a single perceive-plan-act step.

        1. Plan reasoning paths for the query.
        2. Select the best path and extract an action name.
        3. Predict the next world state.
        4. Execute the action.
        5. Observe the result and update beliefs.

        Args:
            query: The query driving this reasoning step.
            world_state: Current world state.
            step_index: Zero-based step counter.
            seed: Deterministic seed for planning in this step.

        Returns:
            AgentStepResult with action, result, and updated state.

        """
        root = self._planner.plan(
            query,
            evaluator=lambda t: min(len(t) / 100.0, 1.0),
            breadth=3,
            depth=2,
            seed=seed + step_index,
        )
        best = self._planner.best_path(root)
        chosen_action = best[-1] if best else query

        predicted_state = self._world_model.predict(world_state, chosen_action)

        action_result = self._action_executor.execute(
            chosen_action,
            {"query": query, "step": step_index},
        )

        observation: dict[str, object] = {
            "_step_result": {
                "action": chosen_action,
                "success": action_result.success,
            },
        }
        observed_state = self._world_model.observe(predicted_state, observation)

        self._belief_tracker.update_belief(
            key=f"step_{step_index}_action",
            value=chosen_action,
            confidence=1.0 if action_result.success else 0.3,
            source="agent_loop",
        )
        if action_result.success:
            self._belief_tracker.update_belief(
                key=f"step_{step_index}_output",
                value=str(action_result.output),
                confidence=0.9,
                source="action_executor",
            )

        self._step_count += 1
        belief_hash = self._belief_tracker.state_hash()
        logger.debug(
            "AgentLoop.step: step=%d action=%r success=%s belief_hash=%s",
            step_index,
            chosen_action,
            action_result.success,
            belief_hash[:16],
        )

        return AgentStepResult(
            step=step_index,
            chosen_action=chosen_action,
            action_result=action_result,
            world_state=observed_state,
            belief_hash=belief_hash,
        )

    def run(
        self,
        query: str,
        max_steps: int = 5,
        seed: int = 42,
    ) -> AgentResult:
        """Execute a complete agent reasoning cycle.

        Repeatedly calls step() until max_steps is reached or the belief
        state converges (hash unchanged between consecutive steps).

        Args:
            query: The query to reason about.
            max_steps: Maximum number of reasoning steps.
            seed: Deterministic seed for the cycle.

        Returns:
            AgentResult with all steps and a final synthesized answer.

        """
        world_state = WorldState()
        steps: list[AgentStepResult] = []
        prev_hash = ""

        for i in range(max_steps):
            result = self.step(query, world_state, step_index=i, seed=seed)
            steps.append(result)
            world_state = result.world_state

            if result.belief_hash == prev_hash:
                logger.info(
                    "AgentLoop.run: belief state converged at step %d", i,
                )
                break
            prev_hash = result.belief_hash

        beliefs = self._belief_tracker.query_beliefs()
        final_answer = _synthesize_answer(query, beliefs)

        self._cycle_count += 1
        final_hash = self._belief_tracker.state_hash()
        self._emit_event(
            "run",
            f"query={query!r} steps={len(steps)} seed={seed}",
        )

        return AgentResult(
            query=query,
            steps=steps,
            final_answer=final_answer,
            total_steps=len(steps),
            final_belief_hash=final_hash,
        )

    def state_hash(self) -> str:
        """Compute a deterministic hash of the full agent state.

        Returns:
            Hex digest combining step count, cycle count, and belief hash.

        """
        hasher = hashlib.sha256()
        hasher.update(f"steps:{self._step_count}".encode())
        hasher.update(f"cycles:{self._cycle_count}".encode())
        hasher.update(self._belief_tracker.state_hash().encode())
        return hasher.hexdigest()


def _synthesize_answer(
    query: str,
    beliefs: list[BeliefEntry],
) -> str:
    """Synthesize a final answer from beliefs.

    Deterministic: joins belief values sorted by key.

    Args:
        query: The original query.
        beliefs: Sorted list of active beliefs.

    Returns:
        Synthesized answer string.

    """
    if not beliefs:
        return f"No beliefs accumulated for query: {query}"
    parts = [f"[{b.key}] {b.value} (conf={b.confidence:.2f})" for b in beliefs]
    return f"Answer for '{query}': " + "; ".join(parts)


__all__ = ["AgentLoop", "AgentResult", "AgentStepResult"]
