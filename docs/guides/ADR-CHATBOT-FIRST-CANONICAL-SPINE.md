# ADR: Chatbot-First Canonical Spine

- Status: Accepted
- Date: 2026-04-20
- Scope: Product contract, API/UI contract, convergence governance

## Context

Repository history shows repeated architectural branching and overlapping subsystems introduced via multiple PR streams (engine rewrites, execution substrate, NEXUS, artifacts/epistemics, search/chat expansions, benchmark paths, and UI variants). This produced capability growth but inconsistent product shape.

The repository now needs one stable product contract that keeps advanced capabilities while preventing new parallel "competing brains".

## Decision

ThalosPrimeLibrary adopts a single product contract:

1. **Chatbot-first knowledge system** is the canonical user interface.
2. **Single engine, single namespace, single execution spine** is the canonical runtime model.
3. All non-chat routes are **capability adapters** that call the canonical engine contract.
4. All outputs use one response schema with mandatory evidence/provenance/reproducibility fields.
5. Determinism, lifecycle compliance, and typed interfaces remain hard merge gates.

## Canonical Contract

### Product Contract

- Primary experience: one chat UI and one chat API surface.
- Optional modes are explicit and bounded: `standard`, `deep_research`, `build`, `image`, `diagnostics`.
- System purpose: knowledge discovery, validation, explanation, and reproducible solving.

### Runtime Contract

- Namespace: `thalos_prime.*` only.
- Execution model: one canonical orchestration spine.
- Lifecycle contract: `initialize -> validate -> operate -> reconcile -> checkpoint -> terminate`.

### Evidence Contract

Every final answer must include:

- answer
- evidence (sources/artifacts)
- confidence
- actions taken / reasoning trace summary
- reproducibility metadata (seed, checkpoint/version identifiers)

## Consequences

### Positive

- Clear user experience and reduced cognitive overhead.
- Reduced architecture drift and lower regression risk.
- Improved trust due to evidence-first outputs.

### Trade-offs

- Requires deprecating or adapter-wrapping legacy parallel entry paths.
- Requires stricter release governance to prevent re-fragmentation.

## Enforcement

Changes are mergeable only when they:

- Preserve single-spine execution,
- Preserve evidence schema requirements,
- Keep `make check` green,
- Avoid introducing parallel orchestrators for the same user workflow.
