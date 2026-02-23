# Thalos Prime Library — File Index

Complete index of significant files in the Thalos Prime repository.

---

## Entry Points

| Path | Description |
|------|-------------|
| `thalos_prime.py` | ControlPlane entry point — orchestrates full pipeline lifecycle |
| `run_thalos.py` | Server launcher — starts the FastAPI server |
| `run_thalos.sh` | Bash launcher script for Linux/macOS |
| `run_thalos.bat` | Windows launcher script |

---

## Core Package — `thalos_prime/`

| Path | Description |
|------|-------------|
| `thalos_prime/__init__.py` | Package exports: version, LIBRARY_MOTTO, core classes |
| `thalos_prime/config.py` | Configuration management — THALOS_LIBRARY_PATH env var |
| `thalos_prime/lifecycle.py` | LifecycleProtocol, BaseLifecycleComponent, LifecycleEvent |
| `thalos_prime/lob_babel_generator.py` | BabelGenerator — deterministic 3200-char page generation |
| `thalos_prime/lob_babel_enumerator.py` | BabelEnumerator — query-to-address n-gram mapping |
| `thalos_prime/lob_decoder.py` | BabelDecoder — multi-metric coherence scoring |
| `thalos_prime/synthesis.py` | Synthesis pipeline combining enumeration and decoding |
| `thalos_prime/ingest.py` | Deterministic canonicalization and semantic hashing |

---

## Authentication — `thalos_prime/auth/`

| Path | Description |
|------|-------------|
| `thalos_prime/auth/__init__.py` | Exports: APIKeyAuthenticator, DeterministicHalt |
| `thalos_prime/auth/api_key.py` | APIKeyAuthenticator — lifecycle-managed API key auth |

---

## Cache — `thalos_prime/cache/`

| Path | Description |
|------|-------------|
| `thalos_prime/cache/__init__.py` | Exports: TTLCache |
| `thalos_prime/cache/ttl_cache.py` | TTLCache[K, V] — generic in-memory TTL cache |

---

## Database — `thalos_prime/database/`

| Path | Description |
|------|-------------|
| `thalos_prime/database/__init__.py` | Exports: ResultStore |
| `thalos_prime/database/store.py` | ResultStore — SQLite persistence (search results + sessions) |
| `thalos_prime/database/connection.py` | DatabaseManager — SQLAlchemy connection pool (optional ORM) |

---

## Workers — `thalos_prime/workers/`

| Path | Description |
|------|-------------|
| `thalos_prime/workers/__init__.py` | Exports: BatchProcessor |
| `thalos_prime/workers/batch_processor.py` | BatchProcessor — deterministic batch page processing |

---

## CLI — `thalos_prime/cli/`

| Path | Description |
|------|-------------|
| `thalos_prime/cli/__init__.py` | Exports: run_cli, build_parser |
| `thalos_prime/cli/commands.py` | CLI subcommands: generate, enumerate, decode, search, serve |

---

## API Server — `thalos_prime/api/`

| Path | Description |
|------|-------------|
| `thalos_prime/api/server.py` | FastAPI application factory and route registration |
| `thalos_prime/api/config.py` | API configuration (host, port, cache TTL, etc.) |
| `thalos_prime/api/routes/main.py` | Root and health check routes |
| `thalos_prime/api/routes/chat.py` | /api/v1/chat — interactive conversation endpoint |
| `thalos_prime/api/routes/search.py` | /api/v1/search — full pipeline search endpoint |
| `thalos_prime/api/routes/generate.py` | /api/v1/generate — page generation endpoint |
| `thalos_prime/api/routes/enumerate.py` | /api/v1/enumerate — address enumeration endpoint |
| `thalos_prime/api/routes/decode.py` | /api/v1/decode — coherence scoring endpoint |
| `thalos_prime/api/routes/admin.py` | /api/v1/admin — system status, metrics, shutdown |

---

## Models — `thalos_prime/models/`

| Path | Description |
|------|-------------|
| `thalos_prime/models/api_models.py` | Pydantic request/response schemas for the API |
| `thalos_prime/models/db_models.py` | SQLAlchemy ORM models (optional) |

---

## Library of Sense — `thalos_prime/library_of_sense/`

