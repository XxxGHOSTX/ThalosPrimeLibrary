"""High-coherence chat task plugin."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from thalos_prime.models.api_models import ChatResponse
from thalos_runtime.plugins.chat_task import ChatTask
from thalos_runtime.plugins.common import ExecutionContext, normalize_chat_payload

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)

_TASK_NAME = "chat.v1.handle_message_high_coherence"
_DEFAULT_MIN_SCORE = 51.0
_DEFAULT_MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class HighCoherenceConfig:
    """Configuration for high-coherence chat task."""

    default_min_score: float = _DEFAULT_MIN_SCORE
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS


class ChatHighCoherenceTask:
    """Task handler for high-coherence chat orchestration."""

    def __init__(self, name: str = _TASK_NAME, config: HighCoherenceConfig | None = None) -> None:
        self.name = name
        self.config = config or HighCoherenceConfig()
        self._payload: dict[str, Any] | None = None
        self._context: ExecutionContext | None = None
        self._min_score = self.config.default_min_score
        self._attempts = 0

    def initialize(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self._context = ExecutionContext.from_payload(self.name, payload)
        request = normalize_chat_payload(payload)
        self._min_score = float(payload.get("min_score", self.config.default_min_score))
        self._payload = {
            **request.model_dump(),
            "min_score": self._min_score,
        }

    def validate(self) -> None:
        if self._payload is None or self._context is None:
            msg = "ChatHighCoherenceTask not initialized"
            raise RuntimeError(msg)
        if self.config.max_attempts < 1:
            msg = "ChatHighCoherenceTask max_attempts must be >= 1"
            raise RuntimeError(msg)

    def _attempt_payload(self, attempt: int) -> dict[str, Any]:
        assert self._payload is not None
        max_results = int(self._payload.get("max_results", 5))
        oversample_multiplier = 1 + attempt
        return {
            **self._payload,
            "max_results": max_results * oversample_multiplier,
        }

    def _select_high_coherence(self, response: ChatResponse) -> tuple[list[Any], bool]:
        selected = [result for result in response.results if result.coherence.overall_score >= self._min_score]
        if selected:
            return selected, True
        return response.results, False

    @staticmethod
    def _is_better_response(selected: list[Any], best_selected: list[Any]) -> bool:
        """Return True when selected results are better than current best."""
        if not selected:
            return False
        if not best_selected:
            return True
        return bool(selected[0].coherence.overall_score > best_selected[0].coherence.overall_score)

    def operate(self) -> ChatResponse:
        assert self._context is not None
        best_response: ChatResponse | None = None
        best_selected: list[Any] = []
        satisfied = False
        for attempt in range(1, self.config.max_attempts + 1):
            self._attempts = attempt
            payload = self._attempt_payload(attempt)
            response = ChatTask().run(payload)
            selected, attempt_satisfied = self._select_high_coherence(response)
            if best_response is None:
                best_response = response
                best_selected = selected
            elif self._is_better_response(selected, best_selected):
                best_response = response
                best_selected = selected
            if attempt_satisfied:
                satisfied = True
                best_response = response
                best_selected = selected
                break

        assert best_response is not None
        metadata = dict(best_response.metadata)
        metadata.update({
            "min_score_target": self._min_score,
            "high_coherence_satisfied": satisfied,
            "fallback_used": not satisfied,
            "attempts": self._attempts,
            "task": self.name,
            "seed": self._context.seed,
            "payload_hash": self._context.payload_hash,
        })
        return ChatResponse(
            reply=best_response.reply,
            session_id=best_response.session_id,
            results=best_selected,
            metadata=metadata,
        )

    def reconcile(self, response: ChatResponse) -> ChatResponse:
        return response

    def checkpoint(self) -> dict[str, Any]:
        return {
            "task": self.name,
            "min_score": self._min_score,
            "attempts": self._attempts,
            "max_attempts": self.config.max_attempts,
        }

    def terminate(self) -> None:
        self._payload = None
        self._context = None
        self._attempts = 0
        self._min_score = self.config.default_min_score

    def run(self, payload: dict[str, Any]) -> ChatResponse:
        self.initialize(payload)
        self.validate()
        response = self.operate()
        reconciled = self.reconcile(response)
        self.checkpoint()
        self.terminate()
        return reconciled


class ChatHighCoherenceTaskPlugin:
    """Registers chat.v1.handle_message_high_coherence task."""

    @property
    def name(self) -> str:
        return _TASK_NAME

    def register(self, engine: RuntimeEngine) -> None:
        engine.register_module(_TASK_NAME, ChatHighCoherenceTask())
        logger.info("ChatHighCoherenceTaskPlugin: registered %s", _TASK_NAME)


def execution_defaults() -> dict[str, float | int]:
    """Return default execution configuration for high-coherence chat."""
    return {
        "default_min_score": _DEFAULT_MIN_SCORE,
        "max_attempts": _DEFAULT_MAX_ATTEMPTS,
    }
