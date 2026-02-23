"""GoalEvaluator — Data Plane component for evaluating Goal progress.

Checks whether a Goal's key words appear as entity canonical names in the
belief graph.  Marks the goal ACHIEVED if all key words are found.
"""

from __future__ import annotations

import re

from thalos_prime.agency.schema import Goal, GoalStatus
from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph

_TOKEN_RE = re.compile(r"\b([a-z]{4,})\b")


class GoalEvaluator:
    """Data Plane component that evaluates Goal achievement.

    A Goal is considered ACHIEVED if all its content-word tokens (≥4 chars)
    are present as entity canonical names in the belief graph.
    """

    def evaluate(self, goal: Goal, graph: KnowledgeGraph) -> GoalStatus:
        """Evaluate goal against the current belief graph.

        Args:
            goal: The Goal to evaluate.
            graph: The current belief graph.

        Returns:
            GoalStatus.ACHIEVED if criteria met, else GoalStatus.ACTIVE.

        """
        if goal.status == GoalStatus.ACHIEVED:
            return GoalStatus.ACHIEVED
        if goal.status == GoalStatus.ABANDONED:
            return GoalStatus.ABANDONED

        tokens = {m.group(1) for m in _TOKEN_RE.finditer(goal.goal_text.lower())}
        if not tokens:
            return GoalStatus.ACTIVE

        for token in tokens:
            if graph.find_entity_by_name(token) is None:
                return GoalStatus.ACTIVE

        return GoalStatus.ACHIEVED
