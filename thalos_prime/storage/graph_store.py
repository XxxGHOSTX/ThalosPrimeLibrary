"""Local filesystem-backed execution graph store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from thalos_prime.execution_ir.graph import ExecutionGraph
from thalos_prime.storage.provider import get_storage_base_path


class GraphStoreProtocol(Protocol):
    """Protocol for execution graph persistence backends."""

    def save(self, graph: ExecutionGraph) -> None:
        """Persist a graph snapshot.

        Args:
            graph: ExecutionGraph to persist.

        """
        ...

    def load(self, graph_id: str, version: int | None = None) -> ExecutionGraph:
        """Load a graph snapshot by ID and optional version.

        Args:
            graph_id: Unique graph identifier.
            version: Specific version to load; loads latest if None.

        Returns:
            Deserialized ExecutionGraph.

        """
        ...

    def list_ids(self) -> list[str]:
        """List all stored graph IDs.

        Returns:
            Sorted list of graph identifiers.

        """
        ...


class LocalGraphStore:
    """Saves ExecutionGraphs as JSON files under ``base_path/{graph_id}/{version}.json``.

    Each graph version is stored as an independent JSON snapshot.
    Loading without a version returns the highest-numbered version.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the store with an optional custom base path.

        Args:
            base_path: Root directory for graph storage. Uses the default
                from get_storage_base_path() if not provided.

        """
        self._base = (base_path if base_path is not None else get_storage_base_path()) / "graphs"
        self._base.mkdir(parents=True, exist_ok=True)

    def _graph_dir(self, graph_id: str) -> Path:
        """Return the directory for a specific graph ID.

        Args:
            graph_id: Unique graph identifier.

        Returns:
            Path to the graph's storage directory.

        """
        return self._base / graph_id

    def save(self, graph: ExecutionGraph) -> None:
        """Persist a graph snapshot as a versioned JSON file.

        Args:
            graph: ExecutionGraph to persist. Uses graph.version for the filename.

        """
        graph_dir = self._graph_dir(graph.id)
        graph_dir.mkdir(parents=True, exist_ok=True)
        version_file = graph_dir / f"{graph.version}.json"
        with version_file.open("w", encoding="utf-8") as fh:
            json.dump(graph.serialize(), fh, ensure_ascii=False, sort_keys=True)

    def load(self, graph_id: str, version: int | None = None) -> ExecutionGraph:
        """Load a graph snapshot by ID and optional version.

        Args:
            graph_id: Unique graph identifier.
            version: Specific version number to load. Loads the latest
                version if None.

        Returns:
            Deserialized ExecutionGraph.

        Raises:
            FileNotFoundError: If the graph ID or version does not exist.

        """
        graph_dir = self._graph_dir(graph_id)
        if not graph_dir.exists():
            msg = f"Graph '{graph_id}' not found in store"
            raise FileNotFoundError(msg)

        if version is None:
            version_files = sorted(graph_dir.glob("*.json"), key=lambda p: int(p.stem))
            if not version_files:
                msg = f"No versions found for graph '{graph_id}'"
                raise FileNotFoundError(msg)
            target = version_files[-1]
        else:
            target = graph_dir / f"{version}.json"
            if not target.exists():
                msg = f"Version {version} not found for graph '{graph_id}'"
                raise FileNotFoundError(msg)

        with target.open(encoding="utf-8") as fh:
            data: dict[str, object] = json.load(fh)
        return ExecutionGraph.from_dict(data)

    def list_ids(self) -> list[str]:
        """List all stored graph IDs.

        Returns:
            Sorted list of graph identifiers found in the store.

        """
        if not self._base.exists():
            return []
        return sorted(p.name for p in self._base.iterdir() if p.is_dir())


__all__ = ["GraphStoreProtocol", "LocalGraphStore"]
