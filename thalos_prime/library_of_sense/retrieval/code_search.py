"""Library of Sense - Code Search Retrieval.

Analyzes Python source code using the ast module to
extract function signatures, class names, and docstrings.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class CodeEntity:
    """Represents a discovered code entity (function, class, or variable)."""

    name: str
    entity_type: str
    docstring: str
    line_number: int
    source_file: str

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this code entity.
        """
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "docstring": self.docstring,
            "line_number": self.line_number,
            "source_file": self.source_file,
        }


class CodeSearchRetriever:
    """Searches indexed Python code for entities matching a query.

    Uses the ast module to parse Python source and extract documented
    functions and classes for retrieval.
    """

    def __init__(self) -> None:
        """Initialize the code search index."""
        self._index: list[CodeEntity] = []

    def index_source(self, source: str, filename: str = "<string>") -> int:
        """Parse Python source and add discovered entities to the index.

        Args:
            source: Python source code string.
            filename: Filename label for indexed entities.

        Returns:
            Number of entities added to the index.
        """
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as exc:
            logger.warning("CodeSearchRetriever: syntax error in %s: %s", filename, exc)
            return 0

        added = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node) or ""
                self._index.append(
                    CodeEntity(
                        name=node.name,
                        entity_type="function",
                        docstring=docstring,
                        line_number=node.lineno,
                        source_file=filename,
                    )
                )
                added += 1
            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                self._index.append(
                    CodeEntity(
                        name=node.name,
                        entity_type="class",
                        docstring=docstring,
                        line_number=node.lineno,
                        source_file=filename,
                    )
                )
                added += 1
        return added

    def search(self, query: str) -> list[CodeEntity]:
        """Search the index for entities whose name or docstring contains the query.

        Args:
            query: Search term to look for in entity names and docstrings.

        Returns:
            List of matching CodeEntity instances.
        """
        query_lower = query.lower()
        return [
            entity
            for entity in self._index
            if query_lower in entity.name.lower()
            or query_lower in entity.docstring.lower()
        ]

    def query(self, query: str, context: QueryContext) -> RetrievalResult:
        """Query the code index for entities matching the query.

        Args:
            query: Search term for entity name or docstring.
            context: Query context with domain and options.

        Returns:
            RetrievalResult with matching entities as content.
        """
        _ = context
        matches = self.search(query)
        if not matches:
            return RetrievalResult(
                source="code_search",
                content="",
                confidence=0.0,
                metadata={"query": query, "match_count": "0"},
            )
        content_parts = [
            f"{e.entity_type} {e.name}: {e.docstring[:100]}" for e in matches[:10]
        ]
        content = "\n".join(content_parts)
        return RetrievalResult(
            source="code_search",
            content=content,
            confidence=0.7,
            metadata={
                "query": query,
                "match_count": str(len(matches)),
                "index_size": str(len(self._index)),
            },
        )

    def validate(self) -> ValidationResult:
        """Validate the code search retriever.

        Returns:
            ValidationResult indicating this source is ready.
        """
        return ValidationResult(
            valid=True,
            message=f"CodeSearchRetriever ready with {len(self._index)} indexed entities",
        )

    def initialize(self) -> None:
        """Initialize the code search retriever."""
        logger.debug("CodeSearchRetriever initialized")

    def operate(self) -> None:
        """Transition to operating state."""
        logger.debug("CodeSearchRetriever operating, indexed=%d", len(self._index))

    def reconcile(self) -> None:
        """Reconcile code search retriever state."""
        logger.debug("CodeSearchRetriever reconcile: indexed=%d", len(self._index))

    def checkpoint(self) -> None:
        """Log current state as a checkpoint."""
        logger.info("CodeSearchRetriever checkpoint: indexed_entities=%d", len(self._index))

    def terminate(self) -> None:
        """Terminate the code search retriever."""
        logger.debug("CodeSearchRetriever terminated")


__all__ = ["CodeEntity", "CodeSearchRetriever"]
