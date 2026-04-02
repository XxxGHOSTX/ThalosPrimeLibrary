.PHONY: help install typecheck lint test validate check pre-commit-install clean \
        launch serve setup-windows setup-unix

# Detect OS for cross-platform targets
UNAME := $(shell uname -s 2>/dev/null || echo Windows)

help:
	@echo "ThalosPrimeLibrary - Development Makefile"
	@echo ""
	@echo "Quick start (all OS):"
	@echo "  make launch            - Setup + start API server (cross-platform)"
	@echo "  make serve             - Start API server only (deps already installed)"
	@echo ""
	@echo "Setup scripts:"
	@echo "  make setup-windows     - Run .\setup.ps1 (Windows PowerShell)"
	@echo "  make setup-unix        - Run bash setup.sh (Linux/macOS)"
	@echo ""
	@echo "Development targets:"
	@echo "  make install           - Install development dependencies"
	@echo "  make typecheck         - Run mypy and pyright type checkers"
	@echo "  make lint              - Run ruff linter"
	@echo "  make test              - Run pytest with coverage"
	@echo "  make validate          - Run all custom validators"
	@echo "  make check             - Run all checks (typecheck + lint + test + validate)"
	@echo "  make clean             - Remove build artifacts and cache"
	@echo "  make pre-commit-install- Install pre-commit hooks"

install:
	pip install -e ".[dev]"

typecheck:
	@echo "Running mypy..."
	mypy thalos_prime tests --strict --show-error-codes --no-implicit-optional
	@echo "Running pyright..."
	pyright thalos_prime tests

lint:
	@echo "Running ruff..."
	ruff check thalos_prime tests --select ALL --ignore COM812,ISC001,ANN101,ANN102,D203,D213

test:
	@echo "Running pytest with coverage..."
	pytest tests -v --cov=thalos_prime --cov-report=term-missing --cov-fail-under=80

validate:
	@echo "Running lifecycle validator..."
	python tools/validate_lifecycle.py
	@echo "Running determinism validator..."
	python tools/validate_determinism.py
	@echo "Running state validator..."
	python tools/validate_state.py
	@echo "Running documentation validator..."
	python tools/validate_docs.py
	@echo "Running prohibited patterns detector..."
	python tools/detect_prohibited_patterns.py

check: typecheck lint test validate
	@echo "✅ All checks passed!"

# ─── Cross-platform launch targets ──────────────────────────────────────────

launch:
	python launch.py

serve:
	python -m thalos_prime

setup-windows:
	powershell.exe -ExecutionPolicy RemoteSigned -File setup.ps1

setup-unix:
	bash setup.sh

pre-commit-install:
	pre-commit install

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf .coverage
	rm -rf htmlcov/
