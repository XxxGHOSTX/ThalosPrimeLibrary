"""
Output formatting helpers.
"""

from __future__ import annotations

from ..core.response_generator import GeneratedResponse


class OutputFormatter:
    @staticmethod
    def format_response(response: GeneratedResponse, verbose: bool = False) -> str:
        lines = [f"Babel: {response.text}"]
        if verbose:
            lines.append("[Metadata]")
            lines.append(f"Coordinate: {response.coordinate}")
            lines.append(f"Template: {response.template_used}")
            lines.append(f"Frame: {response.frame.frame_type.name}")
            lines.append(f"Semantic preserved: {response.semantic_preserved}")
            lines.append(f"Coherent: {response.coherence_report.is_coherent}")
        return "\n".join(lines)
