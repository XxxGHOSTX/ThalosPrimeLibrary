"""
PROPRIETARY AND CONFIDENTIAL
Copyright © 2026 Tony Ray Macier III. All Rights Reserved.
This code implements the Thalos Prime Sovereign Discovery Logic.
"""

from collections.abc import Mapping
from typing import Any

# Built-in template strings rendered via str.format_map (not Jinja2)
TEMPLATES: dict[str, str] = {
    "firewall_rule": (
        "# Thalos Prime Auto-Generated Firewall Rule\n"
        "# Rule ID: {rule_id} | Seed: {seed}\n"
        "# © 2026 Tony Ray Macier III\n"
        "deny outbound tcp to {blocked_endpoint} comment 'Shadow AI block - Thalos Prime'\n"
    ),
    "code_patch": (
        "# Thalos Prime Auto-Generated Patch\n"
        "# Patch Hash: {patch_hash} | Seed: {seed}\n"
        "# Vulnerability: {vulnerability}\n"
        "# © 2026 Tony Ray Macier III\n"
        "# Apply this patch to remediate the identified shadow AI vulnerability.\n"
    ),
}


class TemplateFactory:
    """Sovereign template factory for deterministic artifact generation."""

    def render(self, template_name: str, context: Mapping[str, Any]) -> str:
        """Render a named template with the given context.

        Args:
            template_name: Name of the template to render.
            context: Mapping of variable names to values for substitution.

        Returns:
            The rendered template string.

        Raises:
            ValueError: If the template name is unknown.
        """
        if template_name not in TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")
        return TEMPLATES[template_name].format_map(context)

    def list_templates(self) -> list[str]:
        """Return a list of all registered template names."""
        return list(TEMPLATES.keys())
