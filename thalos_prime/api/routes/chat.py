"""Chat Routes - Conversational interface."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from fastapi import Query as QueryParam

from thalos_prime.models.api_models import ChatRequest, ChatResponse
from thalos_runtime.core.deps import get_engine
from thalos_runtime.core.executor import ExecutionError
from thalos_runtime.core.registry import RegistryError
from thalos_runtime.plugins.chat_task import SESSIONS

router = APIRouter()

@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    """Dispatch chat message handling through RuntimeEngine."""
    try:
        result = get_engine().execute("chat.v1.handle_message", request.model_dump())
        return ChatResponse.model_validate(result)
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc


@router.post("/high_coherence")
async def chat_high_coherence(
    request: ChatRequest,
    min_score: Annotated[float, QueryParam(ge=0.0, le=100.0)] = 51.0,
) -> ChatResponse:
    """Dispatch high-coherence chat through RuntimeEngine."""
    payload = request.model_dump()
    payload["min_score"] = min_score
    try:
        result = get_engine().execute("chat.v1.handle_message_high_coherence", payload)
        return ChatResponse.model_validate(result)
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        raise HTTPException(status_code=500, detail=f"High-coherence chat failed: {exc}") from exc


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 20) -> dict[str, Any]:
    """Get chat history for a session.

    Args:
        session_id: Session ID
        limit: Maximum number of messages to return

    Returns:
        Chat history

    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    history = SESSIONS[session_id]["history"][-limit:]

    return {
        "session_id": session_id,
        "history": history,
        "total_messages": len(SESSIONS[session_id]["history"]),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    """Delete a chat session.

    Args:
        session_id: Session ID to delete

    Returns:
        Success message

    """
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        return {"message": "Session deleted successfully"}

    raise HTTPException(status_code=404, detail="Session not found")
__all__ = ["SESSIONS", "router"]
