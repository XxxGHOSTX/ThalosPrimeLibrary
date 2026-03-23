"""Babel generate task plugin."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from thalos_prime.lob_babel_generator import BabelGenerator, address_to_page, text_to_address
from thalos_prime.models.api_models import AddressInfo, GenerateRequest, GenerateResponse
from thalos_runtime.plugins.common import ExecutionContext

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)
_TASK_NAME = "babel.v1.generate"


class BabelGenerateTask:
    """Task handler for babel.v1.generate."""

    def __init__(self, name: str = _TASK_NAME) -> None:
        self.name = name
        self._request: GenerateRequest | None = None
        self._context: ExecutionContext | None = None
        self._start = 0.0
        self._generator = BabelGenerator()

    def initialize(self, payload: dict[str, Any]) -> None:
        self._request = GenerateRequest.model_validate(payload)
        self._context = ExecutionContext.from_payload(self.name, payload)
        self._start = time.perf_counter()

    def validate(self) -> None:
        if self._request is None:
            msg = "BabelGenerateTask request not initialized"
            raise RuntimeError(msg)
        if not self._request.address and not self._request.query:
            msg = "Either address or query must be provided"
            raise ValueError(msg)

    def operate(self) -> GenerateResponse:
        assert self._request is not None
        address = self._request.address if self._request.address else text_to_address(self._request.query or "")
        page_text = address_to_page(address)
        valid = True
        if self._request.validate_page:
            is_valid, _error = self._generator.validate_page(page_text)
            valid = is_valid
        generation_time_ms = (time.perf_counter() - self._start) * 1000
        return GenerateResponse(
            address=AddressInfo(
                hex_address=address,
                wall=None,
                shelf=None,
                volume=None,
                page=None,
                url=None,
            ),
            text=page_text,
            valid=valid,
            generation_time_ms=generation_time_ms,
        )

    def reconcile(self, response: GenerateResponse) -> GenerateResponse:
        return response

    def checkpoint(self) -> dict[str, Any]:
        return {"task": self.name}

    def terminate(self) -> None:
        self._request = None
        self._context = None
        self._start = 0.0

    def run(self, payload: dict[str, Any]) -> GenerateResponse:
        self.initialize(payload)
        self.validate()
        response = self.operate()
        reconciled = self.reconcile(response)
        self.checkpoint()
        self.terminate()
        return reconciled


class BabelGenerateTaskPlugin:
    """Registers babel.v1.generate task."""

    @property
    def name(self) -> str:
        return _TASK_NAME

    def register(self, engine: RuntimeEngine) -> None:
        engine.register_module(_TASK_NAME, BabelGenerateTask())
        logger.info("BabelGenerateTaskPlugin: registered %s", _TASK_NAME)

