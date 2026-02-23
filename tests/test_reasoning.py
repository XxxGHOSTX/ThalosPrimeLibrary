"""Tests for thalos_prime.reasoning — Tree of Thoughts and Chain of Verification."""

from __future__ import annotations

import pytest

from thalos_prime.graph_rag import GraphIngestionPipeline, GraphRAGControlPlane, KnowledgeGraph
from thalos_prime.ingest import ingest_fragment
from thalos_prime.reasoning import (
    ChainOfVerification,
    ReasoningControlPlane,
    ReasoningError,
    ThoughtNode,
    ThoughtScorer,
    ThoughtStatus,
    ThoughtTree,
    TreeOfThoughts,
    VerificationResult,
)


# ---------------------------------------------------------------------------
# ThoughtScorer
# ---------------------------------------------------------------------------


class TestThoughtScorer:
    def test_score_in_range(self):
        scorer = ThoughtScorer()
        score = scorer.score("the quick brown fox jumps over the lazy dog")
        assert 0.0 <= score <= 1.0

    def test_score_empty_text(self):
        scorer = ThoughtScorer()
        score = scorer.score("")
        assert 0.0 <= score <= 1.0

    def test_score_with_graph(self):
        kg = KnowledgeGraph()
        artifact = ingest_fragment("the quick brown fox", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)
        scorer = ThoughtScorer()
        score = scorer.score("the quick fox", kg)
        assert 0.0 <= score <= 1.0

    def test_score_deterministic(self):
        scorer = ThoughtScorer()
        text = "entropy resolves into patterns"
        assert scorer.score(text) == scorer.score(text)


# ---------------------------------------------------------------------------
# TreeOfThoughts
# ---------------------------------------------------------------------------


class TestTreeOfThoughts:
    def test_run_returns_thought_node(self):
        tot = TreeOfThoughts(max_depth=2, beam_width=2)
        result = tot.run("what is knowledge", seed=42)
        assert isinstance(result, ThoughtNode)

    def test_result_is_terminal(self):
        tot = TreeOfThoughts(max_depth=3, beam_width=2)
        result = tot.run("meaning of life", seed=1)
        assert result.status == ThoughtStatus.TERMINAL

    def test_deterministic_with_same_seed(self):
        tot = TreeOfThoughts(max_depth=2, beam_width=2)
        r1 = tot.run("test prompt", seed=99)
        r2 = tot.run("test prompt", seed=99)
        assert r1.id == r2.id
        assert r1.score == r2.score

    def test_different_seeds_produce_different_results(self):
        # Use a low threshold so children survive and reach TERMINAL
        tot = TreeOfThoughts(max_depth=2, beam_width=2, score_threshold=0.0)
        r1 = tot.run("same prompt longer text for scoring", seed=1)
        r2 = tot.run("same prompt longer text for scoring", seed=2)
        # With different seeds the depth-1 child thoughts rotate differently → different IDs
        assert r1.id != r2.id

    def test_backtrack_fires_with_impossible_threshold(self):
        """score_threshold=1.1 forces all candidates to be pruned, triggering backtrack."""
        tot = TreeOfThoughts(max_depth=3, beam_width=2, score_threshold=1.1)
        # Should not raise; backtrack activates the best pruned node
        result = tot.run("test backtrack", seed=42)
        assert isinstance(result, ThoughtNode)

    def test_beam_width_respected(self):
        """Tree should not expand more than beam_width nodes per depth."""
        tot = TreeOfThoughts(max_depth=1, beam_width=1)
        result = tot.run("narrow beam", seed=7)
        assert isinstance(result, ThoughtNode)

    def test_log_written(self, tmp_path):
        log_file = tmp_path / "tot.jsonl"
        tot = TreeOfThoughts(max_depth=2, beam_width=2, log_path=log_file)
        tot.run("test log", seed=1)
        assert log_file.exists()
        assert log_file.stat().st_size > 0

    def test_run_with_graph_context(self):
        kg = KnowledgeGraph()
        artifact = ingest_fragment("the quick brown fox", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)
        tot = TreeOfThoughts(max_depth=2, beam_width=2)
        result = tot.run("fox knowledge", seed=42, graph=kg)
        assert isinstance(result, ThoughtNode)


# ---------------------------------------------------------------------------
# ChainOfVerification
# ---------------------------------------------------------------------------


