"""Chat Routes - Conversational interface."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from fastapi import Query as QueryParam

from thalos_prime.errors import CoherenceThresholdError
from thalos_prime.models.api_models import ChatRequest, ChatResponse
from thalos_runtime.core.deps import get_engine
from thalos_runtime.core.executor import ExecutionError
from thalos_runtime.core.registry import RegistryError
from thalos_runtime.plugins.chat_task import get_sessions

__all__ = ["router"]

router = APIRouter()


@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    """Dispatch chat message handling through RuntimeEngine.

    Enforces the ``min_score`` coherence threshold from the request body
    (default 80.0).  When the threshold cannot be met within the time/attempt
    budget, a 422 response is returned with the deterministic state snapshot
    and checkpoint payload — no below-threshold results are silently returned.
    """
    try:
        result = get_engine().execute("chat.v1.handle_message", request.model_dump())
        return ChatResponse.model_validate(result)
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        if isinstance(exc.cause, CoherenceThresholdError):
            raise HTTPException(
                status_code=422,
                detail=exc.cause.to_dict(),
            ) from exc
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc


@router.post("/high_coherence")
async def chat_high_coherence(
    request: ChatRequest,
    min_score: Annotated[float, QueryParam(ge=0.0, le=100.0)] = 80.0,
) -> ChatResponse:
    """Dispatch high-coherence chat through RuntimeEngine.

    The ``min_score`` query param overrides the request body value.
    Raises 422 with state snapshot when the threshold cannot be met.
    """
    payload = request.model_dump()
    payload["min_score"] = min_score
    try:
        result = get_engine().execute("chat.v1.handle_message_high_coherence", payload)
        return ChatResponse.model_validate(result)
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        if isinstance(exc.cause, CoherenceThresholdError):
            raise HTTPException(
                status_code=422,
                detail=exc.cause.to_dict(),
            ) from exc
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
    sessions = get_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    history = sessions[session_id]["history"][-limit:]

    return {
        "session_id": session_id,
        "history": history,
        "total_messages": len(sessions[session_id]["history"]),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    """Delete a chat session.

    Args:
        session_id: Session ID to delete

    Returns:
        Success message

    """
    sessions = get_sessions()
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted successfully"}

    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/benchmark/tasks")
async def benchmark_tasks() -> dict[str, Any]:
    """List available latent pattern recovery benchmark tasks."""
    from thalos_prime.benchmarks.latent_pattern_recovery import list_tasks

    tasks = list_tasks()
    return {
        "benchmark": "latent_pattern_recovery_v1",
        "tasks": tasks,
        "count": len(tasks),
    }


@router.post("/benchmark/run")
async def run_benchmark(
    task_id: str,
    seed: Annotated[int, QueryParam(ge=0)] = 2026,
    perturbation: Annotated[int, QueryParam(ge=0)] = 0,
) -> dict[str, Any]:
    """Run a deterministic benchmark task via chat API surface.

    This endpoint allows the chatbot UI to execute the operational compiler
    benchmark and return a concrete inspectable artifact.
    """
    from thalos_prime.benchmarks.latent_pattern_recovery import run_latent_pattern_recovery

    try:
        artifact = run_latent_pattern_recovery(
            task_id=task_id,
            seed=seed,
            perturbation=perturbation,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    selected = artifact["selected_answer"]
    return {
        "benchmark": artifact["benchmark"],
        "task_id": artifact["input"]["task_id"],
        "seed": artifact["seed"],
        "perturbation": artifact["perturbation"],
        "selected_candidate": selected["candidate_id"],
        "selected_query": selected["query"],
        "selected_address": selected["search_top_result"]["address"],
        "constraints_pass": selected["constraints_pass"],
        "stabilized": artifact["stabilization_result"]["stabilized"],
        "artifact": artifact,
    }


@router.post("/benchmark/compare")
async def compare_benchmark(
    seed: Annotated[int, QueryParam(ge=0)] = 2026,
    perturbation: Annotated[int, QueryParam(ge=0)] = 0,
) -> dict[str, Any]:
    """Run comparative benchmark report (operational vs baselines)."""
    from thalos_prime.benchmarks.latent_pattern_recovery import run_comparative_benchmark

    report = run_comparative_benchmark(seed=seed, perturbation=perturbation)
    summary = report["summary"]
    return {
        "benchmark": report["benchmark"],
        "seed": report["seed"],
        "perturbation": report["perturbation"],
        "task_count": report["task_count"],
        "summary": summary,
        "report": report,
    }
