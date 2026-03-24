"""Thalos Prime NEXUS v3.0 — deterministic genome evolution toolkit.

Provides a strict control-plane / data-plane separation for genome ingestion,
gate-based quality enforcement, artifact folding, and deterministic replay.
Also exposes the Universal Solver Registry and Recipe Engine for the
Riemann-Babel Filter pipeline.

Exported surface
----------------
- ``__version__``: package version string
- ``GenomeBundle``: nucleus genome container dataclass
- ``DeterminismSpine``: manages repro_manifest, event_log, gate_results, artifacts
- ``GateSpec``, ``GateResult``, ``GateRunResults``: gate execution types
- ``BudgetGovernor``: wall-clock budget tracker
- ``ToolEnvelope``, ``ToolRegistry``: subprocess-level CLI tool registry
- ``ArtifactFolder``, ``SBOMEntry``: artifact folding
- ``MembraneGateway``: capability / network enforcement context manager
- ``SolverRegistry``, ``SolverDescriptor``, ``SolverInput``, ``SolverOutput``:
  Universal Solver Registry for cognitive solver discovery
- ``SolverNotFoundError``: raised when a named solver is not registered
- ``get_global_solver_registry``: access the process-level singleton registry
- ``DataSignature``, ``RecipeEngine``, ``build_default_recipe_engine``:
  Recipe Engine for Riemann-Babel Filter pipeline planning
"""

from __future__ import annotations

from thalos_nexus.cytoplasm import ToolEnvelope, ToolRegistry
from thalos_nexus.er import ArtifactFolder, SBOMEntry
from thalos_nexus.gates import GateSpec
from thalos_nexus.lysosome import GateResult, GateRunResults
from thalos_nexus.membrane import MembraneGateway
from thalos_nexus.mitochondria import BudgetGovernor
from thalos_nexus.nucleus import GenomeBundle
from thalos_nexus.recipes import DataSignature, RecipeEngine, build_default_recipe_engine
from thalos_nexus.solver_registry import (
    SolverDescriptor,
    SolverInput,
    SolverNotFoundError,
    SolverOutput,
    SolverRegistry,
    get_global_solver_registry,
)
from thalos_nexus.spine import DeterminismSpine

__version__: str = "3.0.0"

__all__: list[str] = [
    "ArtifactFolder",
    "BudgetGovernor",
    "DataSignature",
    "DeterminismSpine",
    "GateResult",
    "GateRunResults",
    "GateSpec",
    "GenomeBundle",
    "MembraneGateway",
    "RecipeEngine",
    "SBOMEntry",
    "SolverDescriptor",
    "SolverInput",
    "SolverNotFoundError",
    "SolverOutput",
    "SolverRegistry",
    "ToolEnvelope",
    "ToolRegistry",
    "__version__",
    "build_default_recipe_engine",
    "get_global_solver_registry",
]
