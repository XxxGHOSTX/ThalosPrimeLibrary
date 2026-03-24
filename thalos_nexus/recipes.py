"""Thalos NEXUS — Recipe Engine.

Maps DataSignature instances to ranked solver tools via registered recipes.
Used by the Riemann-Babel Filter pipeline to select appropriate solvers
for each candidate page.

Control Plane boundary: recipe matching and solver planning only.
No computational execution or I/O happens here.

State surfaces:
    _recipes: tuple[Recipe, ...] in RecipeEngine
        Fixed at construction time; immutable after __init__.
    _registry: SolverRegistry reference in RecipeEngine.

Checkpoint format: N/A — stateless planning layer.

Event log: none — deterministic pure functions with no transitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from thalos_nexus.solver_registry import get_global_solver_registry

if TYPE_CHECKING:
    from collections.abc import Sequence

    from thalos_nexus.solver_registry import SolverDescriptor, SolverRegistry

# ---------------------------------------------------------------------------
# Module-level constants — named to avoid PLR2004 magic-value warnings
# ---------------------------------------------------------------------------

_CIPHER_LOW_ENTROPY: float = 0.35
_CIPHER_HIGH_ENTROPY: float = 0.80
_ENCODING_HIGH_ENTROPY: float = 0.85
_DEFAULT_PRIME_THRESHOLD: float = 0.5

# ---------------------------------------------------------------------------
# Data signature
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DataSignature:
    """Metadata descriptor for a page of text produced by the Babel pipeline.

    Captures structural and statistical properties of a text buffer so that
    the ``RecipeEngine`` can select appropriate solver tools without
    re-reading the raw text.

    Attributes:
        length: Total character count of the text.
        char_classes: Set of character-class labels present in the text
            (drawn from ``{"alpha", "digit", "space", "punct", "other"}``).
        has_whitespace: True when the text contains at least one whitespace
            character.
        entropy: Normalised Shannon entropy of the text in ``[0.0, 1.0]``.
        language_hint: ISO language code hint, or ``None`` if unknown.
        likely_cipher: Name of the most probable cipher type, or ``None``
            if no cipher was identified.
        encoding_layers: Ordered tuple of detected encoding layer names
            (e.g. ``("base64", "rot13")``), innermost last.
        prime_index_score: Composite prime-index alignment score from the
            Riemann-Babel Filter in ``[0.0, 1.0]``.
    """

    length: int
    char_classes: frozenset[str]
    has_whitespace: bool
    entropy: float
    language_hint: str | None
    likely_cipher: str | None
    encoding_layers: tuple[str, ...]
    prime_index_score: float


# ---------------------------------------------------------------------------
# Recipe protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Recipe(Protocol):
    """Protocol for solver-selection recipes used by the ``RecipeEngine``.

    A recipe encapsulates the matching heuristic and tool-ranking logic for
    a specific class of text (e.g. cipher text, encoded data, prime-aligned
    prose).  Implementations may be frozen dataclasses, plain classes, or
    any object satisfying this structural protocol.
    """

    name: str

    def matches(self, sig: DataSignature) -> bool:
        """Return True if this recipe should be applied to *sig*.

        Args:
            sig: The ``DataSignature`` of the candidate page.

        Returns:
            ``True`` when the recipe's heuristics identify *sig* as a
            candidate for its solver tools.
        """
        ...

    def ranked_tools(
        self,
        registry: SolverRegistry,
        signature: DataSignature,
    ) -> list[SolverDescriptor]:
        """Return an ordered list of solver descriptors for *signature*.

        The list is ordered from most to least preferred.  Callers
        (``RecipeEngine.plan``) deduplicate across recipes, so earlier
        entries win when the same solver appears in multiple recipes.

        Args:
            registry: The ``SolverRegistry`` to query.
            signature: The ``DataSignature`` of the candidate page.

        Returns:
            Ordered list of ``SolverDescriptor`` instances.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete recipe implementations
# ---------------------------------------------------------------------------


@dataclass
class CipherIdentificationRecipe:
    """Recipe that matches probable cipher or classical-cipher text.

    Matches when:
    - ``signature.likely_cipher`` is not ``None``, OR
    - entropy is in ``[0.35, 0.80]`` AND character classes are a subset
      of ``{"alpha", "space", "punct"}`` (typical of classical ciphers).

    When a ``likely_cipher`` is identified, tools whose ``tags`` include
    that cipher name are boosted to the front of the result list.

    Attributes:
        name: Recipe name, always ``"cipher-identification"``.
    """

    name: str = field(default="cipher-identification")

    def matches(self, sig: DataSignature) -> bool:
        """Return True when the signature resembles cipher text.

        Args:
            sig: Candidate page signature.

        Returns:
            ``True`` for probable cipher inputs.
        """
        if sig.likely_cipher is not None:
            return True
        return (
            _CIPHER_LOW_ENTROPY <= sig.entropy <= _CIPHER_HIGH_ENTROPY
            and sig.char_classes <= {"alpha", "space", "punct"}
        )

    def ranked_tools(
        self,
        registry: SolverRegistry,
        signature: DataSignature,
    ) -> list[SolverDescriptor]:
        """Return cipher-related tools, boosting likely-cipher matches.

        Args:
            registry: The solver registry to query.
            signature: Candidate page signature.

        Returns:
            Ordered list of cipher solver descriptors.
        """
        tools = registry.find_by_tags(frozenset({"cipher_id", "classical_cipher"}))
        if signature.likely_cipher is not None:
            boost = [t for t in tools if signature.likely_cipher in t.tags]
            rest = [t for t in tools if signature.likely_cipher not in t.tags]
            return boost + rest
        return tools


