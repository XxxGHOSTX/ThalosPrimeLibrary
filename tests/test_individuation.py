"""Tests for the Individuation Engine module.

Verifies the principium individuationis implementation:
- Deterministic entity_id derivation (identical content → identical id)
- Phase assignment based on coherence score
- Lifecycle contract (initialize → validate → operate → reconcile →
  checkpoint → terminate)
- Collective individuation (shared query → COLLECTIVE phase promotion)
- Pre-individual pool management
- Module-level helpers
"""

from __future__ import annotations

import hashlib

from thalos_prime.individuation import (
    IndividuatedEntity,
    IndividuationEngine,
    IndividuationPhase,
    IndividuationResult,
    get_individuation_summary,
    individuate_page,
)

# ---------------------------------------------------------------------------
# Phase assignment
# ---------------------------------------------------------------------------


def test_phase_individual_high_coherence() -> None:
    """coherence_score >= 50 → INDIVIDUAL phase."""
    engine = IndividuationEngine(seed=42)
    engine.initialize()
    engine.validate()

    result = engine.individuate(
        address="addr-high",
        text="the quick brown fox",
        query="fox",
        coherence_score=75.0,
    )
    assert result.entity.phase == IndividuationPhase.INDIVIDUAL


def test_phase_individuating_mid_coherence() -> None:
    """0 < coherence_score < 50 → INDIVIDUATING phase."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    result = engine.individuate(
        address="addr-mid",
        text="random noise xkqw",
        query="noise",
        coherence_score=25.0,
    )
    assert result.entity.phase == IndividuationPhase.INDIVIDUATING


def test_phase_pre_individual_zero_coherence() -> None:
    """coherence_score == 0 → PRE_INDIVIDUAL phase."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    result = engine.individuate(
        address="addr-zero",
        text="zzzzzzzzzzzzzzz",
        query="test",
        coherence_score=0.0,
    )
    assert result.entity.phase == IndividuationPhase.PRE_INDIVIDUAL
    assert not result.entity.is_individual()


# ---------------------------------------------------------------------------
# Determinism: identical content → identical entity_id
# ---------------------------------------------------------------------------


def test_entity_id_determinism() -> None:
    """Identical content always produces the same entity_id (SHA-256)."""
    text = "the same content"
    expected_id = hashlib.sha256(text.encode()).hexdigest()

    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    result1 = engine.individuate("addr1", text, "query", 80.0)
    result2 = engine.individuate("addr2", text, "query", 80.0)

    assert result1.entity.entity_id == expected_id
    assert result2.entity.entity_id == expected_id


def test_different_content_different_entity_id() -> None:
    """Different content produces different entity_ids."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    r1 = engine.individuate("a1", "content alpha", "q", 60.0)
    r2 = engine.individuate("a2", "content beta", "q", 60.0)

    assert r1.entity.entity_id != r2.entity.entity_id


# ---------------------------------------------------------------------------
# Individuation degree
# ---------------------------------------------------------------------------


def test_individuation_degree_boundary() -> None:
    """individuation_degree() is bounded to [0.0, 1.0]."""
    entity = IndividuatedEntity(
        entity_id="abc",
        address="addr",
        phase=IndividuationPhase.INDIVIDUAL,
        coherence_score=100.0,
        seed=0,
        query="q",
    )
    assert entity.individuation_degree() == 1.0

    low = IndividuatedEntity(
        entity_id="def",
        address="addr2",
        phase=IndividuationPhase.PRE_INDIVIDUAL,
        coherence_score=0.0,
        seed=0,
        query="q",
    )
    assert low.individuation_degree() == 0.0


def test_individuation_degree_mid() -> None:
    """individuation_degree() scales coherence_score linearly."""
    entity = IndividuatedEntity(
        entity_id="xyz",
        address="addr",
        phase=IndividuationPhase.INDIVIDUATING,
        coherence_score=50.0,
        seed=0,
        query="q",
    )
    assert abs(entity.individuation_degree() - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# Collective individuation
# ---------------------------------------------------------------------------


def test_collective_promotion_after_reconcile() -> None:
    """Multiple INDIVIDUAL entities with the same query → COLLECTIVE after reconcile."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    engine.individuate("a1", "content one for testing", "query-shared", 80.0)
    engine.individuate("a2", "content two for testing", "query-shared", 85.0)

    # Before reconcile both are INDIVIDUAL
    collective = engine.get_collective("query-shared")
    assert len(collective) == 2

    engine.operate()
    engine.reconcile()

    collective_after = engine.get_collective("query-shared")
    phases = {e.phase for e in collective_after}
    assert IndividuationPhase.COLLECTIVE in phases


def test_single_entity_not_promoted_to_collective() -> None:
    """A single entity with a unique query is not promoted to COLLECTIVE."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    engine.individuate("a1", "unique content here", "query-unique", 80.0)
    engine.reconcile()

    entities = engine.get_collective("query-unique")
    assert len(entities) == 1
    assert entities[0].phase == IndividuationPhase.INDIVIDUAL


# ---------------------------------------------------------------------------
# Pre-individual pool
# ---------------------------------------------------------------------------


def test_add_to_pool() -> None:
    """add_to_pre_individual_pool enqueues addresses correctly."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    added = engine.add_to_pre_individual_pool(["addr-a", "addr-b", "addr-c"])
    assert added == 3
    assert len(engine.get_pre_individual_pool()) == 3


