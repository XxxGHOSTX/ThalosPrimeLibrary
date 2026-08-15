from thalos_prime.evolution.benchmark_v2 import RepeatedBenchmark
from thalos_prime.evolution.policy import EvolutionPolicy
from thalos_prime.evolution.provenance import EvolutionManifest, ProvenanceChain
from thalos_prime.evolution.time_travel import ExecutionTimeline, capture


def test_policy_rejects_workflow_mutation():
    decision = EvolutionPolicy().check_paths([".github/workflows/evolve.yml"])
    assert not decision.allowed


def test_policy_accepts_normal_source_change():
    decision = EvolutionPolicy().check_paths(["thalos_prime/evolution/engine.py"])
    assert decision.allowed


def test_repeated_benchmark_records_latency_and_accuracy():
    result = RepeatedBenchmark(warmups=1, repeats=2).evaluate(
        "v2", lambda x: x * 2,
        [("a", 2, 4), ("b", 3, 6)],
        lambda actual, expected: actual == expected,
    )
    assert result.passed
    assert result.accuracy == 1.0
    assert result.median_latency_ns > 0
    assert result.p95_latency_ns >= result.median_latency_ns


def test_provenance_chain_is_hash_linked():
    chain = ProvenanceChain()
    first = EvolutionManifest("r1", "repo", "base", None, "target")
    first_hash = chain.append(first)
    second = EvolutionManifest("r2", "repo", "base", "candidate", "target", parent_manifest_hash=first_hash)
    chain.append(second)
    assert chain.verify()
    assert chain.head == second.digest()


def test_time_travel_captures_boundaries_and_exceptions():
    timeline = ExecutionTimeline()

    @capture(timeline)
    def twice(value: int) -> int:
        return value * 2

    assert twice(3) == 6
    assert [event.label for event in timeline.events] == ["enter", "return"]
    assert twice.timeline is timeline  # type: ignore[attr-defined]


def test_time_travel_records_failure():
    timeline = ExecutionTimeline()

    @capture(timeline)
    def fail() -> None:
        raise RuntimeError("boom")

    try:
        fail()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")
    assert timeline.events[-1].label == "exception"
