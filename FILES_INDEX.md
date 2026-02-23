# Thalos Prime Library — Files Index

Complete index of files in the ThalosPrimeLibrary repository.

## Root Files

| File | Purpose |
|------|---------|
| `thalos_prime.py` | Pipeline entrypoint — `ControlPlane`, `DeterministicHalt`, CLI |
| `pyproject.toml` | Package metadata, dependencies, linting, and type-check config |
| `requirements.txt` | Runtime dependency pins |
| `setup.py` | Legacy setuptools compatibility shim |
| `conftest.py` | Pytest configuration and shared fixtures |
| `pytest.ini` | Pytest settings (rootdir, coverage options) |
| `Makefile` | Development workflow commands (lint, type, test) |
| `README.md` | Project overview, philosophy, quick-start |
| `ARCHITECTURE.md` | System architecture and design |
| `DELIVERY_SUMMARY.txt` | Delivered component summary |
| `START_HERE.txt` | Quickstart guide |
| `IMPLEMENTATION_COMPLETE.md` | Implementation completeness record |
| `VERIFICATION_REPORT.md` | Test and verification results |
| `PHASE1_PHASE2_GUIDE.md` | Phase 1 and Phase 2 implementation guide |
| `DEPLOYMENT.md` | Deployment guide (Python, Docker, cloud) |
| `QUICK_DEPLOY.md` | Quick deployment reference card |
| `DEPLOYMENT_ARCHITECTURE.md` | Visual ASCII deployment architecture |
| `INSTALLATION_GUIDE.md` | Installation instructions |
| `CONTRIBUTING.md` | Contribution guidelines |
| `LICENSE` | License terms |
| `Dockerfile` | Container build instructions |
| `docker-compose.yml` | Docker Compose production configuration |
| `deploy.sh` | Interactive deployment script |
| `run_thalos.py` | API server launcher |
| `run_thalos.sh` | Shell-based API server launcher |
| `example_usage.py` | Usage examples for the core library |
| `integration_example.py` | Integration usage examples |
| `verify_system.py` | System verification script |

## thalos_prime/ — Core Library Package

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports (`address_to_page`, `enumerate_addresses`, `score_coherence`, etc.) |
| `lob_babel_generator.py` | Deterministic page generation from hex addresses |
| `lob_babel_enumerator.py` | Query-to-address enumeration with BM25 scoring |
| `lob_decoder.py` | Multi-metric coherence scoring (language, structure, n-gram, exact-match) |
| `ingest.py` | Deterministic canonicalization and semantic hashing |
| `config.py` | Configuration management (`THALOS_LIBRARY_PATH`) |
| `synthesis.py` | Deep synthesis / Nexus scaffold |
| `lifecycle.py` | Lifecycle base classes and interfaces |

### thalos_prime/api/

| File | Purpose |
|------|---------|
| `server.py` | FastAPI application — lifespan, middleware, route registration |
| `config.py` | API server configuration |
| `routes/main.py` | Root and status endpoints |
| `routes/generate.py` | `POST /api/v1/generate` — page generation |
| `routes/enumerate.py` | `POST /api/v1/enumerate` — address enumeration |
| `routes/decode.py` | `POST /api/v1/decode` — coherence scoring |
| `routes/search.py` | `POST /api/v1/search` — hybrid search |
| `routes/chat.py` | `POST /api/v1/chat` — interactive chat |
| `routes/admin.py` | Admin monitoring endpoints (status, metrics, shutdown) |

### thalos_prime/models/

| File | Purpose |
|------|---------|
| `api_models.py` | Pydantic request/response models for the API |
| `db_models.py` | SQLAlchemy ORM models |

### thalos_prime/graph_rag/

Knowledge graph RAG pipeline.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `KnowledgeGraph`, `GraphIngestionPipeline`, `GraphRetriever`, `GraphRAGControlPlane` |
| `interfaces.py` | Protocol definitions |
| `simple_graph.py` | `SimpleKnowledgeGraph` implementation |
| `retriever.py` | `HybridRetriever` implementation |

### thalos_prime/reasoning/

Tree-of-Thoughts and Chain-of-Verification reasoning.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `TreeOfThoughts`, `ChainOfVerification`, `ThoughtScorer`, `ReasoningControlPlane` |

### thalos_prime/agency/

Active inference engine and world model.

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `WorldModel`, `ActiveInferenceEngine`, `AgencyControlPlane` |

### thalos_prime/library_of_sense/

Symbolic reasoning, knowledge fusion, and code generation.

