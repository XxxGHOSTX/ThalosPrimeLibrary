"""Graph substrate API routes — execute, retrieve, replay, and provenance endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])

# Module-level substrate singletons (lazy-initialized on first request)
_store: Any = None
_provenance_index: Any = None


def _get_store() -> Any:
    """Return the shared LocalGraphStore, initializing it on first call."""
    global _store
    if _store is None:
        from thalos_prime.storage.graph_store import LocalGraphStore
        _store = LocalGraphStore()
    return _store


def _get_provenance_index() -> Any:
    """Return the shared ProvenanceIndex, initializing it on first call."""
    global _provenance_index
    if _provenance_index is None:
        from thalos_prime.provenance.index import ProvenanceIndex
        _provenance_index = ProvenanceIndex()
    return _provenance_index


@router.get("/")
async def list_graphs() -> dict[str, Any]:
    """List all stored graph IDs.

    Returns a sorted list of graph identifiers that have been persisted
    in the local graph store.
    """
    try:
        store = _get_store()
        ids = store.list_ids()
        return {"graphs": ids, "count": len(ids)}
    except Exception as exc:
        logger.exception("list_graphs failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/execute")
async def execute_graph(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute a payload through the graph substrate.

    Builds an ExecutionGraph from the payload, applies rewrite rules,
    plans and executes all nodes, persists the result, and returns
    a summary with the graph ID and outputs.
    """
    try:
        from thalos_runtime.core.deps import get_engine
        engine = get_engine()
        result: dict[str, Any] = engine.execute_request(payload)
        return result
    except Exception as exc:
        logger.exception("execute_graph failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/{graph_id}")
async def get_graph(graph_id: str) -> dict[str, Any]:
    """Return a serialized snapshot of the stored graph.

    Args:
        graph_id: Unique graph identifier to retrieve.

    """
    try:
        store = _get_store()
        graph = store.load(graph_id)
        result: dict[str, Any] = graph.serialize()
        return result
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph '{graph_id}' not found",
        ) from exc
    except Exception as exc:
        logger.exception("get_graph failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/{graph_id}/replay")
async def replay_graph(graph_id: str) -> dict[str, Any]:
    """Replay a stored graph and return updated outputs and a provenance summary.

    Reuses the runtime engine's ``DeterministicExecutor`` (with all registered
    operation handlers) so that replay semantics stay consistent with the
    original execution.  Falls back to a fresh executor only when the runtime
    engine is not yet configured.

    Args:
        graph_id: Unique graph identifier to replay.

    """
    try:
        from thalos_prime.execution_ir.executor import DeterministicExecutor
        from thalos_prime.replay.engine import ReplayEngine
        from thalos_prime.storage.event_log import EventLog

        store = _get_store()
        graph = store.load(graph_id)

        # Prefer the shared executor from the runtime engine so handler
        # configuration matches the original execution.
        # Deferred import avoids a circular dependency at module load time
        # (thalos_prime.api → thalos_runtime.core is only safe after package
        # initialization completes).
        try:
            from thalos_runtime.core.deps import get_engine
            executor = get_engine().get_substrate_executor()
        except RuntimeError:
            executor = DeterministicExecutor()

        event_log = EventLog()
        prov_index = _get_provenance_index()

        engine = ReplayEngine(executor, event_log=event_log, provenance_index=prov_index)
        updated = engine.replay(graph)
        store.save(updated)

        outputs: dict[str, Any] = {
            nid: n.outputs for nid, n in updated.nodes.items()
        }
        return {
            "graph_id": updated.id,
            "graph_hash": updated.graph_hash,
            "outputs": outputs,
        }
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph '{graph_id}' not found",
        ) from exc
    except Exception as exc:
        logger.exception("replay_graph failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/{graph_id}/provenance")
async def get_provenance(graph_id: str) -> dict[str, Any]:
    """Return node-level provenance records for a graph.

    Args:
        graph_id: Unique graph identifier to query.

    """
    try:
        prov_index = _get_provenance_index()
        records = prov_index.get_by_graph(graph_id)
        return {
            "graph_id": graph_id,
            "records": [r.to_dict() for r in records],
        }
    except Exception as exc:
        logger.exception("get_provenance failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
