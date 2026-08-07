from thalos_prime.evolution import (
    BenchmarkCase, BenchmarkSuite, CognitiveMemory, EvolutionEngine,
    ExecutionGraph, GraphNode, GraphWorkflow, ModuleRegistry,
)


def test_module_evolution_promotes_superior_candidate():
    engine = EvolutionEngine()
    engine.register_module("planner", "v1", lambda value: value, activate=True)
    suite = BenchmarkSuite(
        cases=[BenchmarkCase("1", 1, 2), BenchmarkCase("2", 2, 4)],
        evaluator=lambda actual, expected: actual == expected,
    )
    result = engine.evolve_module("planner", "v2", lambda value: value * 2, suite)
    assert result.promoted is True
    assert engine.registry.active_version("planner") == "v2"
    assert len(engine.memory.evolution_history()) == 1


def test_module_evolution_rejects_regression():
    engine = EvolutionEngine()
    engine.register_module("planner", "v1", lambda value: value * 2, activate=True)
    suite = BenchmarkSuite(
        cases=[BenchmarkCase("1", 1, 2), BenchmarkCase("2", 2, 4)],
        evaluator=lambda actual, expected: actual == expected,
    )
    result = engine.evolve_module("planner", "v2", lambda value: value + 1, suite)
    assert result.promoted is False
    assert engine.registry.active_version("planner") == "v1"


def test_graph_replacement_is_versioned_and_acyclic():
    workflow = GraphWorkflow(
        "workflow_v1",
        {
            "analyze": GraphNode("analyze", "analyzer_v1"),
            "plan": GraphNode("plan", "planner_v1"),
            "execute": GraphNode("execute", "executor_v1"),
        },
        [("analyze", "plan"), ("plan", "execute")],
    )
    candidate = workflow.replace_function("plan", "planner_v2")
    assert candidate.nodes["plan"].function == "planner_v2"
    assert candidate.topological_order() == ["analyze", "plan", "execute"]


def test_registry_and_graph_components_exist():
    assert isinstance(ModuleRegistry(), ModuleRegistry)
    assert isinstance(ExecutionGraph(), ExecutionGraph)
    assert isinstance(CognitiveMemory(), CognitiveMemory)
