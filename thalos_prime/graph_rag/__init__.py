"""GraphRAG Add-on for Thalos Prime.

Provides hybrid retrieval combining in-memory knowledge-graph traversal with
(stubbed) vector-similarity search.  This module is the public entry point for
the graph_rag sub-package.

Control-plane boundary: graph_rag is a DATA-PLANE component.  It executes
retrieval work only; lifecycle coordination is the caller's responsibility.

Lifecycle:
    1. initialize()  — allocate graph and retriever instances.
    2. validate()    — verify graph invariants and configuration.
    3. operate()     — accept queries via HybridRetriever.retrieve().
    4. reconcile()   — converge graph to consistent state.
    5. checkpoint()  — serialise graph state for restart.
    6. terminate()   — release resources.

State surfaces:
    KnowledgeGraph.node_count  — observable node count.
    KnowledgeGraph.edge_count  — observable edge count.
    HybridRetriever.is_ready   — ready flag after initialize/validate.

Event log schema (v1):
    {
        "schema_version": 1,
        "event":   "<lifecycle | query | graph_op>",
        "ts":      "<ISO-8601 UTC>",
        "details": { ... }
    }
"""

from thalos_prime.graph_rag.interfaces import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    RetrievalCandidate,
    Retriever,
)
from thalos_prime.graph_rag.retriever import HybridRetriever
from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph

__all__: list[str] = [
    "GraphEdge",
    "GraphNode",
    "HybridRetriever",
    "KnowledgeGraph",
    "RetrievalCandidate",
    "Retriever",
    "SimpleKnowledgeGraph",
]
