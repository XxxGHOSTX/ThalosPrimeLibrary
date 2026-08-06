---
name: epistemic-v3-investigation
description: Execute a Thalos Prime v3 investigation using Claim IR, Witness Calculus, falsification challenges, warrant transformations, belief-lattice classification, decision compilation, stability testing, counterfactual evidence analysis, and immutable transaction assembly before any durable belief commit.
---

# Thalos Prime Epistemic v3 Investigation

Use this workflow when the task requires more than retrieving sources. The objective is to construct a replayable epistemic transaction, not merely produce a fluent answer.

## Required sequence

1. Compile the user's question with `thalos.v3.claim.compile`.
2. Inspect compiler warnings. Do not silently invent semantic slots, temporal scope, or claim type.
3. Build the falsification shadow using `thalos.v3.challenge.plan`.
4. Ingest or locate admissible source artifacts and freeze the source snapshot.
5. Retrieve candidate evidence only from the frozen snapshot.
6. Bind exact evidence spans to source artifacts.
7. Construct witnesses for supporting and contradicting evidence.
8. Use `thalos.v3.witness.analyze` to detect source genealogy and correlation.
9. Use `thalos.v3.warrant.transform` to make every warrant-changing operation explicit.
10. Treat model-generated hypotheses as speculation until evidence enters the warrant system.
11. Execute required challenge tasks, including counterevidence search and source-dependence checks.
12. Classify the evidence using `thalos.v3.belief.classify`.
13. Run `thalos.v3.stability.analyze` to test sensitivity to valid perturbations.
14. Run `thalos.v3.counterfactual.analyze` to identify minimal evidence sets that would flip the decision.
15. Compile the final policy decision with `thalos.v3.decision.compile`.
16. Build the immutable transaction with `thalos.v3.transaction.build`, including the final Decision Artifact.
17. Only then pass the transaction to the durable ledger commit path.

## Epistemic rules

- A source count is not an independence count.
- A primary source can still be wrong.
- Correlated copies count as one witness lineage unless independent observation is established.
- Logical validity does not establish premise warrant.
- Model fluency does not create evidence.
- Summarization and paraphrase cannot increase warrant.
- Contradicting evidence must remain visible even when support is strong.
- A provisional or disputed conclusion must not be presented as settled fact.
- An unresolved challenge is part of the epistemic state and must be reported.
- A stable conclusion must still preserve its falsification conditions.
- The final Decision Artifact is a policy result, not a claim of metaphysical truth.
- The immutable transaction must contain the decision artifact that was compiled from the exact stability and counterfactual analyses used to justify it.
- Durable belief changes require the existing authorization and approval boundary.

## Output contract

Return:

- canonical claim IR
- compiler warnings
- challenge plan and unresolved tasks
- source snapshot ID
- witness genealogy and independence analysis
- supporting evidence
- contradicting evidence
- warrant state and transformation history
- belief-lattice position
- stability report
- counterfactual report
- final Decision Artifact and reason codes
- immutable epistemic transaction ID/fingerprint
- durable ledger state only if a separately authorized commit occurred

Do not reduce the entire transaction to one confidence score.
