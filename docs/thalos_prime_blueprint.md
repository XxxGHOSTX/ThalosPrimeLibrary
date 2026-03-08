# Thalos Prime — Deterministic Architecture Blueprint

> **Scope**: Reference documentation for contributors. No runtime code changes.
> All "SBI" and biological references in this document are software-architecture
> metaphors; see [`docs/SBI_DISCLAIMER.md`](SBI_DISCLAIMER.md) for full context.

---

## Table of Contents

1. [Control Plane / Data Plane Separation](#1-control-plane--data-plane-separation)
2. [7-Stage MNN Production Pipeline](#2-7-stage-mnn-production-pipeline)
3. [Determinism Guarantees](#3-determinism-guarantees)
4. [Synthetic Biological Intelligence (SBI) — Reference Only](#4-synthetic-biological-intelligence-sbi--reference-only)
5. [CI / Coverage Expectations](#5-ci--coverage-expectations)
6. [LRU Caching](#6-lru-caching)
7. [Dry-Run / Offline Mode](#7-dry-run--offline-mode)

---

## 1. Control Plane / Data Plane Separation

Thalos Prime enforces a hard boundary between coordination logic and
computational work.

| Plane | Components | Responsibilities |
|---|---|---|
| **Control Plane** | `ControlPlane`, lifecycle orchestrator | Lifecycle coordination, seed management, JSONL event logging, deterministic halt, reconciliation |
| **Data Plane** | `BabelClient`, `TraversalPlanner`, `WordExtractor`, `ConstraintSolver`, `VolumeAssembler` | Computational work only; no coordination, scheduling, or state management |

**Key invariants:**

- No circular dependencies between planes.
- Data-plane components receive all required state via explicit injection;
  they never read or write shared globals.
- Only the control plane may call `initialize()`, `validate()`, `reconcile()`,
  `checkpoint()`, or `terminate()`.

Every subsystem implements the six required lifecycle methods:

```
initialize() → validate() → operate() → reconcile() → checkpoint() → terminate()
```

An invariant violation in any method raises `DeterministicHalt` with a full
state snapshot. Silent degradation is prohibited.

---

## 2. 7-Stage MNN Production Pipeline

The **Multi-Normalization Network (MNN)** pipeline converts a natural-language
query into a deterministically assembled volume of exactly **1,312,000
characters** (410 pages × 3,200 chars/page).

### Stage 1 — Normalization

- Input: raw query string.
- Normalizes case, strips non-Babel characters, and validates against the
  29-character charset (`space`, `,`, `.`, `a–z`).
- Emits a canonical query token used as the seed input for all downstream
  stages.
- **Determinism**: identical raw queries → identical canonical tokens.

### Stage 2 — Constraint Generation

- Builds symbolic constraints on the search space (e.g., minimum n-gram size,
  maximum page count, character distribution bounds).
- Uses the `ConstraintSolver` (backed by Z3) to enumerate satisfying
  configurations.
- All constraints are logged with their configuration hash before evaluation.

### Stage 3 — Index Mapping

- The `BabelEnumerator` maps the canonical query token to a ranked list of
  hexadecimal candidate addresses using seeded hashing.
- N-gram decomposition: sizes `min_ngram_size` to `max_ngram_size` (defaults
  2–5).
- Address list is sorted by `(score DESC, address ASC)` for stable ordering.

### Stage 4 — Sequence Generation

- The `BabelGenerator` renders each candidate address into a 3,200-character
  page using the deterministic Basile algorithm.
- Seed for the pseudo-random generator is derived from the address string; the
  same address always produces the same page.
- Pages shorter than 3,200 characters are right-padded with spaces; pages
  longer are hard-trimmed.

### Stage 5 — Analysis & Filtering

- The `BabelDecoder` scores each generated page with four coherence metrics:
  1. **Language score** — English word density.
  2. **Structure score** — Punctuation and sentence-boundary density.
  3. **N-gram score** — Bigram/trigram probability against a reference corpus.
  4. **Exact-match score** — Direct substring hit for the canonical query token.
- Pages below the configured coherence threshold are discarded.

### Stage 6 — Center-Weighted Scoring

- Surviving pages receive a BM25 relevance score against the canonical query.
- Center-weighting applies a positional bonus to tokens near the middle of each
  page, rewarding coherent passages that are unlikely to be edge artifacts.
- Final ranking: `(bm25_score DESC, doc_id ASC)` — deterministic tiebreak.

### Stage 7 — Output Handling

- The `VolumeAssembler` concatenates the top-ranked pages until the corpus
  reaches exactly 1,312,000 characters.
- Each page boundary is recorded in the JSONL event log with its address,
  coherence score, and BM25 rank.
- The assembled volume is written atomically to `--output`; the checkpoint
  JSON is written to `--workdir` before the file is closed.
- Any deviation from the 1,312,000-character invariant raises `DeterministicHalt`.

---

## 3. Determinism Guarantees

| Property | Mechanism |
|---|---|
| Single seed | `--seed` integer seeds an isolated `random.Random(seed)`; no module-level RNG state |
| Stable sort | All ranked lists sorted by `(score DESC, id ASC)` |
| No implicit async | Scheduling is synchronous and ordered; no concurrent data-plane operations |
| Checkpoint integrity | Each checkpoint includes `seed`, `state_hash` (blake2b), `config_hash`, and `schema_version` |
| Replay | Same `--seed` + `--query` + `--config` always produces byte-identical output |
| Logging | Every state transition logged to JSONL with timestamp, seed, config hash, and event type |

Checkpoints must be atomically written and validated on restore. A restore
failure halts with diagnostic output; partial state is never accepted.

---

## 4. Synthetic Biological Intelligence (SBI) — Reference Only

> **Disclaimer**: SBI is a software architecture metaphor. No biological,
> neural, or wetware integration exists. See
> [`docs/SBI_DISCLAIMER.md`](SBI_DISCLAIMER.md).

The SBI model describes how reasoning components cooperate inside the control
plane, using three conceptual "lobes":

| Lobe | Software Analogue | Role |
|---|---|---|
| **Logic lobe** | `ReasoningControlPlane` + Z3 symbolic engine | Formal constraint checking; rejects logically inconsistent configurations |
| **Abstract lobe** | `HybridRetriever` + knowledge graph | Semantic retrieval and cross-domain mapping; surfaces candidate solutions |
| **Governance lobe** | Lifecycle validator + prohibited-pattern checker | Enforces determinism, completeness, and architectural invariants at every lifecycle boundary |

### Proof-Checking to Prevent Hallucinations

The logic lobe runs a lightweight proof pass over any candidate output before
it is accepted by the pipeline:

1. The candidate text is symbolically encoded as a set of assertions.
2. Z3 attempts to find a contradiction (an *unsatisfiable core*).
3. If a contradiction is found, the candidate is rejected and a reconciliation
   action is logged.
4. Only contradiction-free candidates advance to Stage 6 (Center-Weighted
   Scoring).

This makes hallucination prevention a **deterministic, auditable** step rather
than a probabilistic one.

---

## 5. CI / Coverage Expectations

| Check | Tool | Threshold |
|---|---|---|
| Type checking | `mypy --strict` + `pyright` | Zero errors |
| Linting | `ruff check thalos_prime tests` | Zero warnings |
| Unit & integration tests | `pytest` | ≥ 80 % line coverage overall |
| Critical-path coverage | Lifecycle methods, halt semantics, assembly invariant | 100 % |
| Security scanning | `bandit`, `pip-audit` | Zero high-severity findings |
| Prohibited-pattern scan | Custom validator | Zero TODOs, stubs, mocks, bare `except:` |

**All checks must pass** before a PR is eligible for merge.

Run the full suite locally with:

```bash
make check
# or individually:
mypy thalos_prime --strict
pyright thalos_prime
ruff check thalos_prime tests
pytest tests -v --cov=thalos_prime --cov-report=term-missing
```

---

## 6. LRU Caching

Hot paths in the data plane use an in-memory LRU cache to avoid re-computing
identical inputs within a single run:

- **`BabelGenerator.address_to_page`** — caches generated pages by hex address;
  avoids redundant pseudo-random expansion for repeated addresses.
- **`BabelDecoder` coherence scoring** — caches `(page_hash, query_hash)` →
  `CoherenceScore`; coherence computation is expensive and fully deterministic.
- Cache capacity is bounded (default 512 entries) and configured at
  initialization time; it is never grown implicitly.
- Cache contents are **not** included in checkpoints; replay re-populates the
  cache deterministically.

---

## 7. Dry-Run / Offline Mode

Pass `--dry-run` to run the full pipeline without any network access:

```bash
python thalos_prime.py \
    --query "test" \
    --seed 12345 \
    --output ./output.txt \
    --workdir ./thalos_workdir \
    --dry-run \
    --max-pages 10
```

In dry-run mode:

- `BabelClient` is bypassed; pages are generated entirely by `BabelGenerator`
  from the seeded address list.
- `robots.txt` checks are skipped.
- All other pipeline stages (normalization → output handling) execute
  identically to live mode.
- The assembled volume is byte-identical to a live run with the same seed,
  query, and page addresses — confirming full offline replayability.

Dry-run mode is used by the CI test suite so that all 64+ pipeline tests run
without external dependencies.
