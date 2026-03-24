# THALOS LIBRARY DIRECTIVE

## Scope
This directive defines deterministic Library reconstruction semantics, operational constraints, and trust tiers for search and reconstruction pathways.

## Reconstruction Semantics
- Reconstruction MUST be deterministic for identical query, constraints, index state, and execution substrate signatures.
- Reconstruction pipeline MUST be explicit and versioned: artifacts -> store -> index -> reconstruct -> search.
- Reconstructed outputs MUST include provenance linking source artifacts, index references, and reconstruction decisions.
- All reconstruction stages MUST expose validation points and fail closed on invariant violations.

## Constraints
- Input schema validation is mandatory at API boundaries.
- Constraint handling MUST reject ambiguous or invalid reconstruction requests with typed errors.
- Replay constraints MUST verify graph hash + environment signature compatibility before accepting cached outputs.
- State transition logging MUST be enabled for reconstruction and search operations.

## Trust Tiers
- Tier 0: Untrusted external artifacts; require strict validation and provenance checks.
- Tier 1: Validated internal artifacts; allowed for indexed search and bounded reconstruction.
- Tier 2: Verified canonical artifacts; allowed for deterministic reconstruction outputs.
- Trust tier evaluation MUST be explicit and persisted with reconstruction results.

## Implementation Tasks
- Create `thalos_prime/library/{artifacts,store,index,reconstruct,search}.py`.
- Implement `/library/reconstruct` and `/library/search` endpoints.
- Add new main tab in web UI pointing at Library + substrate; move old UI to `Classic` tab.
