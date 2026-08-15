"""Low-overhead execution timeline capture for deterministic debugging."""
from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import inspect
import time
from typing import Any, Callable, Generic, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True)
class TimelineEvent:
    sequence: int
    label: str
    monotonic_ns: int
    payload: dict[str, Any]


class ExecutionTimeline:
    def __init__(self, limit: int = 10_000) -> None:
        if limit < 1:
            raise ValueError("timeline limit must be positive")
        self.limit = limit
        self._events: list[TimelineEvent] = []

    @property
    def events(self) -> tuple[TimelineEvent, ...]:
        return tuple(self._events)

    def record(self, label: str, **payload: Any) -> TimelineEvent:
        if len(self._events) >= self.limit:
            self._events.pop(0)
        event = TimelineEvent(
            sequence=(self._events[-1].sequence + 1 if self._events else 0),
            label=label,
            monotonic_ns=time.monotonic_ns(),
            payload=dict(payload),
        )
        self._events.append(event)
        return event

    def state(self, sequence: int) -> TimelineEvent:
        return self._events[sequence]

    def export(self) -> list[dict[str, Any]]:
        return [
            {
                "sequence": event.sequence,
                "label": event.label,
                "monotonic_ns": event.monotonic_ns,
                "payload": event.payload,
            }
            for event in self._events
        ]


def capture(timeline: ExecutionTimeline | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Capture call/return/exception boundaries without serializing arbitrary memory."""
    active_timeline = timeline or ExecutionTimeline()

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            active_timeline.record("enter", function=func.__qualname__, args_repr=repr(args)[:2048])
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                active_timeline.record(
                    "exception", function=func.__qualname__,
                    exception=type(exc).__name__, message=str(exc)[:2048],
                )
                raise
            active_timeline.record("return", function=func.__qualname__, result_repr=repr(result)[:2048])
            return result

        wrapper.timeline = active_timeline  # type: ignore[attr-defined]
        wrapper.signature = inspect.signature(func)  # type: ignore[attr-defined]
        return wrapper

    return decorator
