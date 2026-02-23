"""Thalos Prime - Knowledge Graph Layer.

Provides a Neo4j-compatible knowledge graph interface backed by NetworkX
for local deterministic operation. Supports Cypher-style queries, node/relationship
CRUD, pattern matching, and path traversal.
"""

from thalos_prime.knowledge_graph.neo4j_graph import (
    CypherQuery,
    Neo4jKnowledgeGraph,
    NodeRecord,
    RelationshipRecord,
)

__all__ = [
    "CypherQuery",
    "Neo4jKnowledgeGraph",
    "NodeRecord",
    "RelationshipRecord",
]
