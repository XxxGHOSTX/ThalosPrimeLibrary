"""Individuation Routes — REST endpoints for individuation operations.

Exposes the principium individuationis as an HTTP API:

* ``POST /api/v1/individuation/individuate`` — individuate a single page.
* ``GET  /api/v1/individuation/collective``  — retrieve collective individual
  for a query.
* ``GET  /api/v1/individuation/pool``        — inspect the pre-individual pool.
* ``POST /api/v1/individuation/pool``        — enqueue addresses into the pool.
* ``GET  /api/v1/individuation/summary``     — observability summary.
* ``POST /api/v1/individuation/reconcile``   — trigger engine reconciliation.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query

from thalos_prime.individuation import (
    IndividuatedEntity,
    IndividuationEngine,
    IndividuationPhase,
    IndividuationResult,
    get_individuation_summary,
    individuate_page,
)

router = APIRouter()

# Shared engine instance for this route module.
_engine = IndividuationEngine(seed=0)
_engine.initialize()
_engine.validate()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity_to_dict(entity: IndividuatedEntity) -> dict[str, Any]:
    """Serialise an IndividuatedEntity to a JSON-safe dict."""
    return {
        "entity_id": entity.entity_id,
        "address": entity.address,
        "phase": entity.phase.value,
        "coherence_score": entity.coherence_score,
        "individuation_degree": entity.individuation_degree(),
        "is_individual": entity.is_individual(),
        "seed": entity.seed,
        "query": entity.query,
        "provenance": entity.provenance,
    }


def _result_to_dict(result: IndividuationResult) -> dict[str, Any]:
    """Serialise an IndividuationResult to a JSON-safe dict."""
    return {
        "entity": _entity_to_dict(result.entity),
        "pre_individual_remainder_count": len(result.pre_individual_remainder),
        "pre_individual_remainder": result.pre_individual_remainder[:10],
        "collective_context": result.collective_context,
        "process_log": result.process_log,
        "is_successful": result.is_successful(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/individuate")
async def individuate_endpoint(
    address: Annotated[str, Body(embed=True, description="Library of Babel address")],
    text: Annotated[str, Body(embed=True, description="Raw page content (3 200 chars)")],
    query: Annotated[str, Body(embed=True, description="User query (psychic individual)")],
    coherence_score: Annotated[
        float,
        Body(embed=True, ge=0.0, le=100.0, description="Pre-computed coherence score"),
    ],
    extra_candidates: Annotated[
        list[str],
        Body(embed=True, description="Extra addresses for the pre-individual pool"),
    ] = [],  # noqa: B006
) -> dict[str, Any]:
    """Individuate a single Library of Babel page.

    Singling out one page from the infinite pre-individual field:
    assigns it a stable SHA-256 entity_id, determines its individuation
    phase, and registers it in the collective index.

    Args:
        address: Library of Babel address of the page.
        text: Raw page content (3 200 characters).
        query: User query that triggered this individuation.
        coherence_score: Pre-computed coherence score in [0.0, 100.0].
        extra_candidates: Additional addresses for the pre-individual pool.

    Returns:
        IndividuationResult serialised as JSON.

    """
    try:
        result = _engine.individuate(
            address=address,
            text=text,
            query=query,
            coherence_score=coherence_score,
            extra_candidates=extra_candidates or [],
        )
        return _result_to_dict(result)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/collective")
async def get_collective(
    query: Annotated[str, Query(description="Query whose collective individual to retrieve")],
) -> dict[str, Any]:
    """Retrieve the collective individual for a query.

    Returns all individuated entities that share the given psychic
    individuation impulse (query), sorted by coherence score descending.
    This embodies Simondon's collective individuation: multiple individuals
    co-arising from the same pre-individual field.

    Args:
        query: The psychic individuation impulse.

    Returns:
        Dict with entity list and collective statistics.

    """
    entities = _engine.get_collective(query)
    return {
        "query": query,
        "collective_size": len(entities),
        "entities": [_entity_to_dict(e) for e in entities],
        "phase_distribution": {
            phase.value: sum(1 for e in entities if e.phase == phase)
            for phase in IndividuationPhase
        },
    }


@router.get("/pool")
async def get_pool(
    limit: Annotated[int, Query(ge=1, le=500, description="Max addresses to return")] = 100,
) -> dict[str, Any]:
    """Inspect the pre-individual pool (unexplored addresses).

    The pre-individual pool is the Simondonian remainder: addresses that
    have not yet been individuated and are available for future operations.

    Args:
        limit: Maximum number of addresses to return.

    Returns:
        Dict with pool size and a sample of addresses.

    """
    pool = _engine.get_pre_individual_pool()
    return {
        "pool_size": len(pool),
        "addresses": pool[:limit],
    }


@router.post("/pool")
async def add_to_pool(
    addresses: Annotated[
        list[str],
        Body(embed=True, description="Addresses to enqueue in the pre-individual pool"),
    ],
) -> dict[str, Any]:
    """Enqueue addresses into the pre-individual pool.

    Adds candidate addresses to the pool of unexplored possibilities, making
    them available for future individuation operations.

    Args:
        addresses: List of Library of Babel addresses to enqueue.

    Returns:
        Dict with the number of addresses added.

    """
    if len(addresses) > 1000:
        raise HTTPException(status_code=400, detail="Cannot enqueue more than 1 000 addresses at once")
    added = _engine.add_to_pre_individual_pool(addresses)
    return {
        "added": added,
        "pool_size": len(_engine.get_pre_individual_pool()),
    }


@router.get("/summary")
async def individuation_summary() -> dict[str, Any]:
    """Return the individuation observability summary.

    Exposes the current state of the shared individuation engine:
    phase distribution, pool size, collective index statistics, and seed.

    Returns:
        Dict with full individuation summary.

    """
    return get_individuation_summary()


@router.post("/reconcile")
async def reconcile() -> dict[str, Any]:
    """Trigger engine reconciliation.

    Promotes INDIVIDUAL entities that share query contexts into the
    COLLECTIVE phase, and prunes duplicates from the pre-individual pool.
    This drives the system toward metastable equilibrium.

    Returns:
        Updated individuation summary after reconciliation.

    """
    try:
        _engine.reconcile()
        return {
            "status": "reconciled",
            "summary": get_individuation_summary(),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/individuate/module")
async def individuate_via_module(
    address: Annotated[str, Body(embed=True)],
    text: Annotated[str, Body(embed=True)],
    query: Annotated[str, Body(embed=True)],
    coherence_score: Annotated[float, Body(embed=True, ge=0.0, le=100.0)],
) -> dict[str, Any]:
    """Individuate using the module-level shared engine.

    Uses the ``individuate_page`` module-level helper which maintains its
    own shared engine instance separate from the route-level engine.
    Useful for callers that prefer module-level state isolation.

    Args:
        address: Library of Babel address.
        text: Raw page content.
        query: User query.
        coherence_score: Coherence score in [0.0, 100.0].

    Returns:
        IndividuationResult serialised as JSON.

    """
    try:
        result = individuate_page(
            address=address,
            text=text,
            query=query,
            coherence_score=coherence_score,
        )
        return _result_to_dict(result)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
