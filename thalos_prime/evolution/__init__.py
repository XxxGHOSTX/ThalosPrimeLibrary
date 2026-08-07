"""THALOS Prime adaptive multi-agent evolution engine.

This package implements the executable architecture for versioned workflow
mutation, agent genomes, shared cognitive memory, sandbox evaluation,
capability routing, dynamic agent spawning, and auditable promotion.
"""

from .agents import AgentFactory, AgentPool, BaseAgent, Genome
from .engine import EvolutionEngine, EvolutionResult
from .graph import ExecutionGraph, GraphNode, GraphWorkflow
from .memory import CognitiveMemory, MemoryEntry
from .mutation import MutationEngine, MutationProposal
from .registry import ModuleRegistry, ModuleSpec
from .sandbox import BenchmarkCase, BenchmarkSuite, SandboxEvaluator

__all__ = [
    "AgentFactory", "AgentPool", "BaseAgent", "Genome",
    "EvolutionEngine", "EvolutionResult", "ExecutionGraph", "GraphNode",
    "GraphWorkflow", "CognitiveMemory", "MemoryEntry", "MutationEngine",
    "MutationProposal", "ModuleRegistry", "ModuleSpec", "BenchmarkCase",
    "BenchmarkSuite", "SandboxEvaluator",
]
