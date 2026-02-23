"""API Key Authentication module for Thalos Prime.

Provides deterministic API key-based authentication with full lifecycle
management. Loads allowed keys from the environment, verifies requests,
and exposes a FastAPI dependency callable for route protection.

Control Plane boundary: manages authentication state and lifecycle.
No data-plane computation logic belongs here.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_ENV_API_KEYS = "THALOS_API_KEYS"
_ENV_AUTH_DISABLED = "THALOS_AUTH_DISABLED"


class DeterministicHalt(RuntimeError):
    """Raised when a lifecycle invariant is violated and the system must halt.

    Attributes:
        message: Human-readable description of the invariant violation.

    """

    def __init__(self, message: str) -> None:
        """Initialize with a descriptive halt message.

        Args:
            message: Description of the invariant violation.

        """
        super().__init__(message)
        self.message = message


class APIKeyAuthenticator:
    """Lifecycle-managed API key authenticator.

    Loads allowed API keys from the ``THALOS_API_KEYS`` environment variable
    (comma-separated list) or from a config dict supplied at construction.
    If ``THALOS_AUTH_DISABLED=1`` is set, all requests pass through without
    key verification.

    Lifecycle methods must be called in order: initialize → validate → operate.
    """

    def __init__(
        self,
        extra_keys: list[str] | None = None,
    ) -> None:
        """Initialize the authenticator.

        Args:
            extra_keys: Additional API keys to allow, merged with environment keys.

        """
        self._extra_keys: list[str] = extra_keys or []
        self._allowed_keys: set[str] = set()
        self._auth_disabled: bool = False
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle protocol implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load allowed API keys from environment or config.

        Reads ``THALOS_API_KEYS`` (comma-separated) and merges with any
        ``extra_keys`` supplied at construction. Respects
        ``THALOS_AUTH_DISABLED=1`` to bypass key enforcement.

        Raises:
            DeterministicHalt: If auth is enabled but no keys are configured.

        """
        raw_disabled = os.environ.get(_ENV_AUTH_DISABLED, "0").strip()
        self._auth_disabled = raw_disabled == "1"

        raw_keys = os.environ.get(_ENV_API_KEYS, "")
        env_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self._allowed_keys = set(env_keys) | set(self._extra_keys)

        if not self._auth_disabled and not self._allowed_keys:
            msg = (
                "APIKeyAuthenticator: auth is enabled but no API keys are configured. "
                f"Set {_ENV_API_KEYS} or pass extra_keys, "
                f"or set {_ENV_AUTH_DISABLED}=1 to disable authentication."
            )
            raise DeterministicHalt(msg)

        self._initialized = True
        logger.info(
            "APIKeyAuthenticator initialized: disabled=%s keys_count=%d",
            self._auth_disabled,
            len(self._allowed_keys),
        )

    def validate(self) -> None:
        """Verify that the authenticator is properly initialized.

        Raises:
            DeterministicHalt: If not initialized or invalid state detected.

        """
        if not self._initialized:
            msg = "APIKeyAuthenticator.validate(): not initialized — call initialize() first"
            raise DeterministicHalt(msg)
        if not self._auth_disabled and not self._allowed_keys:
            msg = "APIKeyAuthenticator.validate(): auth is enabled but key set is empty"
            raise DeterministicHalt(msg)
        logger.info(
            "APIKeyAuthenticator validation passed: disabled=%s keys=%d",
            self._auth_disabled,
            len(self._allowed_keys),
        )

    def operate(self) -> None:
        """No-op: authentication is stateless per-request."""
        logger.debug("APIKeyAuthenticator.operate(): no-op (stateless)")

    def reconcile(self) -> None:
        """No-op: key set is loaded at initialize() and does not drift."""
        logger.debug("APIKeyAuthenticator.reconcile(): no-op")

    def checkpoint(self) -> dict[str, object]:
        """Serialize current configuration state.

        Returns:
            Dictionary with auth configuration (keys are not included for security).

        """
        return {
            "component": "APIKeyAuthenticator",
            "initialized": self._initialized,
            "auth_disabled": self._auth_disabled,
            "key_count": len(self._allowed_keys),
        }

    def terminate(self) -> None:
        """Clear API keys from memory and reset state."""
        self._allowed_keys.clear()
        self._initialized = False
        logger.info("APIKeyAuthenticator terminated: keys cleared")

    # ------------------------------------------------------------------
    # Authentication logic
    # ------------------------------------------------------------------

    def authenticate(self, api_key: str) -> bool:
        """Verify an API key against the allowed set.

        Args:
            api_key: The API key string provided by the caller.

        Returns:
            True if the key is valid or auth is disabled; False otherwise.

        Raises:
            DeterministicHalt: If called before initialize().

        """
        if not self._initialized:
            msg = "APIKeyAuthenticator.authenticate(): not initialized"
            raise DeterministicHalt(msg)
        if self._auth_disabled:
            return True
        return api_key in self._allowed_keys

    def get_fastapi_dependency(self) -> Callable[..., Any]:
        """Return a FastAPI ``Depends()``-compatible callable for route protection.

        The returned callable reads ``X-API-Key`` from request headers and
        raises ``HTTPException(403)`` if the key is not valid.

        Returns:
            A FastAPI dependency function that enforces API key authentication.

        Raises:
            DeterministicHalt: If called before initialize().

        """
        if not self._initialized:
            msg = "APIKeyAuthenticator.get_fastapi_dependency(): not initialized"
            raise DeterministicHalt(msg)

        authenticator = self

        def _verify_api_key(x_api_key: str | None = None) -> bool:
            """Verify the X-API-Key header.

            Args:
                x_api_key: Value from the X-API-Key header.

            Returns:
                True if the key is valid.

            Raises:
                HTTPException: If the key is missing or invalid.

            """
            try:
                from fastapi import Header, HTTPException
            except ImportError as exc:
                msg = "fastapi is required for get_fastapi_dependency()"
                raise ImportError(msg) from exc

            if x_api_key is None:
                _ = Header(None)
                raise HTTPException(status_code=403, detail="X-API-Key header is required")
            if not authenticator.authenticate(x_api_key):
                raise HTTPException(status_code=403, detail="Invalid API key")
            return True

        return _verify_api_key
