# Thalos Prime — Chief Architect Overview

**Control Plane / Data Plane Architecture — Executive Summary**

---

## What is Thalos Prime?

Thalos Prime is a deterministic toolkit for coherence-first discovery and analysis across deterministic information spaces. It is a software library and development toolkit — not a hardware system, not a biological system, and not a cloud service.

> **Disclaimer:** All references to "symbiotic," "biological," "wetware," or "neural" in this project's documentation are software architecture metaphors. Thalos Prime does not integrate with real biological cells, human neural tissue, or any wetware substrate. SBI (Symbiotic Biological Intelligence) is a conceptual architecture term describing the system's design philosophy: components cooperate symbiotically in software, not in biology. No claims of real wetware integration are made or implied.

See `docs/SBI_DISCLAIMER.md` for the full disclaimer.

---

## Architecture: Control Plane vs. Data Plane

Thalos Prime enforces a strict boundary between two planes:

### Control Plane
**Purpose:** Lifecycle coordination, state management, reconciliation, enforcement.

**Responsibilities:**
- Starting, stopping, and validating subsystems (`initialize`, `validate`, `terminate`)
- Reconciling state to consistent values (`reconcile`)
- Checkpointing state for restart (`checkpoint`)
- Enforcing invariants (gates, schemas, lifecycle protocol)
- Logging all state transitions and lifecycle events

**Control Plane Modules:**
- `thalos_prime/lifecycle.py` — LifecycleProtocol, BaseLifecycleComponent
- `thalos_nexus/nucleus.py` — Genome validation and signing enforcement
- `thalos_nexus/lysosome.py` — Gate runner (orchestrates gate execution)
- `thalos_nexus/membrane.py` — Capability gateway enforcement
- `thalos_nexus/mitochondria.py` — Budget governance
- `thalos_nexus/spine.py` — Determinism spine (canonical state surfaces)

### Data Plane
**Purpose:** Execute computational work.

**Responsibilities:**
- Generating pages, running searches, computing scores
- Executing tool commands (ruff, mypy, pytest)
- Folding artifacts into bundles
- Computing hashes and signatures

**Data Plane Modules:**
- `thalos_prime/lob_babel_generator.py` — Deterministic page generation
- `thalos_prime/lob_babel_enumerator.py` — Query enumeration and address mapping
- `thalos_prime/lob_decoder.py` — Multi-metric coherence scoring
- `thalos_nexus/gates.py` — Gate command definitions
- `thalos_nexus/cytoplasm.py` — Tool execution
- `thalos_nexus/er.py` — Artifact folding and SBOM

### Key Invariants
1. No circular dependencies between planes.
2. Control plane components may reference data plane outputs but never execute computational work directly.
3. Data plane components never coordinate lifecycle or enforce invariants.
4. All state flows through the determinism spine (control plane).

---

## NEXUS v3.0

The NEXUS layer adds an evolution/gate pipeline on top of the base Thalos Prime library:

```
Genome File (intent + policy + fitness + lineages)
     │
     ▼
  Nucleus (ingest, validate, sign)
     │
     ▼
  Lysosome (run gates in Windows isolation adapter)
     │  ├─ no-placeholder-scan (FATAL)
     │  ├─ static-analysis
     │  ├─ security-scan
     │  ├─ acceptance-tests
     │  ├─ property-tests
     │  ├─ mutation-resilience
     │  ├─ deterministic-replay (FATAL)
     │  └─ coverage-enforcement
     │
     ▼
  Determinism Spine (repro_manifest + event_log + gate_results + artifacts)
     │
     ▼
  ER (fold artifacts into bundle.zip + SBOM)
```

---

## Determinism Guarantees

- Identical genome + seed + config → identical gate results, every time.
- All runs produce a `repro_manifest.json` with seed, config hash, and genome hash.
- `replay` re-runs with the same parameters and verifies the hash matches.
- The event log is hash-chained — any tampering is detectable.

---

## Getting Started

See `docs/NEXUS_WINDOWS_INSTALL.md` for Windows 10 Home installation and deployment guide.

See `docs/NEXUS_API_EXAMPLES.md` for CLI usage and Python API examples.
