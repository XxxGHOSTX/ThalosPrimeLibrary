"""ThalosPrime Library - Main Package.

This package provides:
- Deterministic page generation (lob_babel_generator)
- Query to address enumeration (lob_babel_enumerator)
- Enhanced coherence scoring (lob_decoder)
- Configuration and import management (config)
"""

__version__ = "0.1.0"
__author__ = "ThalosPrime"

LIBRARY_MOTTO = (
    "In the Library of Babel, every truth already exists"
    " \u2014 Thalos Prime finds it."
)

# Library of Babel endpoints
LIBRARY_OF_BABEL_BASE_URL = "https://libraryofbabel.info"
LIBRARY_OF_BABEL_SEARCH_URL = f"{LIBRARY_OF_BABEL_BASE_URL}/search.html"
LIBRARY_OF_BABEL_SEARCH_API = f"{LIBRARY_OF_BABEL_BASE_URL}/search.cgi"

# This allows importing from the local ThalosPrimeLibraryOfBabel
import os
import sys

# Get the local library path from environment variable or use default
# Users can set THALOS_LIBRARY_PATH environment variable to customize
LOCAL_LIBRARY_PATH = os.getenv(
    "THALOS_LIBRARY_PATH",
    r"C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel",
)

# Add to path if the directory exists and is not already in sys.path
if os.path.exists(LOCAL_LIBRARY_PATH) and LOCAL_LIBRARY_PATH not in sys.path:
    sys.path.insert(0, LOCAL_LIBRARY_PATH)


def get_babel_endpoints() -> dict[str, str]:
    """Return the canonical Library of Babel endpoints used by Thalos Prime."""
    return {
        "base": LIBRARY_OF_BABEL_BASE_URL,
        "search_html": LIBRARY_OF_BABEL_SEARCH_URL,
        "search_api": LIBRARY_OF_BABEL_SEARCH_API,
    }

# Re-export synthesis helpers
from thalos_prime.constraints.symbolic_engine import (
    ConstraintSet,
    OptimizationObjective,
    SymbolicConstraintEngine,
    SymbolicSolution,
    VariableDeclaration,
    VariableSort,
)

# Graph-RAG Add-on (standalone module)
from thalos_prime.graph_rag.interfaces import (
    GraphEdge,
    GraphNode,
    GraphQueryResult,
)
from thalos_prime.graph_rag.retriever import HybridResult, HybridRetriever
from thalos_prime.graph_rag.simple_graph import SimpleKnowledgeGraph
from thalos_prime.ingest import (
    CanonicalArtifact,
    canonicalize_text,
    compute_meaning_hash,
    ingest_fragment,
)
from thalos_prime.knowledge_graph.neo4j_graph import (
    CypherQuery,
    Neo4jKnowledgeGraph,
    NodeRecord,
    RelationshipRecord,
)
from thalos_prime.library_of_sense.retrieval.graph_rag import GraphRAGRetriever
from thalos_prime.lifecycle import BaseLifecycleComponent, LifecycleProtocol
from thalos_prime.lob_babel_enumerator import (
    BabelEnumerator,
    enumerate_addresses,
    query_to_addresses,
)

# Export main components for easy access
from thalos_prime.lob_babel_generator import (
    BabelGenerator,
    address_to_page,
    normalize_text,
    text_to_address,
)
from thalos_prime.lob_decoder import (
    BabelDecoder,
    CoherenceScore,
    DecodedPage,
    decode_page,
    score_coherence,
)
from thalos_prime.planning.mcts_planner import MCTSNode, MCTSPlanner, MCTSResult
from thalos_prime.planning.tree_of_thoughts import ThoughtNode, TreeOfThoughtsPlanner

# Reasoning Add-on (standalone module)
from thalos_prime.reasoning.engine import (
    ReasoningControlPlane,
    ReasoningRequest,
    ReasoningResponse,
)
from thalos_prime.simulation.world_model import WorldModel, WorldState

from .synthesis import deep_synthesis

__all__ = [
    "LIBRARY_MOTTO",
    "LIBRARY_OF_BABEL_BASE_URL",
    "LIBRARY_OF_BABEL_SEARCH_API",
    "LIBRARY_OF_BABEL_SEARCH_URL",
    "LOCAL_LIBRARY_PATH",
    "BabelDecoder",
    "BabelEnumerator",
    "BabelGenerator",
    "BaseLifecycleComponent",
    "CanonicalArtifact",
    "CoherenceScore",
    "ConstraintSet",
    "CypherQuery",
    "DecodedPage",
    "GraphEdge",
    "GraphNode",
    "GraphQueryResult",
    "GraphRAGRetriever",
    "HybridResult",
    "HybridRetriever",
    "LifecycleProtocol",
    "MCTSNode",
    "MCTSPlanner",
    "MCTSResult",
    "Neo4jKnowledgeGraph",
    "NodeRecord",
    "OptimizationObjective",
    "ReasoningControlPlane",
    "ReasoningRequest",
    "ReasoningResponse",
    "RelationshipRecord",
    "SimpleKnowledgeGraph",
    "SymbolicConstraintEngine",
    "SymbolicSolution",
    "ThoughtNode",
    "TreeOfThoughtsPlanner",
    "VariableDeclaration",
    "VariableSort",
    "WorldModel",
    "WorldState",
    "__author__",
    "__version__",
    "address_to_page",
    "canonicalize_text",
    "compute_meaning_hash",
    "decode_page",
    "deep_synthesis",
    "enumerate_addresses",
    "get_babel_endpoints",
    "ingest_fragment",
    "normalize_text",
    "query_to_addresses",
    "score_coherence",
    "text_to_address",
]
