"""Thalos NEXUS — Membrane: capability gateway and network enforcement.

Provides ``MembraneGateway``, a context manager that enforces a default-deny
network posture during gate execution.  On Windows it uses
``netsh advfirewall firewall`` to add a temporary block-all-outbound rule;
on non-Windows platforms it logs the intent without invoking ``netsh``
(platform-appropriate no-op).

The firewall rule is always removed in the ``__exit__`` path, even if an
exception occurred, via ``try/finally``.

Control Plane boundary: this module manages capability enforcement only.
No gate execution logic belongs here.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import uuid
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)

_RULE_PREFIX = "ThalosPrime-NEXUS-"


class MembraneError(RuntimeError):
    """Raised when a membrane firewall operation fails."""


class MembraneGateway:
    """Default-deny network capability gateway.

    On Windows 10, adds a temporary ``netsh advfirewall`` outbound-block rule
    before gate execution and removes it afterwards.  The rule name incorporates
    a UUID to avoid name collisions with pre-existing rules.

    Parameters
    ----------
    allowed_hosts:
        Reserved for future use: list of hostnames that would be exempted from
        the deny rule.  Currently recorded but not enforced at the firewall
        level (rule blocks all outbound traffic).
    dry_run:
        When ``True``, log firewall commands without executing them.  Useful
        for testing on non-Windows CI environments.

    Examples
    --------
    >>> with MembraneGateway(allowed_hosts=[], dry_run=True) as gw:
    ...     pass  # gates run here

    """

    def __init__(
        self,
        allowed_hosts: list[str] | None = None,
        *,
        dry_run: bool = False,
    ) -> None:
        """Initialise the gateway with optional allowed hosts list."""
        self._allowed_hosts: list[str] = allowed_hosts or []
        self._rule_name: str = f"{_RULE_PREFIX}{uuid.uuid4().hex}"
        self._dry_run: bool = dry_run
        self._rule_added: bool = False

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> Self:
        """Activate the network deny rule and return self."""
        self._add_rule()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Remove the network deny rule unconditionally."""
        try:
            self._remove_rule()
        except MembraneError:
            logger.exception("Failed to remove membrane firewall rule '%s'", self._rule_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_windows(self) -> bool:
        """Return ``True`` if running on Windows."""
        return sys.platform == "win32"

    def _run_netsh(self, cmd: list[str]) -> None:
        """Run a netsh command, raising ``MembraneError`` on failure."""
        if self._dry_run:
            logger.info("[DRY-RUN] netsh command: %s", " ".join(cmd))
            return
        try:
            proc = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            msg = f"netsh invocation failed: {exc}"
            raise MembraneError(msg) from exc
        if proc.returncode != 0:
            msg = f"netsh returned {proc.returncode}: {proc.stderr.strip()}"
            raise MembraneError(msg)

    def _add_rule(self) -> None:
        """Add the outbound-block firewall rule."""
        if not self._is_windows():
            logger.info(
                "[Membrane] Non-Windows platform — firewall rule '%s' skipped.",
                self._rule_name,
            )
            self._rule_added = True
            return
        if self._allowed_hosts:
            logger.info(
                "[Membrane] allowed_hosts=%s noted; rule blocks all outbound traffic.",
                self._allowed_hosts,
            )
        cmd = [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={self._rule_name}",
            "dir=out",
            "action=block",
            "protocol=any",
            "enable=yes",
        ]
        self._run_netsh(cmd)
        self._rule_added = True
        logger.info("[Membrane] Added firewall rule '%s'.", self._rule_name)

    def _remove_rule(self) -> None:
        """Remove the outbound-block firewall rule."""
        if not self._rule_added:
            return
        if not self._is_windows():
            logger.info(
                "[Membrane] Non-Windows platform — firewall rule removal skipped.",
            )
            return
        cmd = [
            "netsh",
            "advfirewall",
            "firewall",
            "delete",
            "rule",
            f"name={self._rule_name}",
        ]
        self._run_netsh(cmd)
        logger.info("[Membrane] Removed firewall rule '%s'.", self._rule_name)

    @property
    def rule_name(self) -> str:
        """The unique firewall rule name for this gateway instance."""
        return self._rule_name
