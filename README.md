# ThalosPrimeLibrary

**From proposed solution to evidence that it works.**

ThalosPrimeLibrary is the canonical integration target for Thalos Prime, an AI research and engineering project intended to improve how complex problems are investigated, solutions are generated, and proposed implementations are tested.

The intended workflow coordinates evidence gathering, competing candidate solutions, contradiction and implementation-error checks, executable validation, baseline comparison, and traceable reporting. The product is being developed around measurable results, not claims that it can solve every problem or exceed current scientific, mathematical, computational, or physical limits.

The repository currently contains Library of Babel tooling, symbolic reasoning and planning components, retrieval-related code, infrastructure synthesis, and an API/UI. Those components are starting points, not proof that the full research workflow has been integrated or validated end to end.

## Brief Repo Description

This repository is the canonical integration core. Related Thalos Prime repositories are treated as sources of candidate components. Code is adopted only after its implementation, dependencies, licensing, security boundaries, and tests are reviewed. Repository descriptions and planned capabilities are not accepted as validation evidence by themselves.

**Integration documents**
- [Unified architecture](docs/UNIFIED_THALOS_PRIME_ARCHITECTURE.md)
- [Integration registry](docs/INTEGRATION_REGISTRY.md)
- [Validation and benchmark plan](docs/VALIDATION_AND_BENCHMARK_PLAN.md)
- [Lender brief](docs/funding/THALOSPRIME_LENDER_BRIEF.md)
- [Investor brief](docs/funding/THALOSPRIME_INVESTOR_BRIEF.md)

> **Verification status:** The completion and verification reports dated February 2026 describe earlier repository snapshots. They are not evidence that the current unified workflow passes its tests or is production-ready. The current integration branch requires fresh automated tests, type checks, lint, security scans, and task benchmarks before readiness claims can be made.

## ZIP Setup Walkthrough (Deploy After Downloading ZIP)

1. Download and extract the ZIP.
2. Open a terminal in the extracted `ThalosPrimeLibrary` folder.
3. Install dependencies:
   `pip install -e ".[dev]"` (or `pip install .` for production-only install).
4. Start the API/UI locally:
   `python run_thalos.py`
5. Open `http://localhost:8000` (UI) or `http://localhost:8000/docs` (API docs).

## Ownership & Rights Notice

Tony Ray Macier III (aka XxxGHOSTX) is the owner of the original works he created in this
repository and retains associated legal rights to that original authored content.

---

## Table of Contents

