# THALOS Prime Evolution Engine

This implementation turns the adaptive architecture into executable repository components.

## Implemented scope

- Mutable, validated execution graphs whose nodes reference versioned capabilities.
- Versioned module registry with explicit active-version routing.
- Structured cognitive exchange memory containing strategies, results, warnings, and evolution events.
- Agent genomes containing reasoning strategy, tools, workflow, generation, and performance metrics.
- Agent bidding based on capability fit and historical reliability.
- Dynamic agent creation through `AgentFactory` and `AgentPool.spawn`.
- Explicit mutation proposals with lineage, target, old/new versions, change type, description, confidence, and payload.
- Sandbox benchmark evaluation of candidates against the same benchmark suite as the active implementation.
- Promotion only when a candidate passes the suite and exceeds baseline fitness.
- Auditable evolution history persisted in cognitive memory.
- Graph-node mutation for changing execution paths without arbitrary source-file rewriting.

## Runtime loop

`observe -> diagnose -> propose -> sandbox -> score -> promote -> record -> reuse`

The implementation deliberately makes the mutable unit a workflow/module/agent genome rather than allowing arbitrary runtime source replacement. This preserves the original self-optimizing mechanism while keeping changes versioned, reproducible, testable, and reversible at the capability-routing layer.

## Integration point

The package lives under `thalos_prime/evolution` and is independent of the existing deterministic reasoning, agency, graph-RAG, Library of Sense, runtime, and Nexus layers. Those existing systems can supply real handlers, benchmark suites, memory sources, and agent runners without changing the evolution contracts.

## Example

```python
from thalos_prime.evolution import BenchmarkCase, BenchmarkSuite, EvolutionEngine

engine = EvolutionEngine()
engine.register_module("planner", "v1", lambda x: x, activate=True)

suite = BenchmarkSuite(
    cases=[BenchmarkCase("a", 2, 4), BenchmarkCase("b", 3, 6)],
    evaluator=lambda actual, expected: actual == expected,
)

result = engine.evolve_module(
    "planner", "v2", lambda x: x * 2, suite,
    description="improve planner transformation accuracy",
)

assert result.promoted
```

## Validation

`tests/test_evolution_engine.py` covers successful promotion, regression rejection, graph mutation, and component construction.
