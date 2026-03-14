# ThalosPrimeLibrary

> *"In the Library of Babel, every truth already exists — Thalos Prime finds it."*

ThalosPrimeLibrary is a deterministic, production-grade Python toolkit that integrates the
[Library of Babel](https://libraryofbabel.info) with hybrid cognitive synthesis, symbolic reasoning,
autonomous agency, and infrastructure-as-code generation. It is designed around strict
**Control Plane / Data Plane** separation, enforced lifecycle contracts, and full replay
determinism — identical inputs always produce identical outputs.

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

ThalosPrimeLibrary (`thalos_prime`) is a multi-subsystem Python library that combines:

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

Every subsystem follows the same six-method lifecycle contract
(`initialize → validate → operate → reconcile → checkpoint → terminate`) and every operation is
fully deterministic with a seeded replay guarantee.

---

## Key Capabilities

| Capability | Description |
|---|---|
| **Deterministic page generation** | SHA-256-based generation of 3,200-character Babel pages from hex addresses |
| **Query enumeration** | Map natural-language queries to candidate Babel addresses via n-gram extraction |
| **Coherence scoring** | Four-metric scoring (language, structure, n-gram, exact match) on a 0–100 scale |
| **Deep synthesis** | Multi-view semantic decomposition with Physical/Chemical, Logical/Mathematical, Linguistic/Narrative nexus results |
| **Symbolic reasoning** | Z3 SMT constraint solving, incremental updates, optimization objectives |
| **Tree of Thoughts / MCTS** | Deterministic multi-path planning with explicit thought-node representation |
| **Graph-RAG** | Hybrid knowledge graph retrieval combining BFS graph traversal and text search |
| **Infrastructure synthesis** | YAML-schema → Terraform/OpenTofu/Cloudflare/GitHub Actions/Docker artifacts |
| **Policy enforcement** | `require_ssl`, `limit_scaling`, and extensible policy rules |
| **Release strategies** | `direct`, `blue_green`, `canary` deployment orchestration |
| **Drift detection** | DeepDiff-based schema drift detection and rollback |
| **Replay determinism** | Single seed controls all pseudo-randomness; identical inputs → identical outputs |

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

### Determinism Guarantees

- A single integer `--seed` seeds an isolated `random.Random(seed)` instance.
- All collections are sorted with stable, deterministic keys (e.g. `score DESC, doc_id ASC`).
- No module-level RNG state; no implicit async at the module boundary.
- Checkpoints are blake2b-hashed, versioned, and atomic.
- Replay: same `--seed` + `--query` always produces byte-for-byte identical output.

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

The 64 offline tests cover halt semantics, state serialisation, BM25 scoring, volume assembly,
traversal determinism, and a full dry-run end-to-end pass.

---

## REST API Server

ThalosPrimeLibrary ships a FastAPI server with endpoints for search, generation, enumeration,
decoding, chat, and administration.

### Start the Server

```bash
python run_thalos.py   # or tools/run_thalos.sh on Linux/macOS
```

The server starts on **http://localhost:8000** by default.

### Interactive Documentation

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc (read-only) |
| http://localhost:8000 | Matrix-style browser UI |

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
| `api/` | FastAPI REST server — search, generation, enumeration, decoding, chat, admin |
| `ui/` | Matrix-style HTML5 browser interface |
| `cli/` | Command-line interface with lazy heavy-dependency imports |
| `library_of_sense/` | Multi-source query orchestration and knowledge synthesis |
| `knowledge_graph/` | Neo4j-compatible knowledge graph (NetworkX backend) |
| `graph_rag/` | Hybrid Graph-RAG — BFS graph traversal + text search retrieval |
| `constraints/` | Z3-based symbolic constraint engine with typed variables |
| `reasoning/` | Unified reasoning control plane (symbolic + proof + constraint) |
| `planning/` | Tree of Thoughts and MCTS multi-path planners |
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

For the complete architectural specification see [ARCHITECTURE.md](docs/guides/ARCHITECTURE.md) and
[docs/thalos_prime_blueprint.md](docs/thalos_prime_blueprint.md).

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
| [ARCHITECTURE.md](docs/guides/ARCHITECTURE.md) | Full system architecture and layer descriptions |
| [docs/thalos_prime_blueprint.md](docs/thalos_prime_blueprint.md) | Deterministic architecture blueprint and MNN pipeline spec |
| [DEPLOYMENT.md](docs/guides/DEPLOYMENT.md) | Complete deployment guide |
| [CONTRIBUTING.md](docs/guides/CONTRIBUTING.md) | Development workflow, code standards, and CI requirements |
| [IMPLEMENTATION_COMPLETE.md](docs/IMPLEMENTATION_COMPLETE.md) | Phase 1 / Phase 2 implementation status |
| [VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md) | System verification and test results |

---

## Requirements

- **Python 3.12+** — required for strict type checking and modern language features
- See [DEPLOYMENT.md](docs/guides/DEPLOYMENT.md) for infrastructure prerequisites
- See [CONTRIBUTING.md](docs/guides/CONTRIBUTING.md) for development tool requirements

---

## License

MIT License — see the [LICENSE](LICENSE) file for details.
