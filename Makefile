.PHONY: help install typecheck lint test validate check pre-commit-install clean

help:
	@echo "Thalos Prime Library - Development Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install            - Install development dependencies"
	@echo "  typecheck          - Run mypy and pyright type checkers"
	@echo "  lint               - Run ruff linter"
	@echo "  test               - Run pytest with coverage"
	@echo "  validate           - Run all custom validators"
	@echo "  check              - Run all checks (typecheck + lint + test + validate)"
	@echo "  pre-commit-install - Install pre-commit hooks"
	@echo "  clean              - Remove build artifacts and cache"

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
	@echo "All checks passed!"

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
