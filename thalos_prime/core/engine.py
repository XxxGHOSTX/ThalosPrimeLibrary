"""Canonical Thalos execution spine."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from thalos_prime.core.artifact import Artifact, ArtifactCandidate
from thalos_prime.pipeline import (
    build_plan,
    derive_constraints,
    extract_intent,
    generate_candidates,
    score_candidates,
    synthesize_research,
    validate_candidates,
)

# Two deterministic passes are the minimum required to detect convergence and
# expose oscillation (`stable` true only when both selected IDs match).
_STABILIZATION_CYCLES = 2


def _as_float(value: object) -> float:
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    msg = f"Unsupported numeric value type: {type(value)!r}"
    raise TypeError(msg)


@dataclass(frozen=True)
class EngineConfig:
    """Configuration for canonical engine execution."""

    seed: int = 2026
    version: str = "engine-v1"
    max_candidates: int = 5
    mode: str = "hybrid"
    intent_override: str | None = None


class ThalosEngine:
    """Canonical single-spine engine for chat/search/design execution."""

    def run(self, input_text: str, config: EngineConfig) -> Artifact:
        """Execute the canonical deterministic pipeline."""
        intent = extract_intent(input_text, intent_override=config.intent_override)
        research = synthesize_research(input_text, max_results=config.max_candidates)
        constraints = derive_constraints(input_text, intent=intent)

        provenance_trace: list[dict[str, object]] = []
        cycle_selected_ids: list[str] = []
        cycle_candidates: list[dict[str, object]] = []
        latest_metrics: dict[str, float] = {
            "selected_score": 0.0,
            "baseline_text_to_address": 0.0,
            "baseline_sha256_chain": 0.0,
            "baseline_mean": 0.0,
            "purity_functional": 0.0,
        }

        for cycle_index in range(_STABILIZATION_CYCLES):
            candidates = generate_candidates(
                input_text,
                max_candidates=config.max_candidates,
                mode=config.mode,
                cycle_index=cycle_index,
            )
            validated = validate_candidates(candidates, constraints=constraints)
            scored, latest_metrics = score_candidates(validated, input_text=input_text)
            cycle_candidates = scored
            selected = scored[0]
            selected_id = str(selected["candidate_id"])
            cycle_selected_ids.append(selected_id)
            provenance_trace.append(
                {
                    "cycle": cycle_index,
                    "selected_id": selected_id,
                    "selected_score": _as_float(selected["score"]),
                    "mode": config.mode,
                },
            )

        stabilization = {
            "cycles": len(cycle_selected_ids),
            "selected_ids": cycle_selected_ids,
            "stable": len(set(cycle_selected_ids)) == 1,
            "hash": sha256(":".join(cycle_selected_ids).encode("utf-8")).hexdigest(),
        }

        artifact_candidates = [
            ArtifactCandidate.model_validate(candidate) for candidate in cycle_candidates
        ]
        selected_candidate = artifact_candidates[0]
        plan = build_plan(
            selected_candidate=selected_candidate.model_dump(),
            intent=intent,
            constraints=constraints,
        )

        return Artifact(
            input=input_text,
            intent=intent,
            research=research,
            constraints=constraints,
            candidates=artifact_candidates,
            selected=selected_candidate,
            plan=plan,
            seed=config.seed,
            version=config.version,
            purity_metrics=latest_metrics,
            provenance_trace=provenance_trace,
            stabilization=stabilization,
        )
