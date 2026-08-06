"""Claim Intermediate Representation and deterministic claim compilation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClaimModality(StrEnum):
    """Epistemic modality assigned during claim compilation."""

    ASSERTION = "assertion"
    NEGATION = "negation"
    POSSIBILITY = "possibility"
    NECESSITY = "necessity"
    PREDICTION = "prediction"
    QUESTION = "question"
    UNKNOWN = "unknown"


class ClaimType(StrEnum):
    """Coarse semantic class used to select verification programs."""

    FACTUAL = "factual"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    COMPARATIVE = "comparative"
    IDENTITY = "identity"
    STATISTICAL = "statistical"
    LEGAL = "legal"
    SCIENTIFIC = "scientific"
    PREDICTIVE = "predictive"
    NORMATIVE = "normative"
    UNKNOWN = "unknown"


class ClaimIR(BaseModel):
    """Canonical intermediate representation for an atomic proposition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    source_text: str
    canonical_text: str
    claim_type: ClaimType = ClaimType.UNKNOWN
    modality: ClaimModality = ClaimModality.UNKNOWN
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    qualifiers: tuple[tuple[str, str], ...] = Field(default_factory=tuple)
    compiler_version: str = "claim-ir-v1"


@dataclass(frozen=True)
class CompilationResult:
    """Deterministic result of compiling one user statement."""

    claim: ClaimIR
    warnings: tuple[str, ...] = ()


class ClaimCompiler:
    """Conservative compiler from natural language to Claim IR.

    This is intentionally not a general semantic parser. It provides a stable
    baseline that preserves uncertainty rather than inventing structure. A
    model-assisted parser may enrich the IR later, but enriched fields must be
    explicitly marked as proposals and recompiled through validation.
    """

    VERSION = "claim-ir-v1"

    _QUESTION_PREFIXES = ("is ", "are ", "was ", "were ", "did ", "does ", "do ", "can ", "could ", "will ")
    _NEGATION_TOKENS = ("not ", "never ", "no ", "isn't", "wasn't", "didn't", "doesn't", "don't")
    _CAUSAL_MARKERS = (" caused ", " causes ", " led to ", " resulted in ", " because ", " due to ")
    _PREDICTIVE_MARKERS = ("will ", "expected to ", "projected to ", "forecast to ")
    _TEMPORAL_PATTERN = re.compile(r"\b(\d{4}(?:-\d{2}(?:-\d{2})?)?)\b")

    @classmethod
    def compile(
        cls,
        text: str,
        *,
        claim_type: ClaimType | None = None,
        subject: str | None = None,
        predicate: str | None = None,
        object: str | None = None,
        valid_from: str | None = None,
        valid_to: str | None = None,
    ) -> CompilationResult:
        canonical = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split()).strip()
        if not canonical:
            raise ValueError("Claim text must not be empty")

        lowered = canonical.lower()
        modality = cls._infer_modality(lowered)
        inferred_type = claim_type or cls._infer_type(lowered, modality)
        inferred_from, inferred_to = cls._infer_temporal_scope(canonical)

        start = valid_from if valid_from is not None else inferred_from
        end = valid_to if valid_to is not None else inferred_to
        qualifiers: list[tuple[str, str]] = []
        if start:
            qualifiers.append(("valid_from", start))
        if end:
            qualifiers.append(("valid_to", end))

        identity = {
            "canonical_text": canonical,
            "claim_type": inferred_type.value,
            "modality": modality.value,
            "subject": subject,
            "predicate": predicate,
            "object": object,
            "valid_from": start,
            "valid_to": end,
            "qualifiers": qualifiers,
            "compiler_version": cls.VERSION,
        }
        claim_id = "clmir:" + hashlib.sha256(
            json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        warnings: list[str] = []
        if modality is ClaimModality.UNKNOWN:
            warnings.append("modality could not be inferred; treating as unknown")
        if inferred_type is ClaimType.UNKNOWN:
            warnings.append("claim type could not be inferred; verification planning must remain conservative")
        if subject is None or predicate is None or object is None:
            warnings.append("semantic slots are incomplete; no world-state interpretation is assumed")

        return CompilationResult(
            claim=ClaimIR(
                claim_id=claim_id,
                source_text=text,
                canonical_text=canonical,
                claim_type=inferred_type,
                modality=modality,
                subject=subject,
                predicate=predicate,
                object=object,
                valid_from=start,
                valid_to=end,
                qualifiers=tuple(qualifiers),
                compiler_version=cls.VERSION,
            ),
            warnings=tuple(warnings),
        )

    @classmethod
    def _infer_modality(cls, lowered: str) -> ClaimModality:
        if lowered.endswith("?") or lowered.startswith(cls._QUESTION_PREFIXES):
            return ClaimModality.QUESTION
        if any(marker in lowered for marker in cls._PREDICTIVE_MARKERS):
            return ClaimModality.PREDICTION
        if any(token in lowered for token in cls._NEGATION_TOKENS):
            return ClaimModality.NEGATION
        return ClaimModality.ASSERTION

    @classmethod
    def _infer_type(cls, lowered: str, modality: ClaimModality) -> ClaimType:
        if modality is ClaimModality.PREDICTION:
            return ClaimType.PREDICTIVE
        if any(marker in lowered for marker in cls._CAUSAL_MARKERS):
            return ClaimType.CAUSAL
        if " statistically " in f" {lowered} ":
            return ClaimType.STATISTICAL
        if any(token in lowered for token in ("legal", "lawful", "unlawful", "court", "statute")):
            return ClaimType.LEGAL
        if any(token in lowered for token in ("study", "experiment", "scientific", "clinical")):
            return ClaimType.SCIENTIFIC
        if cls._TEMPORAL_PATTERN.search(lowered):
            return ClaimType.TEMPORAL
        return ClaimType.FACTUAL

    @classmethod
    def _infer_temporal_scope(cls, text: str) -> tuple[str | None, str | None]:
        years = cls._TEMPORAL_PATTERN.findall(text)
        if not years:
            return None, None
        if len(years) == 1:
            return years[0], years[0]
        return years[0], years[-1]


# Small helper used by external callers that need deterministic serialization.
def claim_fingerprint(claim: ClaimIR) -> str:
    payload: dict[str, Any] = claim.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
