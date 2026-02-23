"""GraphRAG Control Plane — lifecycle orchestration for the graph_rag module.

GraphRAGControlPlane owns the lifecycle of the KnowledgeGraph,
GraphIngestionPipeline, and GraphRetriever.  It enforces the six required
lifecycle methods and emits structured JSONL events for every state transition.

Control Plane component — no computational work lives here.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from thalos_prime.graph_rag.ingestion import GraphIngestionPipeline
from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph
from thalos_prime.graph_rag.retrieval import GraphRetriever
from thalos_prime.graph_rag.schema import (
    GRAPH_RAG_SEED_SALT,
    GRAPH_SCHEMA_VERSION,
    GraphRetrievalResult,
)
from thalos_prime.ingest import CanonicalArtifact


class GraphRAGError(Exception):
    """Raised when the GraphRAG subsystem encounters an unrecoverable error."""


class GraphRAGControlPlane:
    """Lifecycle orchestrator for the GraphRAG subsystem.

    Lifecycle:
        initialize() → validate() → operate() → reconcile()
        → checkpoint() → terminate()

    State surfaces:
        graph: KnowledgeGraph (observable, serializable, versioned)
        _pipeline: GraphIngestionPipeline (Data Plane)
        _retriever: GraphRetriever (Data Plane)
        _initialized: bool
        _terminated: bool
    """

    def __init__(
        self,
        seed: int,
        workdir: str,
        *,
        max_hops: int = 3,
        min_edge_weight: float = 0.1,
        alpha: float = 0.6,
        top_k: int = 10,
        co_occurrence_window: int = 256,
    ) -> None:
        """Initialize the GraphRAG Control Plane.

        Args:
            seed: Deterministic seed (XOR-salted to graph_rag seed).
            workdir: Working directory for snapshots and JSONL logs.
            max_hops: BFS hop limit for retriever.
            min_edge_weight: Prune threshold for retriever.
            alpha: Graph vs text score blend for retriever.
            top_k: Maximum retrieval results.
            co_occurrence_window: Character window for co-occurrence edges.

        """
        self._seed = seed ^ GRAPH_RAG_SEED_SALT
        self._workdir = Path(workdir)
        self._max_hops = max_hops
        self._min_edge_weight = min_edge_weight
        self._alpha = alpha
        self._top_k = top_k
        self._co_occurrence_window = co_occurrence_window

        self.graph: KnowledgeGraph = KnowledgeGraph()
        self._pipeline: GraphIngestionPipeline | None = None
        self._retriever: GraphRetriever | None = None
        self._initialized: bool = False
        self._terminated: bool = False
        self._log_path: Path | None = None

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Set up resources and load any persisted graph snapshot.

        Raises:
            GraphRAGError: On initialization failure.

        """
        self._workdir.mkdir(parents=True, exist_ok=True)
        snap_dir = self._workdir / "graph_snapshots"
        snap_dir.mkdir(exist_ok=True)
        self._log_path = self._workdir / "graph_rag_events.jsonl"

        # Restore from latest snapshot if present
        snapshots = sorted(snap_dir.glob("snapshot_*.json"))
        if snapshots:
            latest = snapshots[-1]
            try:
                data = json.loads(latest.read_text(encoding="utf-8"))
                self.graph = KnowledgeGraph.from_dict(data)
            except Exception as exc:
                raise GraphRAGError(f"Failed to load graph snapshot: {exc}") from exc

        self._pipeline = GraphIngestionPipeline(
            self.graph, co_occurrence_window=self._co_occurrence_window
        )
        self._retriever = GraphRetriever(
            max_hops=self._max_hops,
            min_edge_weight=self._min_edge_weight,
            alpha=self._alpha,
            top_k=self._top_k,
        )
        self._initialized = True
        self._emit("lifecycle.initialize", {
            "node_count": self.graph.node_count,
            "edge_count": self.graph.edge_count,
            "seed": self._seed,
        })

    def validate(self) -> None:
        """Validate graph schema version and required component readiness.

        Raises:
            GraphRAGError: If validation fails.

        """
        if not self._initialized:
            raise GraphRAGError("validate() called before initialize()")
        if self._pipeline is None or self._retriever is None:
            raise GraphRAGError("Pipeline or retriever not initialized")
        self._emit("lifecycle.validate", {"schema_version": GRAPH_SCHEMA_VERSION})

    def operate(self, artifacts: list[CanonicalArtifact]) -> list[str]:
        """Ingest a batch of CanonicalArtifacts into the knowledge graph.

        Args:
            artifacts: Artifacts to ingest.

        Returns:
            Flat list of all EntityNode IDs created or updated.

        Raises:
            GraphRAGError: If operate() called before initialize()/validate().

        """
        if not self._initialized:
            raise GraphRAGError("operate() called before initialize()/validate()")
        if self._pipeline is None:
            raise GraphRAGError("Pipeline not initialized")

        all_entity_ids: list[str] = []
        for artifact in artifacts:
            entity_ids = self._pipeline.ingest(artifact)
            all_entity_ids.extend(entity_ids)

        self._emit("lifecycle.operate", {
            "artifacts_ingested": len(artifacts),
            "entities_upserted": len(all_entity_ids),
            "node_count": self.graph.node_count,
            "edge_count": self.graph.edge_count,
        })
        return all_entity_ids

    def query(self, query_text: str) -> list[GraphRetrievalResult]:
        """Run a retrieval query against the knowledge graph.

        Args:
            query_text: Natural language query.

        Returns:
            Sorted list of GraphRetrievalResult.

        Raises:
            GraphRAGError: If not initialized.

        """
        if not self._initialized or self._retriever is None:
            raise GraphRAGError("query() called before initialize()/validate()")
        return self._retriever.retrieve(query_text, self.graph)

    def reconcile(self) -> None:
        """Remove orphaned FragmentNodes and log reconciliation actions."""
        if not self._initialized:
            raise GraphRAGError("reconcile() called before initialize()")
        orphans = self.graph.orphaned_fragment_ids()
        for oid in orphans:
            self.graph._graph.remove_node(oid)
        self._emit("lifecycle.reconcile", {
            "orphans_removed": len(orphans),
            "node_count": self.graph.node_count,
            "edge_count": self.graph.edge_count,
        })

    def checkpoint(self) -> Path:
        """Serialize the graph to an atomic JSONL snapshot.

        Returns:
            Path to the written snapshot file.

        Raises:
            GraphRAGError: If not initialized.

        """
        if not self._initialized:
            raise GraphRAGError("checkpoint() called before initialize()")
        snap_dir = self._workdir / "graph_snapshots"
        snap_dir.mkdir(exist_ok=True)
        ts = int(time.time() * 1000)
        snap_path = snap_dir / f"snapshot_{ts}.json"
        self.graph.snapshot(snap_path)
        self._emit("lifecycle.checkpoint", {
            "snapshot_path": str(snap_path),
            "node_count": self.graph.node_count,
            "edge_count": self.graph.edge_count,
        })
        return snap_path

    def terminate(self) -> None:
        """Release resources and flush pending log events."""
        self._emit("lifecycle.terminate", {
            "node_count": self.graph.node_count,
            "edge_count": self.graph.edge_count,
        })
        self._terminated = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append a structured JSONL event to the log."""
        event = {
            "timestamp_ns": time.time_ns(),
            "version": GRAPH_SCHEMA_VERSION,
            "seed": self._seed,
            "module": "graph_rag",
            "event_type": event_type,
            "payload": payload,
        }
        if self._log_path is not None:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event) + "\n")
