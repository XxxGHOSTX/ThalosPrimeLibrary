"""Library of Sense - Graph Retrieval-Augmented Generation (GraphRAG).

Data Plane subsystem that wraps KnowledgeGraphRetriever and adds:
- top-k subgraph retrieval by path scoring
- document indexing via triple extraction
- context window retrieval (N-hop neighbourhood)

This is a pure Data Plane component — it executes computational work only.
No lifecycle orchestration logic belongs here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from thalos_prime.library_of_sense.core.interfaces import (
    RetrievalResult,
    ValidationResult,
)
from thalos_prime.library_of_sense.retrieval.knowledge_graph import (
    GraphTriple,
    KnowledgeGraphRetriever,
)
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)


class GraphRAGRetriever(BaseLifecycleComponent):
    """Graph Retrieval-Augmented Generation retriever.

    Wraps a KnowledgeGraphRetriever and adds path-scored retrieval,
    document indexing, and multi-hop context window extraction.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize GraphRAGRetriever with an empty knowledge graph.

        Args:
            seed: Deterministic seed for replay identification.

        """
        super().__init__("GraphRAGRetriever", seed=seed)
        self._kg = KnowledgeGraphRetriever()
        self._indexed_documents: list[dict[str, object]] = []
        self._query_cache: dict[str, list[RetrievalResult]] = {}

    # ------------------------------------------------------------------
    # LifecycleProtocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the knowledge graph and reset indexing metadata."""
        self._kg.initialize()
        self._indexed_documents = []
        self._query_cache = {}
        self._initialized = True
        self._emit_event("initialize", "KG initialized, metadata reset")
        logger.debug("GraphRAGRetriever initialized")

    def validate(self) -> ValidationResult:
        """Validate that the retriever is initialized and the KG is consistent.

        Returns:
            ValidationResult indicating readiness.

        """
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="GraphRAGRetriever not initialized; call initialize() first",
            )
        kg_result = self._kg.validate()
        if not kg_result.valid:
            return ValidationResult(
                valid=False,
                message=f"Underlying KG invalid: {kg_result.message}",
            )
        return ValidationResult(
            valid=True,
            message=(
                f"GraphRAGRetriever ready: {self._kg.triple_count} triples, "
                f"{len(self._indexed_documents)} documents indexed"
            ),
        )

    def operate(self) -> None:
        """Log current retriever statistics. Idempotent."""
        self._emit_event(
            "operate",
            f"documents={len(self._indexed_documents)} "
            f"triples={self._kg.triple_count} "
            f"cache_entries={len(self._query_cache)}",
        )
        logger.debug(
            "GraphRAGRetriever operating: docs=%d triples=%d cache=%d",
            len(self._indexed_documents),
            self._kg.triple_count,
            len(self._query_cache),
        )

    def reconcile(self) -> None:
        """Reconcile KG and clear stale cache entries."""
        self._emit_event("reconcile", "Delegating to KG reconcile")
        self._kg.reconcile()
        self._query_cache.clear()
        self._emit_event("reconcile", "Cache cleared, KG consistent")

    def checkpoint(self) -> dict[str, object]:
        """Serialize full retriever state for restart.

        Returns:
            Dict with KG state, indexed document metadata, and cache statistics.

        """
        kg_state = self._kg.checkpoint()
        state: dict[str, object] = {
            "component": self._component_name,
            "seed": self._seed,
            "indexed_document_count": len(self._indexed_documents),
            "indexed_documents": list(self._indexed_documents),
            "query_cache_size": len(self._query_cache),
            "kg": kg_state,
        }
        self._emit_event("checkpoint", f"docs={len(self._indexed_documents)}")
        return state

    def terminate(self) -> None:
        """Terminate the retriever and release all resources."""
        self._kg.terminate()
        self._indexed_documents.clear()
        self._query_cache.clear()
        self._initialized = False
        self._emit_event("terminate", "Resources released, initialized=False")
        logger.debug("GraphRAGRetriever terminated")

    # ------------------------------------------------------------------
    # Data Plane methods
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Retrieve top-k relevant subgraphs for the query entity.

        Traverses the knowledge graph from the query entity, scoring paths
        by cumulative confidence. Results are sorted by descending score.

        Args:
            query: Entity name to use as the traversal root.
            top_k: Maximum number of results to return.

        Returns:
            List of RetrievalResult sorted by descending confidence.

        """
        if query in self._query_cache:
            return self._query_cache[query][:top_k]

        direct_triples = self._kg.query_subject(query)
        results: list[RetrievalResult] = []

        for triple in direct_triples:
            content = f"{triple.subject} {triple.predicate} {triple.obj}"
            results.append(
                RetrievalResult(
                    source="graph_rag",
                    content=content,
                    confidence=triple.confidence,
                    metadata={
                        "subject": triple.subject,
                        "predicate": triple.predicate,
                        "obj": triple.obj,
                    },
                )
            )

            # Extend one hop further for richer context
            neighbour_triples = self._kg.query_subject(triple.obj)
            for nt in neighbour_triples:
                hop_content = (
                    f"{triple.subject} {triple.predicate} {triple.obj} "
                    f"-> {nt.predicate} {nt.obj}"
                )
                hop_confidence = triple.confidence * nt.confidence * 0.8
                results.append(
                    RetrievalResult(
                        source="graph_rag",
                        content=hop_content,
                        confidence=hop_confidence,
                        metadata={
                            "subject": triple.subject,
                            "hop_obj": nt.obj,
                            "depth": "2",
                        },
                    )
                )

        results.sort(key=lambda r: r.confidence, reverse=True)
        self._query_cache[query] = results
        return results[:top_k]

    def index_document(
        self,
        document: str,
        extractor: Callable[[str], list[GraphTriple]],
    ) -> int:
        """Index a document by extracting triples and adding them to the KG.

        Args:
            document: Raw document text to index.
            extractor: Callable that extracts GraphTriples from the document text.

        Returns:
            Count of triples added for this document.

        """
        triples = extractor(document)
        for triple in triples:
            self._kg.add_triple(triple)

        doc_meta: dict[str, object] = {
            "document_hash": str(hash(document)),
            "triple_count": len(triples),
            "indexed_at": datetime.now(UTC).isoformat(),
        }
        self._indexed_documents.append(doc_meta)
        self._query_cache.clear()
        logger.debug("Indexed document: %d triples extracted", len(triples))
        return len(triples)

    def get_context_window(self, entity: str, hops: int = 2) -> list[GraphTriple]:
        """Return all triples within N hops of an entity.

        Args:
            entity: Root entity for the context window.
            hops: Number of graph hops to traverse.

        Returns:
            Deduplicated list of GraphTriple within the hop radius.

        """
        visited: set[str] = set()
        frontier: list[str] = [entity]
        result: list[GraphTriple] = []

        for _ in range(hops):
            next_frontier: list[str] = []
            for node in frontier:
                if node in visited:
                    continue
                visited.add(node)
                triples = self._kg.query_subject(node)
                result.extend(triples)
                next_frontier.extend(
                    triple.obj for triple in triples if triple.obj not in visited
                )
            frontier = next_frontier

        return result


__all__ = ["GraphRAGRetriever"]
