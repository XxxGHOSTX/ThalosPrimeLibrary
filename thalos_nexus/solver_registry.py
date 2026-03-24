"""Thalos NEXUS — Solver Registry.

Provides a typed, keyword-searchable registry of cognitive solver tools
(cryptography, math, games, informatics) for the Universal Solver Registry.

Distinct from the subprocess-level ToolRegistry in thalos_nexus.cytoplasm:
- cytoplasm.ToolRegistry: CLI tool execution via subprocess
- solver_registry.SolverRegistry: cognitive solver discovery and descriptor
  management for the Riemann-Babel Filter pipeline and recipe engine.

Control Plane boundary: solver registration, discovery, and descriptor
management only. No computational execution or I/O happens here.

State surfaces:
    _solvers: dict[str, SolverDescriptor]
        Exposed via list_all() and get() for full observability.

Checkpoint format: N/A — volatile in-memory registry rebuilt on restart
from caller configuration.

Event log: none — stateless registry with no state transitions to record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Type alias — used in public signatures and as a module-level export.
# ---------------------------------------------------------------------------

SolverCategory = Literal["cryptography", "math", "games", "informatics"]


# ---------------------------------------------------------------------------
# Value-object dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SolverInput:
    """Input envelope passed to a solver entrypoint.

    Attributes:
        raw: The raw input string for the solver to process.
        hints: Optional key/value hints that may guide solver behaviour
            (e.g. ``{"cipher": "caesar", "shift": 13}``).
    """

    raw: str
    hints: dict[str, object] = field(default_factory=dict)


@dataclass
class SolverOutput:
    """Output envelope returned from a solver entrypoint.

    Attributes:
        result: The primary result object produced by the solver.
        metadata: Supplementary key/value metadata about the result
            (e.g. confidence scores, intermediate steps).
    """

    result: object
    metadata: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Descriptor
# ---------------------------------------------------------------------------


@dataclass
class SolverDescriptor:
    """Descriptor for a registered cognitive solver tool.

    Not frozen because ``Callable`` fields do not interact well with mypy's
    ``__hash__`` derivation in strict mode; callers should treat descriptors
    as logically immutable after construction.

    Attributes:
        name: Unique solver name used as the registry key.
        category: High-level domain of the solver.
        keywords: Set of lowercase keyword tokens for full-text search.
        description: Human-readable description of what the solver does.
        entrypoint: Callable that accepts a ``SolverInput`` and returns a
            ``SolverOutput``.
        tags: Set of capability tags used by the recipe engine
            (e.g. ``{"cipher_id", "classical_cipher"}``).
        supports_cipher_id: Whether the solver can identify cipher types.
        supports_encoding_chain: Whether the solver can decode encoding chains.
        priority: Lower numbers indicate higher priority; default is 100.
    """

    name: str
    category: Literal["cryptography", "math", "games", "informatics"]
    keywords: frozenset[str]
    description: str
    entrypoint: Callable[[SolverInput], SolverOutput]
    tags: frozenset[str] = field(default_factory=frozenset)
    supports_cipher_id: bool = False
    supports_encoding_chain: bool = False
    priority: int = 100


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SolverNotFoundError(KeyError):
    """Raised when a named solver is not present in the registry.

    Inherits from ``KeyError`` to align with standard mapping semantics.
    Callers may catch ``KeyError`` or the more specific ``SolverNotFoundError``.
    """


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class SolverRegistry:
    """Typed, keyword-searchable registry of cognitive solver descriptors.

    Stores ``SolverDescriptor`` instances keyed by their unique ``name``.
    All mutating operations (``register``, ``unregister``) take effect
    immediately and are visible to subsequent ``get``/``search``/``list_all``
    calls.

    Thread-safety: not guaranteed; callers that share a registry across
    threads must add external locking.
    """

    def __init__(self) -> None:
        """Initialise an empty solver registry."""
        self._solvers: dict[str, SolverDescriptor] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, descriptor: SolverDescriptor) -> None:
        """Register a solver descriptor.

        If a descriptor with the same name is already registered, it is
        silently overwritten.

        Args:
            descriptor: The ``SolverDescriptor`` to register.
        """
        self._solvers[descriptor.name] = descriptor

    def unregister(self, name: str) -> None:
        """Remove a solver from the registry by name.

        Args:
            name: The unique name of the solver to remove.

        Raises:
            SolverNotFoundError: If no solver with *name* is registered.
        """
        if name not in self._solvers:
            raise SolverNotFoundError(name)
        del self._solvers[name]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, name: str) -> SolverDescriptor:
        """Retrieve a solver descriptor by exact name.

        Args:
            name: The unique name of the solver.

        Returns:
            The matching ``SolverDescriptor``.

        Raises:
            SolverNotFoundError: If no solver with *name* is registered.
        """
        try:
            return self._solvers[name]
        except KeyError as exc:
            raise SolverNotFoundError(name) from exc

    def list_all(self) -> list[SolverDescriptor]:
        """Return all registered solvers sorted alphabetically by name.

        Returns:
            A new list of all registered ``SolverDescriptor`` instances,
            sorted by ``name`` ascending.
        """
        return sorted(self._solvers.values(), key=lambda d: d.name)

    def search(
        self,
        query: str,
        *,
        category: Literal["cryptography", "math", "games", "informatics"] | None = None,
    ) -> list[SolverDescriptor]:
        """Search for solvers by keyword query, with optional category filter.

        The *query* is tokenised on whitespace and lowercased.  Each
        descriptor is scored by the size of the intersection between its
        ``keywords`` set and the query tokens.  Descriptors with zero
        overlap are excluded.

        Results are sorted by ``(-overlap, priority, name)`` so the most
        relevant, highest-priority solvers appear first.

        Args:
            query: Whitespace-separated search terms.
            category: If provided, restrict results to this category.

        Returns:
            A list of matching ``SolverDescriptor`` instances, sorted by
            relevance then priority then name.
        """
        tokens = frozenset(query.lower().split())
        if not tokens:
            return []

        matches: list[tuple[int, int, str, SolverDescriptor]] = []
        for descriptor in self._solvers.values():
            if category is not None and descriptor.category != category:
                continue
            overlap = len(tokens & descriptor.keywords)
            if overlap > 0:
                matches.append((-overlap, descriptor.priority, descriptor.name, descriptor))

        matches.sort(key=lambda t: (t[0], t[1], t[2]))
        return [m[3] for m in matches]

    def find_by_tags(self, tags: frozenset[str]) -> list[SolverDescriptor]:
        """Return solvers whose tag sets intersect with *tags*.

        Args:
            tags: Set of capability tags to match against.

        Returns:
            A list of ``SolverDescriptor`` instances whose ``tags`` field
            has at least one element in common with *tags*, sorted by
            ``(priority, name)`` ascending.
        """
        if not tags:
            return []
        results = [
            d for d in self._solvers.values() if d.tags & tags
        ]
        results.sort(key=lambda d: (d.priority, d.name))
        return results


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_GLOBAL_SOLVER_REGISTRY: SolverRegistry = SolverRegistry()


def get_global_solver_registry() -> SolverRegistry:
    """Return the process-level global ``SolverRegistry`` singleton.

    The global registry is initialised empty and populated by solver
    packages at import time or during application startup.

    Returns:
        The singleton ``SolverRegistry`` instance.
    """
    return _GLOBAL_SOLVER_REGISTRY


__all__: list[str] = [
    "SolverCategory",
    "SolverDescriptor",
    "SolverInput",
    "SolverNotFoundError",
    "SolverOutput",
    "SolverRegistry",
    "get_global_solver_registry",
]
