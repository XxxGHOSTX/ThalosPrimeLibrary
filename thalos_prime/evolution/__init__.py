"""THALOS Prime adaptive multi-agent evolution engine."""

from .agents import AgentFactory, AgentPool, BaseAgent, Genome
from .coordination import EvolutionCouncil, Message, MessageBoard, TaskCoordinator
from .engine import EvolutionEngine, EvolutionResult
from .graph import ExecutionGraph, GraphNode, GraphWorkflow
from .memory import CognitiveMemory, MemoryEntry
from .mutation import MutationEngine, MutationProposal
from .observation import Observation, RuntimeRouter, SelfObserver
from .registry import ModuleRegistry, ModuleSpec
from .sandbox import BenchmarkCase, BenchmarkResult, BenchmarkSuite, SandboxEvaluator

__all__ = [
    "AgentFactory", "AgentPool", "BaseAgent", "Genome", "EvolutionCouncil",
    "Message", "MessageBoard", "TaskCoordinator", "EvolutionEngine",
    "EvolutionResult", "ExecutionGraph", "GraphNode", "GraphWorkflow",
    "CognitiveMemory", "MemoryEntry", "MutationEngine", "MutationProposal",
    "Observation", "RuntimeRouter", "SelfObserver", "ModuleRegistry", "ModuleSpec",
    "BenchmarkCase", "BenchmarkResult", "BenchmarkSuite", "SandboxEvaluator",
]
