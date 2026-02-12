"""Observability module with structured logging and event tracking."""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredLogger:
    """Structured logger with JSON formatting."""

    def __init__(self, name: str, level: int = logging.INFO) -> None:
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Remove existing handlers
        self.logger.handlers.clear()

        # Console handler with structured format
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # Custom formatter for structured output
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with optional context."""
        self._log(logging.INFO, message, kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with optional context."""
        self._log(logging.WARNING, message, kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with optional context."""
        self._log(logging.ERROR, message, kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with optional context."""
        self._log(logging.DEBUG, message, kwargs)

    def _log(self, level: int, message: str, context: Dict[str, Any]) -> None:
        """Internal logging method."""
        if context:
            context_str = " | " + " | ".join(f"{k}={v}" for k, v in context.items())
            full_message = message + context_str
        else:
            full_message = message

        self.logger.log(level, full_message)


class EventLog:
    """JSONL event log for tracking system events."""

    def __init__(self, log_path: Path) -> None:
        """Initialize event log."""
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> None:
        """
        Log an event to the JSONL file.

        Args:
            event_type: Type of event (e.g., "chat", "seed_generated", "retrieval")
            event_data: Event-specific data
            session_id: Optional session ID
        """
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "session_id": session_id,
            "data": event_data,
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def read_events(
        self,
        event_type: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        """
        Read events from the log with optional filtering.

        Args:
            event_type: Filter by event type
            session_id: Filter by session ID
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        if not self.log_path.exists():
            return []

        events = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    event = json.loads(line)

                    # Apply filters
                    if event_type and event.get("event_type") != event_type:
                        continue
                    if session_id and event.get("session_id") != session_id:
                        continue

                    events.append(event)

                    if limit and len(events) >= limit:
                        break

                except json.JSONDecodeError:
                    continue

        return events


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)