def test_pool_no_duplicates() -> None:
    """Duplicate addresses are not added to the pool."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    engine.add_to_pre_individual_pool(["dup", "dup", "unique"])
    pool = engine.get_pre_individual_pool()
    assert pool.count("dup") == 1
    assert len(pool) == 2


def test_individuated_address_removed_from_pool() -> None:
    """Individuating an address removes it from the pre-individual pool."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    engine.add_to_pre_individual_pool(["target", "other"])
    engine.individuate("target", "target page content", "q", 70.0)

    pool = engine.get_pre_individual_pool()
    assert "target" not in pool
    assert "other" in pool


def test_extra_candidates_added_to_pool() -> None:
    """extra_candidates passed to individuate() are added to the pool."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    engine.individuate("primary", "content here", "q", 60.0, extra_candidates=["cand1", "cand2"])
    pool = engine.get_pre_individual_pool()
    assert "cand1" in pool
    assert "cand2" in pool


# ---------------------------------------------------------------------------
# Pre-individual pool reconciliation (deduplication)
# ---------------------------------------------------------------------------


def test_reconcile_deduplicates_pool() -> None:
    """reconcile() deduplicates the pre-individual pool."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    # Manually populate pool with duplicates (bypass add helper)
    engine._pre_individual_pool = ["x", "y", "x", "z", "y"]
    engine.reconcile()

    pool = engine.get_pre_individual_pool()
    assert len(pool) == len(set(pool))


# ---------------------------------------------------------------------------
# Lifecycle contract
# ---------------------------------------------------------------------------


def test_lifecycle_full_cycle() -> None:
    """Full initialize → validate → operate → reconcile → checkpoint → terminate."""
    engine = IndividuationEngine(seed=7)
    engine.initialize()

    vr = engine.validate()
    assert vr.valid

    engine.operate()
    engine.reconcile()

    cp = engine.checkpoint()
    assert cp["schema_version"] == "1.0.0"
    assert cp["seed"] == 7
    assert cp["initialized"] is True

    engine.terminate()
    assert not engine._initialized


def test_operate_requires_validate() -> None:
    """operate() raises RuntimeError if validate() was not called."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    # Deliberately skip validate()
    engine._validated = False
    try:
        engine.operate()
    except RuntimeError:
        pass
    else:
        msg = "Expected RuntimeError"
        raise AssertionError(msg)


def test_individuate_requires_initialize() -> None:
    """individuate() raises RuntimeError if engine was not initialised."""
    engine = IndividuationEngine(seed=0)
    # Do NOT call initialize()
    try:
        engine.individuate("addr", "text", "q", 50.0)
    except RuntimeError:
        pass
    else:
        msg = "Expected RuntimeError"
        raise AssertionError(msg)


def test_validate_fails_before_initialize() -> None:
    """validate() returns invalid result before initialize() is called."""
    engine = IndividuationEngine(seed=0)
    # _initialized is False by default
    engine._initialized = False
    vr = engine.validate()
    assert not vr.valid


def test_checkpoint_contains_all_individuated() -> None:
    """checkpoint() serialises all individuated entities."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    engine.individuate("a1", "content for checkpoint one", "q", 80.0)
    engine.individuate("a2", "content for checkpoint two", "q", 85.0)

    cp = engine.checkpoint()
    assert len(cp["individuated"]) == 2  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Individuation summary
# ---------------------------------------------------------------------------


def test_individuation_summary_structure() -> None:
    """individuation_summary() returns expected keys."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    summary = engine.individuation_summary()
    assert "total_individuated" in summary
    assert "pre_individual_pool_size" in summary
    assert "collective_queries" in summary
    assert "phase_distribution" in summary
    assert "seed" in summary


def test_individuation_summary_counts() -> None:
    """Summary counts reflect actual individuated entities."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    engine.individuate("a1", "alpha content page", "q", 80.0)
    engine.individuate("a2", "beta content page", "q", 85.0)

    summary = engine.individuation_summary()
    assert summary["total_individuated"] == 2
    assert summary["collective_queries"] == 1


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def test_module_level_individuate_page() -> None:
    """individuate_page() module helper returns a valid IndividuationResult."""
    result = individuate_page(
        address="module-addr",
        text="module level content for individuation testing",
        query="module-query",
        coherence_score=70.0,
    )
    assert isinstance(result, IndividuationResult)
    assert isinstance(result.entity, IndividuatedEntity)
    assert result.entity.phase == IndividuationPhase.INDIVIDUAL


def test_module_level_summary() -> None:
    """get_individuation_summary() returns a populated summary dict."""
    summary = get_individuation_summary()
    assert isinstance(summary, dict)
    assert "total_individuated" in summary


# ---------------------------------------------------------------------------
# IndividuationResult helpers
# ---------------------------------------------------------------------------


def test_result_is_successful_individual() -> None:
    """IndividuationResult.is_successful() is True for coherent individuals."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    result = engine.individuate("ok", "highly coherent english text here", "q", 80.0)
    assert result.is_successful()


def test_result_is_not_successful_zero_coherence() -> None:
    """IndividuationResult.is_successful() is False for zero-coherence pages."""
    engine = IndividuationEngine(seed=0)
    engine.initialize()
    engine.validate()

    result = engine.individuate("bad", "zzzzzzz", "q", 0.0)
    assert not result.is_successful()
