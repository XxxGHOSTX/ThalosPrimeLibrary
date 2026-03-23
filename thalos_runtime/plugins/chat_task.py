"""Chat task plugin."""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

from thalos_prime.lob_babel_enumerator import enumerate_addresses
from thalos_prime.lob_babel_generator import address_to_page
from thalos_prime.lob_decoder import decode_page
from thalos_prime.models.api_models import ChatRequest, ChatResponse, PageResult
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
SESSIONS: dict[str, dict[str, Any]] = {}


def get_or_create_session(session_id: str | None = None) -> str:
    """Get existing session or create a new one."""
    if session_id and session_id in SESSIONS:
        SESSIONS[session_id]["last_activity"] = time.time()
        return session_id

    new_session_id = str(uuid.uuid4())
    SESSIONS[new_session_id] = {
        "created_at": time.time(),
        "last_activity": time.time(),
        "history": [],
    }
    return new_session_id


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
        self._session_id = get_or_create_session(self._request.session_id)
        SESSIONS[self._session_id]["history"].append({
            "role": "user",
            "content": self._request.message,
            "timestamp": time.time(),
        })

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
        results = []
        if self._request.mode.value in {"local", "hybrid"}:
            addresses = enumerate_addresses(self._request.message, max_results=self._request.max_results)
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
                results.append(page_result)

        results.sort(key=lambda item: item.coherence.overall_score, reverse=True)
        self._results = results
        if results:
            best = results[0]
            snippet = best.snippet or ""
            reply = (
                f"Found {len(results)} results for '{self._request.message}'. "
                f"Best coherence score: {best.coherence.overall_score:.1f}/100 "
                f"({best.coherence.confidence_level}). "
                f"Top result preview: {snippet[:100]}..."
            )
        else:
            reply = f"No results found for '{self._request.message}'. Try a different query."

        SESSIONS[self._session_id]["history"].append({
            "role": "bot",
            "content": reply,
            "timestamp": time.time(),
        })
        elapsed_ms = (time.perf_counter() - self._started_at) * 1000
        self._provenance = {
            "task": self.name,
            "seed": self._context.seed,
            "payload_hash": self._context.payload_hash,
            "query_time_ms": elapsed_ms,
            "mode": self._request.mode.value,
            "results_count": len(results),
        }
        return ChatResponse(
            reply=reply,
            session_id=self._session_id,
            results=results,
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
        }

    def terminate(self) -> None:
        self._request_payload = None
        self._request = None
        self._context = None
        self._results = []
        self._session_id = None
        self._provenance = {}

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
