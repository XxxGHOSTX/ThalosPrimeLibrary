# Experiment Workflow: Design and Usage

## What this adds

ThalosPrimeLibrary now has an initial shared foundation for comparing candidate solutions instead of treating one model's answer as authoritative.

The `thalos_prime.experiments` package contains four pieces:

- `plan.py`: declarative, deterministic dependency graph for task definition, evidence intake, representation generation, candidate generation, validation, comparison, and report persistence. It validates unique stage IDs, known dependencies, and cycles.
- `contracts.py`: explicit task specification, metric definitions, candidate run records, comparisons, and report schema.
- `evaluator.py`: compares pre-recorded candidate measurements against an explicit baseline; ranks only candidates that satisfy test, evidence, required-metric, and target gates.
- `artifact_adapter.py`: converts the report into the existing canonical artifact format, returning a PENDING artifact for the current validation workflow.

The API exposes `GET /api/v1/experiments/plan/default` and `POST /api/v1/experiments/compare`.

## Core method

1. Define the task family, dataset version, baseline, primary metric, metric directions, target thresholds, and evidence requirements before examining candidate results.
2. Run each candidate in an isolated, controlled harness external to the evaluator.
3. Record each metric as a list of measurements, along with test IDs, evidence references, implementation version, model/tool versions, environment fingerprint, configuration digest, elapsed time, and cost.
4. Submit the runs to the evaluator. The evaluator rejects duplicate candidate/run IDs, undeclared metrics, failed baselines, missing required baseline metrics, and candidate/baseline environment mismatches.
5. Inspect the report, including each candidate's exclusion reasons, metric means, sample counts, sample standard deviations, differences from the baseline, test state, evidence references, and deterministic digests.
6. Send the report artifact through the existing artifact-validation process. It is not auto-accepted by the adapter.

## Example API request

```json
{
  "spec": {
    "experiment_id": "repr-search-001",
    "task_family": "repository-fix",
    "task_description": "Compare candidate fixes against a regression test set",
    "dataset_version": "repo-tasks-v1",
    "baseline_candidate_id": "baseline",
    "primary_metric": "pass_rate",
    "metrics": [
      {
        "name": "pass_rate",
        "direction": "maximize",
        "required": true,
        "target_value": 0.9
      },
      {
        "name": "elapsed_ms",
        "direction": "minimize",
        "required": true,
        "target_value": 5000
      }
    ],
    "require_evidence": true,
    "configuration_digest": "replace-with-the-actual-configuration-sha256"
  },
  "runs": [
    {
      "run_id": "baseline-run-001",
      "candidate_id": "baseline",
      "approach": "existing baseline",
      "representation_id": "baseline-representation",
      "implementation_version": "git-commit-sha",
      "environment_fingerprint": "lockfile-and-runtime-fingerprint",
      "model_versions": {"model-or-tool": "version"},
      "configuration_digest": "actual-config-sha256",
      "metric_samples": {
        "pass_rate": [0.8, 0.82, 0.79],
        "elapsed_ms": [3300, 3400, 3290]
      },
      "tests_passed": true,
      "test_ids": ["task-set-v1"],
      "evidence_refs": ["artifact:recorded-test-log"],
      "elapsed_ms": 3400,
      "cost_usd": 0.15,
      "failure_summary": []
    }
  ]
}
```

The request above illustrates the schema, not measured ThalosPrime performance. Include a second or additional candidate run to compare alternatives. Every candidate must use the same `environment_fingerprint` as the baseline. The `model_versions` field can differ because it records the actual model/tool configuration being evaluated.

## Why the environment is matched

Changing the solution representation while holding the execution environment constant helps isolate whether the representation or candidate method contributed to the observed difference. The current implementation rejects environment mismatches rather than silently comparing results produced under different conditions. An experiment intentionally testing hardware or runtime environments should define an explicit matched experimental design in a future extension rather than disabling that guard casually.

## Metric semantics and limitations

