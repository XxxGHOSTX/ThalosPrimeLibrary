"""Determinism tests for Babel subsystem."""

from __future__ import annotations

from pathlib import Path

from thalos_prime.babel.control.semantic_orchestrator import SemanticOrchestrator


def test_identical_inputs_produce_identical_outputs(temp_storage: Path) -> None:
    orch1 = SemanticOrchestrator(temp_storage / "run1")
    orch1.initialize()
    orch2 = SemanticOrchestrator(temp_storage / "run2")
    orch2.initialize()

    prompts = ["what is determinism?", "describe the system."]
    for prompt in prompts:
        r1 = orch1.handle_semantic_input(prompt, "s1")
        r2 = orch2.handle_semantic_input(prompt, "s2")
        assert r1.text == r2.text
        assert r1.coordinate.as_string() == r2.coordinate.as_string()


def test_repeated_question_produces_different_variations(test_orchestrator: SemanticOrchestrator) -> None:
    prompt = "what is a system?"
    outputs = [test_orchestrator.handle_semantic_input(prompt, "session") for _ in range(3)]
    texts = [o.text for o in outputs]
    assert len(set(texts)) > 1


def test_variation_sequence_is_reproducible(temp_storage: Path) -> None:
    prompt = "what is determinism?"
    orch_a = SemanticOrchestrator(temp_storage / "a")
    orch_a.initialize()
    seq_a = [orch_a.handle_semantic_input(prompt, "session") for _ in range(3)]

    orch_b = SemanticOrchestrator(temp_storage / "b")
    orch_b.initialize()
    seq_b = [orch_b.handle_semantic_input(prompt, "session") for _ in range(3)]

    for a, b in zip(seq_a, seq_b, strict=True):
        assert a.text == b.text
        assert a.coordinate.as_string() == b.coordinate.as_string()
