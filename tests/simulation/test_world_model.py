"""Tests for WorldModel simulation subsystem."""

from __future__ import annotations

from thalos_prime.library_of_sense.retrieval.knowledge_graph import GraphTriple
from thalos_prime.simulation.world_model import WorldModel, WorldState


class TestWorldState:
    def test_defaults(self) -> None:
        state = WorldState()
        assert state.entities == {}
        assert state.relations == []
        assert state.timestamp == 0
        assert state.version == 0

    def test_to_dict(self) -> None:
        state = WorldState(
            entities={"a": {"x": 1}},
            relations=[GraphTriple("a", "related_to", "b")],
            timestamp=1,
            version=2,
        )
        d = state.to_dict()
        assert d["timestamp"] == 1
        assert d["version"] == 2
        assert isinstance(d["entities"], dict)
        assert isinstance(d["relations"], list)


class TestWorldModel:
    def test_initialize_sets_initialized(self) -> None:
        model = WorldModel()
        model.initialize()
        assert model._initialized is True

    def test_validate_fails_before_initialize(self) -> None:
        model = WorldModel()
        result = model.validate()
        assert result.valid is False
        assert "not initialized" in result.message

    def test_validate_passes_after_initialize(self) -> None:
        model = WorldModel()
        model.initialize()
        result = model.validate()
        assert result.valid is True

    def test_predict_increments_timestamp_and_version(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState(timestamp=0, version=0)
        new_state = model.predict(state, "move_forward")
        assert new_state.timestamp == 1
        assert new_state.version == 1

    def test_predict_records_action(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState()
        new_state = model.predict(state, "jump")
        assert "_action_log" in new_state.entities
        assert "jump" in new_state.entities["_action_log"].values()

    def test_predict_deterministic(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState(entities={"hero": {"hp": 100}})
        result_a = model.predict(state, "attack")
        result_b = model.predict(state, "attack")
        assert result_a.timestamp == result_b.timestamp
        assert result_a.version == result_b.version
        assert result_a.entities == result_b.entities

    def test_predict_does_not_mutate_input(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState(entities={"x": {"val": 1}})
        original_entities = dict(state.entities)
        model.predict(state, "noop")
        assert state.entities == original_entities

    def test_observe_merges_entities(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState(entities={"hero": {"hp": 100}})
        new_state = model.observe(state, {"hero": {"mp": 50}})
        assert "mp" in new_state.entities["hero"]
        assert "hp" in new_state.entities["hero"]

    def test_observe_adds_relations(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState()
        triple = GraphTriple("a", "knows", "b")
        new_state = model.observe(state, {"relations": [triple]})
        assert len(new_state.relations) == 1
        assert new_state.relations[0].predicate == "knows"

    def test_observe_increments_version(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState(version=3)
        new_state = model.observe(state, {"new_entity": {"x": 1}})
        assert new_state.version == 4

    def test_observe_preserves_timestamp(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState(timestamp=5)
        new_state = model.observe(state, {})
        assert new_state.timestamp == 5

    def test_divergence_identical_states(self) -> None:
        model = WorldModel()
        model.initialize()
        state = WorldState(entities={"a": {"x": 1}})
        assert model.divergence(state, state) == 0.0

    def test_divergence_completely_different(self) -> None:
        model = WorldModel()
        model.initialize()
        state_a = WorldState(
            entities={"a": {}, "b": {}},
            relations=[GraphTriple("a", "r", "b")],
        )
        state_b = WorldState(
            entities={"c": {}, "d": {}},
            relations=[GraphTriple("c", "s", "d")],
        )
        div = model.divergence(state_a, state_b)
        assert div == 1.0

    def test_divergence_partial_overlap(self) -> None:
        model = WorldModel()
        model.initialize()
        state_a = WorldState(entities={"a": {}, "b": {}})
        state_b = WorldState(entities={"a": {}, "c": {}})
        div = model.divergence(state_a, state_b)
        assert 0.0 < div < 1.0

    def test_divergence_both_empty(self) -> None:
        model = WorldModel()
        model.initialize()
        state_a = WorldState()
        state_b = WorldState()
        assert model.divergence(state_a, state_b) == 0.0

    def test_operate_does_not_raise(self) -> None:
        model = WorldModel()
        model.initialize()
        model.operate()

    def test_reconcile_fixes_negative_counters(self) -> None:
        model = WorldModel()
        model.initialize()
        model._predict_count = -3
        model._observe_count = -1
        model.reconcile()
        assert model._predict_count == 0
        assert model._observe_count == 0

    def test_checkpoint_returns_dict(self) -> None:
        model = WorldModel()
        model.initialize()
        state = model.checkpoint()
        assert isinstance(state, dict)
        assert state["component"] == "WorldModel"
        assert "predict_count" in state
        assert "observe_count" in state

    def test_terminate_resets_state(self) -> None:
        model = WorldModel()
        model.initialize()
        model.predict(WorldState(), "action")
        model.terminate()
        assert model._initialized is False
        assert model._predict_count == 0

    def test_lifecycle_events_recorded(self) -> None:
        model = WorldModel()
        model.initialize()
        model.operate()
        model.checkpoint()
        model.terminate()
        events = model.get_events()
        methods = [e.method for e in events]
        assert "initialize" in methods
        assert "checkpoint" in methods
        assert "terminate" in methods
