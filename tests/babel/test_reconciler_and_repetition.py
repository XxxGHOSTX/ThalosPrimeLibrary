"""Tests for Reconciler and RepetitionDetector to cover previously uncovered lines."""

from __future__ import annotations

import pytest

from thalos_prime.babel.control.reconciler import Inconsistency, Reconciler
from thalos_prime.babel.linguistic.repetition_detector import RepetitionDetector


class TestReconciler:
    """Unit tests for Reconciler.check_state() and Reconciler.resolve()."""

    def test_check_state_no_coordinate_returns_empty(self) -> None:
        """check_state(None) must return an empty issues list."""
        rec = Reconciler()
        assert rec.check_state(None) == []

    def test_check_state_valid_coordinate_returns_empty(self) -> None:
        """A well-formed coordinate with a non-empty digest produces no issues."""
        rec = Reconciler()
        # seed:digest:variation — all non-empty so CoordinateValidator passes
        issues = rec.check_state("abc:deadbeefdeadbeef:0")
        assert issues == []

    def test_check_state_malformed_coordinate_returns_inconsistency(self) -> None:
        """A string that cannot be split into three parts is 'malformed'."""
        rec = Reconciler()
        issues = rec.check_state("not-a-valid-coordinate")
        assert len(issues) == 1
        assert issues[0].severity == "critical"
        assert "Malformed" in issues[0].description

    def test_check_state_non_integer_variation_is_malformed(self) -> None:
        """A variation index that is not an integer raises ValueError → malformed."""
        rec = Reconciler()
        issues = rec.check_state("seed:digest:notanint")
        assert len(issues) == 1
        assert issues[0].severity == "critical"

    def test_resolve_no_issues_does_not_raise(self) -> None:
        """resolve([]) must not raise."""
        rec = Reconciler()
        rec.resolve([])  # should be silent

    def test_resolve_critical_inconsistency_raises_runtime_error(self) -> None:
        """resolve() with a critical inconsistency must raise RuntimeError."""
        rec = Reconciler()
        issues = [Inconsistency("state", "Malformed coordinate string", "critical")]
        with pytest.raises(RuntimeError, match="Critical inconsistencies detected"):
            rec.resolve(issues)

    def test_resolve_non_critical_inconsistency_does_not_raise(self) -> None:
        """resolve() with only non-critical inconsistencies must not raise."""
        rec = Reconciler()
        issues = [Inconsistency("state", "Minor drift", "warning")]
        rec.resolve(issues)  # should be silent


class TestRepetitionDetector:
    """Unit tests for RepetitionDetector.record()."""

    def test_first_occurrence_is_not_repeat(self) -> None:
        """A freshly recorded input must not be flagged as a repeat."""
        detector = RepetitionDetector()
        assert detector.record("session-1", "hello world") is False

    def test_second_occurrence_is_repeat(self) -> None:
        """The same input recorded twice must be flagged on the second call."""
        detector = RepetitionDetector()
        detector.record("session-1", "hello world")
        assert detector.record("session-1", "hello world") is True

    def test_different_sessions_are_independent(self) -> None:
        """The same text in different sessions must not cross-contaminate."""
        detector = RepetitionDetector()
        detector.record("session-A", "shared text")
        assert detector.record("session-B", "shared text") is False

    def test_different_inputs_in_same_session_are_not_repeats(self) -> None:
        """Different inputs in the same session must both return False."""
        detector = RepetitionDetector()
        assert detector.record("session-1", "first") is False
        assert detector.record("session-1", "second") is False
