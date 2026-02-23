"""thalos_prime.graph_rag — GraphRAG knowledge graph module.

Exports:
    KnowledgeGraph        — typed networkx.DiGraph wrapper
    GraphIngestionPipeline — Data Plane ingestion
    GraphRetriever         — Data Plane retrieval
    GraphRAGControlPlane   — Control Plane lifecycle orchestrator
    GraphRetrievalResult   — retrieval result dataclass
    EntityNode             — knowledge graph node type
    FragmentNode           — knowledge graph node type
    RelationshipEdge       — knowledge graph edge type
    ContainsEdge           — knowledge graph edge type
"""

from thalos_prime.graph_rag.control_plane import GraphRAGControlPlane, GraphRAGError
from thalos_prime.graph_rag.ingestion import GraphIngestionPipeline
from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph
from thalos_prime.graph_rag.retrieval import GraphRetriever
from thalos_prime.graph_rag.schema import (
    ContainsEdge,
    EntityNode,
    FragmentNode,
    GraphRetrievalResult,
    RelationshipEdge,
)

__all__ = [
    "ContainsEdge",
    "EntityNode",
    "FragmentNode",
    "GraphIngestionPipeline",
    "GraphRAGControlPlane",
    "GraphRAGError",
    "GraphRetrievalResult",
    "GraphRetriever",
    "KnowledgeGraph",
    "RelationshipEdge",
]
