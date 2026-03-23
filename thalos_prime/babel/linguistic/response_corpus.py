"""Response template corpus."""

from __future__ import annotations

from .semantic_frames import FrameType


class ResponseCorpus:
    """Deterministic response templates per frame type."""

    def __init__(self) -> None:
        """Initialize the built-in deterministic template corpus."""
        self._templates: dict[FrameType, list[str]] = {
            FrameType.DEFINITION: [
                "{DEFINIENDUM} is defined by stable properties in this system.",
                "The topic {DEFINIENDUM} follows deterministic behavior.",
                "For {DEFINIENDUM}, deterministic rules apply consistently.",
            ],
            FrameType.ACKNOWLEDGMENT: [
                "{MESSAGE}. All state captured deterministically.",
                "{MESSAGE}. Proceeding with consistent state handling.",
            ],
            FrameType.DESCRIPTION: [
                "{SUBJECT} is recorded with detail: {DETAIL}.",
                "The subject {SUBJECT} remains consistent; detail: {DETAIL}.",
            ],
            FrameType.GENERIC: [
                "This system responds deterministically to provided input.",
            ],
        }

    def get_templates_for_frame(self, frame_type: FrameType) -> list[str]:
        """Return the templates for *frame_type*.

        Args:
            frame_type: Frame type to retrieve templates for.

        Returns:
            List of templates; falls back to GENERIC when missing.

        """
        return self._templates.get(frame_type, self._templates[FrameType.GENERIC])
