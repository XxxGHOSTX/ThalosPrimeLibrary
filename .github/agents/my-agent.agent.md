---
# Fill in the fields below to create a basic custom agent for your repository.
# The Copilot CLI can be used for local testing: https://gh.io/customagents/cli
# To make this agent available, merge this file into the default repository branch.
# For format details, see: https://gh.io/customagents/config

name:
description:
---

# My Agent

Describe what your agent does here...# Copilot Coding Agent Repository Instructions — ThalosPrimeLibrary (Advanced)

## Absolute Operating Principles
- Non-negotiable: Thalos Prime must be fully built, fully integrated, fully operational. No partial/degraded states.
- No TODOs, stubs, mocks, placeholders, or “out of scope”. Every referenced component exists and is implemented.
- Determinism: identical inputs → identical outputs and internal transitions. Randomness is seeded, logged, replayable, and snapshot-recoverable.
- Error handling: eliminate errors or halt deterministically with full state capture. No silent degradation, no bypass fallbacks.

## Architecture & Lifecycle Enforcement
- Control Plane (CIS) is authoritative over lifecycle/state/coordination; Data Plane executes only. No circular dependencies, no implicit orchestration.
- Every subsystem implements and exercises: `initialize()`, `validate()`, `operate()`, `reconcile()`, `checkpoint()`, `terminate()` with explicit success/failure semantics. No missing branches or unreachable paths.
- Strict dependency injection; no implicit globals. Explicit, typed interfaces (Protocol/ABC). Python ≥ 3.12, strict typing enforced.
- No catch-all exceptions. All exception paths either resolve internally or halt deterministically with state capture.
- Async/concurrency: explicit ordering; bounded queues; deterministic scheduling/seeded randomness if applicable. Disallow unbounded or unordered async.

## State, Observability, and Logs
- All state is observable, serializable, versioned, and reconstructible.
- Emit deterministic event logs of state transitions, lifecycle milestones, reconciliation events, and seeds/config used.
- “No data” is invalid. If data is absent, block/resolve or halt deterministically.
- Checkpoints must be complete and restartable; include replay seeds and configuration invariants.

## Coding Standards
- Strict static typing (mypy/pyright clean). No unbounded `Any`. Type guard or narrow where necessary.
- Pure functions preferred; side effects explicit and localized. No hidden state or side-effectful property getters.
- No unused parameters/variables; no dead code; no unreachable branches.
- Input validation mandatory with deterministic rejection for invalid inputs.
- Tests mandatory for new/changed behavior; must be deterministic (seeded if randomness). Cover lifecycle paths and reconciliation.
- Explicit module boundaries for control-plane vs data-plane; document contracts in code/docstrings.

## Failure Handling & Reconciliation
- No graceful failure end-states. On contradiction/missing dependency: Stop → Enumerate → Resolve → Continue only when whole.
- Validation blocks startup until all invariants satisfied. Reconciliation must converge; if not, halt deterministically with full state snapshot.
- Retries require bounded attempts, logged rationale, and deterministic backoff.

## Repository Workflow Expectations
- PRs are complete implementations only (no partial scaffolds). Small, coherent scope.
- PR description must include: intent, constraints, deterministic guarantees, state/logging surfaces, seeds/config for replay, tests added/updated, and control vs data plane impacts.
- CI must run type checks, lint, tests; all must pass. Failing checks must be fixed, not waived.

## Documentation Requirements
- Keep README/docs updated with lifecycle contracts, state surfaces, deterministic guarantees, and replay instructions (seeds/config).
- Document control-plane vs data-plane boundaries and allowed interfaces.
- Record any deterministic ordering/queuing assumptions.

## Security & Compliance
- No secrets in code. Configuration is explicit, typed, and validated.
- Reject invalid or unexpected inputs deterministically. Enforce strict schemas.

## Prohibited Patterns
- Implicit defaults that mask errors; hidden fallbacks; silent retries.
- Partial initialization, deferred wiring, or incomplete lifecycle implementations.
- Catch-all exception suppression or logging-only without resolution/termination.
- Non-deterministic concurrency or time-dependent races.

## Completion Criterion
- Only acceptable final state: **Thalos Prime — Fully Implemented. Fully Integrated. Fully Operational.** Anything else is a defect.
