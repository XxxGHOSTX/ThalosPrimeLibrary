"""Tests for TreeOfThoughtsPlanner."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from thalos_prime.planning.tree_of_thoughts import ThoughtNode, TreeOfThoughtsPlanner


def _constant_evaluator(score: float) -> Callable[[str], float]:
    """Return an evaluator that always returns the given score."""
    def evaluator(thought: str) -> float:
        _ = thought
        return score
    return evaluator


def _length_evaluator(thought: str) -> float:
    """Score based on thought string length (normalized, capped at 1.0)."""
    return min(len(thought) / 100.0, 1.0)


class TestThoughtNode:
    def test_default_fields(self) -> None:
        node = ThoughtNode(thought="test", score=0.5)
        assert node.depth == 0
        assert node.seed == 0
        assert node.children == []

    def test_children_independent(self) -> None:
        a = ThoughtNode(thought="a", score=0.1)
        b = ThoughtNode(thought="b", score=0.2)
        assert a.children is not b.children


class TestTreeOfThoughtsPlanner:
    def test_initialize_sets_initialized(self) -> None:
        planner = TreeOfThoughtsPlanner()
        planner.initialize()
        assert planner._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        planner = TreeOfThoughtsPlanner()
        result = planner.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        planner = TreeOfThoughtsPlanner()
        planner.initialize()
        result = planner.validate()
        assert result.valid is True

    def test_plan_returns_root_node(self) -> None:
        planner = TreeOfThoughtsPlanner()
        root = planner.plan("what is 2+2?", _constant_evaluator(0.8), breadth=2, depth=2, seed=1)
        assert isinstance(root, ThoughtNode)
        assert root.thought == "what is 2+2?"

    def test_plan_tree_has_correct_breadth(self) -> None:
        planner = TreeOfThoughtsPlanner()
        root = planner.plan("test", _constant_evaluator(0.5), breadth=3, depth=1, seed=0)
        assert len(root.children) == 3

    def test_plan_tree_has_correct_depth(self) -> None:
        planner = TreeOfThoughtsPlanner()
        root = planner.plan("test", _constant_evaluator(0.5), breadth=2, depth=3, seed=0)
        # All leaves should be at depth 3
        def max_depth(node: ThoughtNode) -> int:
            if not node.children:
                return node.depth
            return max(max_depth(c) for c in node.children)
        assert max_depth(root) == 3

    def test_identical_seeds_produce_identical_trees(self) -> None:
        planner = TreeOfThoughtsPlanner()
        root_a = planner.plan("query", _length_evaluator, breadth=3, depth=2, seed=42)
        root_b = planner.plan("query", _length_evaluator, breadth=3, depth=2, seed=42)

        def tree_to_thoughts(node: ThoughtNode) -> list[str]:
            result = [node.thought]
            for child in node.children:
                result.extend(tree_to_thoughts(child))
            return result

        assert tree_to_thoughts(root_a) == tree_to_thoughts(root_b)

    def test_different_seeds_produce_different_trees(self) -> None:
        planner = TreeOfThoughtsPlanner()
        root_a = planner.plan("query", _length_evaluator, breadth=3, depth=2, seed=42)
        root_b = planner.plan("query", _length_evaluator, breadth=3, depth=2, seed=99)

        def tree_seeds(node: ThoughtNode) -> list[int]:
            result = [node.seed]
            for child in node.children:
                result.extend(tree_seeds(child))
            return result

        # Seeds for children should differ between runs
        assert tree_seeds(root_a) != tree_seeds(root_b)

    def test_best_path_returns_list_of_strings(self) -> None:
        planner = TreeOfThoughtsPlanner()
        root = planner.plan("root", _constant_evaluator(0.5), breadth=2, depth=2, seed=7)
        path = planner.best_path(root)
        assert isinstance(path, list)
        assert len(path) >= 1
        assert path[0] == "root"

    def test_best_path_follows_highest_score(self) -> None:
        # Build a simple tree manually
        planner = TreeOfThoughtsPlanner()
        child_low = ThoughtNode(thought="low", score=0.1, depth=1)
        child_high = ThoughtNode(thought="high", score=0.9, depth=1)
        root = ThoughtNode(thought="root", score=1.0, children=[child_low, child_high], depth=0)
        path = planner.best_path(root)
        assert path == ["root", "high"]

    def test_prune_removes_low_score_nodes(self) -> None:
        planner = TreeOfThoughtsPlanner()
        root = planner.plan("test", _constant_evaluator(0.2), breadth=3, depth=2, seed=1)
        pruned = planner.prune(root, threshold=0.5)
        # All children of root have score 0.2 < 0.5, so they should be removed
        assert pruned.children == []

    def test_prune_keeps_high_score_nodes(self) -> None:
        planner = TreeOfThoughtsPlanner()
        root = planner.plan("test", _constant_evaluator(0.8), breadth=2, depth=1, seed=1)
        pruned = planner.prune(root, threshold=0.5)
        assert len(pruned.children) == 2

    def test_operate_does_not_raise(self) -> None:
        planner = TreeOfThoughtsPlanner()
        planner.initialize()
        planner.operate()  # Should not raise

    def test_reconcile_fixes_negative_plan_count(self) -> None:
        planner = TreeOfThoughtsPlanner()
        planner.initialize()
        planner._plan_count = -5
        planner.reconcile()
        assert planner._plan_count == 0

    def test_checkpoint_returns_dict(self) -> None:
        planner = TreeOfThoughtsPlanner()
        planner.initialize()
        state = planner.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "TreeOfThoughtsPlanner"
        assert "plan_count" in state

    def test_terminate_resets_state(self) -> None:
        planner = TreeOfThoughtsPlanner()
        planner.initialize()
        planner.plan("q", _constant_evaluator(0.5), breadth=1, depth=1, seed=0)
        planner.terminate()
        assert planner._initialized is False
        assert planner._plan_count == 0

    def test_lifecycle_events_recorded(self) -> None:
        planner = TreeOfThoughtsPlanner()
        planner.initialize()
        planner.operate()
        planner.checkpoint()
        events = planner.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "operate" in methods
        assert "checkpoint" in methods
