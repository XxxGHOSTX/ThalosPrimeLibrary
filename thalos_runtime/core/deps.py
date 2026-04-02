"""Runtime engine dependency helpers.

Provides explicit setter/getter access to the RuntimeEngine singleton used by
the API layer and entrypoints.
"""

from __future__ import annotations

from thalos_runtime.core.engine import RuntimeEngine

_engine: RuntimeEngine | None = None


def set_engine(engine: RuntimeEngine) -> None:
    """Set the process-wide runtime engine instance."""
    global _engine  # noqa: PLW0603
    _engine = engine


def get_engine() -> RuntimeEngine:
    """Return the configured runtime engine instance.

    Raises:
        RuntimeError: If no engine has been configured yet.

    """
    if _engine is None:
        msg = "RuntimeEngine is not configured. Initialize and set_engine() first."
        raise RuntimeError(msg)
    return _engine

