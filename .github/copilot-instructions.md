# Copilot Coding Agent Instructions — ThalosPrimeLibrary

## Purpose and scope
- Thalos Prime is a deterministic Library of Babel toolkit. Control Plane (CIS) coordinates lifecycle/state, Data Plane executes work; keep boundaries explicit.
- Only acceptable end-state: **Thalos Prime — Fully Implemented. Fully Integrated. Fully Operational.** No TODOs, stubs, placeholders, or partial features.

## Absolute operating principles
- Determinism: identical inputs → identical outputs/internal transitions. Seed and log any randomness; ensure replayable checkpoints.
- Error handling: resolve deterministically or halt with full state capture. No silent degradation, hidden fallbacks, or catch-all exceptions.
- Async/concurrency: explicit ordering, bounded queues, deterministic/seeded scheduling; no unbounded or unordered async.

## Architecture & lifecycle enforcement
- Each subsystem implements `initialize()`, `validate()`, `operate()`, `reconcile()`, `checkpoint()`, `terminate()` with explicit success/failure semantics and no unreachable branches.
- Strict dependency injection and typed interfaces (Python ≥ 3.12 for new code); no implicit globals or untyped `Any`.
- Control Plane is authoritative for lifecycle/coordination; Data Plane executes only. Avoid circular dependencies.

## State, observability, and logs
- All state must be observable, serializable, versioned, and reconstructible. Checkpoints must be restartable with seeds/config invariants.
- Emit deterministic event logs for state transitions, lifecycle milestones, reconciliation actions, and seeds/config used.
- “No data” is invalid: block/resolve or halt deterministically when inputs are absent or invalid.

## Failure handling & reconciliation
- Validation blocks startup until all invariants are satisfied. Reconciliation must converge; otherwise halt with a full snapshot.
- Retries must be bounded, logged with rationale, and use deterministic backoff.

## Development workflow
- Install dev tools: `pip install -e ".[dev]"`.
- Primary check: `python -m pytest tests -v` (tests must remain deterministic; seed any randomness).
- When modifying lifecycle/contracts, update docs and keep control-plane vs data-plane boundaries explicit.

## Key surfaces
- Package exports & configuration: `thalos_prime/__init__.py`, `thalos_prime/config.py` (`THALOS_LIBRARY_PATH` env var for local library path).
- Core logic: `thalos_prime/lob_babel_generator.py`, `thalos_prime/lob_babel_enumerator.py`, `thalos_prime/lob_decoder.py`.
- Reference docs: `ARCHITECTURE.md`, `IMPLEMENTATION_COMPLETE.md`, `VERIFICATION_REPORT.md`, `PHASE1_PHASE2_GUIDE.md`.

## Contribution expectations
- Prefer pure functions; make side effects explicit/localized. No unused parameters, dead code, or unreachable branches.
- Reject invalid/unexpected inputs deterministically; enforce strict schemas and typed contracts.
- Tests are mandatory for new/changed behavior and must cover lifecycle and reconciliation paths.
- Document deterministic guarantees, ordering/queuing assumptions, and replay seeds/config whenever they change.
