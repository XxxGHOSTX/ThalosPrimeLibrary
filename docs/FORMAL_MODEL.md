# Thalos Prime — Novel Formal System (Greenfield Definition)

> **Scope**: Authoritative greenfield formal model for Thalos Prime.
> This document **proposes** the formal system first, then maps every element
> onto the current repository as a target architecture.  It is not an audit of
> existing code; it is the design authority that the implementation converges
> toward.

---

## Epistemic Axiom

The global information environment is defined by a structural imbalance: exponential
data production has outpaced the capacity for verifiable, coherence-ranked retrieval.
At any moment, the volume of potentially true, useful, or actionable information
vastly exceeds what any human (or unguided machine) can verify.

Thalos Prime is the formal answer to that asymmetry.

---

## 1. The Formal System T

**T** is the seven-tuple:

```
T = (Ω, Σ, G, E, κ, δ, Φ)
```

| Symbol | Name | Definition |
|--------|------|------------|
| **Ω** | Information Universe | The Library of Babel modeled as Σ^3200 — a discrete, deterministic, effectively infinite corpus.  \|Ω\| ≈ 29^3200. |
| **Σ** | Alphabet | The 29-character Babel charset: {`a`–`z`, `' '`, `','`, `'.'`}. |
| **G** | Generator | A computable bijection G: H → Σ^3200 mapping a hex address h ∈ H to a unique 3 200-character page.  Identical h always yields identical output (determinism invariant). |
| **E** | Enumerator | A deterministic function E: Q × ℕ × ℕ → H\* mapping a query string q ∈ Q, a seed s ∈ ℕ, and a depth d ∈ ℕ to a ranked, reproducible list of candidate addresses. |
| **κ** | Coherence Measure | A computable function κ: Σ\* → [0, 100] ⊂ ℝ.  κ is a weighted combination of four sub-metrics: language density λ, structural density σ, n-gram probability η, and exact-match density μ. |
| **δ** | Epistemic Filter | A predicate δ(x) ≡ (κ(x) ≥ κ_min), where κ_min ∈ [0, 100] (default 80.0). Only pages satisfying δ advance through the pipeline. |
| **Φ** | Assembler | A deterministic function Φ: H\* → Σ^1 312 000 that concatenates top-ranked pages into a volume of exactly 1 312 000 characters (410 pages × 3 200 chars/page), satisfying the volume invariant. |

### 1.1 Formal Properties

| Property | Statement |
|----------|-----------|
| **Determinism** | ∀ h ∈ H: G(h) = G(h).  ∀ q, s, d: E(q, s, d) = E(q, s, d). |
| **Totality** | G is total: every valid address has a unique page. |
| **Coherence first-class** | κ is applied before any result is surfaced; no result with κ(x) < κ_min reaches the user. |
| **Volume invariant** | \|Φ(H\*)| = 1 312 000 or the system raises DeterministicHalt. |
| **Verifiability** | Every output carries provenance (address, seed, config hash, coherence scores). Any output can be independently reproduced and verified. |

### 1.2 Sub-Metric Decomposition of κ

```
κ(x) = w_λ · λ(x) + w_σ · σ(x) + w_η · η(x) + w_μ · μ(x, q)
```

where:

- **λ(x)** — English word-density score (language detection).
- **σ(x)** — Sentence-boundary and punctuation-structure score.
- **η(x)** — Bigram / trigram probability against a reference distribution.
- **μ(x, q)** — Exact-match density of query q in page x.
- Weights w_λ + w_σ + w_η + w_μ = 1.0 (default: 0.30, 0.20, 0.20, 0.30).

---

## 2. The Structural Imbalance Problem (Formal Statement)

Let:

- **P(t)** = volume of information produced by time t (grows super-linearly).
- **V(t)** = human + unguided-machine verification bandwidth at time t (grows slowly).
- **Δ(t)** = P(t) − V(t) — the epistemic gap.

**Observation**: Δ(t) → ∞ as t → ∞.

**Thalos Prime's role**: Make δ computable and fast enough that for any user query q
and coherence threshold κ_min, the system returns a verified, coherent artifact A with
κ(A) ≥ κ_min in bounded time, despite |Ω| → ∞.

The system achieves this through the ordered pipeline:

```
q, s ──► E ──► H* ──► G ──► pages ──► κ ──► δ ──► Φ ──► A
```

Every stage is deterministic.  Given identical (q, s, κ_min, config), A is
byte-identical across runs.

---

## 3. Control Plane / Data Plane Mapping

The formal system T maps onto the control-plane / data-plane separation as follows:

