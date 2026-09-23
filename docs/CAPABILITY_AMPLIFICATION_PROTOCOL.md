# Thalos Prime Capability Amplification Protocol

**Status:** Implemented kernel contract
**Version:** 2.0.0

## Core primitive

Capability amplification is one bounded Control Plane operation:

`requirement → capability selection → execution → independent validation → terminal state`

A limitation matters only when it changes the next executable action.

The kernel rule is:

> **A result cannot become VERIFIED without a passing validator for every acceptance criterion.**

## Architectural boundary

This component is deliberately smaller than a planner.

`RuntimeEngine` owns task registration and execution.
`ExecutionGraph` owns multi-step composition.
Lifecycle components own lifecycle state.
`AuditTrail` owns tamper-evident event history.
The amplification kernel coordinates these existing primitives; it does not replace them.

## Contract

The executable contract contains only decision-critical fields:

- `task_id`
- `objective`
- `payload`
- `required_capabilities`
- `acceptance_criteria`
- `max_attempts`
- `allow_failover`

Acceptance criteria are stable validator IDs, not prose. This makes the final gate executable rather than rhetorical.

## Routing

Providers advertise atomic capabilities such as `retrieve`, `inspect`, `calculate`, `execute`, or `validate`.

A provider is eligible only when it satisfies the complete required capability set.

Selection is deterministic:

1. Filter to eligible providers.
2. Sort by stable `provider_id`.
3. Execute the first candidate.
4. Fail over only to a different eligible provider when the candidate cannot produce a validated result.
5. Never retry the same provider with the same input.

A retry that does not change the execution condition is not amplification.

## Validation

Validators are separate from providers. Every acceptance criterion must have a validator result.

A validator may be blocking or non-blocking:

- A passing set of required checks produces `COMPLETED_VERIFIED`.
- A result with only non-blocking failed checks produces `COMPLETED_QUALIFIED`.
- Missing capability produces `BLOCKED`.
- Blocking validation failure produces `REJECTED`.
- Execution failure with no usable candidate produces `HALTED`.

Validator exceptions terminate that attempt as `HALTED`; the kernel does not pretend that a broken validator produced evidence.

## Provenance and replay

Each operation records:

- deterministic operation ID
- attempt number
- provider ID
- input hash
- output hash when output exists
- status
- failure code and diagnostic type when execution fails

Each result identifies its provider and validators.

Providers explicitly declare whether replay is faithful. The kernel therefore cannot mark an external or mutable provider as replayable merely because the input hash is deterministic.

## Current repository integration

The runtime now contains:

`capability.v1.execute`

The loader registers it as a first-class runtime plugin. Its initial concrete adapter is:

`runtime.search.v1` → `search.v1.query`

That adapter is marked non-replayable because the current search task includes time-dependent execution metadata and can depend on mutable external state.

The provider registry lives on `RuntimeEngine`, so additional capabilities can be registered by future runtime plugins without changing the kernel.

## Corrective loop

The only recovery sequence is:

`route → execute → validate`

followed, when necessary, by:

`different provider → execute → validate`

There is no hidden loop that lowers the acceptance threshold, rephrases a request indefinitely, or converts model confidence into evidence.

## Nonconformance

These are protocol violations:

- VERIFIED without passing validator evidence.
- Acceptance criteria that have no validator result.
- Same-provider retry with identical input presented as recovery.
- Provider selected without all required capabilities.
- Missing capability represented as successful empty output.
- Provider replay declared true despite mutable external state.
- Provenance that cannot identify the executed provider.
- A plan or intention represented as a completed operation.

## Definition of done

The kernel is implemented when deterministic tests cover routing order, verified completion, changed-provider failover, missing capability, contract identity, acceptance-criterion enforcement, and replayability.
