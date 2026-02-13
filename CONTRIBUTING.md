# Contributing to Thalos Prime Library

Thank you for your interest in contributing to Thalos Prime Library! This document outlines the development workflow, requirements, and enforcement criteria.

## Table of Contents

- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [PR Requirements](#pr-requirements)
- [CI/CD Enforcement](#cicd-enforcement)
- [How to Resolve CI Failures](#how-to-resolve-ci-failures)

## Development Setup

### Prerequisites

- Python 3.12 or higher
- pip package manager
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/XxxGHOSTX/ThalosPrimeLibrary.git
   cd ThalosPrimeLibrary
   ```

2. Install development dependencies:
   ```bash
   make install
   # or manually:
   pip install -e ".[dev]"
   ```

3. Install pre-commit hooks:
   ```bash
   make pre-commit-install
   # or manually:
   pre-commit install
   ```

## Development Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards below.

3. **Run local checks** before committing:
   ```bash
   make check
   ```
   This runs:
   - Type checking (mypy, pyright)
   - Linting (ruff)
   - Tests with coverage (pytest)
   - Custom validators

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "Your descriptive commit message"
   ```
   Pre-commit hooks will run automatically.

5. **Push your changes:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub.

## Coding Standards

All code must adhere to the strict standards defined in `.github/copilot-instructions.md`:

### Determinism
- Identical inputs must produce identical outputs
- All randomness must be seeded deterministically and logged
- No non-deterministic operations without explicit logging

### Type Safety
- All code must pass `mypy --strict` and `pyright` type checks
- All functions, methods, and variables must have type annotations
- No `Any` type unless explicitly bounded by protocol

### Error Handling
- No catch-all exception handlers without re-raise
- All exception types must be explicit and typed
- Log all exceptions with full context

### Lifecycle Methods
Each subsystem must implement:
- `initialize()`: Set up resources and initial state
- `validate()`: Check all invariants and preconditions
- `operate()`: Execute primary work
- `reconcile()`: Converge to consistent state
- `checkpoint()`: Serialize state for restart
- `terminate()`: Clean up resources

### Prohibited Patterns
The following are **prohibited** in production code:
- TODOs, FIXMEs, stubs, mocks, or placeholders
- Catch-all exception suppression
- Silent retries without logging
- Untyped `Any` without protocol bounds
- Hidden state or implicit globals
- Unused parameters, variables, or dead code

## Testing Requirements

### Coverage Requirements
- Minimum 80% line coverage overall
- 100% coverage for critical lifecycle paths
- All tests must be deterministic (seed any randomness)

### Running Tests
```bash
# Run all tests with coverage
make test

# Run specific test file
pytest tests/test_specific.py -v

# Run with coverage report
pytest tests -v --cov=thalos_prime --cov-report=html
```

### Writing Tests
- Use descriptive test names: `test_function_name_scenario_expected_result`
- Seed all random operations
- Test both success and failure paths
- Ensure tests are isolated and can run in parallel

## PR Requirements

Your pull request description must include:

1. **Intent**: What problem does this solve?
2. **Constraints**: What invariants must hold?
3. **Deterministic guarantees**: What replay/checkpoint guarantees exist?
4. **State surfaces**: What state is exposed and how?
5. **Logging**: What events are logged?
6. **Tests**: What tests were added or updated?

## CI/CD Enforcement

The CI pipeline runs on every pull request and push to main. It includes:

### Type Checking
- `mypy thalos_prime tests --strict`
- `pyright thalos_prime tests`

### Linting
- `ruff check thalos_prime tests --select ALL`

### Testing
- `pytest tests -v --cov=thalos_prime --cov-fail-under=80`

### Custom Validators
- Lifecycle method validation
- Determinism validation
- State management validation
- Documentation validation
- Prohibited patterns detection

### Security Checks
- `bandit` for security vulnerabilities
- `pip-audit` for dependency vulnerabilities

**All checks must pass** for the PR to be merged.

## How to Resolve CI Failures

### Type Check Failures

If mypy or pyright fails:

1. Check the error message for the specific type issue
2. Add missing type annotations
3. Fix type mismatches
4. Run locally: `make typecheck`

### Lint Failures

If ruff reports issues:

1. Review the specific lint error
2. Fix the code or add appropriate ignore comment with justification
3. Run locally: `make lint`

### Test Failures

If pytest fails:

1. Review the test output
2. Fix the code or update tests
3. Ensure all tests are deterministic
4. Run locally: `make test`

### Validation Failures

If custom validators fail:

1. **Lifecycle validator**: Ensure subsystems implement all lifecycle methods
2. **Determinism validator**: Review warnings about non-deterministic operations
3. **State validator**: Ensure state classes are serializable
4. **Documentation validator**: Add missing docstrings
5. **Prohibited patterns**: Remove TODOs, stubs, and other prohibited patterns

Run validators locally:
```bash
make validate
```

### Security Failures

If bandit or pip-audit reports issues:

1. Review the security vulnerability
2. Fix the code or update dependencies
3. Document why a warning is a false positive if applicable

## Questions?

If you have questions or need help:

1. Check `.github/copilot-instructions.md` for detailed requirements
2. Review existing code for examples
3. Open an issue for discussion

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
