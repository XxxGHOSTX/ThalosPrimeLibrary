"""Thalos Prime - Graph-RAG subsystem.

Provides a standalone knowledge graph with hybrid retrieval (graph + text),
following strict lifecycle and deterministic contracts.
"""

from thalos_prime.graph_rag.interfaces import (
    GraphEdge,
    GraphNode,
    GraphQueryResult,
    KnowledgeGraphProtocol,
)
from thalos_prime.graph_rag.retriever import HybridResult, HybridRetriever
from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph

__all__ = [
    "GraphEdge",
    "GraphNode",
    "GraphQueryResult",
    "HybridResult",
    "HybridRetriever",
    "KnowledgeGraphProtocol",
    "SimpleKnowledgeGraph",
]
