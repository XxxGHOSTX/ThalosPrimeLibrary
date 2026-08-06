"""Witness Calculus for causal independence and source genealogy."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field


class WitnessKind(StrEnum):
    """Origin kind of a witness."""

    OBSERVATION = "observation"
    DOCUMENT = "document"
    TESTIMONY = "testimony"
    RECORD = "record"
    MEASUREMENT = "measurement"
    DERIVED = "derived"
    USER_ASSERTION = "user_assertion"
    SYNTHETIC = "synthetic"


class Witness(BaseModel):
    """A source-level witness with explicit causal ancestry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    witness_id: str
    artifact_id: str
    kind: WitnessKind
    issuer: str | None = None
    observation_time: str | None = None
    acquisition_time: str | None = None
    parent_witness_ids: tuple[str, ...] = Field(default_factory=tuple)
    independence_group: str | None = None
    eligible: bool = True

    @classmethod
    def create(
        cls,
        artifact_id: str,
        kind: WitnessKind,
        *,
        issuer: str | None = None,
        observation_time: str | None = None,
        acquisition_time: str | None = None,
        parent_witness_ids: Iterable[str] = (),
        independence_group: str | None = None,
        eligible: bool = True,
    ) -> "Witness":
        parents = tuple(sorted(set(parent_witness_ids)))
        identity = {
            "artifact_id": artifact_id,
            "kind": kind.value,
            "issuer": issuer,
            "observation_time": observation_time,
            "acquisition_time": acquisition_time,
            "parent_witness_ids": parents,
            "independence_group": independence_group,
            "eligible": eligible,
        }
        digest = hashlib.sha256(
            json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            witness_id=f"wit:{digest}",
            artifact_id=artifact_id,
            kind=kind,
            issuer=issuer,
            observation_time=observation_time,
            acquisition_time=acquisition_time,
            parent_witness_ids=parents,
            independence_group=independence_group,
            eligible=eligible,
        )


@dataclass(frozen=True)
class WitnessAnalysis:
    """Deterministic result of grouping witnesses by causal ancestry."""

    eligible_witness_ids: tuple[str, ...]
    independent_groups: tuple[tuple[str, tuple[str, ...]], ...]
    root_lineages: tuple[tuple[str, tuple[str, ...]], ...]
    independence_score: float
    correlation_penalty: float


class WitnessCalculus:
    """Compute causal witness diversity rather than counting documents."""

    def __init__(self, witnesses: Iterable[Witness]) -> None:
        self._witnesses = {w.witness_id: w for w in witnesses}
        self._validate_acyclic()

    def analyze(self, witness_ids: Iterable[str]) -> WitnessAnalysis:
        selected = tuple(sorted(set(witness_ids)))
        eligible = tuple(
            wid for wid in selected if wid in self._witnesses and self._witnesses[wid].eligible
        )
        groups: dict[str, list[str]] = {}
        roots: dict[str, set[str]] = {}
        for wid in eligible:
            witness = self._witnesses[wid]
            group = witness.independence_group or self._root_signature(wid)
            groups.setdefault(group, []).append(wid)
            for root in self._roots(wid):
                roots.setdefault(root, set()).add(wid)

        group_items = tuple((key, tuple(sorted(value))) for key, value in sorted(groups.items()))
        root_items = tuple((key, tuple(sorted(value))) for key, value in sorted(roots.items()))
        n = len(eligible)
        independent = len(group_items)
        root_count = len(root_items)
        independence_score = 0.0 if n == 0 else min(1.0, (independent + root_count) / (2.0 * n))
        correlation_penalty = 0.0 if n == 0 else 1.0 - (independent / n)
        return WitnessAnalysis(
            eligible_witness_ids=eligible,
            independent_groups=group_items,
            root_lineages=root_items,
            independence_score=round(independence_score, 6),
            correlation_penalty=round(correlation_penalty, 6),
        )

    def _roots(self, witness_id: str, trail: tuple[str, ...] = ()) -> set[str]:
        if witness_id in trail:
            raise ValueError("Witness genealogy contains a cycle")
        witness = self._witnesses[witness_id]
        if not witness.parent_witness_ids:
            return {witness_id}
        roots: set[str] = set()
        for parent in witness.parent_witness_ids:
            if parent not in self._witnesses:
                raise ValueError(f"Unknown parent witness: {parent}")
            roots.update(self._roots(parent, trail + (witness_id,)))
        return roots

    def _root_signature(self, witness_id: str) -> str:
        roots = sorted(self._roots(witness_id))
        payload = json.dumps(roots, separators=(",", ":"))
        return "root:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _validate_acyclic(self) -> None:
        for witness_id in self._witnesses:
            self._roots(witness_id)