| Path | Description |
|------|-------------|
| `thalos_prime/library_of_sense/core/interfaces.py` | Core protocols: ValidationResult, QueryContext, etc. |
| `thalos_prime/library_of_sense/core/orchestrator.py` | Multi-source query orchestration |
| `thalos_prime/library_of_sense/core/state_manager.py` | Shared state management across retrievers |
| `thalos_prime/library_of_sense/reasoning/symbolic_engine.py` | Symbolic math reasoning (sympy) |
| `thalos_prime/library_of_sense/reasoning/constraint_solver.py` | Constraint solving (z3) |
| `thalos_prime/library_of_sense/retrieval/knowledge_graph.py` | Knowledge graph retrieval (networkx) |
| `thalos_prime/library_of_sense/retrieval/web_retrieval.py` | Web content retrieval (requests) |
| `thalos_prime/library_of_sense/retrieval/code_search.py` | Code search and analysis |
| `thalos_prime/library_of_sense/code_generation/generator.py` | Code generation module |

---

## Simulation — `thalos_prime/simulation/`

| Path | Description |
|------|-------------|
| `thalos_prime/simulation/world_model.py` | WorldModel — deterministic world-state predictor |

---

## Legacy Source — `src/`

| Path | Description |
|------|-------------|
| `src/lob_babel_generator.py` | Legacy generator (delegates to thalos_prime) |
| `src/lob_babel_enumerator.py` | Legacy enumerator (delegates to thalos_prime) |
| `src/lob_decoder.py` | Legacy decoder (delegates to thalos_prime) |
| `src/thalosprime/cli.py` | Legacy CLI entry point — delegates to thalos_prime.cli |

---

## Tests — `tests/`

| Path | Description |
|------|-------------|
| `tests/test_generator.py` | BabelGenerator unit tests |
| `tests/test_enumerator.py` | BabelEnumerator unit tests |
| `tests/test_decoder.py` | BabelDecoder unit tests |
| `tests/test_lob_babel_generator.py` | Extended generator tests |
| `tests/test_lob_babel_enumerator.py` | Extended enumerator tests |
| `tests/test_lob_decoder.py` | Extended decoder tests |
| `tests/test_integration.py` | Full pipeline integration tests |
| `tests/test_thalos_prime_pipeline.py` | Pipeline end-to-end tests |
| `tests/test_auth.py` | APIKeyAuthenticator tests |
| `tests/test_cache.py` | TTLCache tests |
| `tests/test_database.py` | ResultStore tests |
| `tests/test_workers.py` | BatchProcessor tests |
| `tests/test_cli_commands.py` | CLI command parsing and dispatch tests |
| `tests/test_config.py` | Configuration management tests |
| `tests/test_package.py` | Package exports and LIBRARY_MOTTO tests |
| `tests/test_ingest.py` | Ingest canonicalization tests |
| `tests/test_schemas.py` | JSON schema validation tests |

---

## Configuration and Tooling

| Path | Description |
|------|-------------|
| `pyproject.toml` | Build config, dependencies, mypy/ruff/pyright/pytest settings |
| `Makefile` | Development commands: test, lint, type-check, build |
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Multi-service deployment configuration |
| `.coveragerc` | Coverage measurement configuration |
| `conftest.py` | pytest fixtures and configuration |
| `tools/validate_lifecycle.py` | CI: validates all subsystem lifecycle methods |
| `tools/validate_determinism.py` | CI: validates deterministic seeding and logging |
| `tools/validate_state.py` | CI: validates state management patterns |
| `tools/validate_docs.py` | CI: validates docstrings and documentation |
| `tools/detect_prohibited_patterns.py` | CI: detects TODO/FIXME/STUB/MOCK/PLACEHOLDER |

---

## Documentation

| Path | Description |
|------|-------------|
| `README.md` | Project overview, installation, and quick start |
| `ARCHITECTURE.md` | System architecture, control/data plane boundaries |
| `IMPLEMENTATION_COMPLETE.md` | Implementation completeness status |
| `VERIFICATION_REPORT.md` | Test results and verification status |
| `PHASE1_PHASE2_GUIDE.md` | Phase 1 and Phase 2 implementation guide |
| `DEPLOYMENT.md` | Deployment options and configuration |
| `CONTRIBUTING.md` | Contribution guidelines |
| `DELIVERY_SUMMARY.txt` | High-level delivery summary |
| `FILES_INDEX.md` | This file — complete repository file index |
| `START_HERE.txt` | Quickstart guide for new users |
| `schemas/hdr.schema.json` | JSON Schema for Human Direction Record governance |
| `schemas/execution_graph.schema.json` | JSON Schema for ExecutionGraph governance |
