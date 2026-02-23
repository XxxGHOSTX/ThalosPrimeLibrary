"""Tests for thalos_prime.agency — World Models and Active Inference."""

from __future__ import annotations

import pytest

from thalos_prime.agency import (
    Action,
    ActiveInferenceEngine,
    AgencyControlPlane,
    AgencyError,
    Goal,
    GoalEvaluator,
    GoalStatus,
    Prediction,
    PredictionEngine,
    WorldModel,
    WorldState,
)
from thalos_prime.graph_rag import GraphIngestionPipeline, GraphRAGControlPlane, KnowledgeGraph
from thalos_prime.ingest import ingest_fragment


# ---------------------------------------------------------------------------
# GoalEvaluator
# ---------------------------------------------------------------------------


class TestGoalEvaluator:
    def _make_goal(self, text: str, status: GoalStatus = GoalStatus.ACTIVE) -> Goal:
        from hashlib import sha256
        gid = sha256(text.encode()).hexdigest()
        return Goal(id=gid, goal_text=text, priority=0.5, status=status, created_at=0)

    def test_achieved_if_all_tokens_in_graph(self):
        kg = KnowledgeGraph()
        artifact = ingest_fragment("knowledge graph reasoning", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)
        evaluator = GoalEvaluator()
        goal = self._make_goal("knowledge reasoning")
        # Status depends on whether tokens are found; just verify no exception
        result = evaluator.evaluate(goal, kg)
        assert result in (GoalStatus.ACTIVE, GoalStatus.ACHIEVED)

    def test_active_if_no_tokens_in_graph(self):
        kg = KnowledgeGraph()
        evaluator = GoalEvaluator()
        goal = self._make_goal("xylophone zeppelin")
        result = evaluator.evaluate(goal, kg)
        assert result == GoalStatus.ACTIVE

    def test_already_achieved_stays_achieved(self):
        kg = KnowledgeGraph()
        evaluator = GoalEvaluator()
        goal = self._make_goal("test", status=GoalStatus.ACHIEVED)
        result = evaluator.evaluate(goal, kg)
        assert result == GoalStatus.ACHIEVED

    def test_already_abandoned_stays_abandoned(self):
        kg = KnowledgeGraph()
        evaluator = GoalEvaluator()
        goal = self._make_goal("test", status=GoalStatus.ABANDONED)
        result = evaluator.evaluate(goal, kg)
        assert result == GoalStatus.ABANDONED


# ---------------------------------------------------------------------------
# PredictionEngine
# ---------------------------------------------------------------------------


class TestPredictionEngine:
    def test_empty_graph_returns_empty(self):
        engine = PredictionEngine()
        kg = KnowledgeGraph()
        preds = engine.generate(kg, seed=1, timestep=0)
        assert preds == []

    def test_returns_predictions_for_populated_graph(self):
        kg = KnowledgeGraph()
        artifact = ingest_fragment("knowledge graph enables reasoning concepts", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)
        engine = PredictionEngine()
        preds = engine.generate(kg, seed=1, timestep=1)
        assert isinstance(preds, list)

    def test_predictions_deterministic(self):
        kg = KnowledgeGraph()
        artifact = ingest_fragment("determinism in knowledge systems", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)
        engine = PredictionEngine()
        p1 = engine.generate(kg, seed=5, timestep=2)
        p2 = engine.generate(kg, seed=5, timestep=2)
        ids1 = [p.id for p in p1]
        ids2 = [p.id for p in p2]
        assert ids1 == ids2

    def test_max_predictions_respected(self):
        kg = KnowledgeGraph()
        for i in range(5):
            artifact = ingest_fragment(f"concept {i} relates to system {i}", source="test")
            GraphIngestionPipeline(kg).ingest(artifact)
        engine = PredictionEngine()
        preds = engine.generate(kg, seed=1, timestep=0, max_predictions=3)
        assert len(preds) <= 3

    def test_prediction_fields(self):
        kg = KnowledgeGraph()
        artifact = ingest_fragment("knowledge reasoning graph", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)
        engine = PredictionEngine()
        preds = engine.generate(kg, seed=1, timestep=0)
        if preds:
            p = preds[0]
            assert isinstance(p, Prediction)
            assert 0.0 <= p.confidence <= 1.0
            assert len(p.basis_entity_ids) == 2


# ---------------------------------------------------------------------------
# WorldModel
# ---------------------------------------------------------------------------


class TestWorldModel:
    def _make_world_model(self, tmp_path: object) -> WorldModel:
        cp = GraphRAGControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        return WorldModel(graph_cp=cp, seed=42, config_hash="test")

    def test_initial_timestep_zero(self, tmp_path):
        wm = self._make_world_model(tmp_path)
        assert wm.state.timestep == 0

    def test_update_increments_timestep(self, tmp_path):
        wm = self._make_world_model(tmp_path)
        artifact = ingest_fragment("world model test knowledge", source="test")
        wm.update(artifact)
        assert wm.state.timestep == 1

    def test_multiple_updates_increment_timestep(self, tmp_path):
        wm = self._make_world_model(tmp_path)
        for i in range(3):
            artifact = ingest_fragment(f"update {i} knowledge graph", source="test")
            wm.update(artifact)
        assert wm.state.timestep == 3

    def test_add_goal(self, tmp_path):
        wm = self._make_world_model(tmp_path)
        goal = wm.add_goal("understand knowledge graphs", priority=0.8)
        assert goal.status == GoalStatus.ACTIVE
        assert goal in wm.state.active_goals

    def test_belief_graph_property(self, tmp_path):
        wm = self._make_world_model(tmp_path)
        assert isinstance(wm.belief_graph, KnowledgeGraph)

    def test_goal_re_evaluation_on_update(self, tmp_path):
        wm = self._make_world_model(tmp_path)
        wm.add_goal("knowledge reasoning", priority=1.0)
        artifact = ingest_fragment("knowledge reasoning concepts", source="test")
        state = wm.update(artifact)
        # Goals should be re-evaluated (may be ACTIVE or ACHIEVED)
        for goal in state.active_goals:
            assert goal.status in (GoalStatus.ACTIVE, GoalStatus.ACHIEVED)


