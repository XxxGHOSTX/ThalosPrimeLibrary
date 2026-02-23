"""ThoughtScorer — Data Plane component for scoring ThoughtNodes.

Scores are derived from text coherence and graph relevance, producing
a float in [0.0, 1.0].  All scoring is deterministic (no LLM calls).
"""

from __future__ import annotations

from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph
from thalos_prime.lob_decoder import BabelDecoder

_decoder = BabelDecoder()


class ThoughtScorer:
    """Data Plane component that scores thought text.

    score = coherence_score * 0.5 + graph_relevance * 0.5

    graph_relevance is the fraction of thought words that appear as entity
    canonical_names in the knowledge graph (clamped to [0, 1]).
    """

    def score(self, thought_text: str, graph: KnowledgeGraph | None = None) -> float:
        """Score a thought string.

        Args:
            thought_text: The thought to score.
            graph: Optional KnowledgeGraph for graph relevance.

        Returns:
            Score in [0.0, 1.0].

        """
        coherence = _decoder.score_coherence(thought_text).overall_score / 100.0
        graph_rel = self._graph_relevance(thought_text, graph) if graph else 0.0
        return coherence * 0.5 + graph_rel * 0.5

    @staticmethod
    def _graph_relevance(text: str, graph: KnowledgeGraph | None) -> float:
        """Fraction of text words found as entity canonical names in graph."""
        if graph is None or graph.node_count == 0:
            return 0.0
        words = set(text.lower().split())
        if not words:
            return 0.0
        hits = sum(
            1
            for w in words
            if graph.find_entity_by_name(w) is not None
        )
        return hits / len(words)
