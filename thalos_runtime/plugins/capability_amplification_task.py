"""Runtime plugin exposing the capability amplification kernel."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from thalos_runtime.core.capability_amplification import (
    Capability,
    CapabilityAmplifier,
    CallableCapabilityProvider,
    TaskContract,
)

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)

_TASK_NAME = "capability.v1.execute"


class CapabilityAmplificationTask:
    """Task adapter that amplifies a bounded operation through RuntimeEngine."""

    def __init__(self, engine: RuntimeEngine) -> None:
        self._engine = engine

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a task contract against registered runtime capabilities."""
        contract = TaskContract.model_validate(payload)
        amplifier = CapabilityAmplifier(
            self._engine.capability_router,
            validators=self._engine.capability_validators(),
        )
        result = amplifier.run(contract)
        return result.model_dump(mode="json")


class CapabilityAmplificationTaskPlugin:
    """Registers the capability amplification runtime task."""

    @property
    def name(self) -> str:
        """Return the stable plugin name."""
        return "capability-amplification"

    def register(self, engine: RuntimeEngine) -> None:
        """Register the amplification task after core runtime tasks."""
        engine.register_module(_TASK_NAME, CapabilityAmplificationTask(engine))
        engine.register_capability_provider(
            CallableCapabilityProvider(
                provider_id="runtime.search.v1",
                capabilities=frozenset({Capability.RETRIEVE}),
                replayable=False,
                operation=lambda operation_payload: engine.execute(
                    "search.v1.query",
                    operation_payload,
                ),
            )
        )
        logger.info("CapabilityAmplificationTaskPlugin: registered %s", _TASK_NAME)


__all__ = ["CapabilityAmplificationTaskPlugin", "CapabilityAmplificationTask"]
