# Unified Thalos Prime Architecture

## Purpose
ThalosPrimeLibrary is the proposed canonical integration repository for Thalos Prime. Its purpose is to turn a human-defined problem into a traceable investigation that compares candidate approaches, tests claims, detects defects, and records what the evidence supports.

The system is not represented as an unrestricted problem solver or as technology that bypasses current scientific, mathematical, computational, or physical limits. Its value must be demonstrated by measured improvements on defined tasks.

## Canonical workflow
1. **Task contract:** capture the human objective, scope, constraints, assumptions, prohibited actions, success criteria, and acceptance tests.
2. **Evidence intake:** gather source documents, code, data, measurements, and references; track source, version, and limitations.
3. **Problem representation:** build explicit entities, relations, constraints, dependencies, variables, and uncertainty. Propose alternate representations only when they can be evaluated.
4. **Candidate generation:** generate multiple hypotheses or implementations using available models and deterministic tools. Preserve disagreement rather than forcing consensus.
5. **Static and logical checks:** validate schemas, constraints, types, dependencies, invariants, and formal properties where supported.
6. **Execution and experiments:** run tests, calculations, simulations, builds, or controlled experiments in a bounded environment.
7. **Baseline comparison:** compare outcomes with a stated baseline using metrics chosen before reviewing results where practical.
8. **Evidence ledger:** record input hashes, source references, model/tool versions, configurations, code commit, commands, outputs, failures, metrics, and uncertainty.
9. **Decision report:** separate passed checks, failed checks, untested claims, assumptions, and external validity limits.
10. **Revision:** change a candidate in response to a specific failure or measurable improvement and rerun relevant checks.

## Target module boundaries

| Module | Responsibility | Status |
|---|---|---|
| Directive/task contract | Human intent, constraints, acceptance criteria | Target architecture; verify implementation |
| Evidence and provenance | Source records, hashes, execution records, traceable artifacts | Candidate from ThalosPrimeConcept; audit before adoption |
| Library of Babel | Deterministic page/address tooling and coherence heuristics | Existing component; not an oracle or proof of truth |
| Retrieval and knowledge graph | Search, retrieval, relationship traversal | Candidate in library/concept repositories; validate dependencies |
| Representation and constraints | Symbolic constraints, SAT/SMT checks, graph/state representations | Candidate in current library; measure benefits |
| Candidate orchestration | Compare candidate solutions and coordinate task stages | Integration target; do not assume fully integrated |
| Test and benchmark harness | Unit, integration, property, regression, comparative tests | Required product foundation |
| Build and artifact tools | Inspect projects, build artifacts, prepare changes | Candidate from core-intelligence/platform work; safe adapter required |
| API and interface | Expose runs, status, artifacts, reports | Existing API/UI starting point; verify end-to-end behavior |
| Governance and security | Permissions, sandboxing, secrets, audit, approval gates | Required before consequential execution |

## Repository contribution map

