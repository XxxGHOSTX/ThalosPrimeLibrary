"""Chat task plugin."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from thalos_prime.errors import CoherenceThresholdError
from thalos_prime.generative_engine import generate_coherent_batch
from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_decoder import decode_page
from thalos_prime.models.api_models import ChatRequest, ChatResponse, PageResult, SearchMode
from thalos_runtime.plugins.common import (
    ExecutionContext,
    build_coherence_info,
    build_page_result,
    normalize_chat_payload,
)

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)

_TASK_NAME = "chat.v1.handle_message"

# Maximum wall-clock time budget for a single chat task (30 minutes).
# Step counters are used for determinism; this bound only caps real-time.
_MAX_TIME_BUDGET_S: float = 1800.0

# Maximum generation attempts within the time budget.
_MAX_ATTEMPTS: int = 5

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

    def operate(self) -> ChatResponse:  # noqa: C901
        assert self._request is not None
        assert self._context is not None
        assert self._session_id is not None

        min_score = self._request.min_score
        mode = self._request.mode
        results: list[PageResult] = []

        # ----------------------------------------------------------------
        # GENERATIVE mode — corpus-based, always produces coherence >= 80
        # ----------------------------------------------------------------
        if mode is SearchMode.GENERATIVE:
            gen_results = generate_coherent_batch(
                query=self._request.message,
                seed=self._context.seed,
                count=self._request.max_results,
            )
            for gr in gen_results:
                decoded = decode_page(
                    address=gr.address,
                    text=gr.text,
                    query=self._request.message,
                    source="generative",
                )
                coherence_info = build_coherence_info(decoded)
                page_result = build_page_result(
                    address=gr.address,
                    raw_text=decoded.raw_text,
                    query=self._request.message,
                    source="generative",
                    timestamp=decoded.timestamp,
                    coherence=coherence_info,
                )
                results.append(page_result)

        # ----------------------------------------------------------------
        # LOCAL / HYBRID mode — babel page generation with retry loop
        # ----------------------------------------------------------------
        elif mode.value in {"local", "hybrid"}:
            best_score = 0.0
            attempt = 0
            start_time = time.perf_counter()

            while attempt < _MAX_ATTEMPTS:
                elapsed = time.perf_counter() - start_time
                if elapsed > _MAX_TIME_BUDGET_S:
                    logger.warning(
                        "%s: time budget %.1fs exhausted after %d attempt(s)",
                        self.name,
                        elapsed,
                        attempt,
                    )
                    break

                attempt += 1
                multiplier = attempt  # oversample on each retry
                addresses = enumerate_addresses(
                    self._request.message,
                    max_results=self._request.max_results * multiplier,
                )
                attempt_results: list[PageResult] = []
                for addr_info in addresses:
                    address = str(addr_info["address"])
                    page_text = address_to_page(address)
                    decoded = decode_page(
                        address=address,
                        text=page_text,
                        query=self._request.message,
                        source="local",
                    )
                    coherence_info = build_coherence_info(decoded)
                    page_result = build_page_result(
                        address=address,
                        raw_text=decoded.raw_text,
                        query=self._request.message,
                        source=decoded.source,
                        timestamp=decoded.timestamp,
                        coherence=coherence_info,
                    )
                    attempt_results.append(page_result)

                attempt_results.sort(
                    key=lambda item: item.coherence.overall_score, reverse=True
                )
                if attempt_results:
                    candidate_score = attempt_results[0].coherence.overall_score
                    if candidate_score > best_score:
                        best_score = candidate_score
                        results = attempt_results

                if results and results[0].coherence.overall_score >= min_score:
                    break

                logger.info(
                    "%s: attempt %d/%d — best score %.1f < min %.1f; retrying",
                    self.name,
                    attempt,
                    _MAX_ATTEMPTS,
                    best_score,
                    min_score,
                )

            # Enforce threshold — halt with state capture if not met
            if min_score > 0 and (
                not results or results[0].coherence.overall_score < min_score
            ):
                achieved = results[0].coherence.overall_score if results else 0.0
                elapsed_s = time.perf_counter() - self._started_at
                checkpoint = self.checkpoint()
                raise CoherenceThresholdError(
                    min_score=min_score,
                    best_score=achieved,
                    attempts=attempt,
                    time_budget_s=elapsed_s,
                    checkpoint=checkpoint,
                    mode=mode.value,
                )

        # ----------------------------------------------------------------
        # REMOTE mode — not implemented; raise explicit typed error
        # ----------------------------------------------------------------
        else:
            msg = (
                f"Search mode {mode.value!r} is not supported in this task. "
                "Use 'local', 'hybrid', or 'generative'."
            )
            raise NotImplementedError(msg)

        # Keep only results that meet the min_score filter (if any passed)
        qualified = [r for r in results if r.coherence.overall_score >= min_score]
        final_results = qualified if qualified else results
        final_results = final_results[: self._request.max_results]
        final_results.sort(key=lambda item: item.coherence.overall_score, reverse=True)
        self._results = final_results

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
        }
        return ChatResponse(
            reply=reply,
            session_id=self._session_id,
            results=final_results,
            metadata=self._provenance,
        )

    def reconcile(self, response: ChatResponse) -> ChatResponse:
        return response

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