- A metric can be maximizing or minimizing. Directed improvement is positive when the candidate is better under that direction.
- Acceptance thresholds are applied to the arithmetic mean of the supplied samples.
- The report includes sample count and sample standard deviation when there is more than one sample. When `sample_ids` are provided, it also aligns baseline and candidate values by ID and reports the mean and sample standard deviation of per-case directed improvements.
- Sample IDs must be unique, their count must match every metric sample list, and the candidate and baseline must use the same set of IDs. Different list order is allowed because values are aligned by ID.
- Paired improvements show whether a representation tends to help or hurt individual cases, but are descriptive statistics, not confidence intervals or a significance test. The evaluator does not currently correct for multiple comparisons or claim statistical significance.
- Relative improvement is omitted when the baseline mean is zero because the usual percent-change calculation would be undefined.
- The evaluator ranks by the predeclared primary metric, then reported candidate cost, elapsed time, and candidate ID for deterministic tie-breaking. It is not a multi-objective optimizer.
- A candidate is excluded from ranking if tests fail, required evidence or metrics are missing, or a declared target is not met. The report preserves the exclusion reason rather than silently discarding the candidate.
- The report digest detects changes to the serialized report under the stated canonicalization. It does not prove that the evidence itself is truthful or that the experiment design is sound.

## Safety boundary

Neither the plan nor the evaluator executes operation names, model-generated code, shell commands, repository patches, or infrastructure artifacts. The plan is declarative and the current sequential executor resolves names only from an application-registered handler map. It applies signed directive authorization, optional stage approvals, input/output budgets, and per-stage reporting. It is not a sandbox: handlers must enforce their own process/tool timeouts and isolation before running builds, tests, or other potentially dangerous workloads.

## Signed human directive records

The `HumanDirectiveRecord` type adapts the useful human-directive concept from `ThalosPrimeConcept` while keeping execution separate from the record itself. It captures objectives, constraints, parameters, acceptance criteria, prohibited actions, prohibited operation IDs, and an explicit allowlist of permitted operation IDs.

The directive can be signed with RSA-PSS/SHA-256. Its canonical signing payload contains the signer identity and every directive field except the signature. Changing a signed field invalidates verification. `authorize_operation(name, public_key)` denies an unsigned/invalid directive, a specifically prohibited operation, or any operation absent from the allowlist. The directive creates no keys and embeds no default private key; key generation, storage, rotation, and public-key trust must be handled by the application owner.

Example:

```python
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import rsa
from thalos_prime.experiments import HumanDirectiveRecord

private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
public_key = private_key.public_key()

directive = HumanDirectiveRecord(
    directive_id="hdr-representation-001",
    timestamp=datetime.now(timezone.utc),
    objectives=["Compare graph, constraint, and state-transition representations"],
    constraints=["Use the same task set and runtime environment"],
    success_criteria=["Pass the declared tests", "Record cost and failure cases"],
    prohibited_operations=["deploy", "delete-production-data"],
    permitted_operations=["ingest-evidence", "run-tests", "compare-results"],
)
directive.sign(private_key, signer_id="trusted-user-id")
assert directive.verify(public_key)
directive.authorize_operation("run-tests", public_key)
```

Use the resulting `directive.directive_digest` in `ExperimentSpec.directive_digest` and the matching ID in `ExperimentSpec.directive_id`. The evaluator requires both fields to be present together and validates the digest format. Report artifacts retain `directive:<id>` as a source reference.

**Security boundary:** the comparison API does not authorize or execute operations. Any future runner must verify the directive using a trusted public key and check the exact operation allowlist before dispatching each operation. A signature proves who signed the encoded record under the application's key-trust assumptions; it does not prove that the objective is wise or the evidence is true.

## Read-only project inventory

`ProjectInventoryBuilder` adapts the useful project-discovery and source-fingerprinting ideas from `THALOS_PRIME_CORE_INTELLIGENCE` into a bounded, non-executing scanner. It reports relative paths, sizes, SHA-256 file hashes, language counts, common manifest/test paths, duplicate files, locally resolvable Python imports, and Python syntax errors. It does not import or execute inspected files, run build tools, or return file contents.

```python
from pathlib import Path

from thalos_prime.experiments import ProjectInventoryBuilder, project_inventory_to_artifact

builder = ProjectInventoryBuilder(
    max_files=5000,
    max_file_bytes=1_048_576,
    max_total_bytes=100 * 1_048_576,
)
inventory = builder.scan("./path/to/project")
print(inventory.project_digest)
print(inventory.language_counts)
print(inventory.python_import_edges)

artifact = project_inventory_to_artifact(
    inventory,
    source_uri=Path("./path/to/project").resolve().as_uri(),
    timestamp_ns=123456789,
)
assert artifact.validation_status.value == "pending"
```

The scan skips known secret-like filenames and directories, symlinks, ignored build/vendor directories, oversized files, and binary files. Limits are explicit and a truncated scan is marked. Filename exclusions are a safety precaution, not a guarantee that every possible secret name will be recognized. The Python import graph is static and incomplete by design: dynamic imports, plugin discovery, runtime configuration, and dependencies declared only in manifests are not fully resolved. Manifest paths are inventoried but dependency manifests are not yet parsed into a transitive dependency graph.

