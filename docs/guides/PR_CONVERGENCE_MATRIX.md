# PR Convergence Keep/Merge/Remove Matrix

This matrix consolidates major PR-introduced capability streams into one product direction.

## Objective

- Keep stable capabilities that reinforce the chatbot-first contract.
- Merge overlapping capabilities under one execution path.
- Remove or deprecate duplicate/fragmenting paths.

## Matrix

| Capability Stream | Representative PRs | Current Value | Convergence Action | Notes |
|---|---|---|---|---|
| Canonical namespace + single engine spine | #103, #102 | High | **KEEP + ENFORCE** | Foundational to single execution model |
| Search/chat benchmark integration | #102, #99 | High | **MERGE** | Keep benchmark as mode/tooling, not separate brain |
| Coherence floor workers and cache guards | #99 | High | **KEEP** | Keep as runtime reliability safety net |
| Search feature expansion (adaptive/diversity/expansion) | #95 | Medium-High | **MERGE + SIMPLIFY** | Expose via mode policies, not scattered flags |
| Artifacts/belief/validation/audit epistemic stack | #89 | High | **MERGE UNDER CHAT CONTRACT** | Reuse as evidence core for all answer flows |
| Execution substrate / graph-native paths | #87 | Medium | **MERGE SELECTIVELY** | Keep useful determinism/provenance pieces only |
| NEXUS packages and Windows isolation tracks | #48, #49 | Medium | **MERGE AS OPTIONAL TOOLING** | Avoid parallel top-level product identity |
| Infra synthesis and repo/build automation | #63, #102 | High | **KEEP AS OPTIONAL CHAT MODE** | Route through `build` mode with full trace |
| Repeated CI/lint/type rescue streams | #80, #78, #75, #73, #56, #54, #53, #29, #28 | High operational value | **KEEP + GOVERN** | Enforce release discipline to reduce recurring debt |
| Deployment unification | #61, #60, #59 | High | **KEEP** | Single deploy/run path aligns with convergence |
| Legacy/experimental fragmented attempts | #40 (WIP), #58, #5 | Low | **REMOVE/DEPRECATE** | Explicitly non-canonical or placeholder history |

## Convergence Rules

1. No new parallel orchestrators for chat/search reasoning.
2. Any advanced capability must be consumable through chat modes.
3. Evidence/provenance schema is mandatory regardless of capability origin.
4. Deprecated paths remain adapter-only until removed in scheduled cleanup.

## Immediate Worklist

- Normalize route adapters so search/benchmark/artifacts/build/image all flow through one contract.
- Mark superseded modules/entrypoints with formal deprecation metadata.
- Maintain a single capability registry for UI mode toggles and policy controls.
