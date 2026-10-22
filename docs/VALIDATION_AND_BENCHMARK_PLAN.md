# Thalos Prime Validation and Benchmark Plan

## Objective

Determine whether the integrated workflow improves the quality or efficiency of solutions for a defined task class compared with a simple baseline. Do not infer general capability from demonstrations or isolated passing tests.

## First evaluation target

Start with repository engineering tasks because they permit executable checks and objective outcomes:
- Identify a reproducible bug or failed test.
- Generate a proposed patch.
- Run relevant tests and static checks.
- Compare with a baseline workflow.
- Report correct fixes, regressions, false positives, runtime, compute use, and human review.

Do not generalize these results to medicine, science, or unrestricted discovery without separate domain-specific evaluations.

## Experimental controls

Before running a benchmark, record:
- Task inclusion criteria and dataset version.
- Ground-truth or acceptance rubric.
- Baseline method and configuration.
- Model/provider versions and prompts where applicable.
- Random seeds, environment, dependencies, and resource limits.
- Scoring rules and handling of ambiguous cases.
- Cost and time measurement method.

Keep a held-out set where feasible. Avoid tuning on evaluation cases and then reporting the same cases as independent validation.

## Paired representation comparisons

For representation experiments, use the same named task cases across the baseline and each candidate. Record one value per case and set `CandidateRun.sample_ids` to the corresponding case identifiers. The evaluator rejects candidate/baseline sample-set mismatches and aligns values by ID rather than trusting list order.

Report average primary-metric change together with per-case paired improvement dispersion. Include cases where the candidate regresses. This is a more informative view than comparing averages alone, but it does not establish statistical significance or generalization. A formal statistical test and independent held-out task set remain separate evaluation requirements.

## Core metrics

| Metric | Meaning |
|---|---|
| Task pass rate | Fraction of tasks meeting predeclared acceptance criteria |
| Defect detection recall | Fraction of known relevant defects detected |
| False-positive rate | Fraction of clean cases incorrectly flagged |
| Regression rate | Fraction of proposed fixes introducing new failures |
| Reproducibility | Fraction of repeated runs yielding equivalent validated outcomes |
| Time per accepted result | End-to-end time, including failed attempts and review |
| Cost per accepted result | Model, compute, infrastructure, and review cost where measurable |
| Traceability completeness | Fraction of conclusions linked to inputs, versions, commands, and supporting results |

Choose the primary metric before running the experiment. Report sample size and uncertainty, not just a percentage.

## Minimum experiment

1. Select a small but representative task set with known outcomes.
2. Run a simple baseline, such as a single-model proposal followed by the existing test suite.
3. Run the ThalosPrime workflow on the same cases under controlled conditions.
4. Have outcomes scored against the same rubric.
5. Record all failures and human interventions.
6. Repeat enough cases/runs to assess variability.
7. Publish raw result records and a summary with limitations.

## Decision rule

Adopt a more complex component only if it provides a measurable benefit, a necessary capability, or a documented risk reduction that justifies its cost and maintenance burden. If it fails to outperform the baseline, narrow its role, revise it, or defer it.

## Report template

- Commit:
- Dataset/task set:
- Date/environment:
- Baseline:
- ThalosPrime configuration:
- Primary metric:
- Sample size:
- Baseline result:
- ThalosPrime result:
- Difference and uncertainty:
- Compute/time/cost:
- False positives / missed defects:
- Regressions:
- Reproducibility:
- Failures and exclusions:
- Conclusion supported by this test:
- Claims this test does not support:
