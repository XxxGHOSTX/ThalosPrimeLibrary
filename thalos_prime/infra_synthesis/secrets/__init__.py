"""Secrets sub-package for infra-synthesis."""

from __future__ import annotations

from thalos_prime.infra_synthesis.secrets.local_vault import (
    LocalVaultSecretsProvider,
    SecretNotFoundError,
)
from thalos_prime.infra_synthesis.secrets.provider import SecretsProvider

__all__ = ["LocalVaultSecretsProvider", "SecretNotFoundError", "SecretsProvider"]
