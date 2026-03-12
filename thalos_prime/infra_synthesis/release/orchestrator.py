"""Release orchestrator for infra-synthesis.

Selects and delegates to the appropriate release strategy based on the
``ci.release_strategy`` schema field.

Control Plane: strategy selection and lifecycle coordination.
"""

from __future__ import annotations

import logging
from typing import Any

from thalos_prime.infra_synthesis.release.strategy import (
    BlueGreenStrategy,
    CanaryStrategy,
    DirectStrategy,
)

logger = logging.getLogger(__name__)

_STRATEGIES = {
    "direct": DirectStrategy,
    "blue_green": BlueGreenStrategy,
    "canary": CanaryStrategy,
}


class ReleaseOrchestrator:
    """Selects and executes the configured release strategy.

    The strategy is read from ``schema["ci"]["release_strategy"]``.
    Defaults to ``"direct"`` when not specified.

    Usage::

        orchestrator = ReleaseOrchestrator()
        orchestrator.deploy(schema, deploy_key="v1.2.3")

    """

    def deploy(self, schema: dict[str, Any], deploy_key: str) -> None:
        """Select the release strategy from *schema* and execute it.

        Args:
            schema: Validated infrastructure schema dict.
            deploy_key: Deployment identifier passed to the strategy.

        Raises:
            ValueError: When the schema specifies an unknown strategy name.

        """
        strategy_name = str(
            schema.get("ci", {}).get("release_strategy", "direct")
        )
        strategy_cls = _STRATEGIES.get(strategy_name)
        if strategy_cls is None:
            msg = (
                f"Unknown release strategy '{strategy_name}'; "
                f"valid options: {sorted(_STRATEGIES)}"
            )
            raise ValueError(msg)

        logger.info(
            "ReleaseOrchestrator: selected strategy '%s' for deploy_key='%s'",
            strategy_name,
            deploy_key,
        )
        strategy_cls().execute(schema, deploy_key)


__all__ = ["ReleaseOrchestrator"]
