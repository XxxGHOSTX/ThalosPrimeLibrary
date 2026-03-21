"""Semantic preservation tests for Babel subsystem."""

from __future__ import annotations

from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator


def test_semantic_preservation_flags(test_orchestrator: SemanticOrchestrator) -> None:
    responses = [test_orchestrator.handle_semantic_input("what is determinism?", "s") for _ in range(3)]
    for response in responses:
        assert response.semantic_preserved is True
        assert response.coherence_report.is_coherent is True


def test_coherence_has_no_violations(test_orchestrator: SemanticOrchestrator) -> None:
    response = test_orchestrator.handle_semantic_input("describe system", "s2")
    assert response.coherence_report.is_coherent is True
    assert response.coherence_report.violations == []
