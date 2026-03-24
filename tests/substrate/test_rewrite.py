"""Tests for rewrite: RewriteRule, GraphTransformer, make_normalization_rule."""

from __future__ import annotations

from thalos_prime.execution_ir.builder import GraphBuilder
from thalos_prime.execution_ir.graph import ExecutionGraph
from thalos_prime.rewrite.dsl import RewriteRule, make_normalization_rule
from thalos_prime.rewrite.engine import GraphTransformer


class TestRewriteRule:
    """Tests for RewriteRule matching and application."""

    def test_rule_applies_when_match_returns_true(self) -> None:
        """apply() calls transform_fn when match_fn returns True."""
        transformed: list[bool] = []

        def _track_and_return(g: ExecutionGraph) -> ExecutionGraph:
            transformed.append(True)
            return g

        rule = RewriteRule(
            name="always",
            match_fn=lambda _g: True,
            transform_fn=_track_and_return,
        )
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        rule.apply(graph)
        assert transformed == [True]

    def test_rule_skips_when_match_returns_false(self) -> None:
        """apply() returns original graph when match_fn returns False."""
        transformed: list[bool] = []

        def _track_and_return(g: ExecutionGraph) -> ExecutionGraph:
            transformed.append(True)
            return g

        rule = RewriteRule(
            name="never",
            match_fn=lambda _g: False,
            transform_fn=_track_and_return,
        )
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        result = rule.apply(graph)
        assert transformed == []
        assert result is graph

    def test_applies_to_delegates_to_match_fn(self) -> None:
        """applies_to correctly delegates to the match function."""
        rule = RewriteRule(
            name="test",
            match_fn=lambda g: len(g.nodes) > 0,
            transform_fn=lambda g: g,
        )
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        empty_graph = ExecutionGraph.new()

        assert rule.applies_to(graph) is True
        assert rule.applies_to(empty_graph) is False


class TestMakeNormalizationRule:
    """Tests for the built-in normalization rule."""

    def test_adds_normalized_tag_to_nodes(self) -> None:
        """Normalization rule adds 'normalized' tag to all nodes."""
        rule = make_normalization_rule()
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        result = rule.apply(graph)

        for node in result.nodes.values():
            assert "normalized" in node.tags

    def test_sets_metadata_normalized_flag(self) -> None:
        """Normalization rule sets metadata['normalized'] = True."""
        rule = make_normalization_rule()
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        result = rule.apply(graph)

        assert result.metadata.get("normalized") is True

    def test_does_not_apply_twice(self) -> None:
        """Normalization rule does not apply to an already-normalized graph."""
        rule = make_normalization_rule()
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        graph = rule.apply(graph)

        # After first apply, match_fn should return False
        assert rule.applies_to(graph) is False

    def test_does_not_duplicate_normalized_tag(self) -> None:
        """Applying normalization manually then via rule does not duplicate tag."""
        rule = make_normalization_rule()
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        # Manually add normalized tag
        for node in graph.nodes.values():
            node.tags.append("normalized")
        graph.metadata["normalized"] = True

        result = rule.apply(graph)
        for node in result.nodes.values():
            assert node.tags.count("normalized") == 1


class TestGraphTransformer:
    """Tests for GraphTransformer multi-rule application."""

    def test_applies_rules_in_order(self) -> None:
        """Rules are applied in registration order and all applied names recorded."""
        call_order: list[str] = []

        def make_rule(name: str) -> RewriteRule:
            captured = name

            def _transform(g: ExecutionGraph) -> ExecutionGraph:
                call_order.append(captured)
                return g

            return RewriteRule(
                name=captured,
                match_fn=lambda _g: True,
                transform_fn=_transform,
            )

        transformer = GraphTransformer(rules=[make_rule("r1"), make_rule("r2")])
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        transformer.transform(graph)

        assert call_order == ["r1", "r2"]

    def test_records_applied_rules_in_metadata(self) -> None:
        """transform() records rule names in graph.metadata['applied_rules']."""
        rule1 = RewriteRule(
            name="rule_one",
            match_fn=lambda _g: True,
            transform_fn=lambda g: g,
        )
        rule2 = RewriteRule(
            name="rule_two",
            match_fn=lambda _g: True,
            transform_fn=lambda g: g,
        )
        transformer = GraphTransformer(rules=[rule1, rule2])
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        result = transformer.transform(graph)

        applied = result.metadata.get("applied_rules")
        assert isinstance(applied, list)
        applied_strs = [str(x) for x in applied]
        assert "rule_one" in applied_strs
        assert "rule_two" in applied_strs

    def test_skipped_rules_not_in_applied_rules(self) -> None:
        """Rules that do not match are not listed in applied_rules."""
        always_rule = RewriteRule(
            name="always",
            match_fn=lambda _g: True,
            transform_fn=lambda g: g,
        )
        never_rule = RewriteRule(
            name="never",
            match_fn=lambda _g: False,
            transform_fn=lambda g: g,
        )
        transformer = GraphTransformer(rules=[always_rule, never_rule])
        builder = GraphBuilder()
        graph = builder.build_from_payload({"x": 1})
        result = transformer.transform(graph)

        applied = result.metadata.get("applied_rules", [])
        applied_strs = [str(x) for x in applied] if isinstance(applied, list) else []
        assert "always" in applied_strs
        assert "never" not in applied_strs

    def test_add_rule_extends_transformer(self) -> None:
        """add_rule appends a new rule to the transformer."""
        transformer = GraphTransformer()
        assert transformer.rule_names() == []

        transformer.add_rule(make_normalization_rule())
        assert "normalization" in transformer.rule_names()
