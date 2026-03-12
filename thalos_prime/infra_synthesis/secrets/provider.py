"""Secrets provider ABC for infra-synthesis.

Defines the abstract interface for encrypted secret storage and retrieval.
"""

from __future__ import annotations

import abc


class SecretsProvider(abc.ABC):
    """Abstract base class for secret storage providers."""

    @abc.abstractmethod
    def put(self, name: str, value: str) -> None:
        """Store an encrypted secret.

        Args:
            name: Secret identifier (must be non-empty).
            value: Plaintext secret value to store encrypted.

        """

    @abc.abstractmethod
    def get(self, name: str) -> str:
        """Retrieve and decrypt a secret.

        Args:
            name: Secret identifier.

        Returns:
            Plaintext secret value.

        Raises:
            KeyError: When *name* is not found.

        """

    @abc.abstractmethod
    def delete(self, name: str) -> None:
        """Delete a stored secret.

        Args:
            name: Secret identifier.  No-op if absent.

        """

    @abc.abstractmethod
    def list_names(self) -> list[str]:
        """Return sorted list of stored secret names.

        Returns:
            List of secret name strings.

        """


__all__ = ["SecretsProvider"]