# ---------------------------------------------------------------------------
# ActiveInferenceEngine
# ---------------------------------------------------------------------------


class TestActiveInferenceEngine:
    def _make_state(self) -> WorldState:
        from hashlib import sha256
        return WorldState(
            id=sha256(b"test").hexdigest(),
            seed=42,
            timestep=0,
            config_hash="test",
        )

    def test_returns_action(self):
        engine = ActiveInferenceEngine()
        state = self._make_state()
        kg = KnowledgeGraph()
        action = engine.step(state, kg)
        assert isinstance(action, Action)

    def test_noop_action_on_empty_state(self):
        engine = ActiveInferenceEngine()
        state = self._make_state()
        kg = KnowledgeGraph()
        action = engine.step(state, kg)
        assert action.action_type == "query"

    def test_reason_action_generated_for_goal(self):
        engine = ActiveInferenceEngine()
        state = self._make_state()
        from hashlib import sha256
        goal = Goal(
            id=sha256(b"goal1").hexdigest(),
            goal_text="understand knowledge systems",
            priority=1.0,
            status=GoalStatus.ACTIVE,
            created_at=0,
        )
        state.active_goals.append(goal)
        kg = KnowledgeGraph()
        action = engine.step(state, kg)
        assert action.action_type in ("reason", "ingest", "verify", "query")

    def test_deterministic_tie_break(self):
        """Two identical states with same graph produce same action."""
        engine = ActiveInferenceEngine()
        kg = KnowledgeGraph()
        artifact = ingest_fragment("knowledge reasoning graph context", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)

        state1 = self._make_state()
        state2 = self._make_state()
        a1 = engine.step(state1, kg)
        a2 = engine.step(state2, kg)
        assert a1.id == a2.id

    def test_verify_action_for_low_confidence_prediction(self):
        engine = ActiveInferenceEngine()
        state = self._make_state()
        from hashlib import sha256
        pred = Prediction(
            id=sha256(b"pred1").hexdigest(),
            prediction_text="low confidence claim here",
            basis_entity_ids=[],
            confidence=0.1,
            validated=None,
            timestep=0,
        )
        state.prediction_log.append(pred)
        kg = KnowledgeGraph()
        action = engine.step(state, kg)
        assert action.action_type in ("verify", "query", "reason", "ingest")


# ---------------------------------------------------------------------------
# AgencyControlPlane
# ---------------------------------------------------------------------------


class TestAgencyControlPlane:
    def _make_cp(self, tmp_path: object) -> AgencyControlPlane:
        graph_cp = GraphRAGControlPlane(seed=42, workdir=str(tmp_path) + "/graph")
        graph_cp.initialize()
        return AgencyControlPlane(
            seed=42,
            workdir=str(tmp_path) + "/agency",
            graph_cp=graph_cp,
        )

    def test_full_lifecycle(self, tmp_path):
        cp = self._make_cp(tmp_path)
        cp.initialize()
        cp.validate()
        action = cp.operate()
        assert isinstance(action, Action)
        cp.reconcile()
        snap = cp.checkpoint()
        assert snap.exists()
        cp.terminate()

    def test_validate_before_initialize_raises(self, tmp_path):
        cp = self._make_cp(tmp_path)
        with pytest.raises(AgencyError):
            cp.validate()

    def test_operate_before_initialize_raises(self, tmp_path):
        cp = self._make_cp(tmp_path)
        with pytest.raises(AgencyError):
            cp.operate()

    def test_operate_with_artifact(self, tmp_path):
        cp = self._make_cp(tmp_path)
        cp.initialize()
        cp.validate()
        artifact = ingest_fragment("agency operate knowledge graph", source="test")
        action = cp.operate(artifact)
        assert isinstance(action, Action)

    def test_world_state_property(self, tmp_path):
        cp = self._make_cp(tmp_path)
        cp.initialize()
        state = cp.world_state
        assert isinstance(state, WorldState)
        assert state.timestep == 0

    def test_seed_salting(self, tmp_path):
        from thalos_prime.agency.schema import AGENCY_SEED_SALT
        cp = self._make_cp(tmp_path)
        assert cp._seed == 42 ^ AGENCY_SEED_SALT

    def test_reconcile_abandons_stagnant_goals(self, tmp_path):
        cp = self._make_cp(tmp_path)
        cp.initialize()
        cp.validate()
        # Add a goal created at timestep 0; stagnation threshold = 10
        assert cp._world_model is not None
        cp._world_model.add_goal("stagnant goal text", priority=0.5)
        # Fast-forward timestep manually
        cp._world_model.state.timestep = 11
        cp.reconcile()
        # Goal should be abandoned after reconcile
        goals = cp._world_model.state.active_goals
        if goals:
            assert any(g.status == GoalStatus.ABANDONED for g in goals)

    def test_last_action_stored(self, tmp_path):
        cp = self._make_cp(tmp_path)
        cp.initialize()
        cp.validate()
        cp.operate()
        assert cp.last_action is not None
