"""Tests for AgentLoop agency subsystem."""

from __future__ import annotations

from thalos_prime.agency.action_executor import ActionExecutor, ActionResult
from thalos_prime.agency.agent_loop import AgentLoop, AgentResult, AgentStepResult
from thalos_prime.agency.belief_tracker import BeliefTracker
from thalos_prime.planning.tree_of_thoughts import TreeOfThoughtsPlanner
from thalos_prime.simulation.world_model import WorldModel, WorldState


def _make_agent() -> AgentLoop:
    """Construct an AgentLoop with default sub-components."""
    return AgentLoop(
        planner=TreeOfThoughtsPlanner(),
        world_model=WorldModel(),
        belief_tracker=BeliefTracker(),
        action_executor=ActionExecutor(),
    )


def _echo_handler(params: dict[str, object]) -> ActionResult:
    """Echo params back in the output."""
    return ActionResult(action="echo", success=True, output=dict(params))


class TestAgentStepResult:
    def test_to_dict(self) -> None:
        result = AgentStepResult(
            step=0,
            chosen_action="test",
            action_result=ActionResult(action="test", success=True),
            world_state=WorldState(),
            belief_hash="abc123",
        )
        d = result.to_dict()
        assert d["step"] == 0
        assert d["chosen_action"] == "test"
        assert isinstance(d["action_result"], dict)
        assert isinstance(d["world_state"], dict)


class TestAgentResult:
    def test_to_dict(self) -> None:
        result = AgentResult(
            query="test query",
            steps=[],
            final_answer="answer",
            total_steps=0,
            final_belief_hash="hash",
        )
        d = result.to_dict()
        assert d["query"] == "test query"
        assert d["final_answer"] == "answer"
        assert d["total_steps"] == 0


class TestAgentLoop:
    def test_initialize_sets_initialized(self) -> None:
        agent = _make_agent()
        agent.initialize()
        assert agent._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        agent = _make_agent()
        result = agent.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        agent = _make_agent()
        agent.initialize()
        result = agent.validate()
        assert result.valid is True

    def test_step_returns_step_result(self) -> None:
        agent = _make_agent()
        agent.initialize()
        result = agent.step("what is 2+2?", WorldState(), step_index=0)
        assert isinstance(result, AgentStepResult)
        assert result.step == 0
        assert result.belief_hash != ""

    def test_step_updates_world_state(self) -> None:
        agent = _make_agent()
        agent.initialize()
        initial = WorldState()
        result = agent.step("test", initial, step_index=0)
        assert result.world_state.version > initial.version

    def test_step_records_beliefs(self) -> None:
        agent = _make_agent()
        agent.initialize()
        agent.step("query", WorldState(), step_index=0)
        belief = agent._belief_tracker.get_belief("step_0_action")
        assert belief is not None

    def test_run_returns_agent_result(self) -> None:
        agent = _make_agent()
        agent.initialize()
        result = agent.run("what is 2+2?", max_steps=3, seed=42)
        assert isinstance(result, AgentResult)
        assert result.query == "what is 2+2?"
        assert result.total_steps >= 1
        assert result.final_answer != ""

    def test_run_deterministic(self) -> None:
        agent1 = _make_agent()
        agent1.initialize()
        result1 = agent1.run("test query", max_steps=3, seed=42)

        agent2 = _make_agent()
        agent2.initialize()
        result2 = agent2.run("test query", max_steps=3, seed=42)

        assert result1.total_steps == result2.total_steps
        assert result1.final_belief_hash == result2.final_belief_hash

    def test_run_respects_max_steps(self) -> None:
        agent = _make_agent()
        agent.initialize()
        result = agent.run("test", max_steps=2, seed=42)
        assert result.total_steps <= 2

    def test_run_with_registered_action(self) -> None:
        agent = _make_agent()
        agent.initialize()
        agent._action_executor.register_action("echo", _echo_handler)
        result = agent.run("echo", max_steps=1, seed=0)
        assert result.total_steps == 1

    def test_operate_does_not_raise(self) -> None:
        agent = _make_agent()
        agent.initialize()
        agent.operate()

    def test_reconcile_fixes_negative_counters(self) -> None:
        agent = _make_agent()
        agent.initialize()
        agent._step_count = -1
        agent._cycle_count = -2
        agent.reconcile()
        assert agent._step_count == 0
        assert agent._cycle_count == 0

    def test_checkpoint_returns_dict(self) -> None:
        agent = _make_agent()
        agent.initialize()
        state = agent.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "AgentLoop"
        assert "planner" in state
        assert "world_model" in state
        assert "belief_tracker" in state
        assert "action_executor" in state

    def test_terminate_resets_state(self) -> None:
        agent = _make_agent()
        agent.initialize()
        agent.run("test", max_steps=1, seed=0)
        agent.terminate()
        assert agent._initialized is False
        assert agent._step_count == 0
        assert agent._cycle_count == 0

    def test_lifecycle_events_recorded(self) -> None:
        agent = _make_agent()
        agent.initialize()
        agent.operate()
        agent.checkpoint()
        agent.terminate()
        events = agent.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "checkpoint" in methods
        assert "terminate" in methods

    def test_state_hash_deterministic(self) -> None:
        agent1 = _make_agent()
        agent1.initialize()
        agent1.run("test", max_steps=2, seed=42)

        agent2 = _make_agent()
        agent2.initialize()
        agent2.run("test", max_steps=2, seed=42)

        assert agent1.state_hash() == agent2.state_hash()
