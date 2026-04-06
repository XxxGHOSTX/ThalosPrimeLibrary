"""Deterministic benchmark suite for coherence, reasoning, and retrieval."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from thalos_prime.library_of_sense.reasoning.symbolic_engine import SymbolicReasoningEngine
from thalos_prime.library_of_sense.retrieval.computational import ComputationalRetriever
from thalos_prime.lob_decoder import decode_page

_DEFAULT_OUTPUT = Path("benchmarks/deterministic_benchmarks.json")
_DEFAULT_EXPECTED = Path("benchmarks/deterministic_benchmarks_expected.json")


def _canonical(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _compute_benchmarks() -> dict[str, Any]:
    decoder_result = decode_page(
        address="abc123",
        text="the quick brown fox jumps over the lazy dog. this is deterministic text.",
        query="quick fox deterministic",
        source="local",
    )

    reasoning_engine = SymbolicReasoningEngine()
    reasoning_result = reasoning_engine.reason("2*x + 2*x", context=None)  # type: ignore[arg-type]

    retriever = ComputationalRetriever()
    retrieval_result = retriever.query("2 + 2", context=None)  # type: ignore[arg-type]

    benchmark: dict[str, Any] = {
        "schema_version": "1.0",
        "coherence": {
            "overall_score": round(decoder_result.coherence.overall_score, 6),
            "language_score": round(decoder_result.coherence.language_score, 6),
            "structure_score": round(decoder_result.coherence.structure_score, 6),
            "ngram_score": round(decoder_result.coherence.ngram_score, 6),
            "exact_match_score": round(decoder_result.coherence.exact_match_score, 6),
            "confidence_level": decoder_result.coherence.confidence_level,
        },
        "reasoning": {
            "conclusion": reasoning_result.conclusion,
            "valid": reasoning_result.valid,
            "confidence": round(reasoning_result.confidence, 6),
            "proof_steps": reasoning_result.proof_steps,
        },
        "retrieval": {
            "source": retrieval_result.source,
            "content": retrieval_result.content,
            "confidence": round(retrieval_result.confidence, 6),
            "metadata": retrieval_result.metadata,
        },
    }
    benchmark["replay_hash"] = hashlib.sha256(_canonical(benchmark).encode("utf-8")).hexdigest()
    return benchmark


def run_benchmarks(output: Path, expected: Path | None = None, write_expected: bool = False) -> int:
    """Run deterministic benchmarks and optionally validate against expected snapshot."""
    result = _compute_benchmarks()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    if write_expected:
        if expected is None:
            msg = "--write-expected requires --expected path"
            raise ValueError(msg)
        expected.parent.mkdir(parents=True, exist_ok=True)
        expected.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        return 0

    if expected is not None:
        if not expected.exists():
            msg = f"Expected benchmark snapshot missing: {expected}"
            raise FileNotFoundError(msg)
        expected_payload = json.loads(expected.read_text(encoding="utf-8"))
        if expected_payload != result:
            msg = (
                "Deterministic benchmark mismatch detected. "
                f"Expected {expected}, got {output}."
            )
            raise RuntimeError(msg)
    return 0


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run deterministic benchmarks for Thalos Prime.")
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--expected", type=Path, default=_DEFAULT_EXPECTED)
    parser.add_argument("--write-expected", action="store_true")
    args = parser.parse_args()
    return run_benchmarks(args.output, args.expected, args.write_expected)


if __name__ == "__main__":
    raise SystemExit(main())