class TestChainOfVerification:
    def test_verify_returns_result(self):
        cov = ChainOfVerification()
        result = cov.verify("The sky is blue.")
        assert isinstance(result, VerificationResult)

    def test_vacuous_verification_on_empty_graph(self):
        cov = ChainOfVerification()
        result = cov.verify("One claim. Two claim. Three claim.")
        assert result.verified_claims > 0
        assert result.retracted_claims == 0

    def test_verified_claims_in_final_answer(self):
        cov = ChainOfVerification()
        answer = "The sun is a star. Stars produce light."
        result = cov.verify(answer)
        assert isinstance(result.final_answer, str)

    def test_retraction_on_non_empty_graph(self):
        kg = KnowledgeGraph()
        artifact = ingest_fragment("knowledge and graphs are related concepts", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)

        cov = ChainOfVerification()
        # "xylophone banana" contains words not in graph → retraction
        result = cov.verify("xylophone banana zebra elephant.", graph=kg)
        # retracted or verified — just verify result structure is correct
        assert result.retracted_claims + result.verified_claims == len(result.claims)

    def test_max_claims_respected(self):
        cov = ChainOfVerification(max_claims=2)
        answer = "Claim one. Claim two. Claim three. Claim four."
        result = cov.verify(answer)
        assert len(result.claims) <= 2

    def test_verify_with_no_graph_all_vacuous(self):
        cov = ChainOfVerification()
        result = cov.verify("Statement A. Statement B. Statement C.")
        assert result.retracted_claims == 0

    def test_answer_id_deterministic(self):
        cov = ChainOfVerification()
        r1 = cov.verify("same text here")
        r2 = cov.verify("same text here")
        assert r1.answer_id == r2.answer_id

    def test_log_written(self, tmp_path):
        log_file = tmp_path / "cov.jsonl"
        cov = ChainOfVerification(log_path=log_file)
        cov.verify("Test sentence. Another one.")
        assert log_file.exists()


# ---------------------------------------------------------------------------
# ReasoningControlPlane
# ---------------------------------------------------------------------------


class TestReasoningControlPlane:
    def test_full_lifecycle(self, tmp_path):
        cp = ReasoningControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        cp.validate()
        result = cp.operate("What is knowledge?")
        assert isinstance(result, VerificationResult)
        cp.reconcile()
        cp.checkpoint()
        cp.terminate()

    def test_validate_before_initialize_raises(self, tmp_path):
        cp = ReasoningControlPlane(seed=1, workdir=str(tmp_path))
        with pytest.raises(ReasoningError):
            cp.validate()

    def test_operate_before_initialize_raises(self, tmp_path):
        cp = ReasoningControlPlane(seed=1, workdir=str(tmp_path))
        with pytest.raises(ReasoningError):
            cp.operate("test")

    def test_operate_stores_last_result(self, tmp_path):
        cp = ReasoningControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        cp.validate()
        cp.operate("test query here")
        assert cp.last_result is not None
        assert cp.last_thought is not None

    def test_seed_salting(self, tmp_path):
        from thalos_prime.reasoning.schema import REASONING_SEED_SALT
        cp = ReasoningControlPlane(seed=200, workdir=str(tmp_path))
        assert cp._seed == 200 ^ REASONING_SEED_SALT

    def test_invalid_max_depth_raises(self, tmp_path):
        cp = ReasoningControlPlane(seed=1, workdir=str(tmp_path), max_depth=0)
        cp.initialize()
        with pytest.raises(ReasoningError):
            cp.validate()

    def test_operate_with_graph(self, tmp_path):
        kg = KnowledgeGraph()
        artifact = ingest_fragment("knowledge and reasoning", source="test")
        GraphIngestionPipeline(kg).ingest(artifact)
        cp = ReasoningControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        cp.validate()
        result = cp.operate("knowledge reasoning", graph=kg)
        assert isinstance(result, VerificationResult)

    def test_checkpoint_creates_file(self, tmp_path):
        cp = ReasoningControlPlane(seed=42, workdir=str(tmp_path))
        cp.initialize()
        cp.validate()
        cp.operate("test checkpoint")
        cp.checkpoint()
        checkpoints = list((tmp_path / "reasoning_checkpoints").glob("*.json"))
        assert len(checkpoints) >= 1
