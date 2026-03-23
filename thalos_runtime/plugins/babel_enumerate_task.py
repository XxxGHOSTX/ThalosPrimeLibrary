"""Babel enumerate task plugin."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.models.api_models import EnumerateRequest, EnumerateResponse
from thalos_runtime.plugins.common import ExecutionContext

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)
_TASK_NAME = "babel.v1.enumerate"


class BabelEnumerateTask:
    """Task handler for babel.v1.enumerate."""

    def __init__(self, name: str = _TASK_NAME) -> None:
        self.name = name
        self._request: EnumerateRequest | None = None
        self._context: ExecutionContext | None = None
        self._start = 0.0

    def initialize(self, payload: dict[str, Any]) -> None:
        self._request = EnumerateRequest.model_validate(payload)
        self._context = ExecutionContext.from_payload(self.name, payload)
        self._start = time.perf_counter()

    def validate(self) -> None:
        if self._request is None:
            msg = "BabelEnumerateTask request not initialized"
            raise RuntimeError(msg)

    def operate(self) -> EnumerateResponse:
        assert self._request is not None
        results = enumerate_addresses(
            self._request.query,
            max_results=self._request.max_results,
            depth=self._request.depth,
        )
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        avg_score = sum(float(r["score"]) for r in results) / len(results) if results else 0.0
        return EnumerateResponse(
            query=self._request.query,
            addresses=results,
            total_found=len(results),
            metadata={
                "enumeration_time_ms": elapsed_ms,
                "depth": self._request.depth,
                "avg_score": avg_score,
            },
        )

    def reconcile(self, response: EnumerateResponse) -> EnumerateResponse:
        return response

    def checkpoint(self) -> dict[str, Any]:
        return {"task": self.name}

    def terminate(self) -> None:
        self._request = None
        self._context = None
        self._start = 0.0

    def run(self, payload: dict[str, Any]) -> EnumerateResponse:
        self.initialize(payload)
        self.validate()
        response = self.operate()
        reconciled = self.reconcile(response)
        self.checkpoint()
        self.terminate()
        return reconciled


class BabelEnumerateTaskPlugin:
    """Registers babel.v1.enumerate task."""

    @property
    def name(self) -> str:
        return _TASK_NAME

    def register(self, engine: RuntimeEngine) -> None:
        engine.register_module(_TASK_NAME, BabelEnumerateTask())
        logger.info("BabelEnumerateTaskPlugin: registered %s", _TASK_NAME)

