# ThalosPrimeLibrary — Architecture

> "In the Library of Babel, every truth already exists — Thalos Prime finds it."

This document describes the production architecture of ThalosPrimeLibrary (TPL), a
deterministic epistemic operating system that indexes, validates, and reasons over
knowledge artifacts.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [System Overview](#system-overview)
3. [Data Pipeline](#data-pipeline)
4. [Deterministic Innovation Objective](#deterministic-innovation-objective)
5. [Purity Network Formalism](#purity-network-formalism)
6. [Closed-Loop Compilation Contract](#closed-loop-compilation-contract)
7. [Control Plane Subsystems](#control-plane-subsystems)
8. [Data Plane Subsystems](#data-plane-subsystems)
9. [REST API Layer](#rest-api-layer)
10. [Lifecycle Contract](#lifecycle-contract)
11. [Determinism and Replay](#determinism-and-replay)
12. [State Surfaces](#state-surfaces)
13. [Audit and Provenance](#audit-and-provenance)
14. [Test Coverage](#test-coverage)
15. [Conformance Rules](#conformance-rules)

---

## Design Principles

| Principle | Enforcement |
|-----------|-------------|
| **Determinism** | Identical inputs → identical outputs and state transitions. All randomness seeded and logged. |
| **Control / Data separation** | Control Plane manages lifecycle and state; Data Plane executes computation only. No mixing. |
| **Epistemic traceability** | Every artifact carries full provenance. No validation-bypass, no lost lineage. |
| **Tamper-evident auditability** | SHA-256-chained append-only event log. `verify_integrity()` re-derives the full chain. |
| **Lifecycle contracts** | Every Control Plane subsystem implements exactly: `initialize → validate → operate → reconcile → checkpoint → terminate`. |
| **No partial implementations** | Fully implemented, fully integrated, fully operational. No stubs, mocks, or TODOs in production code. |

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE                                 │
│                                                                      │
│  ┌────────────────┐   ┌─────────────────┐   ┌──────────────────┐    │
│  │  ValidationPipeline │   BeliefLedger   │   │ TplReasoningLayer│    │
│  │  (6-stage)     │   │  (B_t state     │   │  (claim derive)  │    │
│  │                │   │   machine)      │   │                  │    │
│  └───────┬────────┘   └───────┬─────────┘   └────────┬─────────┘    │
│          │                    │                       │              │
│          └────────────────────┴───────────────────────┘              │
│                               │                                      │
│                          AuditTrail (SHA-256 chained)                │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ interfaces only
┌───────────────────────────────▼──────────────────────────────────────┐
│                          DATA PLANE                                  │
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────────────────┐    │
│  │  PrpIndexer  │   │ EdgeExecutor │   │   ExportPresenter     │    │
│  │ (HMAC-SHA256 │   │  (bounded    │   │ (ProofTrace, Lineage, │    │
│  │  coordinate) │   │   deque)     │   │  JSON export)         │    │
│  └──────────────┘   └──────────────┘   └───────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│                         REST API LAYER                               │
│  POST /ingest   GET /artifact/{id}   POST /derive                    │
│  GET /export/{id}   GET /graph/{id}  POST /consensus                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Pipeline

The canonical TPL pipeline processes knowledge in five sequential stages:

```
raw data
   │
   ▼
[Artifact.create]  ──── SHA-256 identity, canonical form, source URIs, provenance
   │
   ▼
[PrpIndexer]       ──── HMAC-SHA256(key, sha256(content)[:16]) → 5-tuple Coordinate
   │
   ▼
[ValidationPipeline] ── 6 deterministic stages → ValidationVerdict + FacsBundle
   │
   ▼
[BeliefLedger]     ──── admit → (accept | dispute | reject) state machine
   │
   ▼
[TplReasoningLayer] ─── derive claims from ACCEPTED artifacts → CandidateClaim
   │
   ▼
[ExportPresenter]  ──── ProofTrace + LineageGraph + deterministic JSON
```

**Contract**: Code that bypasses validation, loses provenance, or collapses
belief state into a stateless response is **nonconforming** to this architecture.

---

## Deterministic Innovation Objective

TPL treats invention as constrained optimization over a deterministic candidate space:

`x* = arg max_{x∈Ω} (U(x) · N(x) · F(x) · E(x))  s.t.  K(x) ≤ 0`

Where:

- `U(x)` = utility
- `N(x)` = novelty via non-trivial recombination
- `F(x)` = feasibility under explicit constraints
- `E(x)` = explainability and reproducibility
- `K(x)` = hard-constraint violations (must remain bounded/zero)

This objective is the governing selection rule for generated artifacts and is
enforced by deterministic scoring, policy gates, and replayable state.

---

## Purity Network Formalism

For system network `N = (V, E, Θ)` and transitions `x_(t+1) = T_(θ_t)(x_t)`,
purity is measured as:

`Π(N) = α·Coherence + β·Determinism + γ·ConstraintSatisfaction + δ·ProvenanceIntegrity − λ·EntropyLeak`

Primary stability goal:

`max_Θ Π(N)  s.t.  ∀t: K(x_t) ≤ 0, x_t reproducible, trace(x_t) complete`

### Purity Invariants (non-negotiable)

1. Semantic identity continuity across transformations.
2. Complete derivation/provenance chain for every output.
3. Hard-constraint closure: invalid states rejected early.
4. Deterministic replay for identical input + seed.
5. Entropy/ambiguity reduction at each stage transition.

### Convergence Semantics

- Each cycle must tighten constraints, improve traceability, and reduce drift.
- Objective is self-stabilizing epistemic behavior, not single-pass generation.
- Stopping criteria must be deterministic, explicit, and auditable.

---

## Closed-Loop Compilation Contract

Artifact generation is a deterministic compiler:

`Artifact = Φ(ConceptGraph, Constraints, Objectives, DeterministicSeed)`

### Runtime phase mapping to repository surfaces

| Phase | Runtime role | Repository surfaces |
|---|---|---|
| Perception / Parse | Ingest and semantic extraction | `thalos_prime/api/routes/search.py`, `thalos_prime/library_of_sense/retrieval/`, `thalos_prime/lob_babel_enumerator.py` |
| Abstraction | Symbol/entity/claim normalization | `thalos_prime/artifacts/schema.py`, `thalos_prime/validation/pipeline.py`, `thalos_prime/reasoning_tpl/derive.py` |
| Recombination | Graph traversal + planner search | `thalos_prime/planning/` (MCTS/ToT), `thalos_prime/knowledge_graph/`, `thalos_prime/graph_rag/` |
| Constraint Projection | Symbolic constraints + policy gates | `thalos_prime/constraints/`, `thalos_prime/infra_synthesis/policy/`, `thalos_prime/validation/pipeline.py` |
| Selection | Utility/coherence/risk/novelty scoring | `thalos_prime/lob_decoder.py`, `thalos_prime/api/routes/search.py`, `thalos_prime/reasoning/` |
| Externalization | API artifact/report/executable plan output | `thalos_prime/api/`, `thalos_prime/export/presenter.py`, `thalos_prime/infra_synthesis/` |
| Recursion | Feedback, re-score, stabilize | `thalos_prime/belief/ledger.py`, `thalos_prime/audit/trail.py`, `thalos_prime/__main__.py` background maintenance loops |

### API contract updates

- Responses must expose objective/purity metadata in response metadata payloads.
- Runtime signaling must include policy/version headers.
- Existing response schemas remain backward compatible; new fields are additive.

---

## Control Plane Subsystems

### Artifact Schema (`thalos_prime/artifacts/schema.py`)

The canonical data model for all knowledge artifacts.

| Class | Purpose |
|-------|---------|
| `Artifact` | SHA-256-identified content unit; canonical form, confidence, versioning |
| `ProvenanceNode` | Lineage record: parent IDs, derivation steps, source URI |
| `DerivationStep` | Single step in a derivation chain |
| `FacsBundle` | Flags / Annotations / Contradiction-map / Suspension-log |
| `GenesisLock` | HMAC-SHA256 sign and verify for tamper detection |
| `ValidationStatus` | `PENDING` → `ACCEPTED` / `DISPUTED` / `REJECTED` |

**Key invariants:**
- `artifact_id` is always the SHA-256 of `canonical_content` encoded as UTF-8.
- All fields are explicitly typed (Pydantic BaseModel).
- `GenesisLock.sign(artifact)` and `.verify(artifact)` use HMAC-SHA256.

### Belief Ledger (`thalos_prime/belief/ledger.py`)

The epistemic state machine `B_t`. Tracks all artifacts across acceptance states.

```
PENDING  →  ACCEPTED
PENDING  →  DISPUTED
PENDING  →  REJECTED
DISPUTED →  ACCEPTED
DISPUTED →  REJECTED
```

| Method | Description |
|--------|-------------|
| `admit(artifact, coord_hex, confidence, ts)` | Admit an artifact as PENDING |
| `accept(artifact_id, ts)` | Transition to ACCEPTED |
| `dispute(artifact_id, reason, ts)` | Transition to DISPUTED |
| `reject(artifact_id, reason, ts)` | Transition to REJECTED; artifact retained for audit |
| `get_by_state(state)` | Query all records in a given state |
| `query_by_confidence(min, state)` | Filter by minimum confidence score |
| `resolve_by_coordinate(coord_hex)` | Look up record by coordinate |
| `get_lineage(artifact_id)` | Traverse ancestor chain |
| `checkpoint()` / `restore(cp)` | Serialise / restore full ledger state |

**Key invariants:**
- Double-admit raises `ValueError`.
- Rejected records are retained (not deleted) for audit compliance.
- All state transitions are logged with nanosecond timestamps.

### Validation Pipeline (`thalos_prime/validation/pipeline.py`)

Six deterministic stages, run sequentially. Returns `ValidationVerdict` and `FacsBundle`.

| Stage | Name | Passes when |
|-------|------|-------------|
| 1 | Canonicalization | Content non-empty after whitespace normalisation |
| 2 | Source Binding | At least one source URI present |
| 3 | Consistency | Content > 10 chars and confidence in [0.0, 1.0] |
| 4 | Contradiction Search | No duplicate artifact in accepted ledger |
| 5 | Confidence Assignment | Weighted score of stages 1–4 and artifact confidence |
| 6 | Admission Control | Final threshold gate → ACCEPTED / PENDING / REJECTED |

**Confidence thresholds** (see `pipeline.py`):
- `score >= 1.0` → ACCEPTED  
- `score >= _ADMIT_PENDING_THRESHOLD` → PENDING  
- else → REJECTED

### Reasoning Layer (`thalos_prime/reasoning_tpl/derive.py`)

Derives candidate claims **exclusively** from ACCEPTED ledger artifacts.

| Method | Description |
|--------|-------------|
| `derive(artifact_ids, operation, ts)` | Main derivation entry point |
| `operate(...)` | Lifecycle alias for `derive()` |
| `initialize()` | Set `_initialized = True` |
| `validate()` | Returns `True` when initialized |
| `checkpoint()` | Returns `{layer_id, initialized, schema_version}` |

**Supported derivation operations** (`DeriveOperation`):
- `SYNTHESIZE` — Join all artifact content with ` | `
- `SUMMARIZE` — First 200 chars of the first artifact
- `EXTRACT` — Key sentences > 20 chars, up to 5
- `INFER` — `"Inferred: " + first 50 chars of each artifact`
- `COMBINE` — Same as SYNTHESIZE

**Key invariants:**
- Derived claims always have `approved=False` — no self-approval.
- Every derivation step is appended to the `AuditTrail`.
- Raises `ValueError` if any input artifact is not ACCEPTED.

### Audit Trail (`thalos_prime/audit/trail.py`)

SHA-256-chained, append-only tamper-evident event log.

| Method | Description |
|--------|-------------|
| `append(event_type, artifact_id, ts, payload)` | Append a new event |
| `verify_integrity()` | Re-derive full SHA-256 chain; returns `False` on tamper |
| `get_events(event_type)` | Retrieve all (or filtered-by-type) events |
| `get_events_for_artifact(artifact_id)` | Filter events by artifact ID |
| `checkpoint()` / `restore(cp)` | Serialise / restore; integrity checked on restore |

**AuditEventType values:**
`ARTIFACT_ADMITTED`, `ARTIFACT_ACCEPTED`, `ARTIFACT_DISPUTED`, `ARTIFACT_REJECTED`,
`DERIVATION_STEP`, `VALIDATION_COMPLETED`, `CHECKPOINT_CREATED`, `CHECKPOINT_RESTORED`

---

## Data Plane Subsystems

### PRP Indexer (`thalos_prime/indexing/prp.py`)

Deterministic PRF-based coordinate derivation. **No lifecycle methods.**

```
content (str)
   │
   └─ sha256(content.encode('utf-8'))[:16]  →  16-byte input block
         │
         └─ HMAC-SHA256(key, block)[:16]   →  16-byte PRF output
               │
               └─ Coordinate extraction (first 8 bytes):
                    bytes[0:2] → hexagon  (0–65535)
                    bytes[2:3] → wall     (0–255)
                    bytes[3:4] → shelf    (0–255)
                    bytes[4:6] → volume   (0–65535)
                    bytes[6:8] → page     (0–65535)
```

**Key invariants:**
- Key must be ≥ 16 bytes.
- Two indexers with different keys produce independent address spaces.
- `index_artifact()` produces `ArtifactCoordinates` with five typed coordinates.
- AES-128-ECB was considered as an alternative but rejected; it has known weaknesses as a block cipher mode (CodeQL `py/weak-cryptographic-algorithm`). HMAC-SHA256 provides keyed pseudorandomness without those weaknesses.

### Edge Executor (`thalos_prime/edge/executor.py`)

Bounded `deque`-backed deterministic executor. **No threads, no async.**

- `submit(fn, *args)` — enqueue a callable; raises `OverflowError` when full
- `run_all()` — drain the queue, execute in FIFO order
- `DeviceType` — `CPU`, `GPU`, `TPU`, `EDGE`

### Export Presenter (`thalos_prime/export/presenter.py`)

Pure Data Plane — **no lifecycle methods.**

| Method | Returns |
|--------|---------|
| `export_artifact_json(artifact)` | `dict[str, object]` via `model_dump()` |
| `build_proof_trace(artifact, verdict, trail, ledger)` | `ProofTrace` |
| `build_lineage_graph(artifact_id, ledger)` | `LineageGraph` |
| `export_to_json(data)` | Deterministic JSON string (`sort_keys=True`, 2-space indent) |

**`ProofTrace` fields:** `trace_id`, `artifact_id`, `derivation_steps`,
`validation_stages`, `audit_events`, `lineage`, `timestamp_ns`, `schema_version`

**`LineageGraph` fields:** `graph_id`, `root_artifact_id`, `nodes`, `edges`, `timestamp_ns`

---

## REST API Layer

All artifact endpoints are registered under `/api/v1/artifacts/`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest` | Canonicalise → PRP index → 6-stage validate → admit to belief base |
| `GET`  | `/artifact/{id}` | Retrieve BeliefRecord (404 if unknown) |
| `POST` | `/derive` | Derive claim from ACCEPTED artifacts |
| `GET`  | `/export/{id}` | JSON export + ProofTrace bundle (404 if unknown) |
| `GET`  | `/graph/{id}` | LineageGraph (404 if unknown) |
| `POST` | `/consensus` | Highest-confidence ACCEPTED artifact from candidate set |

**Request / Response models** (Pydantic):
- `IngestRequest` — `{content, source_uris, metadata?}`
- `DeriveRequest` — `{artifact_ids, operation}`
- `ConsensusRequest` — `{artifact_ids, min_confidence}`
- `ConsensusResponse` — `{consensus_artifact_id, agreement_score, participant_count, message}`

### Objective/Purity response metadata contract

- Include per-request objective context (utility/novelty/feasibility/explainability weights or defaults).
- Include purity metrics and constraint outcomes in metadata where applicable.
- Include policy and schema version headers for runtime interpretability.
- Preserve backward compatibility by keeping existing response fields unchanged.

---

## Lifecycle Contract

Every Control Plane subsystem must implement all six lifecycle methods:

| Method | Semantics |
|--------|-----------|
| `initialize()` | Allocate resources; set up initial state. Raise typed exception on failure. |
| `validate()` | Check all invariants; block operation until satisfied. Return `bool`. |
| `operate(...)` | Execute primary work; idempotent where applicable. |
| `reconcile()` | Converge to consistent state; deterministically succeed or halt. |
| `checkpoint()` | Serialise state atomically. Include `schema_version`. |
| `terminate()` | Release resources; leave no orphaned state. |

Data Plane components (`PrpIndexer`, `EdgeExecutor`, `ExportPresenter`) must **not**
implement lifecycle methods — they perform computation only.

The `tools/validate_lifecycle.py` CI tool enforces this contract at build time.

---

## Determinism and Replay

To guarantee deterministic replay:

- All timestamps are passed as explicit `timestamp_ns: int` arguments.
- HMAC keys and PRP keys must be persisted in checkpoint metadata.
- `checkpoint()` output includes a `schema_version` field.
- Restore operations validate `schema_version` before applying state.
- JSON export uses `sort_keys=True` to eliminate ordering non-determinism.
- Event logs include `timestamp_ns`, `artifact_id`, and payload for full replay.

---

## State Surfaces

| Subsystem | State description | Checkpoint method |
|-----------|------------------|-------------------|
| `BeliefLedger` | `{artifact_id → BeliefRecord}` dict | `checkpoint()` / `restore()` |
| `AuditTrail` | `[AuditEvent]` deque + SHA-256 chain | `checkpoint()` / `restore()` |
| `TplReasoningLayer` | `{layer_id, initialized}` | `checkpoint()` |

All state surfaces are serialised as plain Python dicts (JSON-compatible).
No external databases are used in the core subsystems.

Additional observability requirements:

- Record per-stage scores and constraint outcomes for each deterministic cycle.
- Persist deterministic seed, configuration hash, and transition logs.
- Preserve checkpoint/restore continuity for objective and purity state.

---

## Audit and Provenance

The TPL architecture guarantees end-to-end provenance for every artifact:

1. **Source URIs** — captured at ingestion (`Artifact.source_uris`).
2. **Derivation steps** — each `TplReasoningLayer.derive()` call records a `CandidateClaim.derivation_log` and appends a `DERIVATION_STEP` event to the `AuditTrail`.
3. **Validation stages** — all six stage results are captured in `ValidationVerdict.stage_results` and surfaced in `ProofTrace.validation_stages`.
4. **Belief state transitions** — every `admit`, `accept`, `dispute`, `reject` call is timestamped in the `BeliefRecord`.
5. **Tamper-evident chain** — `AuditTrail.verify_integrity()` re-derives the full SHA-256 chain; any modification breaks the chain.

**Genesis Lock** (`GenesisLock`): HMAC-SHA256 sign/verify for artifact-level tamper detection. Call `genesis_lock.sign(artifact)` to attach a signature; `.verify(artifact)` returns `True` only if the signature matches.

---

## Test Coverage

| Test file | Subsystem covered | Type |
|-----------|------------------|------|
| `tests/test_artifacts.py` | Artifact schema, GenesisLock, FacsBundle | Unit |
| `tests/test_indexing.py` | PrpIndexer, Coordinate, ArtifactCoordinates | Unit |
| `tests/test_belief.py` | BeliefLedger, BeliefRecord, state machine | Unit |
| `tests/test_validation.py` | ValidationPipeline, 6 stages, thresholds | Unit |
| `tests/test_audit.py` | AuditTrail, SHA-256 chain, checkpoint/restore | Unit |
| `tests/test_edge.py` | EdgeExecutor, DeviceType, overflow | Unit |
| `tests/test_reasoning.py` | TplReasoningLayer, CandidateClaim, lifecycle | Unit |
| `tests/test_export.py` | ExportPresenter, ProofTrace, LineageGraph | Unit |
| `tests/test_artifacts_api.py` | All six `/api/v1/artifacts/*` endpoints | API Integration |
| `tests/test_tpl_pipeline_integration.py` | Full 5-stage pipeline E2E | Integration |

Run all tests: `python -m pytest tests/ -q`

### Deterministic innovation and purity test strategy

- Determinism tests: same input + seed must replay identical outputs.
- Constraint-violation tests: hard constraints must halt or reject deterministically.
- Provenance completeness tests: derivation trace must remain complete end-to-end.
- API integration tests: objective/purity metadata and policy/version headers propagate without schema breakage.

---

## Conformance Rules

The following are **architectural non-conformance** conditions that must be treated as bugs:

1. **Validation bypass** — any code path that admits an artifact to the belief base without running `ValidationPipeline.validate()`.
2. **Lost provenance** — any artifact created without `source_uris` or without logging to `AuditTrail`.
3. **Collapsed belief state** — any route or function that returns a belief-state-dependent answer without querying `BeliefLedger`.
4. **Self-approval** — `TplReasoningLayer` must never call `BeliefLedger.accept()` on its own output.
5. **Lifecycle method in Data Plane** — `PrpIndexer`, `EdgeExecutor`, and `ExportPresenter` must not implement `initialize / operate / reconcile / checkpoint / terminate`.
6. **Weak cryptography** — AES-ECB must not be used. The PRP indexer uses HMAC-SHA256.
7. **Non-deterministic operations** — any use of `time.time()`, `random.random()`, or filesystem scans without explicit seeding and logging.
8. **Purity contract violation** — any path that omits objective scoring dimensions, constraint closure, or provenance-complete traceability.

---

## Verification Gate

Before merge, the repository must pass:

- `make check`
- deterministic replay checks for changed surfaces
- objective/purity observability and API compatibility checks

The release state must remain fully implemented, fully integrated, and fully
operational with no nondeterministic regressions.

---

## Greenfield Formal Design

> **Scope reframe: audit → greenfield design.**
> This section proposes the novel formal system for Thalos Prime first (as the
> authoritative design target), then maps it onto the current repository as the
> implementation architecture.  It does not analyze uploaded whitepapers or exports;
> it defines the formal model and treats the repo as the convergence target.

### Epistemic Premise

The global information environment is defined by a structural imbalance: exponential
data production has outpaced the capacity for verifiable, coherence-ranked retrieval.
Thalos Prime resolves this asymmetry by making verification (κ) computable and
deterministic, filtering the effectively infinite information universe (Ω) down to
artifacts that provably satisfy the user's coherence threshold.

### Formal System T

The novel formal system is **T = ⟨D, I, R, V, E, P, B_t⟩**.
See [`docs/FORMAL_MODEL.md`](docs/FORMAL_MODEL.md) for the complete authoritative
Formal Specification v1.0 definition, including:

- All seven formal elements with precise types (e.g. I: X\* → ℤⁿ, R: (ℤⁿ × B_t) → H, V: H → {A,P,D,R}).
- Canonical artifact schema ⟨c_i, s_i, p_i, v_i, τ_i, λ_i⟩ and coordinate hierarchy ⟨h_i, w_i, s_i, v_i, p_i⟩.
- Two-tier architecture (Core Production + Advanced Research Modules).
- B_t four-state machine (Accepted/Pending/Disputed/Rejected) with update rule B_{t+1} = V(R(I(D_t), B_t)).
- 4-round Feistel PRP construction with HMAC-SHA256.
- R-Matrix YBE in braided form; Persistent Homology (β₀/β₁/β₂); POTSA multilingual ingestion.
- FACS Bundle (Flags, Annotations, Contradiction maps, Suspension logs) with 238ms latency target.
- Genesis Lock TrustRoot = KDF(HW_ID ‖ Sign_Auctor(IEPL)) and Aegis governance.
- Machine-checkable invariants I-Tr through I-9; failure mode analysis.
- Math-to-code mappings; 8 design principles.

### Architecture as Target

Every module in this architecture document is the **implementation convergence target**
for one or more elements of T.  The control-plane / data-plane boundary maps exactly
to the T decomposition: I, R, and E live in the data plane; V, P, B_t, and the
lifecycle contract are enforced by the control plane.

| Formal Element | Plane | Key Module |
|----------------|-------|------------|
| D (Artifact Corpus / X\*) | Both | `thalos_prime/belief/ledger.py` (ctrl), `lob_babel_generator.py` (data) |
| I (PRP Feistel Bijection / X\*→ℤⁿ) | Data | `thalos_prime/indexing/prp.py`, `lob_babel_enumerator.py` |
| R (Reasoning Operator / (ℤⁿ×B_t)→H) | Data | `thalos_prime/lob_decoder.py` |
| V (Validation / H→{A,P,D,R} + Genesis Lock) | Control | `thalos_prime/audit/trail.py`, `thalos_nexus/nucleus.py` |
| E (Edge Execution / Ω_edge) | Data | `lob_babel_generator.py`, `lob_decoder.py` |
| P (Presentation / FACS Bundle / B_t→Γ) | Control | `thalos_prime/audit/trail.py`, `belief/ledger.py` |
| B_t (Belief Base / A\* four-state) | Control | `thalos_prime/belief/ledger.py`, `thalos_nexus/spine.py` |