1. [What Is ThalosPrimeLibrary?](#what-is-thalosprimelibrary)
2. [Key Capabilities](#key-capabilities)
3. [How It Works](#how-it-works)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Using the Python API](#using-the-python-api)
7. [Deterministic Pipeline CLI](#deterministic-pipeline-cli)
8. [REST API Server](#rest-api-server)
9. [Infrastructure Synthesis CLI](#infrastructure-synthesis-cli)
10. [Configuration](#configuration)
11. [Architecture](#architecture)
12. [Development](#development)
13. [Testing](#testing)
14. [Deployment](#deployment)
15. [Documentation](#documentation)
16. [License](#license)

---

## What Is ThalosPrimeLibrary?

ThalosPrimeLibrary currently contains multiple software subsystems that can support the intended evidence-oriented workflow, including:

- **Library of Babel integration** — deterministic generation and coherence-scored retrieval of
  pages from [libraryofbabel.info](https://libraryofbabel.info).
- **Hybrid cognitive synthesis** — multi-view semantic decomposition across Physical/Chemical,
  Logical/Mathematical, and Linguistic/Narrative knowledge planes.
- **Symbolic reasoning** — Z3-based constraint solving, proof checking, and planning.
- **Autonomous agency** — perceive-plan-act loops with belief tracking and multi-path planning.
- **Knowledge graphs** — Neo4j-compatible graph with hybrid graph+text retrieval (Graph-RAG).
- **Infrastructure synthesis** — YAML-driven, multi-provider artifact generation (Terraform,
  OpenTofu, Cloudflare, GitHub Actions, Docker) with policy enforcement and drift detection.
- **REST API & interactive UI** — FastAPI server with a Matrix-style browser interface.

Some subsystems use a shared lifecycle convention (`initialize → validate → operate → reconcile → checkpoint → terminate`). Determinism and replayability must be demonstrated for the specific execution path, inputs, dependencies, and environment being claimed; do not assume every subsystem or external interaction is deterministic.

---

## Key Capabilities

| Capability | Description |
|---|---|
| **Library of Babel page generation** | SHA-256-based page generation and address mapping for the existing Babel subsystem |
| **Query enumeration** | Map natural-language queries to candidate Babel addresses via n-gram extraction |
| **Coherence scoring** | Four-metric scoring (language, structure, n-gram, exact match) on a 0–100 scale |
| **Deep synthesis** | Multi-view semantic decomposition with Physical/Chemical, Logical/Mathematical, Linguistic/Narrative nexus results |
| **Symbolic reasoning** | Z3 SMT constraint solving, incremental updates, optimization objectives |
| **Multi-representation experiment planning** | Declarative DAG that prepares graph, constraint, and state-transition branches for baseline comparison |\n| **Permission-gated workflow runtime** | Invokes only explicitly registered handlers, checks signed directive allowlists and approval gates, records stage results, and bounds input/output data |
| **Baseline candidate evaluation** | Compare recorded metric samples, test status, cost, runtime, and evidence against a declared baseline; align per-case improvements when sample IDs are supplied |
| **Signed human directives** | RSA-PSS/SHA-256 signatures and explicit allowlists; unsigned directives cannot authorize an operation |
| **Read-only project inventory** | Bounded file hashing, manifest/test inventory, duplicate-file grouping, and static Python import graph |
| **Evidence artifacts** | Convert experiment reports and project inventories to PENDING canonical artifacts for downstream validation |
| **Planning** | Tree of Thoughts / MCTS planning components where implemented; test each execution path before claiming deterministic behavior |
| **Graph-RAG** | Hybrid knowledge graph retrieval combining BFS graph traversal and text search |
| **Infrastructure synthesis** | YAML-schema → Terraform/OpenTofu/Cloudflare/GitHub Actions/Docker artifacts |
| **Policy enforcement** | `require_ssl`, `limit_scaling`, and extensible policy rules |
| **Release strategies** | `direct`, `blue_green`, `canary` deployment orchestration |
| **Drift detection** | DeepDiff-based schema drift detection and rollback |
| **Scoped reproducibility** | Seeded replay and stable ordering are supported by specified paths; broader guarantees require path-specific tests |

---

## How It Works

### Control Plane / Data Plane Separation

All subsystems enforce strict separation between coordination logic and computational work:

| Layer | Components | Responsibility |
|---|---|---|
| **Control Plane** | `ControlPlane`, lifecycle orchestrators | Lifecycle management, seed control, state logging, deterministic halt |
| **Data Plane** | `BabelClient`, adapters, solvers, planners | Computational work only; no coordination or scheduling logic |

### Six-Method Lifecycle

Every subsystem implements these methods in order:

```
initialize() → validate() → operate() → reconcile() → checkpoint() → terminate()
```

Any invariant violation raises `DeterministicHalt` with a full state snapshot and
JSONL event log. Silent degradation is never permitted.

### Deterministic Execution and Validation

- Explicit seeds can control pseudo-randomness in execution paths that use them.
- Stable ordering and versioned checkpoints should be used where implemented.
- Replay claims must be tested for the specific command, input, configuration, dependency set, and environment.
- Network responses, timestamps, dependency versions, filesystem state, and concurrency can affect results unless controlled.
- Report commands, versions, outputs, and failures; do not extrapolate narrow tests into guarantees about the full product.

### 7-Stage MNN Pipeline

The core data pipeline runs these stages in order:

1. **Normalization** — Canonicalise and hash input text
2. **Constraint Generation** — Derive symbolic constraints from the query
3. **Index Mapping** — Map queries to Babel address candidates
4. **Sequence Generation** — Fetch or generate page content
5. **Analysis & Filtering** — Score and filter pages with coherence metrics
6. **Center-Weighted Scoring** — BM25 + four-metric coherence, stable sort
7. **Output Handling** — Assemble volume, checkpoint state, emit event log

See [docs/thalos_prime_blueprint.md](docs/thalos_prime_blueprint.md) for the full specification.

---

## Installation

**Python 3.12 or later is required.**

### Windows one-click installer (recommended)

For release builds, use the bundled installer artifacts:

- `Setup.exe` (consumer installer)
- `ThalosPrime.msi` (enterprise installer)

Both create Start Menu shortcuts and can create Desktop shortcuts.
See `/docs/WINDOWS_INSTALLER_GUIDE.md` for the full 3-step flow and troubleshooting.

**Windows (PowerShell) — fully automated:**

```powershell
.\setup.ps1        # creates .venv, installs deps, starts server
```

**Unix / macOS — fully automated:**

```bash
bash setup.sh      # creates .venv, installs deps, starts server
```

**Cross-platform (manual):**

```bash
# Development install (includes type checkers, linters, and test tools)
pip install -e ".[dev]"

# Production install
pip install .
```

---

## Quick Start

```python
import thalos_prime as tp

# Generate a Library of Babel page from a hex address
page = tp.address_to_page("0a1b2c3d")
print(page[:80])

# Convert text to its deterministic Babel address
address = tp.text_to_address("hello world")
print(address)

# Enumerate candidate addresses for a query
addresses = tp.query_to_addresses("antimicrobial peptide")
print(addresses[:3])

# Score how coherent a page is for a given query
score = tp.score_coherence(page, "antimicrobial peptide")
print(score.total, score.confidence)

# Multi-view semantic synthesis
result = tp.deep_synthesis("Find antimicrobial peptide in genomic space")
print(result["semantic_decomposition"]["modalities"])   # ["Genomic", "Chemical"]
print(result["nexus_result"][0]["coordinates_hint"]["search_api"])
# https://libraryofbabel.info/search.cgi
```

Run the bundled examples to see more:

```bash
python scripts/example_usage.py       # Basic usage
python scripts/integration_example.py # Full integration demo
```

---

## Using the Python API

### Library of Babel Endpoints

```python
import thalos_prime as tp

# Retrieve canonical URLs (search UI and programmatic API)
endpoints = tp.get_babel_endpoints()
# {
#   "search_ui":  "https://libraryofbabel.info/search.html",
#   "search_api": "https://libraryofbabel.info/search.cgi"
# }
```

The canonical Library of Babel domain is **libraryofbabel.info** (not thelibraryofbabel.com).

### Page Generation & Address Mapping

```python
page    = tp.address_to_page("hex_address_string")   # → 3,200-char page
address = tp.text_to_address("any text")              # → hex address
normed  = tp.normalize_text("Any Text!")              # → lowercase, 29-char charset
```

### Query Enumeration

```python
addresses = tp.enumerate_addresses("search query", depth=2)  # deeper n-gram search
addresses = tp.query_to_addresses("search query")             # default depth
```

### Coherence Scoring

```python
from thalos_prime import decode_page, score_coherence

decoded = decode_page(page_text, "my query")
print(decoded.total_score)      # 0–100
print(decoded.confidence)       # "high" | "medium" | "sparse" | "minimal"
print(decoded.provenance)       # address, query, metrics breakdown

score = score_coherence(page_text, "my query")
print(score.language_score)     # 30% weight — English word density
print(score.structure_score)    # 20% weight — punctuation & sentence patterns
print(score.ngram_score)        # 20% weight — bigram coherence
print(score.exact_match_score)  # 30% weight — query token matching
```

### Fragment Ingestion

```python
from thalos_prime import ingest_fragment, canonicalize_text, compute_meaning_hash

artifact  = ingest_fragment("raw fragment text")
canonical = canonicalize_text("Some Text")
hash_val  = compute_meaning_hash("Some Text")
```

### Import Path Configuration

By default `thalos_prime` adds a local `ThalosPrimeLibraryOfBabel` directory to `sys.path`.
Override the path with an environment variable or the `setup_local_imports()` helper:

```python
from thalos_prime.config import setup_local_imports

setup_local_imports()                                       # uses THALOS_LIBRARY_PATH or default
setup_local_imports(custom_path="/your/custom/babel/path")  # explicit path
```

Set the `THALOS_LIBRARY_PATH` environment variable to avoid hard-coding a path:

```bash
# Linux / macOS
export THALOS_LIBRARY_PATH=/your/path/ThalosPrimeLibraryOfBabel

# Windows
set THALOS_LIBRARY_PATH=C:\Your\Path\ThalosPrimeLibraryOfBabel
```

---

## Deterministic Pipeline CLI

`thalos_prime.py` is a standalone CLI that traverses [libraryofbabel.info](https://libraryofbabel.info),
extracts English-like tokens, scores them with BM25, and assembles a volume of exactly
**1,312,000 characters** (410 pages × 3,200 chars/page).

### Usage

```bash
# Live mode — fetches pages from libraryofbabel.info
python thalos_prime.py \
    --query "test query" \
    --seed 12345 \
    --output ./output.txt \
    --workdir ./thalos_workdir

# Dry-run mode — fully offline, deterministic synthetic corpus
python thalos_prime.py \
    --query "test" \
    --seed 12345 \
    --output ./output.txt \
    --workdir ./thalos_workdir \
    --dry-run \
    --max-pages 10
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--query` | ✅ | Natural-language query string |
| `--seed` | ✅ | Non-negative integer for deterministic replay |
| `--output` | ✅ | Path to write the assembled volume |
| `--workdir` | ✅ | Directory for checkpoints and JSONL event logs |
| `--max-pages` | — | Maximum pages to fetch (default: 410) |
| `--dry-run` | — | Skip network; use synthetic deterministic corpus |

### Invariants

- Output is exactly 1,312,000 characters; deviations raise `DeterministicHalt`.
- Each page is exactly 3,200 characters (space-padded or hard-trimmed).
- `robots.txt` violations and fetch failures halt deterministically.
- Retries: up to 3 bounded attempts with deterministic delay; all failures logged.

### Observability

Each run writes two files to `--workdir`:

| File | Contents |
|------|----------|
| `checkpoint_<timestamp>_seed<N>.json` | JSON state snapshot with blake2b hash |
| `events_<timestamp>_seed<N>.jsonl` | JSONL event log with timestamps, state hashes, event types |

### Run the Pipeline Tests

```bash
pytest tests/test_thalos_prime_pipeline.py -v
```

The offline pipeline test module covers halt semantics, state serialization, BM25 scoring,
volume assembly, traversal determinism, and an end-to-end dry run. Run the current test suite
before using it as evidence of readiness.

---

## REST API Server

ThalosPrimeLibrary ships a FastAPI server with endpoints for search, generation, enumeration,
decoding, chat, and administration.

### Start the Server

**Windows (PowerShell) — recommended for Windows users:**

```powershell
# One-shot: setup + launch API server
.\setup.ps1

# Other actions:
.\setup.ps1 -Action test       # run tests
.\setup.ps1 -Action validate   # run validators
.\setup.ps1 -Action clean      # clean build artifacts
.\setup.ps1 -Action none       # setup only, no server
.\setup.ps1 -Port 9000         # custom port
```

**Unix / macOS:**

```bash
bash setup.sh                          # setup + start server
bash setup.sh --action test            # run tests
bash setup.sh --action clean           # clean artifacts
bash setup.sh --port 9000              # custom port
```

**Cross-platform (any OS with Python 3.12+):**

```bash
python launch.py                       # setup + start server
python launch.py --action test         # run tests
python launch.py --action validate     # run validators
python launch.py --action check        # full quality check
python launch.py --action clean        # clean artifacts
python launch.py --host 0.0.0.0 --port 9000
```

**Make targets (Unix only):**

```bash
make launch      # setup + start server (cross-platform Python)
make serve       # python -m thalos_prime (deps already installed)
make setup-unix  # bash setup.sh
make test        # run tests
make check       # full quality check
```

**Direct launch (deps already installed):**

```bash
python run_thalos.py --serve           # legacy launcher
python -m thalos_prime                 # module entry point
```

The server starts on **http://localhost:8000** by default.

### Interactive Documentation

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc (read-only) |
| http://localhost:8000 | Matrix-style browser UI |

### Experiment Evaluation Endpoints

The experiment API accepts recorded candidate measurements and returns a baseline comparison report. These endpoints do not execute candidate code or automatically accept the report as verified knowledge.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/experiments/plan/default` | Return the validated declarative research workflow |
| `POST` | `/api/v1/experiments/compare` | Compare recorded candidate results against a defined baseline |

See [docs/EXPERIMENT_WORKFLOW.md](docs/EXPERIMENT_WORKFLOW.md) for the request contract, metric semantics, and safety boundaries.

### Artifact Epistemic Endpoints

The TPL epistemic pipeline is exposed under `/api/v1/artifacts/`:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/artifacts/ingest` | Ingest raw data → validate → admit to belief base |
| `GET`  | `/api/v1/artifacts/artifact/{id}` | Retrieve BeliefRecord for an artifact |
| `POST` | `/api/v1/artifacts/derive` | Derive a claim from ACCEPTED artifacts |
| `GET`  | `/api/v1/artifacts/export/{id}` | Export artifact + ProofTrace bundle |
| `GET`  | `/api/v1/artifacts/graph/{id}` | Lineage graph for an artifact |
| `POST` | `/api/v1/artifacts/consensus` | Find the highest-confidence accepted artifact |

**Example: ingest an artifact**

```bash
curl -X POST http://localhost:8000/api/v1/artifacts/ingest \
  -H "Content-Type: application/json" \
  -d '{"content": "Gravitational waves carry energy away from binary stars.",
       "source_uris": ["https://arxiv.org/example"]}'
```

**Example: derive a claim from accepted artifacts**

```bash
curl -X POST http://localhost:8000/api/v1/artifacts/derive \
  -H "Content-Type: application/json" \
  -d '{"artifact_ids": ["<accepted-artifact-id>"], "operation": "summarize"}'
```

### ASGI / Vercel Deployment

The root `app.py` is the ASGI entrypoint compatible with Vercel and any ASGI host:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## Infrastructure Synthesis CLI

The `thalos_prime.infra_synthesis` package reads a YAML schema and emits
provider-specific deployment artifacts. Install once, then use the `thalos` command.

### Commands

```bash
# Generate artifacts from a schema
thalos build --schema schemas/infra.schema.yaml --out dist

# Validate schema and policy rules
thalos verify --schema schemas/infra.schema.yaml

# Deploy with a release strategy
thalos deploy --schema schemas/infra.schema.yaml --deploy-key v1.2.3
```

### Generated Artifacts

Running `thalos build` creates the following in `dist/`:

| File | Description |
|------|-------------|
| `terraform/provider.tf` | Terraform provider declaration |
| `terraform/main.tf` | Terraform main configuration |
| `opentofu/main.tf` | OpenTofu main configuration |
| `wrangler.toml` | Cloudflare Wrangler configuration |
| `ci.yml` | GitHub Actions CI workflow |
| `Dockerfile` | Container image (when `compute.type: container`) |
| `artifact_manifest.json` | SHA-256 manifest of all generated files |

### Schema Format

```yaml
# schemas/infra.schema.yaml — required top-level sections
project:   { name: my-app, version: "1.0.0" }
compute:   { type: container, scaling: { min: 1, max: 5 } }
network:   { ssl: true, domain: my-app.example.com }
storage:   { type: s3, bucket: my-app-data }
ci:        { provider: github_actions, branch: main }
```

See [`schemas/infra.schema.yaml`](schemas/infra.schema.yaml) for a complete example.

### Infra Synthesis Architecture

| Layer | Modules |
|-------|---------|
| Adapters | `adapters/terraform.py`, `adapters/opentofu.py`, `adapters/cloudflare.py`, `adapters/github_actions.py`, `adapters/docker.py` |
| Engine | `engine.py` — orchestrates adapters, hashes artifacts |
| Validation | `validator.py`, `schema_loader.py` |
| Policy | `policy/engine.py` — `require_ssl`, `limit_scaling` rules |
| Secrets | `secrets/local_vault.py` — Fernet (AES-GCM) encrypted vault |
| State | `state/local.py` — JSON-on-disk snapshot backend |
| Rollback | `rollback/manager.py` — pre-deploy snapshots + restore |
| Drift | `drift.py` — DeepDiff schema drift detection |
| Release | `release/orchestrator.py` — `direct` / `blue_green` / `canary` strategies |
| Events | `events/bus.py` — pub/sub event bus |
| Telemetry | `telemetry/metrics.py` — metric recording + JSON export |
| Security | `security/rbac.py` — role-based access control |
| Audit | `audit/logger.py` — structured JSON audit log |
| Plugins | `plugins/loader.py` — entry-point-based plugin discovery |
| Schema Versioning | `schema_versioning/registry.py` + `diff.py` |
| CLI | `cli/main.py` — `thalos build\|verify\|deploy` |

### Run Infra Synthesis Tests

```bash
pytest tests/infra_synthesis/ -v
```

---

## Configuration

| Setting | How to Set | Default |
|---------|-----------|---------|
| `THALOS_LIBRARY_PATH` | Environment variable | Windows path to local Babel library |

```bash
# Linux / macOS
export THALOS_LIBRARY_PATH=/path/to/ThalosPrimeLibraryOfBabel

# Windows
set THALOS_LIBRARY_PATH=C:\Path\To\ThalosPrimeLibraryOfBabel
```

All other configuration is explicit and typed. There are no hidden defaults or implicit globals.

---

## Architecture

ThalosPrimeLibrary is organised into 22 subsystem packages under `thalos_prime/`:

| Package | Description |
|---------|-------------|
| `api/` | FastAPI REST server — search, generation, enumeration, decoding, chat, admin, artifacts |
| `ui/` | Matrix-style HTML5 browser interface |
| `cli/` | Command-line interface with lazy heavy-dependency imports |
| `library_of_sense/` | Multi-source query orchestration and knowledge synthesis |
| `knowledge_graph/` | Neo4j-compatible knowledge graph (NetworkX backend) |
| `graph_rag/` | Hybrid Graph-RAG — BFS graph traversal + text search retrieval |
| `constraints/` | Z3-based symbolic constraint engine with typed variables |
| `reasoning/` | Unified reasoning control plane (symbolic + proof + constraint) |
| `planning/` | Tree of Thoughts and MCTS multi-path planners |
| `experiments/` | Signed human directives, declarative DAG plans, registered-handler runtime, bounded project inventory, baseline/paired evaluation, canonical artifact adapters |
| `simulation/` | Deterministic world-state simulation |
| `agency/` | Perceive-plan-act agent loop with belief tracking |
| `babel/` | Deterministic conversational pipeline and semantic orchestrator |
| `infra_synthesis/` | YAML → multi-provider infrastructure artifact generation |
| `auth/` | API key authentication |
| `models/` | Pydantic data models |
| `cache/` | TTL-based distributed cache |
| `monitoring/` | Telemetry, metrics, and structured JSON audit logging |
| `database/` | Optional SQLAlchemy data persistence |
| `workers/` | Bounded async background task workers |
| `remote/` | External service integration |
| `utils/` | Shared utility helpers |
| `config.py` | `LibraryConfig` and `setup_local_imports()` |

### TPL Epistemic Subsystems (Control Plane)

These subsystems implement the deterministic epistemic pipeline:

| Package | Role |
|---------|------|
| `artifacts/` | Canonical `Artifact` schema, `GenesisLock` signing, `FacsBundle` |
| `belief/` | `BeliefLedger` — epistemic state machine (`B_t`) |
| `validation/` | `ValidationPipeline` — 6-stage deterministic admission control |
| `reasoning_tpl/` | `TplReasoningLayer` — derive claims from ACCEPTED artifacts |
| `audit/` | `AuditTrail` — SHA-256 chained tamper-evident event log |

### TPL Data Plane Subsystems

| Package | Role |
|---------|------|
| `indexing/` | `PrpIndexer` — HMAC-SHA256 PRF → 5-tuple `Coordinate` |
| `edge/` | `EdgeExecutor` — bounded `deque`-backed deterministic executor |
| `export/` | `ExportPresenter` — `ProofTrace`, `LineageGraph`, JSON export |

For the complete architectural specification see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Development

### Setup

```bash
# 1. Install all development dependencies
pip install -e ".[dev]"
# or
make install

# 2. Install pre-commit hooks
pre-commit install
# or
make pre-commit-install
```

### Running Checks

```bash
make check        # Run all checks (type, lint, test, validate)
make typecheck    # mypy --strict + pyright
make lint         # ruff check
make test         # pytest with 80 % coverage requirement
make validate     # Custom lifecycle / determinism / state / docs validators
```

### CI/CD Pipeline

Every pull request and push to `main` runs:

| Check | Tool |
|-------|------|
| Type checking | `mypy --strict`, `pyright` |
| Linting | `ruff` (all rules) |
| Tests | `pytest` — 80 % minimum coverage |
| Lifecycle validation | Custom validator — ensures subsystems implement required methods |
| Determinism validation | Custom validator — detects non-deterministic operations |
| State validation | Custom validator — checks state serialisation |
| Documentation validation | Custom validator — verifies docstrings and required docs |
| Security scanning | `bandit`, `pip-audit` |
| Prohibited patterns | Detects TODOs, stubs, mocks, placeholders |

**All checks must pass** before a pull request can be merged.
See [CONTRIBUTING.md](docs/guides/CONTRIBUTING.md) for the full contribution workflow.

---

## Testing

```bash
# Run all tests with coverage
make test
# or
python -m pytest tests -v --cov=thalos_prime --cov-report=html

# Run a specific test module
pytest tests/test_generator.py -v

# Run the deterministic pipeline tests (no network required)
pytest tests/test_thalos_prime_pipeline.py -v

# Run the infra synthesis tests
pytest tests/infra_synthesis/ -v
```

### Requirements

- **80 % minimum** line coverage overall
- **100 % coverage** for all critical lifecycle paths
- Every test must be deterministic — no flaky or time-dependent tests

---

## Deployment

See [DEPLOYMENT.md](docs/guides/DEPLOYMENT.md) for the complete deployment guide (Docker,
cloud platforms, production configuration, TLS, reverse proxy).

Quick options:

```bash
# Run locally
python run_thalos.py

# Docker
docker build -t thalos-prime -f infra/Dockerfile .
docker run -p 8000:8000 thalos-prime

# Docker Compose
docker compose -f infra/docker-compose.yml up
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Unified architecture](docs/UNIFIED_THALOS_PRIME_ARCHITECTURE.md) | Canonical product workflow, module boundaries, and integration phases |
| [Integration registry](docs/INTEGRATION_REGISTRY.md) | Candidate repositories, contribution hypotheses, and acceptance requirements |
| [Validation plan](docs/VALIDATION_AND_BENCHMARK_PLAN.md) | Baselines, metrics, and experimental controls |
| [Experiment workflow](docs/EXPERIMENT_WORKFLOW.md) | Task contracts, signed authorization, registered workflow execution, project inventory, repeated measurements, and limits |
| [Lender brief](docs/funding/THALOSPRIME_LENDER_BRIEF.md) | Repayment-oriented financing narrative and risk controls |
| [Investor brief](docs/funding/THALOSPRIME_INVESTOR_BRIEF.md) | Product thesis and technical/commercial validation gates |
| [ARCHITECTURE.md](docs/guides/ARCHITECTURE.md) | Existing system architecture and layer descriptions |
| [docs/thalos_prime_blueprint.md](docs/thalos_prime_blueprint.md) | Deterministic architecture blueprint and MNN pipeline spec |
| [DEPLOYMENT.md](docs/guides/DEPLOYMENT.md) | Complete deployment guide |
| [CONTRIBUTING.md](docs/guides/CONTRIBUTING.md) | Development workflow, code standards, and CI requirements |
| [IMPLEMENTATION_COMPLETE.md](docs/IMPLEMENTATION_COMPLETE.md) | Historical implementation snapshot; not current validation |
| [VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md) | Historical February 2026 test snapshot; rerun checks for current status |

---

## Requirements

- **Python 3.12+** — required for strict type checking and modern language features
- See [DEPLOYMENT.md](docs/guides/DEPLOYMENT.md) for infrastructure prerequisites
- See [CONTRIBUTING.md](docs/guides/CONTRIBUTING.md) for development tool requirements

---

## License

MIT License — see the [LICENSE](LICENSE) file for details.
