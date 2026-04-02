# Thalos Prime Phase 1 + Phase 2 Execution (Action Plan)

Scope: Build and integrate deterministic generator + enumerator + storage (Phase 1) and decoding pipeline + coherence heuristics + optional LLM normalization (Phase 2). Phase 3+ deferred.

## Phase 1 — Deterministic Generator, Enumerator, Storage

### Objectives
- Local deterministic page generator (Basile-style): hex → 3,200-char page.
- Fragment enumerator: map query/substrings/ngrams → candidate addresses.
- Storage: Postgres/Redis (start with Redis) for pages, cache, query logs; optional use of existing shard manager.
- API/UI: expose /api/generate (local), /api/enumerate; toggle in UI (Local Gen vs Remote Fetch).
- Tests: determinism, enumerator coverage, API round-trips.

### Tasks
- Generator module (Python): address_to_page(hex_addr) using exact charset/LCG constants; unit tests with fixed vectors.
- Enumerator: given query, split into ngrams; map to addresses (seeded hash + offsets); allow depth/config; tests for stable outputs.
- Storage: add Redis client; persist generated pages + scores; integrate shard manager for distribution (optional).
- API endpoints: /api/generate (hex or query→hex), /api/enumerate (query→addresses), /api/search to accept mode=local|remote.
- UI toggle: add mode switch; surface provenance (local/remote) and hex.
- Config: add redis URL, mode default, max_results, timeout.
- Tests: unit (generator, enumerator), integration (generate→decode→reply), API smoke.

### Deliverables
- src/lob_babel_generator.py (deterministic generator)
- src/lob_babel_enumerator.py (fragment/substring mapper)
- Redis wiring + config update
- API/UI updates for local mode
- Tests covering determinism/enumeration

## Phase 2 — Decoding Pipeline, Coherence Heuristics, LLM Normalization (optional)

### Objectives
- Heuristic scoring expansion: language detection, n-gram density, punctuation structure, configurable weights.
- Optional LLM cleanup (config-gated) with provenance tags.
- Batch/async pipeline for multi-page scoring (queue-based or simple async worker).
- Provenance logging: address, source (local/remote), score, normalization applied, timing.
- API/UI: /api/decode with flags heuristic_only|with_llm; UI toggle raw vs normalized view.
- Tests: heuristics, LLM-off fallback, decode API.

### Tasks
- Heuristics: implement scorer with configurable weights; include language detection (lightweight) and punctuation metrics; tests with golden samples.
- LLM normalization (optional): pluggable function with provider/key; tag outputs; fallback to heuristic only.
- Batch pipeline: simple async worker or Redis queue for scoring batches; timeouts and error handling.
- API/UI: extend /api/search or add /api/decode to accept mode and return raw+normalized+scores; surface in UI.
- Logging: persist provenance to Redis/Postgres; include score, source, duration.
- Tests: unit (scorer), integration (decode endpoint), LLM-off path.

### Deliverables
- src/lob_decoder.py (heuristics + optional LLM wrapper)
- Pipeline/worker (async function or queue consumer)
- API/UI updates for decode/normalization toggles
- Tests for scoring and decode API

## Non-Goals (for now)
- Phase 3 indexing/embeddings/semantic search
- Phase 4 scaling/security/monitoring
- Phase 5 advanced features, SBI/wetware, quantum

## Dependencies & Config
- Redis (recommended) for cache/queue
- Optional Postgres for persistence
- Config additions: redis_url, default_mode (local/remote), llm_enabled, llm_provider/key, scoring weights, cache TTL

## How to Integrate with Current Code
- Keep /chat and /api/search; add mode flag to switch local generator vs remote fetch.
- Add /api/generate (hex/query) and /api/enumerate; reuse coherence scorer once generator outputs text.
- UI: add mode toggle (Local/Remote), raw vs normalized view, show scores and provenance.
- Reuse shard manager if distributing stored pages.

## Minimal Sequence to Ship (MVP)
1) Implement generator + enumerator + /api/generate + /api/enumerate + UI toggle (Local/Remote).
2) Integrate generator path into /api/search with cache and coherence scoring.
3) Add enhanced heuristics and /api/decode with heuristic-only path; UI toggle raw vs normalized.
4) Add optional LLM normalization (config off by default); log provenance.
5) Add tests for generator, enumerator, scorer, API.

## Filing Alignment
- Phase 1: Supports deterministic corpus and enumerator claims.
- Phase 2: Supports hybrid heuristic/LLM claims, recursive stabilization with scoring and provenance.
- Roadmap (later): embeddings/semantic search (Phase 3) for continuation; SBI/wetware (Phase 5) for CIP.


---

## Greenfield Formal Design — Execution Reframe

> **Scope reframe: audit → greenfield design.**
> The Phase 1 and Phase 2 execution plan below is not derived from analyzing uploaded
> whitepapers or exports.  Instead, it is derived from the novel formal system T
> (defined in [`docs/FORMAL_MODEL.md`](../FORMAL_MODEL.md)) and maps each phase to
> one or more elements of T that must be implemented.

### Formal Traceability

The formal system T = ⟨D, I, R, V, E, P, B_t⟩ maps onto the phased execution plan
as follows.  Each phase implements one or more formal elements (see
[`docs/FORMAL_MODEL.md`](../FORMAL_MODEL.md) for full definitions):

| Phase | Formal Elements Implemented | Deliverable |
|-------|-----------------------------|-------------|
| Phase 1 | I (PRP indexer), E (generator) | `lob_babel_generator.py`, `lob_babel_enumerator.py`, storage |
| Phase 2 | R (coherence scoring / FACS filter), P (provenance) | `lob_decoder.py`, FACS suspension, coherence threshold enforcement |
| Phase 3 | D + I extended (geometric hashing) | Semantic indexing + invariant manifold hashing |
| Phase 4 | R full (R-Matrix / YBE) | Commutative reasoning invariance engine |
| Phase 5 | V full (DeScAI + ZK-SNARKs), E variant (wetware) | Distributed veridiction, ZK-verifiable chains |

### Epistemic Premise

The global information environment is defined by a structural imbalance where
exponential data production has outpaced the capacity for verifiable reasoning and
deterministic retrieval.  Every execution phase reduces this imbalance by implementing
more elements of T, progressively converging the system toward sovereign epistemic
operating system status.

### Phase Completion Criterion

A phase is complete when the formal invariants I-1 through I-9 (see
`docs/FORMAL_MODEL.md §6`) pass for all elements of T introduced in that phase.
