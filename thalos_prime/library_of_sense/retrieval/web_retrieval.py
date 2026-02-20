"""Library of Sense - Web Retrieval Handler.

Performs HTTP-based content retrieval with timeout enforcement,
connection reuse, and deterministic lifecycle management.
"""

from __future__ import annotations

import logging
from typing import Final
from urllib.parse import urlparse

from requests import Session
from requests.exceptions import RequestException, Timeout

from thalos_prime.library_of_sense.core.interfaces import (
    QueryContext,
    RetrievalResult,
    ValidationResult,
)
from thalos_prime.library_of_sense.core.lifecycle import LifecycleState, SubsystemLifecycle

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT: Final[float] = 10.0
_SUBSYSTEM_NAME: Final[str] = "library_of_sense.web_retrieval_handler"
_USER_AGENT: Final[str] = "ThalosPrime-LibraryOfSense/1.0"


class WebRetrievalHandler:
    """Handles HTTP-based retrieval with lifecycle management and timeout control.

    Implements all required lifecycle methods for deterministic operation and
    uses a persistent requests Session for connection reuse.
    """

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT, seed: int = 0) -> None:
        """Initialize the web retrieval handler.

        Args:
            timeout: HTTP request timeout in seconds.
            seed: Deterministic seed for replay identification.

        """
        self._timeout = timeout
        self._seed = seed
        self._session: Session | None = None
        self._lifecycle = SubsystemLifecycle(_SUBSYSTEM_NAME, seed=seed)
        self._request_count = 0

    def initialize(self) -> None:
        """Initialize the HTTP session and transition to INITIALIZED state."""
        self._lifecycle.transition(LifecycleState.INITIALIZING, "Creating HTTP session")
        self._session = Session()
        self._session.headers.update({"User-Agent": _USER_AGENT})
        self._request_count = 0
        self._lifecycle.transition(LifecycleState.INITIALIZED, "Session ready")
        logger.info("WebRetrievalHandler initialized with timeout=%.1fs", self._timeout)

    def validate(self) -> None:
        """Validate handler configuration and transition to READY state.

        Raises:
            RuntimeError: If the handler is not initialized.

        """
        self._lifecycle.transition(LifecycleState.VALIDATING, "Validating configuration")
        if self._session is None:
            msg = "WebRetrievalHandler not initialized; call initialize() first"
            raise RuntimeError(msg)
        if self._timeout <= 0:
            msg = f"Invalid timeout value: {self._timeout}"
            raise RuntimeError(msg)
        self._lifecycle.transition(LifecycleState.READY, "Validation passed")

    def operate(self) -> None:
        """Transition to OPERATING state for active retrieval."""
        self._lifecycle.transition(LifecycleState.OPERATING, "Entering operation mode")
        logger.info(
            "WebRetrievalHandler operating, requests_served=%d",
            self._request_count,
        )

    def reconcile(self) -> None:
        """Reconcile handler state by recreating session if needed.

        Replaces a closed or missing session and returns to READY state.
        """
        self._lifecycle.transition(LifecycleState.RECONCILING, "Reconciling session state")
        if self._session is None:
            self._session = Session()
            self._session.headers.update({"User-Agent": _USER_AGENT})
            logger.info("WebRetrievalHandler: session recreated during reconciliation")
        self._lifecycle.transition(LifecycleState.READY, "Reconciliation complete")

    def checkpoint(self) -> None:
        """Emit a structured checkpoint log with current handler state."""
        self._lifecycle.transition(LifecycleState.CHECKPOINTING, "Checkpointing state")
        logger.info(
            "WebRetrievalHandler checkpoint: seed=%d requests=%d timeout=%.1f",
            self._seed,
            self._request_count,
            self._timeout,
        )
        self._lifecycle.transition(LifecycleState.READY, "Checkpoint complete")

    def terminate(self) -> None:
        """Close the HTTP session and release resources."""
        self._lifecycle.transition(LifecycleState.TERMINATING, "Closing session")
        if self._session is not None:
            self._session.close()
            self._session = None
        self._lifecycle.transition(LifecycleState.TERMINATED, "Terminated")
        logger.info(
            "WebRetrievalHandler terminated, total_requests=%d",
            self._request_count,
        )

    def validate_source(self) -> ValidationResult:
        """Validate this source for use as a RetrievalSource.

        Returns:
            ValidationResult indicating configuration validity.

        """
        if self._session is None:
            return ValidationResult(
                valid=False,
                message="Session not initialized",
            )
        return ValidationResult(valid=True, message="WebRetrievalHandler ready")

    def fetch_url(self, url: str) -> str:
        """Fetch raw text content from the given URL.

        Args:
            url: The URL to fetch content from.

        Returns:
            Text content of the HTTP response.

        Raises:
            RuntimeError: If the handler is not initialized.
            Timeout: If the request exceeds the configured timeout.
            RequestException: If an HTTP error occurs.

        """
        if self._session is None:
            msg = "WebRetrievalHandler not initialized"
            raise RuntimeError(msg)
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        self._request_count += 1
        text: str = response.text
        return text

    def query(self, query: str, context: QueryContext) -> RetrievalResult:
        """Query the web for content matching the given query string.

        Args:
            query: The search query to use as a URL or search term.
            context: Query context with timeout and domain hints.

        Returns:
            RetrievalResult with fetched content, or empty result on error.

        """
        parsed = urlparse(query)
        if parsed.scheme not in {"http", "https"}:
            return RetrievalResult(
                source="web",
                content="",
                confidence=0.0,
                metadata={"reason": "not_a_url"},
            )
        effective_timeout = min(self._timeout, context.timeout_seconds)
        if self._session is None:
            return RetrievalResult(
                source="web",
                content="",
                confidence=0.0,
                metadata={"reason": "not_initialized"},
            )
        try:
            response = self._session.get(query, timeout=effective_timeout)
            response.raise_for_status()
            self._request_count += 1
            content = response.text[:2000]
            return RetrievalResult(
                source="web",
                content=content,
                confidence=0.8,
                metadata={"url": query, "status_code": str(response.status_code)},
            )
        except Timeout:
            logger.warning("WebRetrievalHandler: timeout for %s", query)
            return RetrievalResult(
                source="web",
                content="",
                confidence=0.0,
                metadata={"reason": "timeout", "url": query},
            )
        except RequestException as exc:
            logger.warning("WebRetrievalHandler: request error for %s: %s", query, exc)
            return RetrievalResult(
                source="web",
                content="",
                confidence=0.0,
                metadata={"reason": "request_error", "url": query},
            )


__all__ = ["WebRetrievalHandler"]
