"""DSL for declaring graph rewrite rules."""

from __future__ import annotations

from collections.abc import Callable

from thalos_prime.execution_ir.graph import ExecutionGraph


class RewriteRule:
    """A named, versioned graph rewrite rule.

    A rule consists of a match predicate and a transform function.
    The transform is applied only when the match predicate returns True.
    """

    def __init__(
        self,
        name: str,
        match_fn: Callable[[ExecutionGraph], bool],
        transform_fn: Callable[[ExecutionGraph], ExecutionGraph],
        version: str = "1.0",
    ) -> None:
        """Initialize a rewrite rule.

        Args:
            name: Human-readable name for this rule.
            match_fn: Predicate that determines whether the rule applies.
            transform_fn: Function that transforms a matching graph.
            version: Version string for this rule (default ``"1.0"``).

        """
        self.name = name
        self.version = version
        self._match_fn = match_fn
        self._transform_fn = transform_fn

    def applies_to(self, graph: ExecutionGraph) -> bool:
        """Return True if this rule applies to the given graph.

        Args:
            graph: ExecutionGraph to test against the match predicate.

        Returns:
            True if the match function returns True for this graph.

        """
        return self._match_fn(graph)

    def apply(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Apply the transform function only if the match predicate holds.

        If the match predicate returns False, the original graph is returned
        unchanged.

        Args:
            graph: ExecutionGraph to potentially transform.

        Returns:
            Transformed graph if the rule applies, otherwise the original.

        """
        if not self._match_fn(graph):
            return graph
        return self._transform_fn(graph)


def make_normalization_rule() -> RewriteRule:
    """Create the built-in normalization rule.

    The normalization rule adds the ``"normalized"`` tag to every node that
    does not already have it, and sets ``metadata["normalized"] = True`` on
    the graph.

    Returns:
        A RewriteRule that normalizes any graph.

    """

    def _match(graph: ExecutionGraph) -> bool:
        return not bool(graph.metadata.get("normalized"))

    def _transform(graph: ExecutionGraph) -> ExecutionGraph:
        for node in graph.nodes.values():
            if "normalized" not in node.tags:
                node.tags.append("normalized")
        graph.metadata["normalized"] = True
        graph.compute_graph_hash()
        return graph

    return RewriteRule(
        name="normalization",
        match_fn=_match,
        transform_fn=_transform,
        version="1.0",
    )


__all__ = ["RewriteRule", "make_normalization_rule"]
