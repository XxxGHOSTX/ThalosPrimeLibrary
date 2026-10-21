"""Tests for the standalone discovery and finite-domain solver CLIs."""

from __future__ import annotations

import json

from thalos_prime.discovery.solver_cli import main as solve_main


def test_solver_cli_writes_a_feasibility_report(tmp_path) -> None:
    source = tmp_path / "problem.json"
    target = tmp_path / "report.json"
    source.write_text(json.dumps({
        "problem_id": "cli-test",
        "variables": [{"name": "x", "domain": [0, 1, 2]}],
        "constraints": [
            {"name": "min", "left_variable": "x", "operator": "ge", "right_value": 2},
            {"name": "max", "left_variable": "x", "operator": "le", "right_value": 0},
        ],
    }), encoding="utf-8")
    assert solve_main(["--input", str(source), "--output", str(target)]) == 0
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["verification_status"] == "finite_domain_unsatisfiable"
    assert set(report["conflict_core"]) == {"min", "max"}


def test_discovery_cli_limit_overrides_json(tmp_path) -> None:
    from thalos_prime.discovery.cli import main as discover_main

    source = tmp_path / "problem.json"
    target = tmp_path / "report.json"
    source.write_text(json.dumps({
        "question": "capacity bottleneck feedback threshold",
        "max_hypotheses": 5,
    }), encoding="utf-8")
    assert discover_main([
        "--input", str(source), "--max-hypotheses", "1", "--output", str(target),
    ]) == 0
    report = json.loads(target.read_text(encoding="utf-8"))
    assert len(report["hypotheses"]) == 1


def test_discovery_cli_rejects_null_question_without_traceback(tmp_path, capsys) -> None:
    from thalos_prime.discovery.cli import main as discover_main

    source = tmp_path / "bad.json"
    source.write_text('{"question": null}', encoding="utf-8")
    assert discover_main(["--input", str(source)]) == 2
    assert "question must be a string" in capsys.readouterr().err
