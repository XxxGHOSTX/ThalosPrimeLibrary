"""PredictionEngine — Data Plane component for generating predictions.

Generates deterministic Prediction objects from the belief graph by
inspecting high-weight EntityNode pairs and composing prediction text
from their canonical names.
"""

from __future__ import annotations

from hashlib import sha256

from thalos_prime.agency.schema import AGENCY_SCHEMA_VERSION, Prediction
from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph

_MAX_PREDICTIONS = 10


def _prediction_id(text: str, timestep: int) -> str:
    return sha256(f"{text}:{timestep}".encode()).hexdigest()


class PredictionEngine:
    """Data Plane component that generates Predictions from the belief graph.

    For each EntityNode with outgoing RelationshipEdges, generate a
    prediction of the form "{entity_a} relates to {entity_b}" with
    confidence = edge_weight.  Results are sorted by confidence DESC,
    prediction_id ASC for determinism.
    """

    def generate(
        self,
        graph: KnowledgeGraph,
        seed: int,
        timestep: int,
        max_predictions: int = _MAX_PREDICTIONS,
    ) -> list[Prediction]:
        """Generate predictions from the belief graph.

        Args:
            graph: The current belief graph.
            seed: Deterministic seed (unused in this implementation but
                  required by contract for future seeded generation).
            timestep: Current world-model timestep.
            max_predictions: Maximum number of predictions to return.

        Returns:
            Sorted list of Prediction objects.

        """
        del seed  # deterministic; no randomness needed at this stage

        if graph.node_count == 0:
            return []

        predictions: list[Prediction] = []
        for src_id, tgt_id, edge_attrs in sorted(
            graph._graph.edges(data=True),
            key=lambda e: (-float(e[2].get("weight", 0.0)), str(e[0]), str(e[1])),
        ):
            if len(predictions) >= max_predictions:
                break
            src_entity = graph.get_entity(str(src_id))
            tgt_entity = graph.get_entity(str(tgt_id))
            if src_entity is None or tgt_entity is None:
                continue
            weight = float(edge_attrs.get("weight", 0.0))
            text = (
                f"{src_entity.canonical_name} "
                f"{edge_attrs.get('relation_type', 'relates to')} "
                f"{tgt_entity.canonical_name}"
            )
            pid = _prediction_id(text, timestep)
            predictions.append(
                Prediction(
                    id=pid,
                    prediction_text=text,
                    basis_entity_ids=[src_entity.id, tgt_entity.id],
                    confidence=weight,
                    validated=None,
                    timestep=timestep,
                    version=AGENCY_SCHEMA_VERSION,
                )
            )

        return predictions
