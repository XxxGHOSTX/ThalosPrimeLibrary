# Copilot Coding Agent Instructions — ThalosPrimeLibrary

## Purpose and scope
Thalos Prime is a deterministic Library of Babel toolkit implementing strict control-plane/data-plane separation. The Control Plane coordinates lifecycle and state; the Data Plane executes computational work. All boundaries must remain explicit.

**Only acceptable end-state:** Fully Implemented. Fully Integrated. Fully Operational. No TODOs, stubs, mocks, placeholders, or partial features are permitted in production code.

## Absolute operating principles

### Determinism
- Identical inputs must produce identical outputs and internal state transitions.
- All randomness must be seeded deterministically and logged for replay.
- Checkpoints must be replayable with identical seeds and configuration.
- No non-deterministic operations (system time, network I/O, filesystem scans) without explicit logging and seeding.

### Error handling
- Errors must be resolved deterministically or the system must halt with full state capture.
- No silent degradation, hidden fallbacks, or catch-all exception handlers.
- Every error path must either recover with explicit semantics or terminate deterministically.
- Exceptions must be typed; no bare `except:` or `except Exception:` without re-raise.

### Concurrency and async
- All async operations require explicit ordering and bounded queues.
- Scheduling must be deterministic or seeded for replay.
- No unbounded async operations or unordered concurrent execution.
- Document ordering guarantees and test concurrent paths.

## Architecture and lifecycle enforcement

### Control Plane vs. Data Plane separation
- Control Plane: authoritative for lifecycle coordination, state management, reconciliation.
- Data Plane: executes computational work only; no lifecycle or coordination logic.
- No circular dependencies between planes.
- No implicit orchestration or hidden control flow.

### Required lifecycle methods
Each subsystem must implement the following methods with explicit success/failure semantics:
- `initialize()`: Set up resources, dependencies, and initial state. Must succeed or raise typed exception.
- `validate()`: Check all invariants and preconditions. Block operation until satisfied.
- `operate()`: Execute primary work. Must be idempotent where applicable.
- `reconcile()`: Converge to consistent state. Must deterministically succeed or halt.
- `checkpoint()`: Serialize state for restart. Must be atomic and versioned.
- `terminate()`: Clean up resources. Must not leave orphaned state.

All methods must have no unreachable code branches.

### Dependency management
- Use explicit dependency injection; no implicit globals or singletons.
- All interfaces must be strictly typed (Python ≥ 3.12 for new code).
- No untyped `Any` except where bounded by explicit protocols.
- Pin all dependency versions in `pyproject.toml` or `requirements.txt`.
- No implicit network fetches at runtime; all dependencies resolved at build time.

### Type safety
- All code must pass `mypy --strict` and `pyright` type checks.
- Use `typing` module for all annotations: `Optional`, `Union`, `Callable`, etc.
- No `# type: ignore` without explicit justification comment.
- Prefer `Protocol` for interface definitions over abstract base classes.

## State, observability, and logging

### State requirements
- All state must be observable, serializable, versioned, and reconstructible.
- State machines must have explicit transition logs with timestamps and seeds.
- Checkpoints must be restartable with exact configuration and seed invariants.
- No hidden or implicit state; all state surfaces must be documented.

### Deterministic event logs
- Emit structured event logs for all state transitions, lifecycle milestones, and reconciliation actions.
- Include seeds, configuration hash, and version in all log events.
- Event log schema must be versioned and backward-compatible.
- No "no data" states; missing data must block, resolve, or halt deterministically.

### Observability surfaces
- All internal state transitions must be observable via logging or metrics.
- Performance metrics subordinate to correctness and determinism.
- Expose state query endpoints for debugging and monitoring.

## Coding standards

### Static typing
- All functions, methods, and variables must have type annotations.
- Use `mypy --strict` and `pyright` for static type checking.
- No `Any` type unless explicitly bounded by protocol or interface.

### Code quality
- No unused parameters, variables, or dead code.
- No unreachable branches or redundant conditional logic.
- All side effects must be explicit and localized.
- Prefer pure functions; document and minimize side effects.

### Exception handling
- No catch-all exception handlers (`except Exception:`) without re-raise.
- All exception types must be explicit and typed.
- Log all exceptions with full context (stack trace, state snapshot, seeds/config).
- Every exception path must resolve deterministically or halt with state capture.

### Testing requirements
- All new or changed behavior requires deterministic tests.
- Tests must cover lifecycle paths, reconciliation, and failure modes.
- Seed all randomness in tests; no flaky or non-deterministic tests.
- Tests must pass in isolation and in parallel.
- Minimum coverage: 80% line coverage, 100% for critical paths.

### Concurrency
- Document all ordering and synchronization guarantees.
- Use bounded queues and explicit locks.
- Test concurrent execution paths with deterministic scenarios.
- No unbounded thread pools or async task spawning.

## Failure handling and reconciliation

### No graceful failure end-states
- Systems must not remain in degraded or partially-operational states.
- Contradictions or missing dependencies must trigger: stop → enumerate → resolve → continue when whole.
- Validation blocks startup until all invariants satisfied.

### Reconciliation
- Reconciliation must converge to consistent state or deterministically terminate.
- Log all reconciliation actions with before/after state snapshots.
- Retries must be bounded, logged with rationale, and use deterministic backoff.
- No silent retries without logging and state capture.

### Validation
- All inputs must be validated and rejected if invalid.
- No implicit defaults that mask validation errors.
- Schema enforcement at API boundaries.
- Type validation at runtime for dynamic inputs.

## Workflow expectations

