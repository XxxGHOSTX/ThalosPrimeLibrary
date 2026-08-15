"""Provider-neutral LLM proposal interface.

The adapter returns source text only. Repository mutation remains the responsibility
of the autonomous evolution pipeline, where policy and tests can reject it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CodeProposal:
    source: str
    rationale: str = ""
    model: str = "unknown"


class CodeProposalProvider(Protocol):
    def propose(self, *, source: str, objective: str, context: str = "") -> CodeProposal:
        """Return a candidate implementation without applying it."""


class DisabledProvider:
    """Default provider that makes autonomous LLM generation opt-in."""

    def propose(self, *, source: str, objective: str, context: str = "") -> CodeProposal:
        raise RuntimeError("no code-generation provider configured")


class OpenAICompatibleProvider:
    """Small adapter for OpenAI-compatible clients supplied by the host application."""

    def __init__(self, client: object, model: str) -> None:
        self.client = client
        self.model = model

    def propose(self, *, source: str, objective: str, context: str = "") -> CodeProposal:
        prompt = (
            "Return only a complete replacement for the supplied Python source. "
            "Preserve the public interface. Do not add network access, shell execution, "
            "credential handling, or self-triggering automation.\n\n"
            f"Objective: {objective}\nContext: {context}\n\nSource:\n{source}"
        )
        responses = getattr(self.client, "responses", None)
        if responses is None or not hasattr(responses, "create"):
            raise TypeError("client must expose responses.create")
        response = responses.create(model=self.model, input=prompt)
        output = getattr(response, "output_text", None)
        if not output:
            raise ValueError("LLM provider returned no output text")
        return CodeProposal(source=str(output).strip(), model=self.model)
