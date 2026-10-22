# Thalos Prime Integration Registry

This registry tracks candidate source repositories and the evidence required before their code becomes part of the canonical ThalosPrimeLibrary.

## Status definitions
- **Candidate** — identified from repository metadata or README; implementation not yet audited.
- **Inspected** — relevant files and dependencies reviewed.
- **Adapted** — code ported behind a documented interface.
- **Tested** — target-repository tests run with recorded results.
- **Accepted** — requirements, security review, integration tests, and acceptance criteria passed.
- **Deferred / Rejected** — not included, with reason recorded.

## Candidate registry

| Source repository | Candidate contribution | Current status | Acceptance requirement |
|---|---|---|---|
| [ThalosPrimeLibrary](https://github.com/XxxGHOSTX/ThalosPrimeLibrary) | Canonical base: Babel tooling, symbolic constraints, planning, retrieval, API/UI, artifact synthesis | Canonical target | Establish current baseline and regression suite |
| [ThalosPrimeLibrary.v2](https://github.com/XxxGHOSTX/ThalosPrimeLibrary.v2) | Staged retrieval, reasoning, validation, presentation concepts | Candidate; README reviewed | Inspect code and tests; identify concrete improvements not already present |
| [ThalosPrimeConcept](https://github.com/XxxGHOSTX/ThalosPrimeConcept) | Human directive records, execution DAGs, provenance, graph/vector retrieval, sandbox concepts | Declarative DAG and RSA-PSS-signed HumanDirectiveRecord adapted in this branch; raw callable executor not imported | Verify tests, key management, provenance integrity, graph execution semantics, and sandbox boundaries before further adoption |
| [THALOS_PRIME_CORE_INTELLIGENCE](https://github.com/XxxGHOSTX/THALOS_PRIME_CORE_INTELLIGENCE) | Project analysis, dependency graph, build orchestration, caching | Bounded read-only ProjectInventoryBuilder adapted in this branch; no build commands are executed | Verify tests, file/byte bounds, import graph results, and dependency/security handling; build orchestration remains deferred |
| [ThalosPrime-Platform](https://github.com/XxxGHOSTX/ThalosPrime-Platform) | Governance, risk analysis, audit and artifact workflow | Candidate; README reviewed | Separate enterprise-specific features from reusable governance; verify security |
| [Thalos-Prime-Directive2](https://github.com/XxxGHOSTX/Thalos-Prime-Directive2) | Container/deployment/CI and health-check patterns | Candidate; README reviewed | Confirm actual stack, endpoints, tests, license compatibility, secrets handling |
| [Thalos-Prime-Directive](https://github.com/XxxGHOSTX/Thalos-Prime-Directive) | Bio-inspired simulations and general software modules | Candidate; README reviewed | Audit ordinary software separately; exclude unverified biological/organism claims |
| [Thalos_Prime_New_system_build](https://github.com/XxxGHOSTX/Thalos_Prime_New_system_build) | Custom math, tokenizer, transformer, memory, inference, UI | Candidate; README reviewed | Compare correctness/performance to standard libraries; audit crypto before reuse |
| [THALOS-PRIME-CORE-BUILD-V2](https://github.com/XxxGHOSTX/THALOS-PRIME-CORE-BUILD-V2) | SBI-style inference, persistence, GUI, multimodal interfaces | Candidate; README reviewed | Inspect source; substantiate parameter-count and architecture claims; test dependencies |
| [Thalos-Prime-Web](https://github.com/XxxGHOSTX/Thalos-Prime-Web) | Web interface | Candidate; README reviewed | Verify API connectivity, accessibility, dependency/security posture |
| [ThalosPrimeLibraryOfBabel](https://github.com/XxxGHOSTX/ThalosPrimeLibraryOfBabel) | Potential standalone Babel implementation | Candidate; repository discovered | Inspect repository contents; compare with core implementation before deciding |
| [ThalosPrime-v1](https://github.com/XxxGHOSTX/ThalosPrime-v1) | Earlier private implementation | Candidate; metadata available | Review access, source, licensing and provenance before considering reuse |
| [ThalosPrime-v1.0](https://github.com/XxxGHOSTX/ThalosPrime-v1.0) | Earlier version | Candidate; metadata available | Compare unique, tested components only |
| [ThalosPrimeMedv1](https://github.com/XxxGHOSTX/ThalosPrimeMedv1) | Medical-domain implementation | Candidate; metadata available | Keep domain-specific and clinically unvalidated functions out of general claims; assess privacy and safety |
| [Thalos-Prime-Revision](https://github.com/XxxGHOSTX/Thalos-Prime-Revision) | Revision branch/project | Candidate; README reviewed | Inspect tree and commits to identify unique work and overlap |
| [ThalosPrimeCodev1](https://github.com/XxxGHOSTX/ThalosPrimeCodev1) | Earlier code project | Candidate; metadata available | Inspect tree, tests, license and unique code before selection |

## Implemented shared foundation on the integration branch

The following implementation now exists in `thalos_prime/experiments/`; the experiment comparator and DAG plan are exposed through the API, while project scanning and directive authorization are Python interfaces:

- Declarative DAG planning with stable topological ordering, parallel-ready representation branches (graph, constraints, state transitions), and cycle/missing-dependency rejection. This adapts the dependency-graph idea from ThalosPrimeConcept rather than importing its raw callable executor.
- Signed `HumanDirectiveRecord` with RSA-PSS/SHA-256 signatures, explicit operation allowlists, deny-by-default authorization, and directive ID/digest linkage in experiment specs. Key lifecycle and public-key trust remain application responsibilities.
- Typed experiment specifications and candidate-run records that preserve repeated metric samples, model/tool versions, implementation version, environment fingerprint, configuration digest, tests, evidence references, time, and cost.
- Baseline comparison with explicit maximize/minimize semantics, target gates, eligibility reasons, sample counts, dispersion, stable ranking, and report/spec digests.
- Adapter to the existing canonical artifact schema. Experiment reports and project inventories become PENDING artifacts and must go through the existing validation workflow.
- `ProjectInventoryBuilder`, a bounded read-only scanner that hashes files, inventories manifests/tests, detects byte-identical files, creates a best-effort Python import graph, records syntax errors, and avoids code execution. Output can be stored through the canonical artifact adapter.
- API endpoints for retrieving the default declarative plan and comparing recorded result batches.

Source modules and targeted tests have been added in this branch. Repository-wide CI jobs have been failing before runner assignment (the job API reports no runner and no executed steps), so those results do not establish test or lint status. The new local test suite has not yet been verified against the complete repository environment. This implementation does not yet dispatch models, execute candidate code, implement a sandbox, calculate confidence intervals/statistical significance, or import the candidate repositories wholesale.

## Current limitations of this registry

The listed candidate contributions are inferred from repository README summaries and metadata. This registry does not assert that source code has been ported, that all listed repositories have compatible licenses, or that advertised features are implemented or tested. Update each status only after collecting evidence from the actual source and target test runs.

## Per-component decision record

For every proposed import, record:
- Component name and source repository.
- Source commit SHA and source file paths.
- License and copyright obligations.
- Target path and public interface.
- Dependency/runtime changes.
- Security and data-handling implications.
- Tests run, environment, and results.
- Benchmark/acceptance result and limitations.
- Decision, reviewer, and date.
