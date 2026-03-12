"""Local AES-GCM (Fernet) secrets vault for infra-synthesis.

Persists encrypted secrets as individual files under a configurable
directory.  Uses ``cryptography.fernet`` (AES-128-CBC + HMAC-SHA256)
for authenticated encryption.

Secrets are keyed by name; the symmetric key must be supplied by the
caller — never hard-coded or defaulted.

Data Plane implementation: crypto + file I/O only.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from thalos_prime.infra_synthesis.secrets.provider import SecretsProvider

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"


class SecretNotFoundError(KeyError):
    """Raised when a requested secret name does not exist in the vault."""


class LocalVaultSecretsProvider(SecretsProvider):
    """Fernet-encrypted on-disk secrets vault.

    Args:
        vault_dir: Directory where encrypted secret files are stored.
        key: A valid Fernet key (32 URL-safe base-64 bytes).  Generate
             with ``Fernet.generate_key()``.

    """

    def __init__(self, vault_dir: str | Path, key: bytes) -> None:
        """Initialise the vault.

        Args:
            vault_dir: Filesystem path to the vault directory.
            key: Fernet symmetric key bytes.

        """
        self._vault = Path(vault_dir)
        self._fernet = Fernet(key)

    def _secret_path(self, name: str) -> Path:
        safe = name.replace("/", "_").replace("\\", "_")
        return self._vault / f"{safe}.enc"

    def _ensure_vault(self) -> None:
        self._vault.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, value: str) -> None:
        """Encrypt and store *value* under *name*.

        Args:
            name: Secret identifier.
            value: Plaintext secret value.

        """
        if not name:
            msg = "Secret name must be non-empty"
            raise ValueError(msg)
        self._ensure_vault()
        ciphertext = self._fernet.encrypt(value.encode(_ENCODING))
        self._secret_path(name).write_bytes(ciphertext)
        logger.debug("LocalVault: stored secret '%s'", name)

    def get(self, name: str) -> str:
        """Decrypt and return the secret stored under *name*.

        Args:
            name: Secret identifier.

        Returns:
            Plaintext secret value.

        Raises:
            SecretNotFoundError: When *name* is not stored.
            InvalidToken: When the ciphertext is tampered or the key changed.

        """
        path = self._secret_path(name)
        if not path.exists():
            raise SecretNotFoundError(name)
        ciphertext = path.read_bytes()
        try:
            plaintext = self._fernet.decrypt(ciphertext).decode(_ENCODING)
        except InvalidToken as exc:
            msg = f"Invalid or corrupted secret '{name}'"
            raise InvalidToken(msg) from exc
        logger.debug("LocalVault: retrieved secret '%s'", name)
        return plaintext

    def delete(self, name: str) -> None:
        """Delete the secret stored under *name* (no-op if absent).

        Args:
            name: Secret identifier.

        """
        self._secret_path(name).unlink(missing_ok=True)
        logger.debug("LocalVault: deleted secret '%s'", name)

    def list_names(self) -> list[str]:
        """Return sorted list of stored secret names.

        Returns:
            List of secret name strings.

        """
        if not self._vault.exists():
            return []
        return sorted(p.stem for p in self._vault.glob("*.enc"))


__all__ = ["LocalVaultSecretsProvider", "SecretNotFoundError"]