| File | Purpose |
|------|---------|
| `reasoning/symbolic_engine.py` | Symbolic reasoning using sympy |
| `reasoning/constraint_solver.py` | Constraint solving using z3 |
| `reasoning/proof_checker.py` | Proof verification |
| `synthesis/knowledge_fusion.py` | Knowledge fusion |
| `synthesis/conflict_resolution.py` | Conflict resolution |
| `synthesis/answer_generator.py` | Answer generation |
| `synthesis/verification.py` | Answer verification |
| `code_generation/generator.py` | Code generation |
| `code_generation/executor.py` | Code execution |
| `code_generation/validator.py` | Code validation |
| `api/query_handler.py` | Query handling |
| `api/response_builder.py` | Response construction |

### thalos_prime/auth/

Authentication package. No runtime implementation required for current
operational scope (the system operates as a deterministic Library of Babel
pipeline without authentication).

### thalos_prime/cli/

CLI command modules package. No runtime implementation required for current
operational scope; CLI delegation is handled by `src/thalosprime/cli.py`.

### thalos_prime/cache/

Caching package. No runtime implementation required for current operational
scope; in-process dict caching is used in the API routes directly.

### thalos_prime/workers/

Worker subsystem package. No runtime implementation required for current
operational scope.

## src/ — Legacy Source Directory

| File | Purpose |
|------|---------|
| `lob_decoder.py` | Lightweight coherence scoring (used by legacy `src/` modules) |
| `lob_babel_generator.py` | Page generation (legacy src/ variant) |
| `lob_babel_enumerator.py` | Address enumeration (legacy src/ variant) |
| `lob_babel_search.py` | Search utilities |
| `babel_search_expansion.py` | Search expansion |
| `semantic_parser.py` | Semantic parsing |
| `constraint_navigator.py` | Constraint navigation |
| `peptide_space.py` | Peptide space traversal |
| `main.py` | Legacy main entrypoint |
| `thalosprime/cli.py` | CLI entrypoint (delegates to `thalos_prime.main()`) |

## tests/

| File | Purpose |
|------|---------|
| `test_lob_decoder.py` | Tests for `src/lob_decoder.py` |
| `test_decoder.py` | Tests for `thalos_prime/lob_decoder.py` |
| `test_generator.py` | Tests for `thalos_prime/lob_babel_generator.py` |
| `test_enumerator.py` | Tests for `thalos_prime/lob_babel_enumerator.py` |
| `test_lob_babel_generator.py` | Additional generator tests |
| `test_lob_babel_enumerator.py` | Additional enumerator tests |
| `test_lob_babel_search.py` | Tests for `src/lob_babel_search.py` |
| `test_ingest.py` | Tests for `thalos_prime/ingest.py` |
| `test_thalos_prime_pipeline.py` | Full pipeline and ControlPlane tests |
| `test_config.py` | Configuration tests |
| `test_package.py` | Package-level exports and metadata tests |
| `test_schemas.py` | JSON schema sanity tests |
| `test_validators.py` | Lifecycle, determinism, and doc validators |
| `test_integration.py` | Integration tests |
| `test_main.py` | `src/main.py` tests |
| `test_api_chat.py` | Chat API tests |
| `test_api_search.py` | Search API tests |
| `test_babel_endpoints.py` | Babel endpoint tests |
| `test_execution_graph.py` | Execution graph tests |
| `test_semantic_parser.py` | Semantic parser tests |
| `test_constraint_navigator.py` | Constraint navigator tests |
| `test_peptide_space.py` | Peptide space tests |
| `test_lob_shard_manager.py` | Shard manager tests |

## schemas/

| File | Purpose |
|------|---------|
| `hdr.schema.json` | JSON Schema for Human Direction Record (HDR) governance |
| `execution_graph.schema.json` | JSON Schema for ExecutionGraph governance |

## tools/

| File | Purpose |
|------|---------|
| `validate_lifecycle.py` | Validates lifecycle method completeness |
| `validate_determinism.py` | Detects non-deterministic operations |
| `detect_prohibited_patterns.py` | Detects TODOs, catch-all exceptions, etc. |
| `validate_docs.py` | Validates module and function docstrings |
| `validate_state.py` | Validates state serialization |

## Infrastructure

| File | Purpose |
|------|---------|
| `infra/` | Infrastructure-as-code configuration |
| `.github/workflows/` | CI/CD workflows (enforce-standards.yml) |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `.coveragerc` | Coverage measurement configuration |
| `.env.example` | Environment variable template |
