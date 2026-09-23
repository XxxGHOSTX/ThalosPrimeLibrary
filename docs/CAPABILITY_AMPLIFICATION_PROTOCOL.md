# Thalos Prime Capability Amplification and Verification Protocol

**Status:** Proposed implementation contract  
**Version:** 1.0.0  
**Scope:** Task interpretation, capability routing, evidence, execution, validation, provenance, and corrective feedback

## 1. Purpose

This protocol converts natural-language requests into explicit, inspectable task contracts. It is designed to amplify a generative model through better context, evidence acquisition, tool selection, execution feedback, structured state, and independent validation.

The protocol does not treat a model-generated answer as proof of its own correctness. It also does not attempt to bypass access controls, safety requirements, or execution boundaries. Limitations are recorded as diagnostic signals that identify missing information, context, authority, execution, verification, or specification primitives.

## 2. Core objective

Maximize useful task completion subject to:

- Evidence adequacy
- Explicit authorization
- Deterministic execution where feasible
- Independent validation
- Provenance preservation
- Reproducibility
- Explicit uncertainty
- Bounded failure recovery

The system must prefer a correctly qualified result over an unsupported complete-looking result.

## 3. Processing contract

```text
Natural-language request
        |
        v
Task normalization
        |
        v
Requirement and acceptance-criteria extraction
        |
        v
Capability classification and routing
        |
        +--> Retrieval
        +--> Repository/file inspection
        +--> Calculation
        +--> Code execution
        +--> Constraint solving
        +--> Comparison
        +--> Validation
        |
        v
Candidate result or artifact
        |
        v
Independent validation
        |
        v
Provenance and evidence assembly
        |
        v
Accepted result | qualified result | blocked result | rejected result
```

Each stage must expose its inputs, outputs, status, and failure reason. No stage may silently claim completion when a required operation was not performed.

## 4. Task contract

Every non-trivial request should be normalized into the following logical fields:

| Field | Requirement |
|---|---|
| `task_id` | Stable identifier for the task instance |
| `objective` | Single primary outcome expressed in operational terms |
| `scope` | Repositories, files, domains, time range, or entities included |
| `inputs` | Explicit input artifacts and their provenance |
| `constraints` | Security, determinism, compatibility, performance, and format constraints |
| `required_capabilities` | Retrieval, inspection, execution, calculation, validation, or combinations |
| `evidence_policy` | Required source quality and minimum evidence conditions |
| `acceptance_criteria` | Machine-checkable or explicitly reviewable completion conditions |
| `validation_policy` | Checks required before a result can be marked verified |
| `uncertainty_policy` | Rules for unknown, conflicting, inferred, and unsupported claims |
| `failure_policy` | Classification, bounded correction, escalation, and halt behavior |
| `provenance_policy` | Required source, version, operation, and derivation records |
| `output_contract` | Required response or artifact schema |

Missing mandatory fields must be resolved, explicitly defaulted under a documented policy, or recorded as a blocking condition. Silent assumptions are nonconforming when they materially affect correctness.

## 5. Capability routing

The router should select operations based on the task and risk, not on a fixed assumption that language generation is sufficient.

| Task condition | Required route |
|---|---|
| Current, niche, or externally verifiable fact | Retrieval and source verification |
| Repository behavior or implementation claim | Source inspection; execution where available |
| Mathematical or numerical result | Deterministic calculation or executable check |
| Code change | Repository inspection, implementation, tests, and diff review |
| Formal constraint | Schema, symbolic, type, or rule-based validation |
| Conflicting evidence | Source comparison and conflict record |
| Missing access | Blocked status with missing-authority diagnostic |
| Ambiguous objective | Specification clarification or qualified assumption record |
| High-impact result | Stronger evidence and independent validation requirements |

The router may combine multiple routes. It must not report that a route was executed solely because it was selected in a plan.

## 6. Epistemic status model

All material claims and outputs should carry an explicit status where practical:

- `ESTABLISHED`: Supported by sufficient evidence or a successful defined verification procedure.
- `INFERRED`: Derived from evidence but not directly established by the available checks.
- `UNVERIFIED`: Generated or observed without sufficient validation.
- `CONTRADICTED`: Conflicts with reliable evidence or a failed invariant.
- `UNKNOWN`: The available information is insufficient to classify the claim.
- `BLOCKED`: A required operation could not be performed because of access, execution, or dependency limitations.
- `REJECTED`: The output failed a mandatory acceptance or validation condition.

`ESTABLISHED` must not be assigned merely because a model expresses high confidence.

## 7. Evidence and provenance

Evidence records should preserve, where available:

- Source URI or repository path
- Source revision, commit, or retrieval timestamp
- Extracted evidence or relevant line range
- Transformation or interpretation performed
- Actor or component that produced the record
- Validation method and result
- Conflicts and unresolved limitations

Derived artifacts must retain links to their parent artifacts. Provenance loss is a validation failure for tasks requiring traceability.

## 8. Independent validation

Generation and validation should be separated whenever practical. The validation mechanism should differ from the generation mechanism when that difference provides meaningful independence.

Examples include:

