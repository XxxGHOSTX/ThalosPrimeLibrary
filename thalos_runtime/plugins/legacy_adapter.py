"""Legacy adapter plugin for thalos_runtime.

Wraps existing thalos_prime repository logic into the TaskHandler
and PluginInterface protocols, exposing it under the 'legacy' task name.

Control Plane boundary (LegacyPlugin): manages registration lifecycle.
Data Plane boundary (LegacyAdapter): executes thalos_prime synthesis.

The wrapped logic calls thalos_prime.synthesis.deep_synthesis(), which
performs deterministic structural decomposition of a text query and
maps the result to canonical Library of Babel endpoints.

Payload contract for the 'legacy' task:
    {"query": str}  -  text to synthesize (default: "thalos runtime legacy task")

Result contract:
    dict[str, object] as returned by thalos_prime.synthesis.deep_synthesis()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from thalos_prime.synthesis import deep_synthesis

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)

_PLUGIN_NAME: str = "legacy"


class LegacyAdapter:
    """Data Plane handler wrapping thalos_prime synthesis.

    Implements the TaskHandler protocol via run(payload).
    All existing thalos_prime logic is invoked here and nowhere else.
    """

    def run(self, payload: dict[str, Any]) -> dict[str, object]:
        """Execute the legacy thalos_prime synthesis pipeline.

        Args:
            payload: Input dict.  Recognized key:
                ``query`` (str): Text prompt for deep_synthesis.
                Defaults to ``"thalos runtime legacy task"`` if absent.

        Returns:
            Structured synthesis result from
            ``thalos_prime.synthesis.deep_synthesis()``.

        """
        query: str = str(payload.get("query", "thalos runtime legacy task"))
        logger.info("LegacyAdapter.run(): query=%r", query)
        result = deep_synthesis(query)
        logger.info("LegacyAdapter.run(): synthesis complete")
        return result


class LegacyPlugin:
    """Control Plane plugin registering LegacyAdapter with the engine.

    Implements the PluginInterface protocol.  Registers a LegacyAdapter
    instance under the 'legacy' task name during engine wiring.
    """

    @property
    def name(self) -> str:
        """Return the unique plugin identifier.

        Returns:
            The string ``"legacy"``.

        """
        return _PLUGIN_NAME

    def register(self, engine: RuntimeEngine) -> None:
        """Register the LegacyAdapter handler with the runtime engine.

        Args:
            engine: RuntimeEngine instance to register the handler into.

        """
        adapter = LegacyAdapter()
        engine.register_module(_PLUGIN_NAME, adapter)
        logger.info("LegacyPlugin: registered '%s' handler", _PLUGIN_NAME)


__all__ = ["LegacyAdapter", "LegacyPlugin"]
