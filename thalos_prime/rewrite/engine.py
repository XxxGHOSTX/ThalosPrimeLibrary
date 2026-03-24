"""Graph transformation engine — applies ordered rewrite rules to execution graphs."""

from __future__ import annotations

from thalos_prime.execution_ir.graph import ExecutionGraph
from thalos_prime.rewrite.dsl import RewriteRule


class GraphTransformer:
    """Applies a sequence of RewriteRules to an ExecutionGraph deterministically.

    Rules are applied in registration order. Each applied rule's name is
    recorded in ``graph.metadata["applied_rules"]``.
    """

    def __init__(self, rules: list[RewriteRule] | None = None) -> None:
        """Initialize the transformer with an optional initial rule list.

        Args:
            rules: Initial list of RewriteRules. An empty list is used if None.

        """
        self._rules: list[RewriteRule] = list(rules) if rules is not None else []

    def add_rule(self, rule: RewriteRule) -> None:
        """Append a rewrite rule to the end of the rule list.

        Args:
            rule: RewriteRule to add.

        """
        self._rules.append(rule)

    def rule_names(self) -> list[str]:
        """Return the names of all registered rules in order.

        Returns:
            List of rule names in registration order.

        """
        return [r.name for r in self._rules]

    def transform(self, graph: ExecutionGraph) -> ExecutionGraph:
        """Apply all registered rules to the graph in order.

        Each rule whose match predicate returns True is applied.
        The names of all applied rules are recorded in
        ``graph.metadata["applied_rules"]``.

        Args:
            graph: ExecutionGraph to transform.

        Returns:
            Transformed ExecutionGraph (may be the same object mutated in place).

        """
        applied: list[str] = []
        current = graph
        for rule in self._rules:
            if rule.applies_to(current):
                current = rule.apply(current)
                applied.append(rule.name)

        existing = current.metadata.get("applied_rules", [])
        if isinstance(existing, list):
            combined: list[str] = [str(x) for x in existing] + applied
        else:
            combined = applied
        current.metadata["applied_rules"] = combined
        return current


__all__ = ["GraphTransformer"]
