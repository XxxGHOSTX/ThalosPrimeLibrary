# Automation Infrastructure Quick Reference

## Quick Start

```bash
# 1. Install development dependencies
make install

# 2. Install pre-commit hooks
make pre-commit-install

# 3. Run all checks before committing
make check
```

## Daily Development Workflow

### Before Starting Work
```bash
git checkout -b feature/your-feature-name
make check  # Ensure clean state
```

### During Development
```bash
# Edit code...

# Run relevant checks
make typecheck  # Check types
make lint       # Check code style
make test       # Run tests
make validate   # Run custom validators
```

### Before Committing
```bash
make check  # Run all checks

git add .
git commit -m "Your descriptive message"
# Pre-commit hooks run automatically
```

### Before Pushing
```bash
make check  # Final verification
git push origin feature/your-feature-name
```

## Available Commands

### Makefile Targets
```bash
make help              # Show all available targets
make install           # Install dev dependencies
make typecheck         # Run mypy + pyright
make lint              # Run ruff linter
make test              # Run pytest with coverage
make validate          # Run all custom validators
make check             # Run ALL checks
make pre-commit-install # Install hooks
make clean             # Remove build artifacts
```

### Direct Tool Usage
```bash
# Type checking
mypy thalos_prime tests --strict
pyright thalos_prime tests

# Linting
ruff check thalos_prime tests --select ALL --ignore COM812,ISC001,ANN101,ANN102,D203,D213

# Testing
pytest tests -v --cov=thalos_prime --cov-report=term-missing --cov-fail-under=80

# Custom validators
python tools/validate_lifecycle.py
python tools/validate_determinism.py
python tools/validate_state.py
python tools/validate_docs.py
python tools/detect_prohibited_patterns.py

# Security checks
bandit -r thalos_prime
pip-audit --desc
```

## CI/CD Pipeline

The CI pipeline runs automatically on:
- Every push to main
- Every pull request

### CI Checks
1. ✅ Type checking (mypy, pyright)
2. ✅ Linting (ruff)
3. ✅ Testing (pytest with 80% coverage)
4. ✅ Lifecycle validation
5. ✅ Determinism validation
6. ✅ State validation
7. ✅ Documentation validation
8. ✅ Prohibited patterns detection
9. ✅ Security scanning (bandit)
10. ✅ Dependency vulnerabilities (pip-audit)

**All checks must pass to merge.**

## Pre-commit Hooks

Hooks run automatically on every commit:
- Trailing whitespace removal
- End-of-file fixer
- YAML/TOML validation
- Large file detection
- Merge conflict detection
- Debug statement detection
- Ruff formatting and linting
- Mypy type checking
- Secret detection
- Bandit security scanning
- Custom validators

## Troubleshooting

### Type Check Failures
```bash
# Run mypy with verbose output
mypy thalos_prime tests --strict --show-error-codes

# Run pyright with verbose output
pyright thalos_prime tests --verbose
```

### Lint Failures
```bash
# Auto-fix what's possible
ruff check thalos_prime tests --fix

# Show all issues
ruff check thalos_prime tests --select ALL
```

### Test Failures
```bash
# Run with verbose output
pytest tests -v -s

# Run specific test
pytest tests/test_file.py::test_function -v

# Run with coverage
pytest tests --cov=thalos_prime --cov-report=html
open htmlcov/index.html
```

### Validation Failures
```bash
# Run each validator individually
python tools/validate_lifecycle.py
python tools/validate_determinism.py
python tools/validate_state.py
python tools/validate_docs.py
python tools/detect_prohibited_patterns.py
```

### Pre-commit Hook Issues
```bash
# Update hooks
pre-commit autoupdate

# Run manually on all files
pre-commit run --all-files

# Skip hooks (emergency only)
git commit --no-verify -m "Emergency commit"
```

## Code Quality Standards

### Required for All Code
- ✅ Type annotations on all functions/methods
- ✅ Docstrings on all public classes/functions
- ✅ No catch-all exceptions without re-raise
- ✅ No TODOs, FIXMEs, stubs, or mocks
- ✅ Deterministic operations (seed randomness)
- ✅ 80% test coverage minimum

### Lifecycle Methods Required
For any subsystem class (Manager, Controller, Service, Handler):
- `initialize()` - Setup resources
- `validate()` - Check invariants
- `operate()` - Execute work
- `reconcile()` - Converge to consistent state
- `checkpoint()` - Serialize state
- `terminate()` - Cleanup resources

All methods must have explicit return type annotations.

## Getting Help

1. Check [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines
2. Check [VALIDATION_STATUS.md](VALIDATION_STATUS.md) for known issues
3. Check [.github/copilot-instructions.md](.github/copilot-instructions.md) for requirements
4. Run `make help` for available commands
5. Open an issue for questions

## Performance Tips

```bash
# Run only changed files with pre-commit
pre-commit run

# Run tests in parallel (if pytest-xdist installed)
pytest tests -n auto

# Run only fast tests during development
pytest tests -m "not slow"

# Skip slow validators during rapid iteration
# (Run full 'make check' before committing)
make typecheck lint test
```

## Important Notes

⚠️ **Never skip checks in CI** - All checks must pass for merge

⚠️ **Pre-commit hooks are mandatory** - Install with `make pre-commit-install`

⚠️ **Type hints are required** - Use Python 3.12+ type annotations

⚠️ **Coverage requirement is 80%** - Write tests for all new code

✅ **Use `make check` frequently** - Catch issues early

✅ **Read error messages carefully** - They contain actionable guidance

✅ **Keep commits focused** - Small, incremental changes are easier to review