The adapter requires a caller-supplied `source_uri` that identifies the inspected project; it does not invent a provenance pointer. The resulting artifact is a pending record for the existing validation and provenance pipeline. It is not an assertion that the project is secure, correctly configured, or fully reproducible.

## Registered workflow execution

`WorkflowExecutor` is the controlled runtime for declarative plans. It does not load a handler by importing the operation name. Application code must explicitly register each trusted handler:

```python
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import rsa
from thalos_prime.experiments import (
    ExperimentSpec,
    HumanDirectiveRecord,
    MetricDefinition,
    MetricDirection,
    WorkflowExecutor,
    default_research_plan,
)

private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
public_key = private_key.public_key()

plan = default_research_plan()
allowed_operations = sorted({stage.operation for stage in plan.stages})
directive = HumanDirectiveRecord(
    directive_id="research-run-001",
    timestamp=datetime.now(timezone.utc),
    objectives=["Compare candidate representations on a fixed task set"],
    constraints=["Use the same environment and named cases"],
    success_criteria=["Record test outputs, cost, and failures"],
    permitted_operations=allowed_operations,
)
directive.sign(private_key, signer_id="trusted-user-or-service-id")

spec = ExperimentSpec(
    experiment_id="research-run-001",
    task_family="repository-engineering",
    task_description="Inspect and compare representation alternatives",
    dataset_version="task-set-v1",
    baseline_candidate_id="baseline",
    primary_metric="pass_rate",
    metrics=[
        MetricDefinition(
            name="pass_rate",
            direction=MetricDirection.MAXIMIZE,
            target_value=0.9,
        )
    ],
    directive_id=directive.directive_id,
    directive_digest=directive.directive_digest,
)

executor = WorkflowExecutor()
executor.register("define_task", lambda context: {"task": context.initial_context["task"]})
# Register a trusted handler for each remaining operation before execution.
```

Execution then requires `plan`, the matching `spec`, the signed `directive`, its trusted public key, and a JSON-compatible `initial_context`. `authorize_experiment_operation` verifies the exact directive ID/digest and checks each operation against the signed allowlist before the registered handler is invoked. A stage marked `requires_approval=True` additionally requires its stage ID in `approved_stage_ids`.

The report records each stage's input and output digest, status, elapsed time, and bounded error details. An unsuccessful dependency blocks its descendants, while independent branches can still complete. Defaults cap an initial context at 1 MiB, each stage input at 2 MiB, each stage output at 1 MiB, accumulated outputs at 20 MiB per run, and a plan at 200 stages. These limits are configurable where exposed by the runtime. Outputs are passed as JSON-cloned data so that one handler cannot mutate stored prior-stage results through shared object references.

**Execution safety boundaries:** handlers are trusted application code; registering a handler is an explicit trust decision. The executor does not sandbox a handler or forcibly terminate an in-process Python call. Its timeout field detects that a handler returned after its allotted time; a handler invoking a test runner, build system, or external tool must enforce a real process/tool timeout and isolation itself. Do not register model-generated Python or commands as handlers. Review consequential operations separately and require explicit approvals.

A run report can be converted into a PENDING artifact via `workflow_report_to_artifact(report, source_uris=..., timestamp_ns=...)`. The caller must supply actual supporting source/evidence references; the adapter does not manufacture one and does not bypass the existing artifact validation or belief-admission path.

## Next integration stages

1. Add durable stage checkpoints, restart/recovery semantics, and a process-level cancellation mechanism. The existing in-memory handler registry and stage records do not provide crash recovery or forcibly terminate long-running in-process calls.
2. Connect evidence intake to existing artifact and retrieval interfaces.
3. Add safe adapters for model providers and code/test harnesses; never import callable execution from legacy execution graphs without redesigning trust boundaries.
4. Add dataset-level benchmark runners and statistical analysis that can handle paired tasks, repeated trials, uncertainty intervals, and regression tests.
5. Connect the existing signed-directive and stage-approval gates to a reviewed patch/output flow before generating changes or deployment artifacts.
6. Add operational telemetry only after measuring real workloads; avoid claiming performance gains until benchmarks support them.

## Validation status

The source and tests have been added to the integration branch. This document does not claim that CI has passed. Check the current pull-request checks and run the package's tests, type checks, lint, lifecycle validation, and security scans before merging.
