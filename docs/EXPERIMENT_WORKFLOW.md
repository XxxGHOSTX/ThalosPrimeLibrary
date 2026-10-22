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
- The report includes sample count and sample standard deviation when there is more than one sample. It does not currently calculate confidence intervals, correct for multiple comparisons, or claim statistical significance.
- Relative improvement is omitted when the baseline mean is zero because the usual percent-change calculation would be undefined.
- The evaluator ranks by the predeclared primary metric, then reported candidate cost, elapsed time, and candidate ID for deterministic tie-breaking. It is not a multi-objective optimizer.
- A candidate is excluded from ranking if tests fail, required evidence or metrics are missing, or a declared target is not met. The report preserves the exclusion reason rather than silently discarding the candidate.
- The report digest detects changes to the serialized report under the stated canonicalization. It does not prove that the evidence itself is truthful or that the experiment design is sound.

## Safety boundary

Neither the plan nor the evaluator executes operation names, model-generated code, shell commands, repository patches, or infrastructure artifacts. The plan is declarative. A later execution service must resolve operations from an allowlisted handler registry, use resource limits and isolated workspaces, log each stage, and require explicit approval before consequential actions.

## Next integration stages

1. Add a handler registry and structured stage-run records, with explicit retry and timeout semantics.
2. Connect evidence intake to existing artifact and retrieval interfaces.
3. Add safe adapters for model providers and code/test harnesses; never import callable execution from legacy execution graphs without redesigning trust boundaries.
4. Add dataset-level benchmark runners and statistical analysis that can handle paired tasks, repeated trials, uncertainty intervals, and regression tests.
5. Add permission-gated review and optional human approval before producing patches or deployment artifacts.
6. Add operational telemetry only after measuring real workloads; avoid claiming performance gains until benchmarks support them.

## Validation status

The source and tests have been added to the integration branch. This document does not claim that CI has passed. Check the current pull-request checks and run the package's tests, type checks, lint, lifecycle validation, and security scans before merging.
