# EXECUTION SUBSTRATE SPEC

## Scope
This specification defines deterministic execution substrate requirements for hashing, environment signatures, and side-effect memoization.

## Deterministic Hashing
- All execution graph hashing MUST be deterministic and replayable for identical graph structure and node payloads.
- Hash input canonicalization MUST include stable ordering for node IDs, edge tuples, and typed node attributes.
- `ExecutionGraph` MUST expose a Merkle-style `graph_hash` computed from per-node hashes plus normalized adjacency.
- Hash algorithm: SHA-256 over UTF-8 encoded canonical payloads unless a stronger deterministic algorithm is explicitly versioned in this spec.

## Environment Signatures
- Environment signatures MUST capture deterministic runtime identity for replay validation.
- Signature payload MUST include: Python version, platform string, selected dependency versions, and config hash.
- Signature generation MUST be isolated from non-deterministic process state and serialized in canonical key order.
- Signature module MUST provide stable APIs for generation and verification.

## Side-Effect Memoization
- Side-effecting execution nodes MUST be explicitly marked and tracked.
- Memoization keys MUST include node identity, deterministic inputs, graph hash, and environment signature.
- Memoized outputs MUST be returned only when key, schema version, and trust policy all match.
- Memoization store entries MUST include provenance metadata and deterministic timestamps when available from execution state.

## Implementation Tasks
- Create `execution_ir.hash` and `execution_ir.signature` modules.
- Implement Merkle-style `graph_hash` for `ExecutionGraph`.
- Add memoization store and mark side-effect nodes.
