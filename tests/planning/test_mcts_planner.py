"""Tests for MCTSPlanner."""

from __future__ import annotations

from thalos_prime.planning.mcts_planner import MCTSNode, MCTSPlanner, MCTSResult


def _fixed_actions(state: str) -> list[str]:
    """Generate a fixed set of 3 actions from any state."""
    return [f"{state}_a", f"{state}_b", f"{state}_c"]


def _length_reward(state: str) -> float:
    """Reward based on state string length (normalized)."""
    return min(len(state) / 50.0, 1.0)





class TestMCTSNode:
    def test_default_fields(self) -> None:
        node = MCTSNode(state="root")
        assert node.visits == 0
        assert node.total_reward == 0.0
        assert node.children == []
        assert node.depth == 0

    def test_mean_reward_zero_visits(self) -> None:
        node = MCTSNode(state="x")
        assert node.mean_reward == 0.0

    def test_mean_reward_with_visits(self) -> None:
        node = MCTSNode(state="x", visits=4, total_reward=2.0)
        assert node.mean_reward == 0.5

    def test_to_dict(self) -> None:
        node = MCTSNode(state="root", visits=10, total_reward=5.0, depth=0, seed=42)
        d = node.to_dict()
        assert d["state"] == "root"
        assert d["visits"] == 10
        assert d["mean_reward"] == 0.5
        assert d["seed"] == 42

    def test_children_independent(self) -> None:
        a = MCTSNode(state="a")
        b = MCTSNode(state="b")
        assert a.children is not b.children


class TestMCTSResult:
    def test_to_dict(self) -> None:
        root = MCTSNode(state="s", visits=50)
        result = MCTSResult(
            best_action="s_a",
            best_path=["s", "s_a"],
            root=root,
            iterations_run=50,
            total_simulations=50,
        )
        d = result.to_dict()
        assert d["best_action"] == "s_a"
        assert d["iterations_run"] == 50


class TestMCTSPlanner:
    def test_initialize_sets_initialized(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        assert planner._initialized is True
        assert planner.plan_count == 0

    def test_validate_fails_before_initialize(self) -> None:
        planner = MCTSPlanner()
        result = planner.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        result = planner.validate()
        assert result.valid is True

    def test_search_returns_result(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        result = planner.search(
            root_state="start",
            action_generator=_fixed_actions,
            reward_evaluator=_length_reward,
            iterations=20,
            max_depth=3,
            seed=42,
        )
        assert isinstance(result, MCTSResult)
        assert result.best_action != ""
        assert len(result.best_path) >= 1
        assert result.iterations_run == 20

    def test_search_deterministic(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        result_a = planner.search(
            root_state="s",
            action_generator=_fixed_actions,
            reward_evaluator=_length_reward,
            iterations=30,
            max_depth=3,
            seed=42,
        )
        # Re-initialize to reset state
        planner2 = MCTSPlanner()
        planner2.initialize()
        result_b = planner2.search(
            root_state="s",
            action_generator=_fixed_actions,
            reward_evaluator=_length_reward,
            iterations=30,
            max_depth=3,
            seed=42,
        )
        assert result_a.best_action == result_b.best_action
        assert result_a.best_path == result_b.best_path

    def test_search_different_seeds_may_differ(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()

        def _binary_actions(state: str) -> list[str]:
            return [f"{state}_L", f"{state}_R"]

        result_a = planner.search(
            root_state="s",
            action_generator=_binary_actions,
            reward_evaluator=_length_reward,
            iterations=50,
            max_depth=3,
            seed=1,
        )
        result_b = planner.search(
            root_state="s",
            action_generator=_binary_actions,
            reward_evaluator=_length_reward,
            iterations=50,
            max_depth=3,
            seed=999,
        )
        # Trees are independently seeded, so rollout paths may differ
        assert result_a.root.seed != result_b.root.seed

    def test_search_with_no_actions(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()

        def no_actions(state: str) -> list[str]:
            _ = state
            return []

        result = planner.search(
            root_state="start",
            action_generator=no_actions,
            reward_evaluator=_length_reward,
            iterations=10,
            max_depth=5,
            seed=0,
        )
        assert result.best_action == "start"
        assert result.best_path == ["start"]

    def test_root_visits_match_iterations(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        result = planner.search(
            root_state="root",
            action_generator=_fixed_actions,
            reward_evaluator=_length_reward,
            iterations=25,
            max_depth=2,
            seed=7,
        )
        assert result.root.visits == 25

    def test_best_action_method(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        result = planner.search(
            root_state="s",
            action_generator=_fixed_actions,
            reward_evaluator=_length_reward,
            iterations=30,
            max_depth=2,
            seed=42,
        )
        best = planner.best_action(result.root)
        assert best == result.best_action

    def test_best_action_no_children(self) -> None:
        planner = MCTSPlanner()
        root = MCTSNode(state="leaf")
        assert planner.best_action(root) == "leaf"

    def test_plan_count_increments(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        assert planner.plan_count == 0
        planner.search("s", _fixed_actions, _length_reward, iterations=5, seed=0)
        planner.search("s", _fixed_actions, _length_reward, iterations=5, seed=1)
        assert planner.plan_count == 2

    def test_total_iterations_accumulates(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        planner.search("s", _fixed_actions, _length_reward, iterations=10, seed=0)
        planner.search("s", _fixed_actions, _length_reward, iterations=15, seed=1)
        assert planner.total_iterations == 25

    def test_operate_does_not_raise(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        planner.operate()

    def test_reconcile_fixes_negative_counters(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        planner._plan_count = -5
        planner._total_iterations = -10
        planner.reconcile()
        assert planner._plan_count == 0
        assert planner._total_iterations == 0

    def test_checkpoint_returns_dict(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        state = planner.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "MCTSPlanner"
        assert "plan_count" in state
        assert "exploration_constant" in state

    def test_terminate_resets_state(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        planner.search("s", _fixed_actions, _length_reward, iterations=5, seed=0)
        planner.terminate()
        assert planner._initialized is False
        assert planner.plan_count == 0
        assert planner.total_iterations == 0

    def test_lifecycle_events_recorded(self) -> None:
        planner = MCTSPlanner()
        planner.initialize()
        planner.operate()
        planner.checkpoint()
        events = planner.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "operate" in methods
        assert "checkpoint" in methods

    def test_custom_exploration_constant(self) -> None:
        planner = MCTSPlanner(exploration_constant=0.5)
        planner.initialize()
        state = planner.checkpoint()
        assert state["exploration_constant"] == 0.5

    def test_ucb1_unvisited_returns_inf(self) -> None:
        planner = MCTSPlanner()
        node = MCTSNode(state="x", visits=0)
        score = planner._ucb1_score(node, parent_visits=10)
        assert score == float("inf")
