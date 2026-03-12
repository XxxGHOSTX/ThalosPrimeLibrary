"""Simple pub/sub event bus for infra-synthesis.

Used by :class:`InfraSynthesisEngine` to emit lifecycle events such as
``"generated"`` and ``"hashed"`` to registered subscribers.

Control Plane: event routing only; no computational logic.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Handler signature: receives the event name and a payload dict.
EventHandler = Callable[[str, dict[str, Any]], None]


class EventBus:
    """Minimal synchronous publish/subscribe event bus.

    Subscribers register for named event channels; publishers call
    :meth:`publish` and all matching handlers are invoked in registration
    order.  Errors in handlers are logged and re-raised to prevent silent
    degradation.
    """

    def __init__(self) -> None:
        """Initialise an empty handler registry."""
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event: str, handler: EventHandler) -> None:
        """Register *handler* to be called when *event* is published.

        Args:
            event: Event name (arbitrary string).
            handler: Callable invoked with ``(event_name, payload)``.

        """
        self._handlers[event].append(handler)
        logger.debug("EventBus: subscribed handler '%s' to '%s'", handler.__name__, event)

    def publish(self, event: str, payload: dict[str, Any] | None = None) -> None:
        """Publish *event* with optional *payload* to all registered handlers.

        Args:
            event: Event name to publish.
            payload: Arbitrary dict passed to each handler.

        Raises:
            Exception: Re-raises any exception raised by a handler.

        """
        data = payload or {}
        logger.info("EventBus: publish '%s' payload_keys=%s", event, list(data.keys()))
        for handler in self._handlers.get(event, []):
            handler(event, data)

    def subscribers(self, event: str) -> list[EventHandler]:
        """Return a copy of all handlers registered for *event*.

        Args:
            event: Event name to query.

        Returns:
            List of handler callables (may be empty).

        """
        return list(self._handlers.get(event, []))


__all__ = ["EventBus", "EventHandler"]
