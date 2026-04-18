"""Chat task plugin."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from thalos_prime.core.engine import EngineConfig, ThalosEngine
from thalos_prime.errors import CoherenceThresholdError
from thalos_prime.models.api_models import (
    AddressInfo,
    ChatRequest,
    ChatResponse,
    CoherenceInfo,
    ConfidenceLevel,
    PageResult,
    ProvenanceInfo,
    SearchMode,
)
from thalos_runtime.plugins.common import (
    ExecutionContext,
    normalize_chat_payload,
)

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)

_TASK_NAME = "chat.v1.handle_message"

@dataclass
class RuntimeSessionStore:
    """Deterministic, observable chat session state store."""

    version: str
    sessions: dict[str, dict[str, Any]]
    base_epoch: float = 1_700_000_000.0

    def initialize(self) -> None:
        """Initialize store state."""
        if not hasattr(self, "sessions"):
            self.sessions = {}

    def _deterministic_timestamp(self, seed: int, offset: int) -> float:
        return self.base_epoch + float(seed % 1_000_000) + (offset / 1000.0)

    def _new_session_id(self, seed: int, payload_hash: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{seed}:{payload_hash}"))

    def get_or_create(self, session_id: str | None, *, seed: int, payload_hash: str) -> str:
        """Get an existing session ID or deterministically create one."""
        self.initialize()
        effective_id = session_id or self._new_session_id(seed, payload_hash)
        session = self.sessions.get(effective_id)
        if session is None:
            created_at = self._deterministic_timestamp(seed, 0)
            self.sessions[effective_id] = {
                "created_at": created_at,
                "last_activity": created_at,
                "sequence": 0,
                "history": [],
            }
            return effective_id

        sequence = int(session["sequence"]) + 1
        session["sequence"] = sequence
        session["last_activity"] = self._deterministic_timestamp(seed, sequence)
        return effective_id

    def append_message(self, session_id: str, *, role: str, content: str, seed: int) -> None:
        """Append message with deterministic timestamp."""
        session = self.sessions[session_id]
        sequence = int(session["sequence"]) + 1
        session["sequence"] = sequence
        timestamp = self._deterministic_timestamp(seed, sequence)
        session["last_activity"] = timestamp
        session["history"].append({"role": role, "content": content, "timestamp": timestamp})

    def checkpoint(self) -> dict[str, Any]:
        """Checkpoint serializable session store state."""
        return {
            "version": self.version,
            "session_count": len(self.sessions),
            "sessions": self.sessions,
        }

    def terminate(self) -> None:
        """Terminate store state (no-op for in-memory store)."""


SESSION_STORE = RuntimeSessionStore(version="1.0", sessions={})
SESSIONS = SESSION_STORE.sessions


def get_sessions() -> dict[str, dict[str, Any]]:
    """Return session dictionary for history and admin endpoints."""
    return SESSION_STORE.sessions


class ChatTask:
    """Task handler for chat.v1.handle_message."""

    def __init__(self, name: str = _TASK_NAME) -> None:
        self.name = name
        self._context: ExecutionContext | None = None
        self._request_payload: dict[str, Any] | None = None
        self._request: ChatRequest | None = None
        self._session_id: str | None = None
        self._results: list[PageResult] = []
        self._started_at = 0.0
        self._provenance: dict[str, Any] = {}

    def initialize(self, payload: dict[str, Any]) -> None:
        self._request_payload = payload
        self._context = ExecutionContext.from_payload(self.name, payload)
        self._started_at = time.perf_counter()
        self._request = normalize_chat_payload(payload)
        assert self._context is not None
        self._session_id = SESSION_STORE.get_or_create(
            self._request.session_id,
            seed=self._context.seed,
            payload_hash=self._context.payload_hash,
        )
        SESSION_STORE.append_message(
            self._session_id,
            role="user",
            content=self._request.message,
            seed=self._context.seed,
        )

    def validate(self) -> None:
        if self._request is None:
            msg = "ChatTask validation failed: request not initialized"
            raise RuntimeError(msg)
        if self._session_id is None:
            msg = "ChatTask validation failed: session not initialized"
            raise RuntimeError(msg)

    def operate(self) -> ChatResponse:
        assert self._request is not None
        assert self._context is not None
        assert self._session_id is not None

        min_score = self._request.min_score
        mode = self._request.mode
        artifact = ThalosEngine().run(
            self._request.message,
            EngineConfig(
                seed=self._context.seed,
                max_candidates=self._request.max_results,
                mode=mode.value,
                intent_override="chat",
            ),
        )
        results = [
            self._candidate_to_page_result(candidate.model_dump(), query=self._request.message)
            for candidate in artifact.candidates
        ]

        # Keep only results that meet the min_score filter (if any passed)
        qualified = [r for r in results if r.coherence.overall_score >= min_score]
        final_results = qualified or results
        final_results = final_results[: self._request.max_results]
        final_results.sort(key=lambda item: item.coherence.overall_score, reverse=True)
        self._results = final_results

        if min_score > 0.0 and (not qualified):
            achieved = final_results[0].coherence.overall_score if final_results else 0.0
            elapsed_time_s = time.perf_counter() - self._started_at
            checkpoint = self.checkpoint()
            raise CoherenceThresholdError(
                min_score=min_score,
                best_score=achieved,
                attempts=1,
                time_budget_s=elapsed_time_s,
                checkpoint=checkpoint,
                mode=self._request.mode.value,
            )

        if final_results:
            best = final_results[0]
            snippet = best.snippet or ""
            reply = (
                f"Found {len(final_results)} results for '{self._request.message}'. "
                f"Best coherence score: {best.coherence.overall_score:.1f}/100 "
                f"({best.coherence.confidence_level}). "
                f"Top result preview: {snippet[:100]}..."
            )
        else:
            reply = (
                f"No results found for '{self._request.message}'. "
                "Try mode='generative' for coherent text generation."
            )

        SESSION_STORE.append_message(
            self._session_id,
            role="bot",
            content=reply,
            seed=self._context.seed,
        )
        elapsed_ms = (time.perf_counter() - self._started_at) * 1000
        self._provenance = {
            "task": self.name,
            "seed": self._context.seed,
            "payload_hash": self._context.payload_hash,
            "query_time_ms": elapsed_ms,
            "mode": mode.value,
            "results_count": len(final_results),
            "min_score": min_score,
            "llm_provider": None,
            "stabilization": artifact.stabilization,
            "purity_metrics": artifact.purity_metrics,
        }
        return ChatResponse(
            reply=reply,
            session_id=self._session_id,
            results=final_results,
            metadata=self._provenance,
        )

    def reconcile(self, response: ChatResponse) -> ChatResponse:
        return response

    def _candidate_to_page_result(self, candidate: dict[str, Any], *, query: str) -> PageResult:
        score = float(candidate["coherence_score"])
        confidence = ConfidenceLevel.HIGH if score >= 80.0 else ConfidenceLevel.MEDIUM
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
            normalized_text=None,
        )

    def checkpoint(self) -> dict[str, Any]:
        return {
            "task": self.name,
            "context": None if self._context is None else {
                "seed": self._context.seed,
                "payload_hash": self._context.payload_hash,
            },
            "session_id": self._session_id,
            "result_count": len(self._results),
            "session_store": SESSION_STORE.checkpoint(),
        }

    def terminate(self) -> None:
        self._request_payload = None
        self._request = None
        self._context = None
        self._results = []
        self._session_id = None
        self._provenance = {}
        SESSION_STORE.terminate()

    def run(self, payload: dict[str, Any]) -> ChatResponse:
        self.initialize(payload)
        self.validate()
        response = self.operate()
        reconciled = self.reconcile(response)
        self.checkpoint()
        self.terminate()
        return reconciled


class ChatTaskPlugin:
    """Registers chat.v1.handle_message task."""

    @property
    def name(self) -> str:
        return _TASK_NAME

    def register(self, engine: RuntimeEngine) -> None:
        engine.register_module(_TASK_NAME, ChatTask())
        logger.info("ChatTaskPlugin: registered %s", _TASK_NAME)
