"""Thalos Runtime API server.

FastAPI application exposing a ``POST /execute`` endpoint that
dispatches task execution through the RuntimeEngine.

Control Plane: FastAPI lifespan initializes the engine and loads
    all plugins on startup; terminates the engine on shutdown.
Data Plane: ``engine.execute()`` handles all computational work.

Start with::

    uvicorn thalos_runtime.api.server:app --host 0.0.0.0 --port 8080

Endpoints:
    POST /execute   - execute a named task with a JSON payload
    GET  /health    - liveness probe returning engine status
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from thalos_runtime.core.engine import RuntimeEngine
from thalos_runtime.core.executor import ExecutionError
from thalos_runtime.core.registry import RegistryError
from thalos_runtime.plugins.loader import PluginLoader

logger = logging.getLogger(__name__)

_engine: RuntimeEngine | None = None


def _get_engine() -> RuntimeEngine:
    """Return the initialized RuntimeEngine singleton.

    Returns:
        Initialized RuntimeEngine instance.

    Raises:
        RuntimeError: If the engine has not been initialized yet.

    """
    if _engine is None:
        raise RuntimeError(
            "RuntimeEngine is not initialized; lifespan startup failed."
        )
    return _engine


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Application lifespan: initialize engine on startup, terminate on shutdown.

    Args:
        app: FastAPI application instance (unused, required by signature).

    """
    global _engine  # noqa: PLW0603
    logger.info("Thalos Runtime API: startup")
    engine = RuntimeEngine()
    loader = PluginLoader()
    loader.discover_and_register(engine)
    engine.initialize()
    _engine = engine
    logger.info(
        "Thalos Runtime API: engine ready, tasks=%s",
        engine.task_names(),
    )
    yield
    logger.info("Thalos Runtime API: shutdown")
    engine.terminate()
    _engine = None


app = FastAPI(
    title="Thalos Runtime API",
    version="1.0",
    description="Execute registered tasks through the Thalos Runtime Engine.",
    lifespan=_lifespan,
)


class ExecuteRequest(BaseModel):
    """Request body for the POST /execute endpoint.

    Attributes:
        task: Name of the task to execute.
        payload: Arbitrary JSON payload passed to the task handler.

    """

    task: str
    payload: dict[str, Any] = {}


class ExecuteResponse(BaseModel):
    """Response body for the POST /execute endpoint.

    Attributes:
        task: Name of the task that was executed.
        result: Value returned by the task handler.

    """

    task: str
    result: Any


class HealthResponse(BaseModel):
    """Response body for the GET /health endpoint.

    Attributes:
        status: Operational status string.
        tasks: List of registered task names.

    """

    status: str
    tasks: list[str]


@app.post("/execute", response_model=ExecuteResponse)
def execute(request: ExecuteRequest) -> ExecuteResponse:
    """Execute a registered task via the runtime engine.

    Args:
        request: Task name and payload from the request body.

    Returns:
        ExecuteResponse containing the task name and result.

    Raises:
        HTTPException: 404 if the task is not registered.
        HTTPException: 500 if the handler raises an exception.

    """
    engine = _get_engine()
    try:
        result = engine.execute(request.task, request.payload)
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ExecuteResponse(task=request.task, result=result)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe returning engine operational status.

    Returns:
        HealthResponse with status and registered task names.

    """
    engine = _get_engine()
    return HealthResponse(status="ok", tasks=engine.task_names())


__all__ = ["ExecuteRequest", "ExecuteResponse", "HealthResponse", "app"]
