"""Shared task helpers for RuntimeEngine plugins."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from thalos_prime.models.api_models import ChatRequest, CoherenceInfo, PageResult

HIGH_CONFIDENCE_FLOOR = 80.0


@dataclass(frozen=True)
class ExecutionContext:
    """Deterministic execution context for a task invocation."""

    seed: int
    task: str
    payload_hash: str

    @staticmethod
    def from_payload(task: str, payload: dict[str, Any]) -> ExecutionContext:
        """Build deterministic context from task and payload."""
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return ExecutionContext(seed=int(digest[:16], 16), task=task, payload_hash=digest)


def build_page_result(
    *,
    address: str,
    raw_text: str,
    query: str | None,
    source: str,
    timestamp: float,
    coherence: CoherenceInfo,
) -> PageResult:
    """Create PageResult in canonical API schema."""
    from thalos_prime.models.api_models import AddressInfo, PageResult, ProvenanceInfo

    snippet = raw_text[:200] + "..."
    return PageResult(
        address=AddressInfo(
            hex_address=address,
            wall=None,
            shelf=None,
            volume=None,
            page=None,
            url=None,
        ),
        text=raw_text,
        snippet=snippet,
        normalized_text=None,
        coherence=coherence,
        provenance=ProvenanceInfo(
            address=address,
            source=source,
            query=query,
            timestamp=timestamp,
            normalized=False,
            llm_provider=None,
        ),
    )


def build_coherence_info(decoded: Any) -> CoherenceInfo:
    """Convert decoded coherence object to API model CoherenceInfo."""
    from thalos_prime.models.api_models import CoherenceInfo, ConfidenceLevel

    return CoherenceInfo(
        overall_score=decoded.coherence.overall_score,
        language_score=decoded.coherence.language_score,
        structure_score=decoded.coherence.structure_score,
        ngram_score=decoded.coherence.ngram_score,
        exact_match_score=decoded.coherence.exact_match_score,
        confidence_level=ConfidenceLevel(decoded.coherence.confidence_level),
        metrics=decoded.coherence.metrics,
    )


def normalize_chat_payload(payload: dict[str, Any]) -> ChatRequest:
    """Validate chat payload using ChatRequest schema."""
    from thalos_prime.models.api_models import ChatRequest

    return ChatRequest.model_validate(payload)
