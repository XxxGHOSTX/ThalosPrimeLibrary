"""Release strategy definitions for infra-synthesis.

Each strategy implements a ``execute(schema, deploy_key)`` method that
logs actionable deployment steps.  No external system calls are made;
the strategy layer is responsible for ordered orchestration decisions.

Data Plane: logging-only execution; no lifecycle coordination.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DirectStrategy:
    """Deploy all changes immediately to the target environment.

    Steps:
    1. Validate pre-conditions.
    2. Apply all infrastructure changes in a single operation.
    3. Run smoke tests.
    4. Confirm deployment.
    """

    def execute(self, schema: dict[str, Any], deploy_key: str) -> None:
        """Execute a direct (all-at-once) deployment.

        Args:
            schema: Validated infrastructure schema.
            deploy_key: Deployment identifier for tracing.

        """
        project = schema.get("project", {}).get("name", "unknown")
        logger.info("[%s] DirectStrategy: starting deployment for '%s'", deploy_key, project)
        logger.info("[%s] DirectStrategy: step 1/4 — validating pre-conditions", deploy_key)
        logger.info("[%s] DirectStrategy: step 2/4 — applying all infrastructure changes", deploy_key)
        logger.info("[%s] DirectStrategy: step 3/4 — running smoke tests", deploy_key)
        logger.info("[%s] DirectStrategy: step 4/4 — confirming deployment complete", deploy_key)


class BlueGreenStrategy:
    """Deploy to a green environment, then cut traffic over from blue.

    Steps:
    1. Provision green environment.
    2. Deploy schema to green.
    3. Run green validation suite.
    4. Shift 100% traffic to green.
    5. Decommission blue environment.
    """

    def execute(self, schema: dict[str, Any], deploy_key: str) -> None:
        """Execute a blue/green deployment.

        Args:
            schema: Validated infrastructure schema.
            deploy_key: Deployment identifier for tracing.

        """
        project = schema.get("project", {}).get("name", "unknown")
        logger.info("[%s] BlueGreenStrategy: starting blue/green deployment for '%s'", deploy_key, project)
        logger.info("[%s] BlueGreenStrategy: step 1/5 — provisioning green environment", deploy_key)
        logger.info("[%s] BlueGreenStrategy: step 2/5 — deploying schema to green", deploy_key)
        logger.info("[%s] BlueGreenStrategy: step 3/5 — running green validation suite", deploy_key)
        logger.info("[%s] BlueGreenStrategy: step 4/5 — shifting 100%% traffic to green", deploy_key)
        logger.info("[%s] BlueGreenStrategy: step 5/5 — decommissioning blue environment", deploy_key)


class CanaryStrategy:
    """Deploy to a small canary slice, then progressively roll out.

    Steps:
    1. Deploy schema to canary (5% traffic).
    2. Monitor canary error rate for stability window.
    3. Expand canary to 50% traffic.
    4. Monitor again.
    5. Roll out to 100% and retire canary.
    """

    def execute(self, schema: dict[str, Any], deploy_key: str) -> None:
        """Execute a canary deployment.

        Args:
            schema: Validated infrastructure schema.
            deploy_key: Deployment identifier for tracing.

        """
        project = schema.get("project", {}).get("name", "unknown")
        logger.info("[%s] CanaryStrategy: starting canary deployment for '%s'", deploy_key, project)
        logger.info("[%s] CanaryStrategy: step 1/5 — deploying to canary slice (5%% traffic)", deploy_key)
        logger.info("[%s] CanaryStrategy: step 2/5 — monitoring canary error rate (stability window)", deploy_key)
        logger.info("[%s] CanaryStrategy: step 3/5 — expanding canary to 50%% traffic", deploy_key)
        logger.info("[%s] CanaryStrategy: step 4/5 — re-monitoring for stability confirmation", deploy_key)
        logger.info("[%s] CanaryStrategy: step 5/5 — rolling out to 100%% and retiring canary", deploy_key)


__all__ = ["BlueGreenStrategy", "CanaryStrategy", "DirectStrategy"]
