<!-- PROPRIETARY AND CONFIDENTIAL -->
<!-- Copyright © 2026 Tony Ray Macier III. All Rights Reserved. -->

# Experiment: [NAME]

⚠️ **UNSTABLE — EXPERIMENTAL MODULE**

## Hypothesis
<!-- What do you expect to prove? -->

## Isolation Principles
- This module is isolated from `core/` and `system/`.
- It **must not** be imported by any stable module.
- All I/O goes to `STATELOG/experiments/` not the main STATELOG.

## Promotion Criteria
- [ ] Stable for 30 days with no breaking changes
- [ ] Test coverage ≥ 90%
- [ ] No dependencies on other experimental modules
- [ ] Performance benchmarked
- [ ] Reviewed and approved by owner

## Risk Evaluation
<!-- What could go wrong? What is the blast radius of a failure? -->