| Formal Element | Plane | Repository Module |
|----------------|-------|-------------------|
| E (Enumerator) | Data | `thalos_prime/lob_babel_enumerator.py` |
| G (Generator) | Data | `thalos_prime/lob_babel_generator.py` |
| κ (Coherence Measure) | Data | `thalos_prime/lob_decoder.py` |
| δ (Epistemic Filter) | Control | `thalos_prime/api/routes/chat.py`, `errors.py` |
| Φ (Assembler) | Data | Pipeline assembly in `thalos_prime/api/routes/` |
| Lifecycle contract | Control | `thalos_prime/lifecycle.py`, `thalos_nexus/` |
| Provenance logging | Control | `thalos_prime/audit/trail.py` |
| Belief state machine | Control | `thalos_prime/belief/ledger.py` |
| Seed management | Control | `thalos_nexus/spine.py` |

---

## 4. Greenfield Target Architecture

This section describes the ideal state that the current repository should converge
toward.  Each item is a design goal, not an audit finding.

### 4.1 Generative Mode (SearchMode.GENERATIVE)

The formal system T extends to include a Generative sub-mode G_gen where G draws
from a curated Thalos Prime corpus rather than from Ω directly.  This guarantees
κ(G_gen(q, s)) ≥ 80.0 for all q, s by construction.

**Target module**: `thalos_prime/generative_engine.py` (already present in this PR).

### 4.2 Coherence Enforcement at API Boundary

δ must be applied at every external-facing API endpoint.  The system must raise
`CoherenceThresholdError` (carrying min_score, best_score, attempts, time_budget_s,
checkpoint, mode) rather than silently returning below-threshold results.

**Target module**: `thalos_prime/errors.py`, `thalos_prime/api/routes/chat.py`.

### 4.3 Single-Launch Lifecycle

T's lifecycle contract requires a single, deterministic entry point that:
1. Validates the environment.
2. Initialises all subsystems via the control plane.
3. Starts bounded background workers (index_refresh, cache_warm, session_maintenance).
4. Starts the API server.

**Target module**: `thalos_prime/__main__.py`.

### 4.4 Deterministic Replay

For any run with (q, s, κ_min, config), the system must produce byte-identical
output A.  Checkpoints must include seed, config_hash, schema_version, and
state_hash (blake2b).

**Target modules**: `thalos_prime/checkpoint.py` (existing), `thalos_nexus/spine.py`.

### 4.5 PRP-Indexed Addressing

The formal enumerator E may be accelerated by a Pseudo-Random Permutation (PRP)
index using HMAC-SHA256 as the keyed PRF, mapping query tokens to coordinate pairs
in the address space without collisions.

**Target module**: `thalos_prime/indexing/prp.py`.

---

## 5. Formal Invariants (Machine-Checkable)

The following invariants must hold at all times.  They are enforced by the lifecycle
validator (`tools/validate_lifecycle.py`) and CI gates:

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| I-1 | G is total and deterministic | Unit tests with fixed address vectors |
| I-2 | E is seeded and reproducible | Unit tests with fixed (q, s) pairs |
| I-3 | κ ∈ [0, 100] for all inputs | Type annotation + runtime assertion |
| I-4 | δ(x) = False → CoherenceThresholdError raised | API integration tests |
| I-5 | \|Φ(H\*)| = 1 312 000 or DeterministicHalt | Pipeline assembly tests |
| I-6 | All state transitions logged with seed + config_hash | AuditTrail event log |
| I-7 | No subsystem may bypass δ | Prohibited-pattern scanner |

---

## 6. Mapping to Patent Claims

| Formal Element | Patent Claim Basis |
|----------------|--------------------|
| T = (Ω, Σ, G, E, κ, δ, Φ) | Coherence-first discovery over deterministic infinite data space |
| κ sub-metrics | Hybrid heuristic + optional LLM normalization coherence engine |
| δ (epistemic filter) | Recursive stabilization with configurable threshold |
| E × G pipeline | Deterministic corpus + fragment enumerator |
| Φ (assembler) | Synthesis and assembly engine with provenance |
| Provenance metadata | Cross-domain translation with preserved lineage |
| SBI substrate hook | Optional biological/wetware parallel constraint solver |

See `docs/guides/Thalos_Prime_Patent_Charter.md` and
`docs/guides/Thalos_Prime_Claims_Scaffold.md` for full claim language.

---

## 7. Extension Points (Future Phases)

| Extension | Formal Addition | Phase |
|-----------|----------------|-------|
| Semantic embeddings | Add V: Σ\* → ℝ^n (vector map) to T | Phase 3 |
| Distributed shard manager | Partition H across nodes; Φ becomes distributed | Phase 4 |
| SBI / wetware co-processor | Replace δ with δ_bio: Σ\* → {pass, reject} backed by biological substrate | Phase 5 |
| Quantum acceleration | Replace E with E_q: quantum walk over H | Phase 5+ |

---

*Last updated: 2026-04-02 — greenfield formal model, authoritative.*
