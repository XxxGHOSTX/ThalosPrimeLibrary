"""Library API routes — text reconstruction and artifact retrieval endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["library"])

# Module-level store singleton (lazy-initialized on first request)
_lib_store: Any = None


def _get_lib_store() -> Any:
    """Return the shared LocalLibraryStore, initializing it on first call."""
    global _lib_store
    if _lib_store is None:
        from thalos_prime.library.store import LocalLibraryStore
        _lib_store = LocalLibraryStore()
    return _lib_store


@router.post("/reconstruct")
async def reconstruct_text(body: dict[str, str]) -> dict[str, Any]:
    """Reconstruct garbled text into valid Library artifacts.

    Expects a JSON body with a ``"text"`` key. Runs the deterministic
    reconstruction pipeline and stores the resulting artifacts.

    Args:
        body: Request body containing ``{"text": "<input text>"}``.

    """
    text = body.get("text", "")
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body must contain a non-empty 'text' field",
        )
    try:
        from thalos_prime.library.reconstruct import reconstruct
        store = _get_lib_store()
        artifacts = reconstruct(text, store=store)
        return {
            "artifacts": [a.to_dict() for a in artifacts],
            "count": len(artifacts),
        }
    except Exception as exc:
        logger.exception("reconstruct_text failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str) -> dict[str, Any]:
    """Return a stored library artifact by its content-addressed ID.

    Args:
        artifact_id: SHA-256 hex content address of the artifact.

    """
    try:
        store = _get_lib_store()
        artifact = store.get(artifact_id)
        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found",
            )
        result: dict[str, Any] = artifact.to_dict()
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_artifact failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
