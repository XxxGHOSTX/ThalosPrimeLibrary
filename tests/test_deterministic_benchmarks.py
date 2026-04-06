"""Tests for deterministic benchmark suite."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_deterministic_benchmarks import run_benchmarks


def test_benchmark_script_writes_and_matches_expected(tmp_path: Path) -> None:
    output = tmp_path / "bench.json"
    expected = tmp_path / "expected.json"
    run_benchmarks(output=output, expected=expected, write_expected=True)
    rc = run_benchmarks(output=output, expected=expected, write_expected=False)
    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert "replay_hash" in payload
    assert "coherence" in payload
    assert "reasoning" in payload
    assert "retrieval" in payload

