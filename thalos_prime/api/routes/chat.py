"""
Chat Routes - Conversational interface

Provides chat endpoint with session management and conversation history.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Optional
import time
import uuid

from thalos_prime.models.api_models import (
    ChatRequest,
    ChatResponse,
    PageResult,
    AddressInfo,
    CoherenceInfo,
    ProvenanceInfo,
    ConfidenceLevel
)
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.lob_decoder import decode_page

router = APIRouter()

# In-memory session storage (replace with Redis in production)
SESSIONS: dict[str, dict[str, Any]] = {}


def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create new one"""
    if session_id and session_id in SESSIONS:
        # Update last activity
        SESSIONS[session_id]['last_activity'] = time.time()
        return session_id
    
    # Create new session
    new_session_id = str(uuid.uuid4())
    SESSIONS[new_session_id] = {
        'created_at': time.time(),
        'last_activity': time.time(),
        'history': []
    }
    return new_session_id


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint for conversational interface.
    
    This endpoint handles user messages, searches for relevant content,
    and returns a conversational response with results.
    
    Args:
        request: Chat request with message and optional session_id
    
    Returns:
        ChatResponse with reply, session_id, and results
    """
    start_time = time.time()
    
    # Get or create session
    session_id = get_or_create_session(request.session_id)
    
    # Store user message in history
    SESSIONS[session_id]['history'].append({
        'role': 'user',
        'content': request.message,
        'timestamp': time.time()
    })
    
    try:
        # Search for relevant pages
        results = []
        
        if request.mode in ["local", "hybrid"]:
            # Enumerate addresses from query
            addresses = enumerate_addresses(request.message, max_results=request.max_results)
            
            # Generate and score pages
            for addr_info in addresses:
                address = addr_info['address']
                page_text = address_to_page(address)
                
                # Decode and score
                decoded = decode_page(
                    address=address,
                    text=page_text,
                    query=request.message,
                    source='local'
                )
                
                # Convert to PageResult
                page_result = PageResult(
                    address=AddressInfo(
                        hex_address=address,
                        wall=None,
                        shelf=None,
                        volume=None,
                        page=None,
                        url=None
                    ),
                    text=decoded.raw_text,
                    snippet=decoded.raw_text[:200] + "...",
                    normalized_text=None,
                    coherence=CoherenceInfo(
                        overall_score=decoded.coherence.overall_score,
                        language_score=decoded.coherence.language_score,
                        structure_score=decoded.coherence.structure_score,
                        ngram_score=decoded.coherence.ngram_score,
                        exact_match_score=decoded.coherence.exact_match_score,
                        confidence_level=ConfidenceLevel(decoded.coherence.confidence_level),
                        metrics=decoded.coherence.metrics
                    ),
                    provenance=ProvenanceInfo(
                        address=decoded.address,
                        source=decoded.source,
                        query=request.message,
                        timestamp=decoded.timestamp,
                        normalized=False,
                        llm_provider=None
                    )
                )
                
                results.append(page_result)
        
        # Sort by coherence score
        results.sort(key=lambda x: x.coherence.overall_score, reverse=True)
        
        # Format reply message
        if results:
            best_score = results[0].coherence.overall_score
            reply = f"Found {len(results)} results for '{request.message}'. "
            reply += f"Best coherence score: {best_score:.1f}/100 ({results[0].coherence.confidence_level}). "
            snippet = results[0].snippet
            if snippet:
                reply += f"Top result preview: {snippet[:100]}..."
            else:
                reply += "Top result has no snippet."
        else:
            reply = f"No results found for '{request.message}'. Try a different query."
        
        # Store bot response in history
        SESSIONS[session_id]['history'].append({
            'role': 'bot',
            'content': reply,
            'timestamp': time.time()
        })
        
        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000
        
        return ChatResponse(
            reply=reply,
            session_id=session_id,
            results=results,
            metadata={
                'query_time_ms': query_time_ms,
                'mode': request.mode,
                'results_count': len(results)
            }
        )
        
    except Exception as e:
        # Store error in history
        error_message = f"Error processing query: {str(e)}"
        SESSIONS[session_id]['history'].append({
            'role': 'bot',
            'content': error_message,
            'timestamp': time.time()
        })
        
        raise HTTPException(status_code=500, detail=error_message)


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 20) -> dict[str, Any]:
    """
    Get chat history for a session.
    
    Args:
        session_id: Session ID
        limit: Maximum number of messages to return
    
    Returns:
        Chat history
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    history = SESSIONS[session_id]['history'][-limit:]
    
    return {
        'session_id': session_id,
        'history': history,
        'total_messages': len(SESSIONS[session_id]['history'])
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    """
    Delete a chat session.
    
    Args:
        session_id: Session ID to delete
    
    Returns:
        Success message
    """
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        return {'message': 'Session deleted successfully'}
    
    raise HTTPException(status_code=404, detail="Session not found")
