.PHONY: help install build-index serve test lint typecheck clean

help:
	@echo "Thalos Prime - Available Commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make build-index  - Build TF-IDF index from corpus"
	@echo "  make serve        - Start the server"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linter"
	@echo "  make typecheck    - Run type checker"
	@echo "  make clean        - Clean generated files"

install:
	pip install -r requirements.txt
	pip install -e ".[dev]"

build-index:
	python scripts/build_index.py

serve:
	python scripts/serve.py

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/ scripts/ configs/

typecheck:
	mypy src/ tests/ scripts/ configs/

clean:
	rm -rf data/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
