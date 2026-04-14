"""Individuation Engine for Thalos Prime.

Implements the *principium individuationis* — the process by which distinct
entities emerge from the pre-individual field of infinite possibility
represented by the Library of Babel.

Theoretical grounding
---------------------
* **Philosophical** (Leibniz, Schopenhauer): a thing is identified as
  individual through its unique position in space and time; here, an
  address constitutes that position within the infinite library.
* **Jungian psychology**: individuation is the integration of disparate
  elements (raw page content) into a coherent, differentiated whole
  (a decoded, meaningful page).  Coherence scoring measures how far along
  that integration has progressed.
* **Simondon's ontology**: individuation is a *never-ending* process that
  always leaves a pre-individual remainder enabling future individuations.
  Unexplored addresses constitute that remainder.
* **Stiegler's triple individuation**: psychic (the query formulated by
  the user), collective (the shared corpus of all Babel pages), and
  technical (the deterministic address-generation algorithm) individuations
  proceed together and are inseparable.
* **Privacy / GDPR framing**: individuation is the act of "singling out"
  — distinguishing one page from all others.  The ``entity_id`` field
  provides the unique identifier that achieves this singling-out.

In the Library of Babel context
--------------------------------
* The *pre-individual field* is the infinite space of all possible 3 200-
  character pages.
* Each address generation is an act of individuation: one specific page is
  singled out from the infinite.
* The coherence score quantifies the *degree* of individuation achieved:
  0 = undifferentiated noise, 100 = fully meaningful, distinct individual.
* The search process represents *metastable equilibrium*: the system
  resolves tension between undifferentiated possibility and individuated
  meaning through repeated address enumeration and coherence scoring.

Control-plane role
------------------
This module belongs to the **Control Plane**.  It coordinates which
addresses have been individuated, tracks the pre-individual remainder, and
logs all individuation events for deterministic replay.  No data-plane
computational work (page generation, n-gram scoring) belongs here.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from enum import StrEnum

from thalos_prime.library_of_sense.core.interfaces import ValidationResult
from thalos_prime.lifecycle import BaseLifecycleComponent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase taxonomy
# ---------------------------------------------------------------------------


class IndividuationPhase(StrEnum):
    """Phases of the individuation process.

    Mirrors Simondon's ontological stages: the individual emerges *through*
    a process that begins in the undifferentiated pre-individual and may
    eventually participate in a collective.
    """

    PRE_INDIVIDUAL = "pre_individual"
    """Undifferentiated possibility; the address exists but has not been
    explored or scored."""

    INDIVIDUATING = "individuating"
    """Active differentiation; the page has been retrieved and scoring is
    in progress."""

    INDIVIDUAL = "individual"
    """Distinctly identified; the page has a stable coherence score and a
    unique entity_id."""

    COLLECTIVE = "collective"
    """Part of a collective individual; the page has been grouped with
    related individuated pages to form a higher-order meaning unit."""


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndividuatedEntity:
    """A fully individuated entity with unique identity and provenance.

    Represents an entity singled out from the pre-individual field through
    the individuation process.  Each entity is distinct and identifiable by
    its ``entity_id`` (SHA-256 of the page content), its Library of Babel
    ``address``, and its ``phase``.

    Analogous to Schopenhauer's *principium individuationis*: the ``address``
    (space) and ``seed`` (time-like ordering seed) constitute the ground of
    distinction from all other possible pages.
    """

    entity_id: str
    """SHA-256 hex digest of the raw page text — the unique fingerprint."""

    address: str
    """Library of Babel address that deterministically generates this page."""

    phase: IndividuationPhase
    """Current phase of the individuation process for this entity."""

    coherence_score: float
    """Degree of individuation on a 0-100 scale.

    0.0  = pre-individual (pure noise)
    100.0 = fully individuated (maximally coherent and distinct)
    """

    seed: int
    """Deterministic seed used during individuation for replay."""

    query: str
    """The psychic individuation impulse — the query that triggered singling
    out this entity."""

    provenance: dict[str, object] = field(default_factory=dict)
    """Arbitrary provenance metadata (source, timestamp, etc.)."""

    def is_individual(self) -> bool:
        """Return True if this entity has completed individuation."""
        return self.phase in (IndividuationPhase.INDIVIDUAL, IndividuationPhase.COLLECTIVE)

    def individuation_degree(self) -> float:
        """Return normalised individuation degree in ``[0.0, 1.0]``.

        Maps ``coherence_score`` (0-100) to the unit interval used by
        Simondon's metastability model.
        """
        return min(1.0, max(0.0, self.coherence_score / 100.0))


@dataclass
class IndividuationResult:
    """Result of a single individuation operation.

    Captures the individuated entity together with the pre-individual
    remainder (unexplored addresses) and collective context (related
    individuated addresses), as required by Simondon's model.
    """

    entity: IndividuatedEntity
    """The entity that emerged from this individuation act."""

    pre_individual_remainder: list[str]
    """Addresses that were considered but not individuated in this pass.
    These constitute the pre-individual remainder available for future
    individuations."""

    collective_context: list[str]
    """Addresses of previously individuated entities related to the same
    query — the collective individual into which this entity is inscribed."""

    process_log: list[str] = field(default_factory=list)
    """Ordered log of discrete individuation steps for deterministic replay."""

    def is_successful(self) -> bool:
        """Return True if individuation produced a distinct individual."""
        return self.entity.is_individual() and self.entity.coherence_score > 0.0


# ---------------------------------------------------------------------------
# Engine (Control Plane lifecycle component)
# ---------------------------------------------------------------------------


class IndividuationEngine(BaseLifecycleComponent):
    """Control-plane engine that coordinates the individuation process.

    The engine tracks which addresses have been individuated, maintains the
    pre-individual remainder, and logs all events for deterministic replay.

    Triple individuation (Stiegler)
    --------------------------------
    * **Psychic** — the user's query is the psychic individual that drives
      the search.
    * **Collective** — the Library of Babel corpus is the collective
      individual from which pages emerge.
    * **Technical** — the deterministic SHA-256 address generation algorithm
      is the technical individual that makes address-to-page mapping stable.

    Lifecycle contract
    ------------------
    ``initialize`` → ``validate`` → ``operate`` → ``reconcile`` →
    ``checkpoint`` → ``terminate``.  All methods are idempotent and produce
    deterministic state transitions for identical inputs.
    """

    # Schema version for checkpoint serialization.
    _CHECKPOINT_SCHEMA_VERSION: str = "1.0.0"

    def __init__(self, seed: int = 0) -> None:
        """Initialize the individuation engine.

        Args:
            seed: Deterministic seed for all operations.  Identical seeds
                produce identical individuation sequences.

        """
        super().__init__(component_name="IndividuationEngine", seed=seed)
        self._individuated: dict[str, IndividuatedEntity] = {}
        """Map from entity_id → IndividuatedEntity for all completed entities."""

        self._collective_index: dict[str, list[str]] = {}
        """Map from query → list[entity_id] for collective individuation."""

        self._pre_individual_pool: list[str] = []
        """Addresses not yet individuated — the current pre-individual field."""

        self._validated: bool = False

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialise internal state and verify preconditions.

        Clears any stale state from a previous session and marks the engine
        as initialised.  Must complete fully or raise a typed exception.
        """
        self._individuated.clear()
        self._collective_index.clear()
        self._pre_individual_pool.clear()
        self._initialized = True
        self._validated = False
        self._emit_event(
            "initialize",
            "IndividuationEngine initialised; pre-individual field cleared",
        )

    def validate(self) -> ValidationResult:
        """Check that the engine invariants are satisfied.

        Returns:
            ValidationResult indicating whether the engine is ready to
            operate.

        """
        if not self._initialized:
            result = ValidationResult(
                valid=False,
                message="IndividuationEngine has not been initialised",
                details={"hint": "Call initialize() before validate()"},
            )
            self._emit_event("validate", f"INVALID: {result.message}")
            return result

        self._validated = True
        result = ValidationResult(
            valid=True,
            message="IndividuationEngine invariants satisfied",
            details={
                "individuated_count": str(len(self._individuated)),
                "pool_size": str(len(self._pre_individual_pool)),
            },
        )
        self._emit_event("validate", "Validation passed")
        return result

    def operate(self) -> None:
        """Execute primary individuation work.

        Processes all addresses in the pre-individual pool by promoting
        them to the ``INDIVIDUATING`` phase in the log.  Actual page
        retrieval and scoring must be performed by callers through
        :meth:`individuate`.
        """
        if not self._validated:
            msg = "IndividuationEngine.validate() must succeed before operate()"
            raise RuntimeError(msg)

        pending = len(self._pre_individual_pool)
        self._emit_event(
            "operate",
            f"operate() called; {pending} addresses in pre-individual pool; "
            f"{len(self._individuated)} already individuated",
        )

    def reconcile(self) -> None:
        """Converge engine state to a consistent, metastable equilibrium.

        Promotes INDIVIDUAL entities that share query contexts into the
        COLLECTIVE phase, and prunes any duplicate entity_ids from the
        pre-individual pool.
        """
        # Promote to COLLECTIVE where multiple entities share a query.
        promoted = 0
        updated: dict[str, IndividuatedEntity] = {}
        for entity_id, entity in self._individuated.items():
            collective = self._collective_index.get(entity.query, [])
            if len(collective) > 1 and entity.phase == IndividuationPhase.INDIVIDUAL:
                updated[entity_id] = IndividuatedEntity(
                    entity_id=entity.entity_id,
                    address=entity.address,
                    phase=IndividuationPhase.COLLECTIVE,
                    coherence_score=entity.coherence_score,
                    seed=entity.seed,
                    query=entity.query,
                    provenance=entity.provenance,
                )
                promoted += 1
            else:
                updated[entity_id] = entity
        self._individuated = updated

        # Deduplicate the pre-individual pool (preserve order).
        seen: set[str] = set()
        deduped: list[str] = []
        for addr in self._pre_individual_pool:
            if addr not in seen:
                seen.add(addr)
                deduped.append(addr)
        removed = len(self._pre_individual_pool) - len(deduped)
        self._pre_individual_pool = deduped

        self._emit_event(
            "reconcile",
            f"Reconciled: {promoted} entities promoted to COLLECTIVE; "
            f"{removed} duplicate addresses pruned from pre-individual pool",
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialise full engine state for deterministic restart.

        Returns:
            Versioned, serialisable dict with complete engine state.

        """
        checkpoint: dict[str, object] = {
            "schema_version": self._CHECKPOINT_SCHEMA_VERSION,
            "seed": self._seed,
            "initialized": self._initialized,
            "validated": self._validated,
            "individuated": {
                eid: {
                    "entity_id": e.entity_id,
                    "address": e.address,
                    "phase": e.phase.value,
                    "coherence_score": e.coherence_score,
                    "seed": e.seed,
                    "query": e.query,
                    "provenance": e.provenance,
                }
                for eid, e in self._individuated.items()
            },
            "collective_index": dict(self._collective_index),
            "pre_individual_pool": list(self._pre_individual_pool),
            "event_count": len(self._events),
        }
        self._emit_event(
            "checkpoint",
            f"Checkpoint serialised; schema={self._CHECKPOINT_SCHEMA_VERSION}",
        )
        return checkpoint

    def terminate(self) -> None:
        """Release all resources and clear internal state.

        After termination the engine must be re-initialised before use.
        """
        self._individuated.clear()
        self._collective_index.clear()
        self._pre_individual_pool.clear()
        self._initialized = False
        self._validated = False
        self._emit_event("terminate", "IndividuationEngine terminated; all state cleared")

    # ------------------------------------------------------------------
    # Core individuation API
    # ------------------------------------------------------------------

    def individuate(
        self,
        address: str,
        text: str,
        query: str,
        coherence_score: float,
        extra_candidates: list[str] | None = None,
    ) -> IndividuationResult:
        """Individuate a single Library of Babel page.

        Singling out the page at ``address`` from the pre-individual field:
        assigns it a stable ``entity_id`` (SHA-256 of its content), places it
        in the appropriate phase, and records it in the collective index.

        Args:
            address: Library of Babel address of the page.
            text: Raw 3 200-character page content.
            query: The psychic individuation impulse (user query).
            coherence_score: Pre-computed coherence score in [0.0, 100.0].
            extra_candidates: Additional addresses to add to the
                pre-individual pool for future individuations.

        Returns:
            IndividuationResult describing the individuated entity and the
            remaining pre-individual field.

        Raises:
            RuntimeError: If the engine has not been initialised.

        """
        if not self._initialized:
            msg = "IndividuationEngine must be initialised before individuating"
            raise RuntimeError(msg)

        process_log: list[str] = []

        # --- Psychic individuation: derive stable entity_id from content -----
        entity_id = hashlib.sha256(text.encode()).hexdigest()
        process_log.append(f"psychic:  entity_id={entity_id[:12]}… derived from content SHA-256")

        # --- Technical individuation: determine phase from coherence ----------
        if coherence_score >= 50.0:  # noqa: PLR2004
            phase = IndividuationPhase.INDIVIDUAL
            process_log.append(
                f"technical: coherence={coherence_score:.1f} ≥ 50 → phase=INDIVIDUAL"
            )
        elif coherence_score > 0.0:
            phase = IndividuationPhase.INDIVIDUATING
            process_log.append(
                f"technical: 0 < coherence={coherence_score:.1f} < 50 → phase=INDIVIDUATING"
            )
        else:
            phase = IndividuationPhase.PRE_INDIVIDUAL
            process_log.append(
                f"technical: coherence={coherence_score:.1f} = 0 → phase=PRE_INDIVIDUAL"
            )

        entity = IndividuatedEntity(
            entity_id=entity_id,
            address=address,
            phase=phase,
            coherence_score=coherence_score,
            seed=self._seed,
            query=query,
            provenance={"source": "individuation_engine", "seed": self._seed},
        )

        # --- Collective individuation: register in collective index -----------
        self._individuated[entity_id] = entity
        if query not in self._collective_index:
            self._collective_index[query] = []
        if entity_id not in self._collective_index[query]:
            self._collective_index[query].append(entity_id)
        collective_context = [
            self._individuated[eid].address
            for eid in self._collective_index[query]
            if eid != entity_id and eid in self._individuated
        ]
        process_log.append(
            f"collective: {len(collective_context)} related entities in collective index"
        )

        # --- Update pre-individual pool ---------------------------------------
        if extra_candidates:
            for cand in extra_candidates:
                if cand not in self._pre_individual_pool and cand != address:
                    self._pre_individual_pool.append(cand)
        # Remove this address from pool if present
        self._pre_individual_pool = [
            a for a in self._pre_individual_pool if a != address
        ]
        pre_individual_remainder = list(self._pre_individual_pool)

        self._emit_event(
            "individuate",
            f"address={address[:16]}… entity_id={entity_id[:12]}… "
            f"phase={phase.value} coherence={coherence_score:.1f}",
        )

        return IndividuationResult(
            entity=entity,
            pre_individual_remainder=pre_individual_remainder,
            collective_context=collective_context,
            process_log=process_log,
        )

    def get_collective(self, query: str) -> list[IndividuatedEntity]:
        """Return all individuated entities for a query (the collective individual).

        Args:
            query: Query whose collective individual is requested.

        Returns:
            List of IndividuatedEntity objects, ordered by coherence score
            descending.

        """
        entity_ids = self._collective_index.get(query, [])
        entities = [self._individuated[eid] for eid in entity_ids if eid in self._individuated]
        return sorted(entities, key=lambda e: e.coherence_score, reverse=True)

    def get_pre_individual_pool(self) -> list[str]:
        """Return the current pre-individual pool (unexplored addresses).

        Returns:
            Ordered list of addresses not yet individuated.

        """
        return list(self._pre_individual_pool)

    def add_to_pre_individual_pool(self, addresses: list[str]) -> int:
        """Add addresses to the pre-individual field for future individuations.

        Args:
            addresses: Addresses to enqueue.

        Returns:
            Number of new addresses added (duplicates skipped).

        """
        added = 0
        existing = set(self._pre_individual_pool)
        for addr in addresses:
            if addr not in existing:
                self._pre_individual_pool.append(addr)
                existing.add(addr)
                added += 1
        self._emit_event("add_to_pool", f"Added {added} addresses to pre-individual pool")
        return added

    def individuation_summary(self) -> dict[str, object]:
        """Return a human-readable summary of the current individuation state.

        Returns:
            Dict with counts and phase distribution for observability.

        """
        phase_counts: dict[str, int] = {p.value: 0 for p in IndividuationPhase}
        for entity in self._individuated.values():
            phase_counts[entity.phase.value] += 1

        return {
            "total_individuated": len(self._individuated),
            "pre_individual_pool_size": len(self._pre_individual_pool),
            "collective_queries": len(self._collective_index),
            "phase_distribution": phase_counts,
            "seed": self._seed,
            "initialized": self._initialized,
            "validated": self._validated,
        }


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

# Shared engine instance for module-level helpers.
_default_engine: IndividuationEngine | None = None


def _get_default_engine() -> IndividuationEngine:
    """Return (lazily initialised) module-level IndividuationEngine."""
    global _default_engine  # noqa: PLW0603
    if _default_engine is None:
        _default_engine = IndividuationEngine(seed=0)
        _default_engine.initialize()
        _default_engine.validate()
    return _default_engine


def individuate_page(
    address: str,
    text: str,
    query: str,
    coherence_score: float,
    extra_candidates: list[str] | None = None,
) -> IndividuationResult:
    """Individuate a single Library of Babel page using the shared engine.

    Convenience wrapper around :meth:`IndividuationEngine.individuate` for
    callers that do not need a dedicated engine instance.

    Args:
        address: Library of Babel address of the page.
        text: Raw page content (3 200 characters).
        query: User query that triggered this individuation.
        coherence_score: Pre-computed coherence score in [0.0, 100.0].
        extra_candidates: Additional addresses to enqueue in the
            pre-individual pool.

    Returns:
        IndividuationResult with the individuated entity and remainder.

    """
    return _get_default_engine().individuate(
        address=address,
        text=text,
        query=query,
        coherence_score=coherence_score,
        extra_candidates=extra_candidates,
    )


def get_individuation_summary() -> dict[str, object]:
    """Return the individuation summary for the shared engine.

    Returns:
        Dict with phase distribution and pool statistics.

    """
    return _get_default_engine().individuation_summary()


__all__ = [
    "IndividuatedEntity",
    "IndividuationEngine",
    "IndividuationPhase",
    "IndividuationResult",
    "get_individuation_summary",
    "individuate_page",
]
