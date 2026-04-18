"""Search task plugin."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from thalos_prime.core.engine import EngineConfig, ThalosEngine
from thalos_prime.models.api_models import (
    AddressInfo,
    CoherenceInfo,
    ConfidenceLevel,
    PageResult,
    ProvenanceInfo,
    SearchRequest,
    SearchResponse,
)
from thalos_runtime.plugins.common import HIGH_CONFIDENCE_FLOOR, ExecutionContext

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
        artifact = ThalosEngine().run(
            self._request.query,
            EngineConfig(
                seed=self._context.seed,
                max_candidates=self._request.max_results,
                mode=self._request.mode.value,
                intent_override="search",
            ),
        )
        results = [
            self._candidate_to_page_result(candidate.model_dump(), query=self._request.query)
            for candidate in artifact.candidates
            if float(candidate.coherence_score) >= self._request.min_score
        ]

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
                "addresses_enumerated": len(artifact.research.get("notes", [])),
                "task": self.name,
                "seed": self._context.seed,
                "payload_hash": self._context.payload_hash,
                "stabilization": artifact.stabilization,
                "purity_metrics": artifact.purity_metrics,
            },
        )

    def _candidate_to_page_result(self, candidate: dict[str, Any], *, query: str) -> PageResult:
        """Convert canonical engine candidates to API ``PageResult`` records."""
        score = float(candidate["coherence_score"])
        confidence = ConfidenceLevel.HIGH if score >= HIGH_CONFIDENCE_FLOOR else ConfidenceLevel.MEDIUM
        return PageResult(
            address=AddressInfo(
                hex_address=str(candidate["address"]),
                wall=None,
                shelf=None,
                volume=None,
                page=None,
                url=f"https://libraryofbabel.info/book.cgi?hex={candidate['address']}",
            ),
            text=str(candidate["text"]),
            snippet=str(candidate["text"])[:200],
            normalized_text=None,
            coherence=CoherenceInfo(
                overall_score=score,
                language_score=score,
                structure_score=score,
                ngram_score=score,
                exact_match_score=score,
                confidence_level=confidence,
                metrics={
                    "constraint_score": float(candidate["constraint_score"]),
                    "purity_score": float(candidate["purity_score"]),
                    "combined_score": float(candidate["score"]),
                },
            ),
            provenance=ProvenanceInfo(
                address=str(candidate["address"]),
                source=str(candidate["source"]),
                query=query,
                timestamp=time.time(),
                normalized=False,
                llm_provider=None,
            ),
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
