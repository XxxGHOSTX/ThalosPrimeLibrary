"""Babel decode task plugin."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from thalos_prime.lob_decoder import BabelDecoder, decode_page
from thalos_prime.models.api_models import (
    AddressInfo,
    CoherenceInfo,
    ConfidenceLevel,
    DecodeRequest,
    DecodeResponse,
    NormalizationMode,
    ProvenanceInfo,
)
from thalos_runtime.plugins.common import ExecutionContext

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)
_TASK_NAME = "babel.v1.decode"


class BabelDecodeTask:
    """Task handler for babel.v1.decode."""

    def __init__(self, name: str = _TASK_NAME) -> None:
        self.name = name
        self._request: DecodeRequest | None = None
        self._context: ExecutionContext | None = None
        self._decoder = BabelDecoder()

    def initialize(self, payload: dict[str, Any]) -> None:
        self._request = DecodeRequest.model_validate(payload)
        self._context = ExecutionContext.from_payload(self.name, payload)

    def validate(self) -> None:
        if self._request is None:
            msg = "BabelDecodeTask request not initialized"
            raise RuntimeError(msg)
        if self._request.normalization == NormalizationMode.LLM and (
            not self._decoder.llm_enabled or self._decoder.llm_provider is None
        ):
            msg = (
                "LLM normalization requested but no LLM provider is configured. "
                "Use 'heuristic' mode or configure an LLM provider."
            )
            raise NotImplementedError(msg)

    def operate(self) -> DecodeResponse:
        assert self._request is not None
        normalize = self._request.normalization != NormalizationMode.NONE
        decoded = decode_page(
            address=self._request.address,
            text=self._request.text,
            query=self._request.query,
            source="user_provided",
        )
        normalized_text = None
        if normalize and self._request.normalization == NormalizationMode.LLM:
            normalized = self._decoder.decode_page(
                address=decoded.address,
                text=decoded.raw_text,
                query=self._request.query,
                source=decoded.source,
                normalize=True,
            )
            normalized_text = normalized.normalized_text
        elif normalize and self._request.normalization == NormalizationMode.HEURISTIC:
            normalized_text = decoded.raw_text.strip()
        return DecodeResponse(
            address=AddressInfo(
                hex_address=self._request.address,
                wall=None,
                shelf=None,
                volume=None,
                page=None,
                url=None,
            ),
            raw_text=decoded.raw_text,
            normalized_text=normalized_text,
            coherence=CoherenceInfo(
                overall_score=decoded.coherence.overall_score,
                language_score=decoded.coherence.language_score,
                structure_score=decoded.coherence.structure_score,
                ngram_score=decoded.coherence.ngram_score,
                exact_match_score=decoded.coherence.exact_match_score,
                confidence_level=ConfidenceLevel(decoded.coherence.confidence_level),
                metrics=decoded.coherence.metrics,
            ),
            provenance=ProvenanceInfo(
                address=decoded.address,
                source=decoded.source,
                query=self._request.query,
                timestamp=decoded.timestamp,
                normalized=normalize,
                llm_provider=None,
            ),
        )

    def reconcile(self, response: DecodeResponse) -> DecodeResponse:
        return response

    def checkpoint(self) -> dict[str, Any]:
        return {"task": self.name}

    def terminate(self) -> None:
        self._request = None
        self._context = None

    def run(self, payload: dict[str, Any]) -> DecodeResponse:
        self.initialize(payload)
        self.validate()
        response = self.operate()
        reconciled = self.reconcile(response)
        self.checkpoint()
        self.terminate()
        return reconciled


class BabelDecodeTaskPlugin:
    """Registers babel.v1.decode task."""

    @property
    def name(self) -> str:
        return _TASK_NAME

    def register(self, engine: RuntimeEngine) -> None:
        engine.register_module(_TASK_NAME, BabelDecodeTask())
        logger.info("BabelDecodeTaskPlugin: registered %s", _TASK_NAME)
