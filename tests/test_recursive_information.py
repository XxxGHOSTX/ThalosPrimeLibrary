from thalos_prime.cognition import (
    CognitiveObservation,
    Prediction,
    RecursiveInformationEngine,
    SelfModelSnapshot,
)


def make_observation(correct: bool = True) -> CognitiveObservation:
    expected = "b" if correct else "wrong"
    return CognitiveObservation(
        observation_id="obs-1",
        predictions=(Prediction(expected, "b", 1.0),),
        self_model=SelfModelSnapshot(
            state={"memory": "stable"},
            predicted_state={"memory": "stable"},
        ),
        operation_cost=1,
    )


def test_prediction_accuracy_and_self_model() -> None:
    score = RecursiveInformationEngine().score(make_observation())
    assert score.prediction_accuracy == 1.0
    assert score.self_model_consistency == 1.0
    assert score.contradiction_rate == 0.0
    assert score.composite == 1.0


def test_incorrect_prediction_reduces_score() -> None:
    score = RecursiveInformationEngine().score(make_observation(False))
    assert score.prediction_accuracy == 0.0
    assert score.composite < 1.0


def test_memory_stability_uses_history() -> None:
    engine = RecursiveInformationEngine()
    first = make_observation()
    second = CognitiveObservation(
        observation_id="obs-2",
        predictions=first.predictions,
        self_model=SelfModelSnapshot(
            state={"memory": "changed"},
            predicted_state={"memory": "changed"},
        ),
    )
    score = engine.score(second, (first,))
    assert score.memory_stability == 0.0