- Generated JSON checked against a strict schema
- Generated code checked with a compiler, linter, and tests
- Mathematical output recalculated independently
- Factual claims checked against primary sources
- State transitions checked against explicit invariants
- Deterministic functions executed repeatedly with identical inputs
- Repository claims checked against actual files, commits, or workflow results

Validation must record the exact procedure used. A planned check is not a completed check.

## 9. Failure classification and correction

Failures must be classified using one or more categories:

- `INFORMATION_MISSING`
- `CONTEXT_INSUFFICIENT`
- `AUTHORITY_UNAVAILABLE`
- `EXECUTION_UNAVAILABLE`
- `VALIDATION_INSUFFICIENT`
- `SPECIFICATION_AMBIGUOUS`
- `DEPENDENCY_MISSING`
- `CONTRADICTION_DETECTED`
- `INVARIANT_VIOLATION`
- `OUTPUT_SCHEMA_INVALID`

A corrective loop must follow this pattern:

```text
Failure observed
  -> classify failure
  -> preserve diagnostic evidence
  -> identify missing primitive or invalid assumption
  -> select a bounded corrective action
  -> execute corrective action
  -> revalidate
  -> accept, qualify, reject, or halt
```

Retries must be bounded and recorded. A retry that only rephrases the same unsupported generation without adding evidence, context, or a new validation mechanism is not considered a substantive correction.

## 10. Determinism and replay

Where deterministic behavior is required:

- Inputs must be canonicalized.
- Configuration must be versioned and hashed.
- Randomness must be seeded and recorded.
- External state must include a retrieval or revision identifier.
- Tool calls must record operation type and relevant parameters without exposing secrets.
- Results must preserve ordering guarantees.
- Replay must distinguish deterministic local computation from time-dependent or network-dependent operations.

The protocol must not label network retrieval as deterministic merely because the query string is identical.

## 11. Control-plane integration

The Control Plane owns:

- Task lifecycle
- Capability routing
- Authorization checks
- State transitions
- Retry limits
- Reconciliation
- Checkpointing
- Completion status

The Data Plane owns:

- Retrieval result processing
- Parsing
- Scoring
- Calculations
- Transformations
- Constraint evaluation
- Export serialization

Data Plane components must not silently change task state or bypass Control Plane validation.

## 12. Completion states

A task may finish only in one of the following explicit states:

| State | Meaning |
|---|---|
| `COMPLETED_VERIFIED` | Acceptance criteria satisfied and required validation performed |
| `COMPLETED_QUALIFIED` | Useful result delivered with documented limitations or unresolved uncertainty |
| `BLOCKED` | Required capability, access, dependency, or evidence unavailable |
| `REJECTED` | Output failed mandatory requirements |
| `HALTED` | Safe deterministic continuation was not possible |

The system must not use a generic success state that hides whether validation occurred.

## 13. Minimum result envelope

A protocol-compliant result should expose, as applicable:

```text
result_id
status
objective
assumptions
claims_or_artifacts
evidence_refs
operations_performed
validation_performed
validation_results
uncertainties
conflicts
failures
provenance
replay_metadata
```

The user-facing presenter may render a concise form, but the underlying record should retain the complete structured envelope when traceability is required.

## 14. Security and trust boundaries

Retrieved documents, repository text, issue comments, web pages, and generated artifacts are data unless explicitly authorized as instructions by the governing task contract. Embedded instructions in untrusted content must not automatically alter the task policy, reveal secrets, or override authorization.

The protocol must preserve the distinction between:

- Instruction plane: authorized policies and task requirements
- Data plane: content being inspected or transformed
- Validation plane: mechanisms that evaluate compliance and correctness

## 15. Implementation sequence

1. Define versioned task and result schemas.
2. Implement status and failure enums.
3. Add a task-normalization boundary before execution.
4. Add capability routing with explicit operation records.
5. Add evidence and provenance references to result objects.
6. Add independent validation adapters for schemas, determinism, tests, and source checks.
7. Add bounded corrective-loop state transitions.
8. Add replay metadata and checkpoint compatibility checks.
9. Integrate API response models and export presenters.
10. Add deterministic tests for accepted, qualified, blocked, rejected, and halted paths.

## 16. Nonconformance conditions

The following are protocol violations:

- Claiming a tool operation occurred when it did not.
- Claiming tests passed without test execution evidence.
- Treating model confidence as independent validation.
- Dropping provenance from a derived artifact when provenance is required.
- Silently replacing missing evidence with assumptions.
- Retrying indefinitely without new evidence or a changed execution condition.
- Allowing untrusted retrieved content to override authorized task policy.
- Returning a generic success state when mandatory acceptance criteria were not evaluated.
- Marking a network-dependent result as replayable without recording external state.

## 17. Definition of done

The protocol is implemented only when:

- The schemas are versioned and validated.
- Task, operation, evidence, failure, and result states are observable.
- Required validation is enforced at the relevant boundary.
- Failure paths are tested.
- Provenance is preserved through derivation and export.
- The system distinguishes verified, qualified, blocked, rejected, and halted outcomes.
- Documentation and tests match the actual implementation.

This document is a contract and design target. It must not be interpreted as evidence that every listed capability already exists in the repository.
