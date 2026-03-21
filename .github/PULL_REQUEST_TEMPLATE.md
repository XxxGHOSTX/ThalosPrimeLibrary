## Intent

<!-- What problem does this PR solve? What is the motivation? -->

## Changes

<!-- Summarize the changes made in this PR. -->

## Constraints

<!-- What invariants must hold after this change? -->

## Deterministic Guarantees

<!-- What replay/checkpoint guarantees exist? How is determinism preserved? -->

## State Surfaces

<!-- What state is exposed or modified, and how? -->

## Logging

<!-- What events are logged by the new or changed code? -->

## Tests

<!-- What tests were added or updated? -->

- [ ] New tests added for changed behavior
- [ ] Existing tests pass (`make test`)
- [ ] Coverage meets the 80% minimum threshold

## CI Checklist

- [ ] Type checks pass (`make typecheck`)
- [ ] Linting passes (`make lint`)
- [ ] Tests pass with coverage (`make test`)
- [ ] Custom validators pass (`make validate`)
- [ ] Security checks pass (`bandit`, `pip-audit`)
- [ ] No TODOs, stubs, mocks, or placeholders in production code
- [ ] All new public functions/classes have type annotations and docstrings
