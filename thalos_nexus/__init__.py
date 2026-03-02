"""Thalos Prime NEXUS Core v1.

Control Plane nucleus for deterministic lifecycle management, Windows-native
isolation, artifact accountability, and hard-gate enforcement.
"""Thalos Prime NEXUS v3.0 — deterministic genome evolution toolkit.

Provides a strict control-plane / data-plane separation for genome ingestion,
gate-based quality enforcement, artifact folding, and deterministic replay.

Exported surface
----------------
- ``__version__``: package version string
- ``GenomeBundle``: nucleus genome container dataclass
- ``DeterminismSpine``: manages repro_manifest, event_log, gate_results, artifacts
- ``GateSpec``, ``GateResult``, ``GateRunResults``: gate execution types
- ``BudgetGovernor``: wall-clock budget tracker
- ``ToolEnvelope``, ``ToolRegistry``: tool registry
- ``ArtifactFolder``, ``SBOMEntry``: artifact folding
- ``MembraneGateway``: capability / network enforcement context manager
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__: list[str] = []
from thalos_nexus.cytoplasm import ToolEnvelope, ToolRegistry
from thalos_nexus.er import ArtifactFolder, SBOMEntry
from thalos_nexus.gates import GateSpec
from thalos_nexus.lysosome import GateResult, GateRunResults
from thalos_nexus.membrane import MembraneGateway
from thalos_nexus.mitochondria import BudgetGovernor
from thalos_nexus.nucleus import GenomeBundle
from thalos_nexus.spine import DeterminismSpine

__version__: str = "3.0.0"

__all__: list[str] = [
    "ArtifactFolder",
    "BudgetGovernor",
    "DeterminismSpine",
    "GateResult",
    "GateRunResults",
    "GateSpec",
    "GenomeBundle",
    "MembraneGateway",
    "SBOMEntry",
    "ToolEnvelope",
    "ToolRegistry",
    "__version__",
]
