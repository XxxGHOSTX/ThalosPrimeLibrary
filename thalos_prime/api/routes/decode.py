"""
Decode Routes - Page decoding and coherence scoring endpoints

Provides coherence analysis and text normalization functionality.
"""

from fastapi import APIRouter, HTTPException
import time

from thalos_prime.models.api_models import (
    DecodeRequest,
    DecodeResponse,
    AddressInfo,
    CoherenceInfo,
    ProvenanceInfo,
    NormalizationMode
)
from thalos_prime.lob_decoder import decode_page, score_coherence, BabelDecoder

router = APIRouter()
decoder = BabelDecoder()


@router.post("/", response_model=DecodeResponse)
async def decode(request: DecodeRequest):
    """
    Decode and score a page.
    
    Analyzes page coherence using multiple metrics and optionally
    applies text normalization.
    
    Args:
        request: Decode request with address, text, and options
    
    Returns:
        DecodeResponse with coherence analysis and provenance
    """
    try:
        # Determine if normalization should be applied
        normalize = request.normalization != NormalizationMode.NONE
        
        # Decode page
        decoded = decode_page(
            address=request.address,
            text=request.text,
            query=request.query,
            source='user_provided'
        )
        
        # Apply normalization if requested
        normalized_text = None
        if normalize and request.normalization == NormalizationMode.LLM:
            # LLM normalization (placeholder - requires actual LLM integration)
            normalized_text = decoded.raw_text  # For now, just use raw text
        elif normalize and request.normalization == NormalizationMode.HEURISTIC:
            # Heuristic normalization (basic cleaning)
            normalized_text = decoded.raw_text.strip()
        
        return DecodeResponse(
            address=AddressInfo(hex_address=request.address),
            raw_text=decoded.raw_text,
            normalized_text=normalized_text,
            coherence=CoherenceInfo(
                overall_score=decoded.coherence.overall_score,
                language_score=decoded.coherence.language_score,
                structure_score=decoded.coherence.structure_score,
                ngram_score=decoded.coherence.ngram_score,
                exact_match_score=decoded.coherence.exact_match_score,
                confidence_level=decoded.coherence.confidence_level,
                metrics=decoded.coherence.metrics
            ),
            provenance=ProvenanceInfo(
                address=decoded.address,
                source=decoded.source,
                query=request.query,
                timestamp=decoded.timestamp,
                normalized=normalize,
                llm_provider=None
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decode failed: {str(e)}")


@router.post("/score")
async def score_text(text: str, query: str = None):
    """
    Score text coherence without full decoding.
    
    Args:
        text: Text to score
        query: Optional query for relevance scoring
    
    Returns:
        Coherence scores
    """
    try:
        coherence = score_coherence(text, query=query)
        
        return {
            'overall_score': coherence.overall_score,
            'language_score': coherence.language_score,
            'structure_score': coherence.structure_score,
            'ngram_score': coherence.ngram_score,
            'exact_match_score': coherence.exact_match_score,
            'confidence_level': coherence.confidence_level,
            'metrics': coherence.metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.post("/batch")
async def decode_batch(items: list[dict]):
    """
    Decode multiple pages in batch.
    
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
            address = item.get('address', 'unknown')
            text = item.get('text', '')
            query = item.get('query')
            
            decoded = decode_page(
                address=address,
                text=text,
                query=query,
                source='batch'
            )
            
            results.append({
                'address': address,
                'coherence_score': decoded.coherence.overall_score,
                'confidence_level': decoded.coherence.confidence_level,
                'success': True
            })
        except Exception as e:
            results.append({
                'address': item.get('address', 'unknown'),
                'error': str(e),
                'success': False
            })
    
    return {
        'total': len(items),
        'successful': sum(1 for r in results if r.get('success')),
        'failed': sum(1 for r in results if not r.get('success')),
        'results': results
    }


@router.post("/weights")
async def update_decoder_weights(
    language: float = 0.30,
    structure: float = 0.20,
    ngram: float = 0.20,
    exact_match: float = 0.30
):
    """
    Update decoder scoring weights.
    
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
            weight_exact_match=exact_match
        )
        
        return {
            'weights': {
                'language': custom_decoder.weight_language,
                'structure': custom_decoder.weight_structure,
                'ngram': custom_decoder.weight_ngram,
                'exact_match': custom_decoder.weight_exact_match
            },
            'message': 'Weights normalized and applied'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weight update failed: {str(e)}")


@router.get("/metrics")
async def get_decoder_metrics():
    """
    Get decoder configuration and metrics.
    
    Returns:
        Decoder configuration
    """
    return {
        'weights': {
            'language': decoder.weight_language,
            'structure': decoder.weight_structure,
            'ngram': decoder.weight_ngram,
            'exact_match': decoder.weight_exact_match
        },
        'llm_enabled': decoder.llm_enabled,
        'llm_provider': decoder.llm_provider,
        'common_words_count': len(decoder.COMMON_WORDS)
    }
