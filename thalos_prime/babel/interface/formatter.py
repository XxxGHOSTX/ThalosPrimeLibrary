"""Output formatting helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thalos_prime.babel.core.response_generator import GeneratedResponse


class OutputFormatter:
    """Format generated responses for terminal or API output."""

    @staticmethod
    def format_response(response: GeneratedResponse, *, verbose: bool = False) -> str:
        """Format *response* as a human-readable string, including metadata when *verbose*."""
        lines = [f"Babel: {response.text}"]
        if verbose:
            lines.append("[Metadata]")
            lines.append(f"Coordinate: {response.coordinate}")
            lines.append(f"Template: {response.template_used}")
            lines.append(f"Frame: {response.frame.frame_type.name}")
            lines.append(f"Semantic preserved: {response.semantic_preserved}")
            lines.append(f"Coherent: {response.coherence_report.is_coherent}")
        return "\n".join(lines)
