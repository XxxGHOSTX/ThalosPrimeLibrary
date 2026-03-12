"""Policy engine for infra-synthesis.

Evaluates named rules against a schema dict and returns a structured
verdict.  Rules are registered in a global registry and can be queried
or extended by name.

Control Plane: policy enforcement only; no resource generation.

Built-in rules
--------------
* ``require_ssl`` — ``network.protocol`` must be ``"https"``.
* ``limit_scaling`` — ``compute.scaling`` must be ≤ 50.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Rule signature: receives schema dict, returns (passed: bool, message: str)
PolicyRule = Callable[[dict[str, Any]], tuple[bool, str]]

# Global rule registry mapping rule names to callables.
_RULE_REGISTRY: dict[str, PolicyRule] = {}


def register_rule(name: str, rule: PolicyRule) -> None:
    """Register a policy rule under *name*.

    Args:
        name: Unique rule identifier.
        rule: Callable that accepts a schema dict and returns ``(bool, str)``.

    Raises:
        ValueError: When *name* is already registered.

    """
    if name in _RULE_REGISTRY:
        msg = f"Policy rule '{name}' is already registered"
        raise ValueError(msg)
    _RULE_REGISTRY[name] = rule
    logger.debug("PolicyEngine: registered rule '%s'", name)


def _rule_require_ssl(schema: dict[str, Any]) -> tuple[bool, str]:
    protocol = schema.get("network", {}).get("protocol", "")
    if protocol == "https":
        return True, "require_ssl: PASSED — network.protocol is 'https'"
    return (
        False,
        f"require_ssl: FAILED — network.protocol must be 'https'; got '{protocol}'",
    )


def _rule_limit_scaling(schema: dict[str, Any]) -> tuple[bool, str]:
    scaling = schema.get("compute", {}).get("scaling")
    if scaling is None:
        return True, "limit_scaling: PASSED — no scaling value specified"
    if not isinstance(scaling, int):
        return False, f"limit_scaling: FAILED — compute.scaling must be an integer; got {type(scaling).__name__}"
    if scaling <= 50:
        return True, f"limit_scaling: PASSED — compute.scaling={scaling} ≤ 50"
    return False, f"limit_scaling: FAILED — compute.scaling={scaling} exceeds maximum of 50"


# Register built-in rules at import time.
register_rule("require_ssl", _rule_require_ssl)
register_rule("limit_scaling", _rule_limit_scaling)


@dataclass
class PolicyResult:
    """Result of policy evaluation.

    Attributes:
        passed: True only when every evaluated rule passes.
        results: Per-rule ``(passed, message)`` tuples.

    """

    passed: bool
    results: list[tuple[str, bool, str]] = field(default_factory=list)


class PolicyEngine:
    """Evaluates registered policy rules against a schema dict.

    By default all registered rules are evaluated; pass *rules* to
    restrict evaluation to a subset.
    """

    def evaluate(
        self,
        schema: dict[str, Any],
        rules: list[str] | None = None,
    ) -> PolicyResult:
        """Evaluate *rules* (or all registered rules) against *schema*.

        Args:
            schema: Validated infrastructure schema dict.
            rules: Optional list of rule names to evaluate.  When ``None``
                   all registered rules are evaluated.

        Returns:
            :class:`PolicyResult` with per-rule outcomes.

        Raises:
            KeyError: When a requested rule name is not registered.

        """
        to_run: dict[str, PolicyRule]
        if rules is None:
            to_run = dict(_RULE_REGISTRY)
        else:
            to_run = {}
            for name in rules:
                if name not in _RULE_REGISTRY:
                    msg = f"Policy rule '{name}' is not registered"
                    raise KeyError(msg)
                to_run[name] = _RULE_REGISTRY[name]

        results: list[tuple[str, bool, str]] = []
        all_passed = True
        for name, rule in to_run.items():
            passed, message = rule(schema)
            results.append((name, passed, message))
            if passed:
                logger.debug("Policy rule '%s': PASSED", name)
            else:
                logger.warning("Policy rule '%s': FAILED — %s", name, message)
                all_passed = False

        return PolicyResult(passed=all_passed, results=results)


__all__ = ["PolicyEngine", "PolicyResult", "PolicyRule", "register_rule"]
