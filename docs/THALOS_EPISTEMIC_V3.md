# Thalos Prime Epistemic Computing v3

## Purpose

The v3 layer changes Thalos Prime from a source-and-confidence system into a replayable epistemic computation substrate.

The current transactional foundation remains authoritative for durable state. v3 supplies the computation performed before a belief transition is committed.

```text
Natural language
      |
      v
Claim Compiler
      |
      v
Claim IR
      |
      +-------------------+
      |                   |
      v                   v
Witness Calculus     Challenge Engine
      |                   |
      +---------+---------+
                |
                v
          Warrant Algebra
                |
                v
          Belief Lattice
                |
        +-------+--------+
        |                |
        v                v
 Perturbation       Counterfactual
 Stability           Decision Surface
        |                |
        +-------+--------+
                |
                v
         Decision Compiler
                |
                v
      Epistemic Transaction
                |
                v
        Epistemic VM / Replay
                |
                v
        Proof + Provenance
                |
                v
        Transactional Ledger
```

## Core invariants

### Epistemic conservation

A transformation cannot create usable warrant for free.

- Copy preserves warrant.
- Paraphrase preserves or reduces warrant.
- Summarization preserves or reduces warrant.
- Deduction is bounded by premise warrant and formal validity.
- Corroboration can increase warrant only through explicitly modeled independent evidence.
- Contradiction increases visible conflict; it never deletes prior support.
- Speculation becomes a search hypothesis and does not inherit factual warrant.

The system therefore separates **hypothesis generation** from **warrant acquisition**.

### Witness independence

Ten documents are not ten independent witnesses when nine derive from the first.

Witnesses carry causal parent relationships. The Witness Calculus groups witnesses by lineage and independence group before support is aggregated.

### Falsification shadow

Every claim receives deterministic challenge tasks for:

- counterevidence
- source dependence
- temporal scope
- claim scope
- causal alternatives when applicable
- identity ambiguity when applicable
- measurement failure when applicable

An accepted decision with unresolved challenges is not equivalent to a stable fact.

### Multidimensional belief state

Thalos does not reduce the epistemic state to a single confidence number. It keeps independent dimensions:

- support
- contradiction
- entailment
- temporal validity
- scope validity
- witness independence
- provenance integrity
- reproducibility
- falsifiability
- information state
- stability
- reversibility

The belief state is not itself the final authority. The Decision Compiler applies explicit policy over the belief state plus stability and counterfactual analysis.

### Decision compilation

The Decision Compiler converts a computed belief state into a policy artifact with explicit reason codes.

It can downgrade an apparently accepted claim to provisional when:

- required challenges remain unresolved
- the decision is fragile under perturbation
- a small critical evidence set can flip the decision
- contradiction is present

The compiler also produces `safe_to_state_as_fact`, which is intentionally stricter than `accepted`.

### Counterfactual decision analysis

For an evidence set `E`, Thalos can evaluate:

```text
Decision(E)
Decision(E - {e1})
Decision(E - {e2})
Decision(E - {e1,e2})
...
```

This produces:

- critical evidence: evidence whose removal can flip the decision
- robust evidence: evidence whose removal does not change the decision
- minimal flip sets: smallest detected removals that reverse the decision

The result answers a more useful question than confidence:

> What would have to change for this conclusion to change?

### Immutable epistemic transaction

The complete pre-commit computational state is represented by an `EpistemicTransaction` containing:

- canonical Claim IR
- challenge-plan identity
- witness analysis
- warrant state
- belief-lattice position
- final Decision Artifact
- perturbation stability report
- counterfactual report
- source snapshot identity
- run identity
- proof-bundle identity

The transaction is content-addressed. Its fingerprint excludes only the later durable commit-event reference, so committing the transaction does not alter the identity of the computation that produced it.

The final decision artifact is part of the transaction itself. The transaction cannot be considered ready for commit unless its decision, stability baselines, counterfactual baselines, and unresolved-challenge state agree.

### Replayable epistemic VM

The v3 VM contains pure deterministic operations and no network or model calls:

```text
COMPILE_CLAIM
BUILD_CHALLENGE_PLAN
CLASSIFY_BELIEF
EMIT_RESULT
```

A model may propose a richer claim parse or evidence hypothesis, but the resulting object must be validated before entering the VM.

The VM execution fingerprint is derived from the program, serialized state, claim identity, belief position, and challenge plan identity.

## MCP boundary

The v3 MCP tools are computational adapters, not the authority:

```text
thalos.v3.claim.compile
thalos.v3.challenge.plan
thalos.v3.belief.classify
thalos.v3.decision.compile
thalos.v3.program.run
thalos.v3.witness.analyze
thalos.v3.warrant.transform
thalos.v3.stability.analyze
thalos.v3.counterfactual.analyze
thalos.v3.transaction.build
```

None of these tools directly commits durable belief state.

Durable commitment remains behind the existing transactional ledger and approval boundary.

## Recommended workflow

```text
1. Compile user question into Claim IR.
2. Build falsification shadow.
3. Retrieve candidate sources into a frozen snapshot.
4. Construct witnesses and causal genealogy.
5. Bind exact evidence spans.
6. Evaluate support and contradiction separately.
7. Aggregate independent witnesses through Witness Calculus.
8. Apply Warrant Algebra transformations explicitly.
9. Run required challenge tasks.
10. Classify the claim in the Belief Lattice.
11. Run perturbation stability analysis.
12. Run counterfactual evidence analysis.
13. Compile the final policy Decision Artifact.
14. Build the immutable Epistemic Transaction containing the Decision Artifact.
15. Generate proof and provenance package.
16. Commit to durable ledger only through policy-controlled transaction and authorization.
```

## What v3 does not claim

v3 is not a truth oracle.

It does not prove that a source is truthful merely because it is primary.
It does not prove causation merely from temporal sequence.
It does not turn model output into evidence.
It does not treat source count as independence.
It does not guarantee real-world truth from logical consistency.

The architecture instead guarantees that the system's own epistemic operations are explicit, versioned, replayable, and inspectable.

## Future extension points

The next safe extensions are:

1. Claim-IR enrichment with a validated semantic parser.
2. Causal challenge programs for intervention and confounding analysis.
3. Temporal interval algebra with explicit uncertainty bounds.
4. Evidence replacement and substitution counterfactuals.
5. Signed transparency logs over committed epistemic events.
6. Independent proof-bundle verification for v3 lattice, decision, and counterfactual outputs.
7. Benchmark datasets for stability, witness correlation, appropriate abstention, and decision sensitivity.

Advanced cryptographic proofs, distributed consensus, and learned semantic retrieval should remain downstream of these primitives rather than defining them.
