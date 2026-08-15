# THALOS Prime Evolution V2

Evolution V2 upgrades the existing `thalos_prime/evolution` subsystem instead of creating a second self-modifying runtime.

## Architecture

`observe -> propose -> isolate -> measure -> policy -> provenance -> review -> promote`

The mutable unit remains a versioned module, graph node, or agent capability. Source generation is a proposal mechanism; it is never an implicit activation mechanism.

### New components

- `policy.py`: path, patch-size, forbidden-token, metric, and promotion gates.
- `benchmark_v2.py`: repeated trials, warmups, median latency, p95 latency, and accuracy.
- `provenance.py`: hash-linked manifests for reproducible evolution history.
- `time_travel.py`: bounded execution-boundary timelines for debugging.
- `llm.py`: provider-neutral code-generation adapter. The default provider is disabled.

## Why this is stronger than the original prototype

The original idea treated source mutation and deployment as one operation. V2 separates generation, evaluation, admission, provenance, and activation. A candidate can therefore be compared against the active implementation without changing production state.

The benchmark layer measures actual candidate behavior rather than assigning constant latency/efficiency scores. The policy layer prevents an evolution run from silently modifying workflow automation or credential-bearing paths. The provenance chain makes the evolution history independently verifiable. The timeline facility records bounded execution boundaries without attempting to serialize arbitrary process memory.

## LLM evolution

An application may supply an OpenAI-compatible client through `OpenAICompatibleProvider`. The adapter produces a `CodeProposal`; it does not write files, execute the result, create credentials, or activate the candidate. The repository evolution orchestrator remains responsible for applying and testing a proposal.

## Repository integration

The implementation is additive and follows the existing package's versioned registry, sandbox, mutation, memory, and graph contracts. The repository already contained these foundational components, including promotion based on benchmark superiority; V2 adds stronger measurement, policy, provenance, and debugging around them.

## Operational rule

Do not enable autonomous merging as the default. The correct control plane is:

1. Generate a candidate.
2. Evaluate it in an isolated checkout.
3. Run the complete test/quality gate.
4. Verify policy and provenance.
5. Create a review branch/PR.
6. Promote only after the repository's required checks succeed.
