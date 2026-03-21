"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json

# Version metadata — bump on every stable release
MODULE_VERSION = "2.0.0"
MODULE_OWNER = "Tony Ray Macier III"


@dataclass
class ExecutionContext:
    """Immutable execution context passed to every engine invocation."""

    seed: int
    session_id: str
    owner: str = MODULE_OWNER
    version: str = MODULE_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def state_hash(self) -> str:
        """Compute a deterministic hash of this execution context."""
        payload = json.dumps(
            {"seed": self.seed, "session_id": self.session_id, "version": self.version},
            sort_keys=True,
        ).encode()
        return sha256(payload).hexdigest()


class BaseEngine(ABC):
    """
    Abstract base class for all ThalosPrime engine implementations.

    Rules:
    - Core modules CANNOT depend on experimental modules.
    - Every engine invocation MUST receive a valid ExecutionContext.
    - Every engine MUST log its output state hash.
    """

    @abstractmethod
    def execute(self, context: ExecutionContext, payload: dict) -> dict:
        """
        Execute the engine logic.

        Args:
            context: Immutable execution context with seed and session ID.
            payload: Input data for this engine invocation.

        Returns:
            dict with at minimum: {"result": ..., "state_hash": ..., "version": ...}
        """
        ...

    def _build_response(self, context: ExecutionContext, result: dict) -> dict:
        """Wrap a result with standard metadata and state hash."""
        return {
            "result": result,
            "state_hash": context.state_hash(),
            "version": context.version,
            "session_id": context.session_id,
            "seed": context.seed,
        }
