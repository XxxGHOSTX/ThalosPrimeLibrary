"""Presentation and export layer for ThalosPrime Library.

Data Plane module: provides JSON export, proof trace bundles, and lineage
graphs. No lifecycle orchestration. Pure data transformation.

Exports:
    ProofTrace: Pydantic model for a proof trace bundle.
    LineageGraph: Pydantic model for an artifact lineage graph.
    ExportPresenter: Data Plane export utility.
"""

from __future__ import annotations

from thalos_prime.export.presenter import ExportPresenter, LineageGraph, ProofTrace

__all__ = [
    "ExportPresenter",
    "LineageGraph",
    "ProofTrace",
]
