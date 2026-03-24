"""Tools Routes — Solver registry search and analysis endpoints.

Provides keyword-based discovery of cognitive solver tools from the
Universal Solver Registry, and text analysis via the Riemann-Babel
Filter pipeline combined with the Recipe Engine.

GET  /api/v1/tools/search?query=...&category=...   keyword search
GET  /api/v1/tools?category=...                    list all registered solvers
POST /api/v1/tools/analyze                         submit text for prime analysis
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from thalos_nexus.recipes import build_default_recipe_engine
from thalos_nexus.solver_registry import (
    SolverCategory,
    SolverDescriptor,
    get_global_solver_registry,
)
from thalos_runtime.core.prime_pipeline import find_prime_aligned_candidates

router = APIRouter()

# Allowed category values for manual validation
_VALID_CATEGORIES: frozenset[str] = frozenset(
    {"cryptography", "math", "games", "informatics"}
)


def _descriptor_to_dict(descriptor: SolverDescriptor) -> dict[str, object]:
    """Serialise a ``SolverDescriptor`` to a JSON-safe dictionary.

    Args:
        descriptor: A ``SolverDescriptor`` instance.

    Returns:
        Dictionary representation suitable for API responses.
    """
    return {
        "name": descriptor.name,
        "category": descriptor.category,
        "description": descriptor.description,
        "keywords": sorted(descriptor.keywords),
        "tags": sorted(descriptor.tags),
        "supports_cipher_id": descriptor.supports_cipher_id,
        "supports_encoding_chain": descriptor.supports_encoding_chain,
        "priority": descriptor.priority,
    }


@router.get("/search")
async def search_tools(
    query: str = Query(..., description="Whitespace-separated search terms"),
    category: str | None = Query(
        default=None,
        description="Optional category filter: cryptography, math, games, informatics",
    ),
) -> dict[str, Any]:
    """Search registered solver tools by keyword query.

    Tokenises *query* and returns descriptors whose ``keywords`` sets overlap
    with the query tokens, sorted by relevance then priority.

    Args:
        query: Whitespace-separated search terms (required).
        category: Optional category to restrict results.

    Returns:
        JSON object with ``results`` list and ``total`` count.

    Raises:
        HTTPException: 400 if *category* is not a recognised value.
        HTTPException: 422 if *query* is empty.
    """
    if not query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    validated_category: SolverCategory | None = None
    if category is not None:
        if category not in _VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category {category!r}. "
                f"Must be one of: {sorted(_VALID_CATEGORIES)}",
            )
        validated_category = cast("SolverCategory", category)

    registry = get_global_solver_registry()
    descriptors = registry.search(query, category=validated_category)

    return {
        "results": [_descriptor_to_dict(d) for d in descriptors],
        "total": len(descriptors),
    }


@router.get("")
async def list_tools(
    category: str | None = Query(
        default=None,
        description="Optional category filter: cryptography, math, games, informatics",
    ),
) -> dict[str, Any]:
    """List all registered solver tools, with optional category filter.

    Args:
        category: Optional category to restrict results.

    Returns:
        JSON object with ``results`` list and ``total`` count.

    Raises:
        HTTPException: 400 if *category* is not a recognised value.
    """
    validated_category: SolverCategory | None = None
    if category is not None:
        if category not in _VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category {category!r}. "
                f"Must be one of: {sorted(_VALID_CATEGORIES)}",
            )
        validated_category = cast("SolverCategory", category)

    registry = get_global_solver_registry()
    all_descriptors = registry.list_all()

    if validated_category is not None:
        all_descriptors = [d for d in all_descriptors if d.category == validated_category]

    return {
        "results": [_descriptor_to_dict(d) for d in all_descriptors],
        "total": len(all_descriptors),
    }


class AnalyzeRequest(BaseModel):
    """Request body for ``POST /api/v1/tools/analyze``.

    Attributes:
        text: The text to analyse through the Riemann-Babel Filter pipeline.
        max_candidates: Maximum number of prime-aligned Babel candidates to
            consider; must be in ``[1, 256]``; default is 16.
    """

    text: str
    max_candidates: int = 16


@router.post("/analyze")
async def analyze_text(request: AnalyzeRequest) -> dict[str, Any]:
    """Analyse text through the Riemann-Babel Filter and Recipe Engine.

    Runs ``find_prime_aligned_candidates`` to locate prime-aligned Babel
    page candidates, then applies ``RecipeEngine.plan`` to each candidate's
    ``DataSignature`` to recommend appropriate solver tools.

    Args:
        request: Body containing ``text`` and optional ``max_candidates``.

    Returns:
        JSON object with:
        - ``candidates``: list of scored page candidates with recommended tools
        - ``total_candidates``: count of candidates found

    Raises:
        HTTPException: 422 if ``text`` is empty or ``max_candidates`` is out
            of range.
        HTTPException: 500 if the pipeline raises an unexpected error.
    """
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    if not (1 <= request.max_candidates <= 256):
        raise HTTPException(
            status_code=422,
            detail="max_candidates must be in [1, 256]",
        )

    try:
        candidates = find_prime_aligned_candidates(
            request.text,
            max_candidates=request.max_candidates,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    engine = build_default_recipe_engine()

    result_items: list[dict[str, Any]] = []
    for page in candidates:
        recommended = engine.plan(page.signature)
        result_items.append(
            {
                "index": page.index,
                "address": page.address,
                "prime_score": {
                    "combined": page.prime_score.combined,
                    "entropy_score": page.prime_score.entropy_score,
                    "prime_gap_score": page.prime_score.prime_gap_score,
                    "primorial_rank": page.prime_score.primorial_rank,
                    "composite_periodicity_score": page.prime_score.composite_periodicity_score,
                },
                "signature": {
                    "length": page.signature.length,
                    "entropy": page.signature.entropy,
                    "has_whitespace": page.signature.has_whitespace,
                    "char_classes": sorted(page.signature.char_classes),
                    "prime_index_score": page.signature.prime_index_score,
                    "likely_cipher": page.signature.likely_cipher,
                    "encoding_layers": list(page.signature.encoding_layers),
                },
                "recommended_tools": [_descriptor_to_dict(d) for d in recommended],
            }
        )

    return {
        "candidates": result_items,
        "total_candidates": len(result_items),
    }
