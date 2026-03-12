"""RBAC (Role-Based Access Control) for infra-synthesis.

Defines a static role map and a deterministic permission check function.
No dynamic role assignment or mutation is performed at runtime.

Control Plane: access enforcement only.
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

# Role → frozenset of granted permissions.
ROLE_MAP: Final[dict[str, frozenset[str]]] = {
    "admin": frozenset({
        "build",
        "verify",
        "deploy",
        "rollback",
        "manage_secrets",
        "manage_policies",
        "manage_users",
        "audit_read",
    }),
    "devops": frozenset({
        "build",
        "verify",
        "deploy",
        "rollback",
        "manage_secrets",
        "audit_read",
    }),
    "developer": frozenset({
        "build",
        "verify",
        "audit_read",
    }),
}


def check(role: str, permission: str) -> bool:
    """Return ``True`` when *role* grants *permission*.

    Args:
        role: Role identifier (e.g. ``"admin"``, ``"devops"``, ``"developer"``).
        permission: Permission string to check (e.g. ``"deploy"``).

    Returns:
        ``True`` when the role is registered and grants the permission.

    """
    granted = ROLE_MAP.get(role, frozenset())
    result = permission in granted
    if result:
        logger.debug("RBAC: role='%s' permission='%s' -> GRANTED", role, permission)
    else:
        logger.warning("RBAC: role='%s' permission='%s' -> DENIED", role, permission)
    return result


__all__ = ["ROLE_MAP", "check"]