- **Primary core:** [ThalosPrimeLibrary](https://github.com/XxxGHOSTX/ThalosPrimeLibrary). Preserve and improve existing Library of Babel tooling, symbolic reasoning, planning, retrieval, infrastructure synthesis, API, and UI where tests support behavior.
- **High priority:** [ThalosPrimeLibrary.v2](https://github.com/XxxGHOSTX/ThalosPrimeLibrary.v2). Inspect staged retrieval/reasoning/validation/presentation design and tests; adopt concrete traceability improvements, not claims wholesale.
- **High priority:** [ThalosPrimeConcept](https://github.com/XxxGHOSTX/ThalosPrimeConcept). Inspect directive records, execution graphs, provenance, graph/vector retrieval, sandbox, and Babel integration. Prioritize task contracts and evidence-linked execution.
- **High priority:** [THALOS_PRIME_CORE_INTELLIGENCE](https://github.com/XxxGHOSTX/THALOS_PRIME_CORE_INTELLIGENCE). Inspect project analysis, dependency mapping, build orchestration, signatures, caching, and failure reporting. Integrate only verified components behind a safe adapter.
- **High priority, selective:** [ThalosPrime-Platform](https://github.com/XxxGHOSTX/ThalosPrime-Platform). Inspect governance, audit, risk analysis, and artifact workflow. Enterprise Shadow-AI detection is a separate product domain; reuse only broadly applicable, tested components.
- **Conditional:** [Thalos-Prime-Directive2](https://github.com/XxxGHOSTX/Thalos-Prime-Directive2). Inspect CI/CD, container, health-check, deployment, and security artifacts. Verify the actual stack and tests before porting.
- **Conditional:** [Thalos-Prime-Directive](https://github.com/XxxGHOSTX/Thalos-Prime-Directive). Review ordinary software modules individually. Do not make biological hardware, organoid, consciousness, or neural-interface claims part of the core product without real implementations and independent evidence.
- **Conditional:** [Thalos_Prime_New_system_build](https://github.com/XxxGHOSTX/Thalos_Prime_New_system_build) and [THALOS-PRIME-CORE-BUILD-V2](https://github.com/XxxGHOSTX/THALOS-PRIME-CORE-BUILD-V2). Inspect custom math, tokenizer, transformer, memory, UI, and inference code as experimental candidates; benchmark against maintained libraries and audit cryptography before reuse.
- **Conditional:** [Thalos-Prime-Web](https://github.com/XxxGHOSTX/Thalos-Prime-Web). Inspect interface components and API wiring; adopt only after accessibility and security checks.
- **Conditional:** [ThalosPrimeLibraryOfBabel](https://github.com/XxxGHOSTX/ThalosPrimeLibraryOfBabel). Inspect contents and compare with the core to avoid duplicate packages and ambiguous imports.

## Integration phases

### Phase 0 — Inventory
Capture each source repository's default branch, latest commit, license, tree, package metadata, runtime requirements, and tests. Identify duplicate modules, incompatible names, unsafe code paths, secrets, and unverified claims. Run source tests where feasible and record exact commands and outcomes. Produce an adopt/adapt/defer/reject decision for each component.

### Phase 1 — Canonical contracts
Define typed task, evidence, candidate, test-result, and report schemas. Standardize stable IDs, provenance links, error types, timestamps, version metadata, and result statuses. Missing tests must never count as a pass.

### Phase 2 — Minimum integrated vertical slice
Implement one end-to-end path: accept a bounded task and criteria; ingest evidence; generate competing approaches where appropriate; run deterministic validation and relevant tests; compare against a baseline; emit a machine-readable report with provenance and failures.

### Phase 3 — Selective integration
Add one adapter at a time. Require passing unit and integration tests, documented dependencies, security review, and evidence that it improves a defined metric or provides a necessary capability.

### Phase 4 — Comparative evaluation
Use fixed task sets and simple baselines. Measure correctness, defect detection, false positives, missed errors, latency, compute cost, human review time, and reproducibility. Include failed cases.

### Phase 5 — Controlled execution
Use least privilege, isolated workspaces, allowlisted commands, resource limits, secret redaction, audit logs, and human approval for consequential changes. Deploy generated artifacts only after tests and explicit authorization.

## Evidence statuses
- **Proposed:** generated but not checked.
- **Checked:** passed a named static or logical check.
- **Tested:** executed under recorded conditions.
- **Reproduced:** repeated with recorded inputs and environment.
- **Empirically supported:** supported by observations in a relevant real-world setting.
- **Unresolved:** evidence is missing, conflicting, or insufficient.

These statuses are not interchangeable. A hash establishes identity/integrity of recorded bytes under relevant assumptions, not truth. A coherence score reflects its scoring function, not factual accuracy. A successful build proves only the conditions and tests that actually ran.

### Registered stage execution

The `WorkflowExecutor` now runs the declarative plan through explicitly registered handlers. Before dispatch, it checks that the experiment spec is bound to the exact signed Human Directive Record and that the stage's operation identifier is allowlisted by that directive. Stages requiring separate approval remain blocked until their IDs are explicitly approved. Failed dependencies block descendant stages without erasing successful independent branch results.

The runtime records stage input/output digests, status, elapsed time and errors, clones JSON input between stages, and enforces configurable per-stage and aggregate output budgets plus a bounded stage-input budget. It is sequential today; the DAG identifies independent branches for future concurrency once cancellation, output persistence and resource isolation can be guaranteed. The current timeout behavior is post-return overrun detection, not forced interruption, and the executor is not a sandbox. Any registered handler that calls a build system or test runner must enforce its own subprocess timeout, permissions and isolation.

Execution reports can be converted to PENDING canonical artifacts with caller-supplied evidence references. The adapter does not manufacture evidence URIs or accept the report into the belief ledger.

## Definition of done
A component is integrated only when its source and license are recorded; dependencies and interface are documented; it is called through a canonical interface; unit and integration tests pass in the target repository; failure modes and security boundaries are documented; acceptance tests demonstrate the stated effect; and product claims match validated scope.



## Additional integrated engineering foundations

### Signed directive contract

`thalos_prime.experiments.directive.HumanDirectiveRecord` adapts the Human Directive Record idea from ThalosPrimeConcept. It signs a canonical payload with RSA-PSS/SHA-256, binds the signer identity to the signature, and requires every operation to be explicitly allowlisted. It is intentionally separate from scheduling and execution so that an unverified directive cannot run a stage merely by appearing in a request.

### Project inventory

`thalos_prime.experiments.project_inventory.ProjectInventoryBuilder` adapts the project-analysis and file-fingerprinting idea from THALOS_PRIME_CORE_INTELLIGENCE. It scans within explicit file and byte budgets; skips known secret-like paths, symlinks, ignored build/vendor directories, and binary files; hashes file bytes; indexes manifests and test paths; resolves a best-effort static Python import graph; and reports syntax failures without executing source. An inventory can be converted into a PENDING canonical artifact and passed through the existing validation workflow.

### Multi-representation tournament

The default plan is version 2 and branches into graph, constraint, and state-transition representations after a shared task/evidence/model phase. Each branch proposes a candidate; the shared validation stage runs only after all branches complete; the baseline-comparison stage ranks candidates by predeclared metrics. Independent branches are eligible for parallel scheduling in a future runtime, but the current plan is declarative and does not itself schedule or execute handlers.

This method is useful because it makes representation a measurable variable. On the same task set and controlled environment, the system can compare the quality, runtime, cost, failure rate, and other declared criteria of each representation rather than asserting that one is generally superior.

## First integrated research substrate

The `thalos_prime.experiments` package is the first concrete shared foundation in this integration branch. It combines three useful architectural ideas: human-defined task criteria, dependency-aware execution planning, and evidence-linked artifact records.

- `ExperimentSpec` fixes the task family, dataset version, declared metrics, baseline, and acceptance targets before candidate results are compared.
- `ExperimentPlan` declares a directed acyclic workflow from task definition through evidence intake, representation construction, candidate generation, validation, baseline comparison, and report persistence. Topological ordering is stable; missing dependencies and cycles are rejected.
- `CandidateRun` preserves the implementation version, environment fingerprint, model/tool versions, configuration digest, test IDs, evidence references, cost, elapsed time, and repeated metric observations.
- `ExperimentEvaluator` computes metric means and sample dispersion, compares candidates with the baseline, excludes failed or untraceable candidates, applies declared targets, and produces a deterministic report digest.
- `report_to_artifact` writes the report into the existing canonical artifact schema as a PENDING artifact. The existing validation and belief-ledger workflow remains responsible for downstream admission.

This is an initial working substrate, not the full product. It does not dispatch model calls, execute candidate code, sandbox generated code, perform statistical significance tests, or claim that a result generalizes beyond its dataset and execution conditions. Its role is to make later integrations measurable, reproducible, and safer to compose.

## Immediate next step
Inventory the full source trees and tests for high-priority candidate repositories. README summaries are not enough to safely copy code or assert integration. Integrate the smallest useful vertical slice first: task contract → evidence/provenance → candidate comparison → test runner → baseline report.
