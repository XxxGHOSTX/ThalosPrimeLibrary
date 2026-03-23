"""Decode Routes - Page decoding and coherence scoring endpoints.

Provides coherence analysis and text normalization functionality.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from thalos_prime.lob_decoder import BabelDecoder, decode_page, score_coherence
from thalos_prime.models.api_models import DecodeRequest, DecodeResponse
from thalos_runtime.core.deps import get_engine
from thalos_runtime.core.executor import ExecutionError
from thalos_runtime.core.registry import RegistryError

router = APIRouter()
decoder = BabelDecoder()


@router.post("")
async def decode(request: DecodeRequest) -> DecodeResponse:
    """Decode and score a page.

    Analyzes page coherence using multiple metrics and optionally
    applies text normalization.

    Args:
        request: Decode request with address, text, and options

    Returns:
        DecodeResponse with coherence analysis and provenance

    """
    try:
        result = get_engine().execute("babel.v1.decode", request.model_dump())
        return DecodeResponse.model_validate(result)
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        cause = exc.cause
        if isinstance(cause, NotImplementedError):
            raise HTTPException(status_code=501, detail=str(cause)) from exc
        raise HTTPException(status_code=500, detail=f"Decode failed: {exc}") from exc


@router.post("/score")
async def score_text(text: str, query: str | None = None) -> dict[str, Any]:
    """Score text coherence without full decoding.

    Args:
        text: Text to score
        query: Optional query for relevance scoring

    Returns:
        Coherence scores

    """
    try:
        coherence = score_coherence(text, query=query)

        return {
            "overall_score": coherence.overall_score,
            "language_score": coherence.language_score,
            "structure_score": coherence.structure_score,
            "ngram_score": coherence.ngram_score,
            "exact_match_score": coherence.exact_match_score,
            "confidence_level": coherence.confidence_level,
            "metrics": coherence.metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e!s}")


@router.post("/batch")
async def decode_batch(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Decode multiple pages in batch.

    Args:
        items: List of {address, text, query} dicts

    Returns:
        List of decode results

    """
    if len(items) > 50:
        raise HTTPException(status_code=400, detail="Batch size limited to 50 items")

    results = []

    for item in items:
        try:
            address = item.get("address", "unknown")
            text = item.get("text", "")
            query = item.get("query")

            decoded = decode_page(
                address=address,
                text=text,
                query=query,
                source="batch",
            )

            results.append({
                "address": address,
                "coherence_score": decoded.coherence.overall_score,
                "confidence_level": decoded.coherence.confidence_level,
                "success": True,
            })
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError) as e:
            results.append({
                "address": item.get("address", "unknown"),
                "error": str(e),
                "success": False,
            })

    return {
        "total": len(items),
        "successful": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results,
    }


@router.post("/weights")
async def update_decoder_weights(
    language: float = 0.30,
    structure: float = 0.20,
    ngram: float = 0.20,
    exact_match: float = 0.30,
) -> dict[str, Any]:
    """Update decoder scoring weights.

    Args:
        language: Weight for language detection
        structure: Weight for structure analysis
        ngram: Weight for n-gram coherence
        exact_match: Weight for exact matching

    Returns:
        Updated weights

    """
    try:
        # Create new decoder with custom weights
        custom_decoder = BabelDecoder(
            weight_language=language,
            weight_structure=structure,
            weight_ngram=ngram,
            weight_exact_match=exact_match,
        )

        return {
            "weights": {
                "language": custom_decoder.weight_language,
                "structure": custom_decoder.weight_structure,
                "ngram": custom_decoder.weight_ngram,
                "exact_match": custom_decoder.weight_exact_match,
            },
            "message": "Weights normalized and applied",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weight update failed: {e!s}")


@router.get("/metrics")
async def get_decoder_metrics() -> dict[str, Any]:
    """Get decoder configuration and metrics.

    Returns:
        Decoder configuration

    """
    return {
        "weights": {
            "language": decoder.weight_language,
            "structure": decoder.weight_structure,
            "ngram": decoder.weight_ngram,
            "exact_match": decoder.weight_exact_match,
        },
        "llm_enabled": decoder.llm_enabled,
        "llm_provider": decoder.llm_provider,
        "common_words_count": len(decoder.COMMON_WORDS),
    }
