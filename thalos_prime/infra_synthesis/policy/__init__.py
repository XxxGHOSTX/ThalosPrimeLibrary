"""Policy sub-package for infra-synthesis.

Exports the PolicyEngine, rule registry accessor, and built-in rule names.
"""

from __future__ import annotations

from thalos_prime.infra_synthesis.policy.engine import (
    PolicyEngine,
    PolicyResult,
    PolicyRule,
    register_rule,
)

__all__ = [
    "PolicyEngine",
    "PolicyResult",
    "PolicyRule",
    "register_rule",
]
