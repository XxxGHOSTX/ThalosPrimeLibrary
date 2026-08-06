"""Warrant Algebra and epistemic-conservation transfer rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import prod
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field


class WarrantOperation(StrEnum):
    """Explicit transformation type for epistemic warrant."""

    COPY = "copy"
    PARAPHRASE = "paraphrase"
    SUMMARIZE = "summarize"
    DEDUCE = "deduce"
    CORROBORATE = "corroborate"
    CONTRADICT = "contradict"
    SPECULATE = "speculate"


class Warrant(BaseModel):
    """Multi-dimensional warrant state; never reduced to one confidence scalar."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    support: float = Field(ge=0.0, le=1.0)
    contradiction: float = Field(ge=0.0, le=1.0)
    entailment: float = Field(ge=0.0, le=1.0)
    temporal_validity: float = Field(ge=0.0, le=1.0)
    scope_validity: float = Field(ge=0.0, le=1.0)
    independence: float = Field(ge=0.0, le=1.0)
    provenance_integrity: float = Field(ge=0.0, le=1.0)
    reproducibility: float = Field(ge=0.0, le=1.0)
    falsifiability: float = Field(ge=0.0, le=1.0)

    @property
    def usable_support(self) -> float:
        """Support usable for a decision without hiding individual dimensions."""
        return min(
            self.support,
            self.entailment,
            self.temporal_validity,
            self.scope_validity,
            self.independence,
            self.provenance_integrity,
        )

    @property
    def conflict_index(self) -> float:
        """Explicit conflict measure; support is never silently canceled."""
        return min(1.0, self.contradiction)


@dataclass(frozen=True)
class WarrantTransfer:
    """Audit record for an epistemic transformation."""

    operation: WarrantOperation
    input_warrant: Warrant
    output_warrant: Warrant
    rule_id: str
    explanation: str

    @property
    def conserved(self) -> bool:
        """Whether the transfer obeyed the no-free-warrant invariant."""
        return self.output_warrant.usable_support <= self.input_warrant.usable_support + 1e-12


class WarrantAlgebra:
    """Apply explicit, replayable warrant transformations.

    The central invariant is epistemic conservation: a transformation cannot
    create stronger usable support without an explicit operation that introduces
    new independent evidence or a formally valid inference rule.
    """

    @staticmethod
    def copy(warrant: Warrant) -> WarrantTransfer:
        return WarrantTransfer(
            operation=WarrantOperation.COPY,
            input_warrant=warrant,
            output_warrant=warrant,
            rule_id="warrant.copy.v1",
            explanation="Identity transformation; no warrant is created or destroyed.",
        )

    @staticmethod
    def paraphrase(warrant: Warrant, fidelity: float = 1.0) -> WarrantTransfer:
        fidelity = _clamp(fidelity)
        output = warrant.model_copy(update={
            "support": min(warrant.support, fidelity),
            "entailment": min(warrant.entailment, fidelity),
        })
        return WarrantTransfer(
            operation=WarrantOperation.PARAPHRASE,
            input_warrant=warrant,
            output_warrant=output,
            rule_id="warrant.paraphrase.v1",
            explanation="Paraphrase cannot increase warrant; imperfect fidelity may reduce it.",
        )

    @staticmethod
    def summarize(warrant: Warrant, retention: float) -> WarrantTransfer:
        retention = _clamp(retention)
        output = warrant.model_copy(update={
            "support": warrant.support * retention,
            "entailment": warrant.entailment * retention,
            "scope_validity": warrant.scope_validity * retention,
        })
        return WarrantTransfer(
            operation=WarrantOperation.SUMMARIZE,
            input_warrant=warrant,
            output_warrant=output,
            rule_id="warrant.summarize.v1",
            explanation="Summarization can omit qualifiers and therefore cannot improve warrant.",
        )

    @staticmethod
    def deduce(premises: Iterable[Warrant], formal_validity: float) -> WarrantTransfer:
        items = tuple(premises)
        if not items:
            raise ValueError("Deduction requires at least one premise")
        validity = _clamp(formal_validity)
        premise_support = min(item.usable_support for item in items)
        contradiction = max(item.contradiction for item in items)
        output_support = min(premise_support, validity)
        output = Warrant(
            support=output_support,
            contradiction=contradiction,
            entailment=validity,
            temporal_validity=min(item.temporal_validity for item in items),
            scope_validity=min(item.scope_validity for item in items),
            independence=min(item.independence for item in items),
            provenance_integrity=min(item.provenance_integrity for item in items),
            reproducibility=min(item.reproducibility for item in items),
            falsifiability=min(item.falsifiability for item in items),
        )
        aggregate = _aggregate_warrant(items)
        return WarrantTransfer(
            operation=WarrantOperation.DEDUCE,
            input_warrant=aggregate,
            output_warrant=output,
            rule_id="warrant.deduce.v1",
            explanation="Formal deduction is bounded by the weakest usable premise and formal validity.",
        )

    @staticmethod
    def corroborate(warrants: Iterable[Warrant], independence: float) -> WarrantTransfer:
        items = tuple(warrants)
        if not items:
            raise ValueError("Corroboration requires at least one witness")
        independence = _clamp(independence)
        base = _aggregate_warrant(items)
        marginal = 1.0 - prod(1.0 - _clamp(item.usable_support) for item in items)
        output_support = min(1.0, base.support + (marginal - base.support) * independence)
        output = base.model_copy(update={
            "support": output_support,
            "independence": independence,
        })
        return WarrantTransfer(
            operation=WarrantOperation.CORROBORATE,
            input_warrant=base,
            output_warrant=output,
            rule_id="warrant.corroborate.v1",
            explanation="Independent corroboration may add warrant; correlated witnesses contribute less.",
        )

    @staticmethod
    def contradict(warrant: Warrant, contradiction_strength: float) -> WarrantTransfer:
        contradiction_strength = _clamp(contradiction_strength)
        output = warrant.model_copy(update={
            "contradiction": max(warrant.contradiction, contradiction_strength),
        })
        return WarrantTransfer(
            operation=WarrantOperation.CONTRADICT,
            input_warrant=warrant,
            output_warrant=output,
            rule_id="warrant.contradict.v1",
            explanation="Counterevidence increases explicit contradiction rather than deleting support.",
        )

    @staticmethod
    def speculate(warrant: Warrant) -> WarrantTransfer:
        output = warrant.model_copy(update={
            "support": 0.0,
            "entailment": 0.0,
            "provenance_integrity": min(warrant.provenance_integrity, 0.25),
        })
        return WarrantTransfer(
            operation=WarrantOperation.SPECULATE,
            input_warrant=warrant,
            output_warrant=output,
            rule_id="warrant.speculate.v1",
            explanation="A hypothesis is useful for search but does not inherit factual warrant automatically.",
        )


def _aggregate_warrant(items: tuple[Warrant, ...]) -> Warrant:
    return Warrant(
        support=max(item.support for item in items),
        contradiction=max(item.contradiction for item in items),
        entailment=min(item.entailment for item in items),
        temporal_validity=min(item.temporal_validity for item in items),
        scope_validity=min(item.scope_validity for item in items),
        independence=min(item.independence for item in items),
        provenance_integrity=min(item.provenance_integrity for item in items),
        reproducibility=min(item.reproducibility for item in items),
        falsifiability=max(item.falsifiability for item in items),
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
