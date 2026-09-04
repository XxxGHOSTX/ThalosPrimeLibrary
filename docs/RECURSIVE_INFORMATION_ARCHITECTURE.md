# Recursive Information Architecture

## Purpose

Thalos Prime already provides deterministic artifacts, validation, belief state,
provenance, reasoning, auditability, and a versioned evolution engine. This layer
turns the recent information-first hypothesis into an executable measurement
framework rather than treating the hypothesis itself as a fact.

## Core model

The operational loop is:

`observe -> predict -> compare -> self-model -> score -> validate -> evolve -> record -> reuse`

The system measures six separable signals:

1. Prediction accuracy — how often expected outcomes match observations.
2. Self-model consistency — how accurately an externally supplied model predicts the system's recorded state.
3. Memory stability — persistence of state representations across evaluation windows.
4. Contradiction rate — frequency of incompatible predictions or claims.
5. Calibration — agreement between confidence and observed correctness.
6. Efficiency — useful predictive performance relative to declared operation cost.

The composite score is a deterministic engineering metric, not a consciousness,
awareness, sentience, or personhood detector.

## Integration with existing TPL

Artifact identity remains SHA-256 based. Validation and the Belief Ledger remain
the epistemic gate. The recursive-information layer consumes validated evaluation
artifacts and emits measurements that can themselves be stored as artifacts.
The existing audit trail records measurement and evolution events. The existing
Evolution Engine can use the score as an additional benchmark dimension while
retaining sandboxing, versioning, promotion gates, and rollback capability.

This preserves the architecture's control/data separation and its requirement
that derived knowledge remain traceable to accepted inputs.

## Developmental analogy

For an infant-like learner, the engineering analogue is not biological breathing.
It is a persistent homeostatic execution loop: receive input, maintain internal
state, predict the next state, observe the result, update memory, and regulate
resource use. The same abstract protocol can be instantiated in software, a
robotic system, or another substrate without assuming the substrates are
phenomenologically equivalent.

## Emergence test

Do not encode a conclusion that intelligence or consciousness must emerge.
Instead, evaluate whether measurable properties show phase changes as system
capacity increases. A candidate threshold should require:

- a preregistered metric definition;
- repeated evaluation windows;
- baseline and candidate comparison;
- robustness under controlled noise;
- cross-task generalization;
- independent replication;
- full provenance and deterministic replay.

A threshold is a statistical observation only after these conditions are met.

## Evolution integration

The Evolution Engine should optimize capability implementations against this
suite rather than rewriting arbitrary source code at runtime. Candidate modules
must run in the sandbox, beat baseline fitness, and produce an auditable mutation
record. This follows the repository's existing `observe -> diagnose -> propose ->
sandbox -> score -> promote -> record -> reuse` loop.

## Multi-agent extension

When multiple agents are connected, represent communication as explicit messages
and evaluate whether coordination improves prediction, consistency, and task
fitness. A discovered communication shorthand is an observable protocol; it is
not evidence by itself of independent social motivation.

## Scientific boundary

This architecture is intentionally substrate-neutral and epistemically conservative:
behavioral measurements can establish behavioral properties. They cannot, by
measurement alone, establish subjective experience. If future evidence supports a
stronger theory, the data model can add new observables without rewriting the
existing provenance and validation foundations.
