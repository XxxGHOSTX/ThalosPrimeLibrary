# Thalos Prime Architecture

## Overview

ThalosPrimeLibrary (`thalos_prime`) is a deterministic, production-grade Python
toolkit that integrates the [Library of Babel](https://libraryofbabel.info) with
hybrid cognitive synthesis, symbolic reasoning, autonomous agency, and
infrastructure-as-code generation.

Every subsystem is built on two foundational principles:

1. **Determinism** — identical inputs always produce identical outputs. A single
   integer seed controls all pseudo-randomness; all collections are sorted with
   stable, deterministic keys; no module-level RNG state exists.
2. **Strict Control Plane / Data Plane separation** — coordination and lifecycle
   logic (Control Plane) is never mixed with computational work (Data Plane).

---

## Plane Separation

| Plane | Responsibility | Key Components |
|---|---|---|
| **Control Plane** | Lifecycle coordination, seed control, state logging, deterministic halt | `ControlPlane`, lifecycle orchestrators, `BaseLifecycleComponent` |
| **Data Plane** | Computational work only; no scheduling or coordination | `BabelClient`, adapters, solvers, planners, retrieval engines |

---

## Six-Method Lifecycle Contract

Every subsystem implements these methods in order, with explicit success/failure
semantics:

```
initialize() → validate() → operate() → reconcile() → checkpoint() → terminate()
```

- `initialize()` — allocate resources, verify preconditions; must fully succeed
  or raise a typed exception.
- `validate()` — check all invariants; returns `ValidationResult`.
- `operate()` — execute primary work; idempotent where applicable.
- `reconcile()` — converge to consistent state; deterministically succeeds or
  halts with full state capture.
- `checkpoint()` — serialize atomic, versioned state for restart.
- `terminate()` — release all resources; no orphaned state permitted.

Any invariant violation raises `DeterministicHalt` with a full state snapshot
and JSONL event log. Silent degradation is never permitted.

---

## Subsystems

### Library of Babel (`thalos_prime.lob_babel_*`)

- **`lob_babel_generator.py`** — deterministic SHA-256-based generation of
  3,200-character Babel pages from hex addresses.
- **`lob_babel_enumerator.py`** — maps natural-language queries to candidate
  Babel addresses via n-gram extraction.
- **`lob_decoder.py`** — multi-metric coherence scoring (language, structure,
  n-gram, exact match) on a 0–100 scale.

### Hybrid Cognitive Synthesis (`thalos_prime.library_of_sense`)

Multi-view semantic decomposition across Physical/Chemical, Logical/Mathematical,
and Linguistic/Narrative knowledge planes. Components:

- **Core orchestrator** (`core/orchestrator.py`) — Control Plane; manages the
  synthesis pipeline lifecycle.
- **Retrieval** (`retrieval/`) — knowledge graph retrieval, Graph-RAG, web
  retrieval, multi-source and computational retrieval.
- **Reasoning** (`reasoning/`) — symbolic engine, constraint solver, proof checker.
- **Synthesis** (`synthesis/`) — knowledge fusion, conflict resolution,
  answer generation, and verification.
- **Code generation** (`code_generation/`) — deterministic code generation with
  structural validation.

### Symbolic Reasoning (`thalos_prime.constraints`)

Z3-based SMT constraint solving with typed variables, optimization objectives,
incremental solving, and model extraction. `SymbolicConstraintEngine` provides the
full lifecycle contract and a deterministic solving guarantee.

### Autonomous Agency (`thalos_prime.agency`)

Perceive-plan-act loops with:

- `BeliefTracker` — maintains probabilistic beliefs with deterministic updates.
- `ActionExecutor` — deterministic action handler registry; raises typed
  `ActionExecutionError` when handlers fail.
- `AgentLoop` — orchestrates perceive-plan-act cycles.

### Planning (`thalos_prime.planning`)

- `TreeOfThoughtsPlanner` — deterministic multi-path thought-node planning.
- `MCTSPlanner` — Monte Carlo Tree Search with seeded pseudo-random simulation.

### Knowledge Graph (`thalos_prime.knowledge_graph`, `thalos_prime.graph_rag`)

Neo4j-compatible graph with hybrid graph+text retrieval (Graph-RAG). All traversals
are BFS with deterministic node ordering.

### Infrastructure Synthesis (`thalos_prime.infra_synthesis`)

YAML-schema → multi-provider artifact generation:

- **Adapters**: Terraform, OpenTofu, Cloudflare, GitHub Actions, Docker.
- **Policy engine**: `require_ssl`, `limit_scaling`, and extensible rules.
- **Release strategies**: `direct`, `blue_green`, `canary`.
- **Drift detection**: DeepDiff-based schema drift detection and rollback.
- **State backend**: versioned, atomic checkpoint/restore.

### REST API (`thalos_prime.api`, `thalos_prime.babel.interface.api`)

FastAPI server exposing chat, search, agent, and admin routes with a Matrix-style
browser interface. See `thalos_prime/__init__.py:get_babel_endpoints()` for the
canonical endpoint map.

### CLI (`thalos_prime.cli`, `thalos_prime.infra_synthesis.cli`)

- **`thalos_prime.cli`** — exports `run_cli` and `build_parser` for the main
  Thalos Prime command-line interface.
- **`thalos_prime.infra_synthesis.cli`** — `thalos` entrypoint for
  infrastructure synthesis operations.

---

## Deterministic Innovation Objective

Innovation is modeled as constrained deterministic selection:

`x* = arg max_{x∈Ω} (U(x) · N(x) · F(x) · E(x))  s.t.  K(x) ≤ 0`

Where `U` is utility, `N` is novelty, `F` is feasibility, `E` is
explainability/reproducibility, and `K` captures hard-constraint violations.

For runtime execution:

`Artifact = Φ(ConceptGraph, Constraints, Objectives, DeterministicSeed)`

This objective governs ranking and selection of output artifacts.

---

## Purity Network Formalism and Convergence

Given `N = (V, E, Θ)` with transitions `x_(t+1) = T_(θ_t)(x_t)`, purity is:

`Π(N) = α·Coherence + β·Determinism + γ·ConstraintSatisfaction + δ·ProvenanceIntegrity − λ·EntropyLeak`

Convergence target:

`max_Θ Π(N)  s.t.  ∀t: K(x_t) ≤ 0, x_t reproducible, trace(x_t) complete`

Purity invariants:

1. Semantic identity continuity.
2. Complete causal/provenance traceability.
3. Hard-constraint closure.
4. Deterministic replay with same input and seed.
5. Entropy/ambiguity reduction per stage.

---

## Closed-Loop Runtime Mapping

| Phase | Repository mapping |
|---|---|
| Perception/Parse | ingest and semantic extraction (`api/routes`, `library_of_sense/retrieval`, `lob_babel_enumerator`) |
| Abstraction | symbol/entity/claim normalization (`artifacts/schema`, `validation/pipeline`, `reasoning_tpl/derive`) |
| Recombination | planner and graph traversal (`planning`, `knowledge_graph`, `graph_rag`) |
| Constraint Projection | symbolic + policy filtering (`constraints`, `infra_synthesis/policy`, validation gates) |
| Selection | utility/coherence/risk/novelty scoring (`lob_decoder`, `api/routes/search`, reasoning control plane) |
| Externalization | API responses, reports, executable plans (`api`, `export/presenter`, `infra_synthesis`) |
| Recursion | feedback-driven rescoring and stabilization (`belief/ledger`, `audit/trail`, maintenance loops) |

---

## Acceptance Criteria

- Objective and purity metadata are emitted in response metadata as additive fields.
- Policy/schema version headers are present for runtime signaling.
- Per-stage scores, constraint outcomes, seed, config hash, and transition logs are observable.
- Checkpoint/restore preserves objective/purity continuity.
- Determinism, constraint-closure, provenance-completeness, and API-compatibility tests pass.
- `make check` passes with no nondeterministic regressions.

---

## Determinism Guarantees

- A single integer `--seed` seeds an isolated `random.Random(seed)` instance.
- All collections use stable, deterministic sort keys (`score DESC, doc_id ASC`).
- No module-level RNG state; no implicit async at module boundary.
- Checkpoints include seed, configuration hash, and schema version for exact
  replay.

---

## Event Log Schema

All state transitions emit structured JSONL events with:

| Field | Description |
|---|---|
| `component` | Subsystem name |
| `method` | Lifecycle method invoked |
| `seed` | Deterministic seed at invocation |
| `timestamp` | ISO-8601 UTC timestamp |
| `details` | Human-readable transition summary |

---

## References

- Full API reference: `thalos_prime/__init__.py`
- Lifecycle base class: `thalos_prime/lifecycle.py`
- Configuration: `thalos_prime/config.py`
- Detailed guide: `docs/guides/ARCHITECTURE.md`
- Implementation status: `IMPLEMENTATION_COMPLETE.md`
