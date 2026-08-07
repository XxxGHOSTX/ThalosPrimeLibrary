"""End-to-end observe -> diagnose -> mutate -> benchmark -> promote loop."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .graph import ExecutionGraph, GraphWorkflow
from .memory import CognitiveMemory
from .mutation import MutationEngine, MutationProposal
from .registry import ModuleRegistry, ModuleSpec
from .sandbox import BenchmarkResult, BenchmarkSuite, SandboxEvaluator


@dataclass
class EvolutionResult:
    workflow_id: str
    mutation: MutationProposal | None
    baseline: BenchmarkResult | None
    candidate: BenchmarkResult | None
    promoted: bool
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


class EvolutionEngine:
    """Coordinates self-optimization without direct arbitrary source mutation."""

    def __init__(self, registry: ModuleRegistry | None = None, graphs: ExecutionGraph | None = None, memory: CognitiveMemory | None = None) -> None:
        self.registry = registry or ModuleRegistry()
        self.graphs = graphs or ExecutionGraph()
        self.memory = memory or CognitiveMemory()
        self.mutations = MutationEngine()
        self.sandbox = SandboxEvaluator()

    def register_module(self, name: str, version: str, handler: Callable[..., Any], activate: bool = False, capabilities: tuple[str, ...] = ()) -> None:
        self.registry.register(ModuleSpec(name=name, version=version, handler=handler, capabilities=capabilities), activate=activate)

    def evolve_module(self, name: str, candidate_version: str, candidate: Callable[[Any], Any], suite: BenchmarkSuite, description: str = "candidate optimization") -> EvolutionResult:
        active = self.registry.get(name)
        baseline = self.sandbox.evaluate(active.key, active.handler, suite)
        candidate_result = self.sandbox.evaluate(f"{name}:{candidate_version}", candidate, suite)
        proposal = self.mutations.propose_module(
            target=name, old_version=active.version, new_version=candidate_version,
            description=description, confidence=candidate_result.fitness,
        )
        promoted = candidate_result.passed and candidate_result.fitness > baseline.fitness
        if promoted:
            self.registry.register(ModuleSpec(name=name, version=candidate_version, handler=candidate), activate=True)
        event = {
            "mutation_id": proposal.mutation_id, "old_version": active.version,
            "new_version": candidate_version, "reason": description,
            "tests": candidate_result.cases, "baseline_fitness": baseline.fitness,
            "candidate_fitness": candidate_result.fitness, "promoted": promoted,
        }
        self.memory.record_evolution(event)
        self.memory.publish("evolution", event, "evolution_engine", confidence=candidate_result.fitness)
        return EvolutionResult(
            workflow_id=name, mutation=proposal, baseline=baseline,
            candidate=candidate_result, promoted=promoted,
            reason="candidate superior and benchmark-passing" if promoted else "candidate rejected",
            evidence=event,
        )

    def evolve_graph(self, family: str, candidate: GraphWorkflow, proposal: MutationProposal, baseline_score: float, candidate_score: float) -> EvolutionResult:
        promoted = candidate_score > baseline_score
        if promoted:
            self.graphs.register(candidate)
            self.graphs.promote(family, candidate.workflow_id)
        event = {
            "mutation_id": proposal.mutation_id, "old_version": proposal.old_version,
            "new_version": proposal.new_version, "baseline_score": baseline_score,
            "candidate_score": candidate_score, "promoted": promoted,
        }
        self.memory.record_evolution(event)
        self.memory.publish("evolution", event, "evolution_engine", confidence=max(0.0, min(1.0, candidate_score)))
        return EvolutionResult(family, proposal, None, None, promoted, "graph candidate superior" if promoted else "graph candidate rejected", event)