### Complete implementations
- Deliver fully implemented, integrated, and operational features.
- No partial implementations, TODOs, or deferred work.
- All features must have tests, documentation, and integration points.

### Pull request requirements
PR descriptions must include:
- Intent: What problem does this solve?
- Constraints: What invariants must hold?
- Deterministic guarantees: What replay/checkpoint guarantees exist?
- State surfaces: What state is exposed and how?
- Logging: What events are logged?
- Tests: What tests were added or updated?

### CI requirements
- All CI checks must pass: type checks (`mypy --strict`, `pyright`), linters (`ruff`), and tests (`pytest`).
- CI failures must block merge.
- No warnings or errors tolerated in CI output.

### Development workflow
1. Install dev tools: `pip install -e ".[dev]"`
2. Run type checks: `mypy thalos_prime --strict` and `pyright thalos_prime`
3. Run linters: `ruff check thalos_prime tests`
4. Run tests: `python -m pytest tests -v`
5. Update documentation for lifecycle, state surfaces, and deterministic guarantees.

## Documentation requirements

### Module documentation
- Every module must have a docstring with purpose, interfaces, and lifecycle.
- Document all state surfaces, checkpoint formats, and event log schemas.
- Document seeds and configuration for replayability.
- Document control-plane vs. data-plane boundaries.

### Interface documentation
- All public functions and classes must have type-annotated docstrings.
- Document deterministic guarantees, ordering assumptions, and failure modes.
- Provide usage examples for complex interfaces.

### Architecture documentation
- Update `ARCHITECTURE.md` for architectural changes.
- Maintain consistency between code and documentation.
- Document design decisions, tradeoffs, and constraints.

## Security and compliance

### Secrets management
- No secrets, credentials, or tokens in source code.
- Use environment variables or secret management systems.
- All secrets must be explicitly validated and rotated.

### Configuration
- All configuration must be explicit, typed, and validated at startup.
- Use environment variables or configuration files with schema validation.
- Document all configuration options with types and defaults.

### Input validation
- Mandatory input validation at all API boundaries.
- Reject invalid inputs with explicit error messages.
- No implicit coercion or silent normalization.
- Sanitize all user inputs to prevent injection attacks.

## Prohibited patterns

The following patterns are prohibited and must be rejected in code review:
- Implicit defaults that mask validation errors.
- Partial initialization or deferred wiring (all initialization must be complete).
- Catch-all exception suppression without logging and re-raise.
- Silent retries without logging and bounded backoff.
- Bypassed enforcement or fallback paths that skip validation.
- TODOs, stubs, mocks, or placeholders in production code.
- Non-deterministic operations without explicit seeding and logging.
- Untyped `Any` without protocol bounds.
- Hidden state or implicit globals.
- Unused parameters, variables, or dead code.

## Advanced enforcement

### Deterministic configuration surfaces
- Single source of truth for all configuration.
- Configuration must be versioned and tracked with state.
- Configuration changes must be logged and reversible.

### Reproducible seeds and checkpoints
- All seeds must be persisted in checkpoint metadata.
- Checkpoints must include configuration hash and version.
- Restore operations must validate seed and configuration consistency.

### Event log schema and versioning
- Event logs must have explicit schema with version field.
- Schema changes require migration path and backward compatibility.
- All events must include timestamp, version, seed, and configuration hash.

### Checkpoint and restore contracts
- Checkpoints must be atomic and consistent.
- Restore must validate checkpoint integrity and version compatibility.
- Restore failure must halt with diagnostic information.

### Reconciliation invariants
- Document all reconciliation invariants explicitly.
- Test invariant violations and recovery paths.
- Log all invariant checks and enforcement actions.

### Performance subordination
- Correctness and determinism take absolute priority over performance.
- Performance optimizations must not compromise deterministic guarantees.
- Document and test performance tradeoffs explicitly.

## Completion criterion

The only acceptable final state is: **Fully Implemented. Fully Integrated. Fully Operational.**

Any code that fails to meet these criteria is a defect:
- Incomplete implementations.
- Missing tests or documentation.
- Violations of deterministic guarantees.
- Unresolved TODOs or placeholders.
- CI failures or warnings.
- Type check errors.
- Unhandled error paths.

All code must converge to complete, deterministic, and operational state before merge.

## Key surfaces

### Package exports and configuration
- `thalos_prime/__init__.py`: Main package exports.
- `thalos_prime/config.py`: Configuration management (`THALOS_LIBRARY_PATH` environment variable).

### Core logic modules
- `thalos_prime/lob_babel_generator.py`: Deterministic page generation.
- `thalos_prime/lob_babel_enumerator.py`: Query enumeration and address mapping.
- `thalos_prime/lob_decoder.py`: Multi-metric coherence scoring.

### Reference documentation
- `ARCHITECTURE.md`: System architecture and design.
- `IMPLEMENTATION_COMPLETE.md`: Implementation status and completeness.
- `VERIFICATION_REPORT.md`: Test results and verification status.
- `PHASE1_PHASE2_GUIDE.md`: Phase 1 and 2 implementation guide.

## Enforcement summary

This document defines the absolute requirements for code contributions to Thalos Prime. All code must:
1. Be fully deterministic with explicit seeding and logging.
2. Implement required lifecycle methods with explicit semantics.
3. Maintain strict control-plane/data-plane separation.
4. Pass all type checks, linters, and tests in CI.
5. Include comprehensive documentation and tests.
6. Reject invalid inputs deterministically.
7. Avoid all prohibited patterns.
8. Converge to fully implemented, integrated, and operational state.

Violations of these requirements are defects and must be resolved before merge.
