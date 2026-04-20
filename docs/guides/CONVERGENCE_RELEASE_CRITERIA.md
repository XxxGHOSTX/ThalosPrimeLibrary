# Convergence Release Criteria

Release gates for the unified chatbot-first system.

## A. Reliability and Determinism (Required)

- `make check` passes in CI.
- Deterministic replay verified for representative mode runs.
- Lifecycle validation passes for touched components.
- No prohibited patterns introduced.

## B. Product Convergence (Required)

- User flows resolve through one chatbot-first contract.
- Non-chat endpoints are adapter/thin capability wrappers.
- No new parallel orchestration path added for equivalent tasks.

## C. Evidence Quality (Required)

For each mode, responses include:

- evidence references,
- confidence output,
- action trace,
- reproducibility metadata.

Any missing field is release-blocking for mode-capable endpoints.

## D. Simplicity and UX (Required)

- Default user journey is single chat flow.
- Optional modes are clearly named and discoverable.
- Response schema shape remains uniform across modes.

## E. Safety and Integrity (Required)

- Contradiction/error paths are explicit and observable.
- No silent downgrade from advanced mode to weaker hidden mode.
- State, audit, and provenance surfaces remain queryable.

## F. Exit Criteria for "Advanced/Novel" Claims

A release may claim "advanced/novel" only when:

1. Deep research mode outputs multi-step verified evidence,
2. Build mode shows deterministic plan->apply->test->report trace,
3. Image mode returns provenance-bearing generation metadata,
4. Discover+solve behavior includes what was tried and why chosen,
5. All of the above are reachable from the same chatbot UI.
