"""Search task plugin."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_decoder import decode_page
from thalos_prime.models.api_models import PageResult, SearchRequest, SearchResponse
from thalos_runtime.plugins.common import ExecutionContext, build_coherence_info, build_page_result

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)

_TASK_NAME = "search.v1.query"


class SearchTask:
    """Task handler for search.v1.query."""

    def __init__(self, name: str = _TASK_NAME) -> None:
        self.name = name
        self._context: ExecutionContext | None = None
        self._request: SearchRequest | None = None
        self._start = 0.0

    def initialize(self, payload: dict[str, Any]) -> None:
        self._context = ExecutionContext.from_payload(self.name, payload)
        self._request = SearchRequest.model_validate(payload)
        self._start = time.perf_counter()

    def validate(self) -> None:
        if self._request is None:
            msg = "SearchTask request not initialized"
            raise RuntimeError(msg)

    def operate(self) -> SearchResponse:
        assert self._request is not None
        assert self._context is not None
        results: list[PageResult] = []
        addresses_enumerated = 0
        if self._request.mode.value in {"local", "hybrid"}:
            addresses = enumerate_addresses(
                self._request.query,
                max_results=self._request.max_results * 2,
                depth=2,
            )
            addresses_enumerated = len(addresses)
            for addr_info in addresses:
                address = str(addr_info["address"])
                page_text = address_to_page(address)
                decoded = decode_page(address=address, text=page_text, query=self._request.query, source="local")
                coherence_info = build_coherence_info(decoded)
                if coherence_info.overall_score >= self._request.min_score:
                    results.append(
                        build_page_result(
                            address=address,
                            raw_text=decoded.raw_text,
                            query=self._request.query,
                            source=decoded.source,
                            timestamp=decoded.timestamp,
                            coherence=coherence_info,
                        )
                    )

        results.sort(key=lambda item: item.coherence.overall_score, reverse=True)
        results = results[: self._request.max_results]
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        return SearchResponse(
            query=self._request.query,
            results=results,
            total_found=len(results),
            mode=self._request.mode,
            cached=False,
            metadata={
                "query_time_ms": elapsed_ms,
                "cache_hit": False,
                "addresses_enumerated": addresses_enumerated,
                "task": self.name,
                "seed": self._context.seed,
                "payload_hash": self._context.payload_hash,
            },
        )

    def reconcile(self, response: SearchResponse) -> SearchResponse:
        return response

    def checkpoint(self) -> dict[str, Any]:
        return {
            "task": self.name,
            "query": None if self._request is None else self._request.query,
        }

    def terminate(self) -> None:
        self._context = None
        self._request = None
        self._start = 0.0

    def run(self, payload: dict[str, Any]) -> SearchResponse:
        self.initialize(payload)
        self.validate()
        response = self.operate()
        reconciled = self.reconcile(response)
        self.checkpoint()
        self.terminate()
        return reconciled


class SearchTaskPlugin:
    """Registers search.v1.query task."""

    @property
    def name(self) -> str:
        return _TASK_NAME

    def register(self, engine: RuntimeEngine) -> None:
        engine.register_module(_TASK_NAME, SearchTask())
        logger.info("SearchTaskPlugin: registered %s", _TASK_NAME)

