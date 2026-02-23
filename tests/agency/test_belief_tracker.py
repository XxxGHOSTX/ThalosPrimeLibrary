"""Tests for BeliefTracker agency subsystem."""

from __future__ import annotations

from thalos_prime.agency.belief_tracker import BeliefEntry, BeliefTracker


class TestBeliefEntry:
    def test_defaults(self) -> None:
        entry = BeliefEntry(key="k", value="v", confidence=0.9)
        assert entry.version == 1
        assert entry.source == ""

    def test_to_dict(self) -> None:
        entry = BeliefEntry(key="k", value="v", confidence=0.5, version=2, source="test")
        d = entry.to_dict()
        assert d["key"] == "k"
        assert d["value"] == "v"
        assert d["confidence"] == 0.5
        assert d["version"] == 2
        assert d["source"] == "test"


class TestBeliefTracker:
    def test_initialize_sets_initialized(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        assert tracker._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        tracker = BeliefTracker()
        result = tracker.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        result = tracker.validate()
        assert result.valid is True

    def test_update_belief_creates_entry(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        entry = tracker.update_belief("sky", "blue", 0.95, source="observation")
        assert entry.key == "sky"
        assert entry.value == "blue"
        assert entry.confidence == 0.95
        assert entry.version == 1
        assert entry.source == "observation"

    def test_update_belief_increments_version(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.update_belief("sky", "blue", 0.95)
        entry = tracker.update_belief("sky", "dark blue", 0.99)
        assert entry.version == 2

    def test_update_belief_clamps_confidence(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        high = tracker.update_belief("a", "x", 1.5)
        low = tracker.update_belief("b", "y", -0.5)
        assert high.confidence == 1.0
        assert low.confidence == 0.0

    def test_get_belief_returns_entry(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.update_belief("sky", "blue", 0.9)
        entry = tracker.get_belief("sky")
        assert entry is not None
        assert entry.value == "blue"

    def test_get_belief_returns_none_for_missing(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        assert tracker.get_belief("nonexistent") is None

    def test_remove_belief(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.update_belief("sky", "blue", 0.9)
        assert tracker.remove_belief("sky") is True
        assert tracker.get_belief("sky") is None

    def test_remove_belief_returns_false_for_missing(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        assert tracker.remove_belief("nonexistent") is False

    def test_query_beliefs_returns_sorted(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.update_belief("b", "two", 0.8)
        tracker.update_belief("a", "one", 0.9)
        tracker.update_belief("c", "three", 0.7)
        beliefs = tracker.query_beliefs()
        keys = [b.key for b in beliefs]
        assert keys == ["a", "b", "c"]

    def test_query_beliefs_filters_by_confidence(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.update_belief("low", "x", 0.2)
        tracker.update_belief("high", "y", 0.8)
        beliefs = tracker.query_beliefs(min_confidence=0.5)
        assert len(beliefs) == 1
        assert beliefs[0].key == "high"

    def test_query_beliefs_uses_instance_threshold(self) -> None:
        tracker = BeliefTracker(confidence_threshold=0.6)
        tracker.initialize()
        tracker.update_belief("low", "x", 0.3)
        tracker.update_belief("high", "y", 0.8)
        beliefs = tracker.query_beliefs()
        assert len(beliefs) == 1

    def test_state_hash_deterministic(self) -> None:
        tracker1 = BeliefTracker()
        tracker1.initialize()
        tracker1.update_belief("a", "1", 0.5)
        tracker1.update_belief("b", "2", 0.7)

        tracker2 = BeliefTracker()
        tracker2.initialize()
        tracker2.update_belief("a", "1", 0.5)
        tracker2.update_belief("b", "2", 0.7)

        assert tracker1.state_hash() == tracker2.state_hash()

    def test_state_hash_changes_on_update(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.update_belief("a", "1", 0.5)
        hash1 = tracker.state_hash()
        tracker.update_belief("a", "2", 0.9)
        hash2 = tracker.state_hash()
        assert hash1 != hash2

    def test_belief_count_property(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        assert tracker.belief_count == 0
        tracker.update_belief("a", "1", 0.5)
        assert tracker.belief_count == 1

    def test_operate_does_not_raise(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.operate()

    def test_reconcile_fixes_negative_counters(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker._update_count = -3
        tracker.reconcile()
        assert tracker._update_count == 0

    def test_checkpoint_returns_dict(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        state = tracker.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "BeliefTracker"
        assert "belief_count" in state
        assert "state_hash" in state

    def test_terminate_resets_state(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.update_belief("sky", "blue", 0.9)
        tracker.terminate()
        assert tracker._initialized is False
        assert tracker.belief_count == 0

    def test_lifecycle_events_recorded(self) -> None:
        tracker = BeliefTracker()
        tracker.initialize()
        tracker.operate()
        tracker.checkpoint()
        tracker.terminate()
        events = tracker.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "checkpoint" in methods
        assert "terminate" in methods