@dataclass
class EncodingChainRecipe:
    """Recipe that matches multi-layer encoded text.

    Matches when:
    - ``signature.encoding_layers`` is non-empty, OR
    - entropy >= 0.85 (high entropy is characteristic of encoded data).

    Attributes:
        name: Recipe name, always ``"encoding-chain"``.
    """

    name: str = field(default="encoding-chain")

    def matches(self, sig: DataSignature) -> bool:
        """Return True when the signature indicates an encoding chain.

        Args:
            sig: Candidate page signature.

        Returns:
            ``True`` for probable encoded inputs.
        """
        return bool(sig.encoding_layers) or sig.entropy >= _ENCODING_HIGH_ENTROPY

    def ranked_tools(
        self,
        registry: SolverRegistry,
        signature: DataSignature,
    ) -> list[SolverDescriptor]:
        """Return encoding-chain capable tools.

        Args:
            registry: The solver registry to query.
            signature: Candidate page signature (unused beyond tag lookup).

        Returns:
            Ordered list of encoding-chain solver descriptors.
        """
        return registry.find_by_tags(frozenset({"encoding_chain"}))


@dataclass
class PrimeTextRecipe:
    """Recipe that matches prime-index-aligned page text.

    Matches when ``signature.prime_index_score >= score_threshold``.

    Attributes:
        name: Recipe name, always ``"prime-text"``.
        score_threshold: Minimum composite prime-index score required for
            a match; default is ``0.5``.
    """

    name: str = field(default="prime-text")
    score_threshold: float = field(default=_DEFAULT_PRIME_THRESHOLD)

    def matches(self, sig: DataSignature) -> bool:
        """Return True when the prime-index score clears the threshold.

        Args:
            sig: Candidate page signature.

        Returns:
            ``True`` when ``sig.prime_index_score >= self.score_threshold``.
        """
        return sig.prime_index_score >= self.score_threshold

    def ranked_tools(
        self,
        registry: SolverRegistry,
        signature: DataSignature,
    ) -> list[SolverDescriptor]:
        """Return prime-sieve and Babel-aware tools.

        Args:
            registry: The solver registry to query.
            signature: Candidate page signature (unused beyond tag lookup).

        Returns:
            Ordered list of prime-text solver descriptors.
        """
        return registry.find_by_tags(frozenset({"prime_sieve", "babel"}))


# ---------------------------------------------------------------------------
# Recipe engine
# ---------------------------------------------------------------------------


class RecipeEngine:
    """Plans a ranked, deduplicated tool list for a ``DataSignature``.

    Iterates over the registered recipes in order, applying each whose
    ``matches()`` predicate fires, and collecting the resulting
    ``SolverDescriptor`` lists.  Duplicates (by ``SolverDescriptor.name``)
    are eliminated, preserving the order of first occurrence.

    Control Plane boundary: planning only.  No computation or I/O.
    """

    def __init__(
        self,
        registry: SolverRegistry,
        recipes: Sequence[Recipe],
    ) -> None:
        """Initialise the engine with a registry and an ordered recipe list.

        Args:
            registry: The ``SolverRegistry`` to pass to each recipe.
            recipes: Ordered sequence of ``Recipe`` objects; earlier recipes
                take precedence in deduplication.
        """
        self._registry = registry
        self._recipes: tuple[Recipe, ...] = tuple(recipes)

    def plan(self, signature: DataSignature) -> list[SolverDescriptor]:
        """Produce a ranked, deduplicated solver list for *signature*.

        Recipes are evaluated in registration order.  When multiple recipes
        return the same solver, only the first occurrence is retained.

        Args:
            signature: The ``DataSignature`` of the candidate page.

        Returns:
            Ordered, deduplicated list of ``SolverDescriptor`` instances.
        """
        seen: set[str] = set()
        result: list[SolverDescriptor] = []
        for recipe in self._recipes:
            if recipe.matches(signature):
                for descriptor in recipe.ranked_tools(self._registry, signature):
                    if descriptor.name not in seen:
                        seen.add(descriptor.name)
                        result.append(descriptor)
        return result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_default_recipe_engine() -> RecipeEngine:
    """Build a ``RecipeEngine`` with all built-in recipes and the global registry.

    The default engine includes, in order:

    1. ``CipherIdentificationRecipe`` — classical cipher detection
    2. ``EncodingChainRecipe`` — multi-layer encoding detection
    3. ``PrimeTextRecipe`` — prime-index-aligned text detection

    Returns:
        A fully configured ``RecipeEngine`` backed by the global
        ``SolverRegistry``.
    """
    registry = get_global_solver_registry()
    recipes: list[Recipe] = [
        CipherIdentificationRecipe(),
        EncodingChainRecipe(),
        PrimeTextRecipe(),
    ]
    return RecipeEngine(registry=registry, recipes=recipes)


__all__: list[str] = [
    "CipherIdentificationRecipe",
    "DataSignature",
    "EncodingChainRecipe",
    "PrimeTextRecipe",
    "Recipe",
    "RecipeEngine",
    "build_default_recipe_engine",
]
