# Thalos NEXUS Tool Architecture

## Universal Solver Registry, Recipe Engine, Riemann-Babel Filter & Web API

---

## Table of Contents

1. [Overview](#overview)
2. [Control Plane vs Data Plane Boundaries](#control-plane-vs-data-plane-boundaries)
3. [Universal Solver Registry — `thalos_nexus/solver_registry.py`](#universal-solver-registry)
4. [Recipe Engine — `thalos_nexus/recipes.py`](#recipe-engine)
5. [Riemann-Babel Filter](#riemann-babel-filter)
   - [Data Plane: `thalos_prime/babel/prime_filter.py`](#data-plane-prime_filterpy)
   - [Control Plane: `thalos_runtime/core/prime_pipeline.py`](#control-plane-prime_pipelinepy)
6. [Web/API Integration — `thalos_prime/api/routes/tools.py`](#webapi-integration)
7. [Relationship to Existing Architecture](#relationship-to-existing-architecture)
8. [Lifecycle Contracts](#lifecycle-contracts)
9. [State Surfaces](#state-surfaces)
10. [Checkpoint Formats](#checkpoint-formats)
11. [Event Log Schema](#event-log-schema)
12. [Data Flow Diagram](#data-flow-diagram)

---

## Overview

The **Universal Solver Registry + Riemann-Babel Filter** stack adds a
cognitive-solver discovery and text-analysis pipeline to ThalosPrimeLibrary.
It consists of four new modules arranged in a strict control-plane / data-plane
hierarchy:

| Layer | Module | Responsibility |
|---|---|---|
| Control Plane | `thalos_nexus/solver_registry.py` | Solver descriptor storage & discovery |
| Control Plane | `thalos_nexus/recipes.py` | Solver planning from `DataSignature` |
| Data Plane | `thalos_prime/babel/prime_filter.py` | Prime-index numerical scoring |
| Control Plane | `thalos_runtime/core/prime_pipeline.py` | Pipeline orchestration |
| API Layer | `thalos_prime/api/routes/tools.py` | HTTP endpoints for discovery & analysis |

The stack is **distinct** from the existing `thalos_nexus.cytoplasm.ToolRegistry`
(which manages subprocess-level CLI tools) — the new `SolverRegistry` manages
*cognitive solver descriptors* for cryptography, mathematics, games, and
informatics domains.

---

## Control Plane vs Data Plane Boundaries

### Strict separation principle

ThalosPrimeLibrary enforces a hard boundary between **control-plane** code
(coordination, lifecycle, planning, I/O) and **data-plane** code (pure
numerical/text computation with no side effects).

```
┌─────────────────────────────────────────────────────────────────┐
│  CONTROL PLANE                                                  │
│                                                                 │
│  SolverRegistry ──► RecipeEngine ──► PrimePipeline             │
│  (discovery)        (planning)       (orchestration)           │
│                                                                 │
│       │                                    │                   │
│       ▼                                    ▼                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  DATA PLANE                                             │   │
│  │                                                         │   │
│  │  prime_filter: score_index, sieve, entropy, gap_walk   │   │
│  │  BabelGenerator: address_to_page (deterministic)        │   │
│  │  BabelEnumerator: enumerate_addresses (deterministic)   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
             API Layer (tools.py)
             GET /api/v1/tools/search
             GET /api/v1/tools
             POST /api/v1/tools/analyze
```

| Property | Control Plane | Data Plane |
|---|---|---|
| I/O side effects | Allowed (logs, HTTP) | **None** |
| Lifecycle management | Yes | No |
| State mutation | Allowed (registry) | **None** |
| Determinism | Best-effort | **Required** |
| Callable types | Any | Pure functions only |

---

## Universal Solver Registry

**File:** `thalos_nexus/solver_registry.py`

### Purpose

Provides a typed, keyword-searchable dictionary of *cognitive solver tools*
— functions that solve cryptographic, mathematical, game-theoretic, or
informatics problems. It is the single source of truth for solver discovery
within the Riemann-Babel Filter pipeline and the Recipe Engine.

### Naming disambiguation

```
thalos_nexus.cytoplasm.ToolRegistry
  → subprocess-level CLI tool execution
  → managed by cytoplasm.py
  → executes shell commands in sandboxed environments

thalos_nexus.solver_registry.SolverRegistry
  → cognitive solver descriptor storage
  → managed by solver_registry.py
  → no execution; pure discovery and descriptor management
```

### Key types

#### `SolverCategory`
```python
SolverCategory = Literal["cryptography", "math", "games", "informatics"]
```
A type alias for the four high-level solver domains. Used as a filter in
`SolverRegistry.search()`.

#### `SolverInput` / `SolverOutput`
Thin envelope dataclasses wrapping raw string input and result objects,
with optional `hints` / `metadata` dictionaries for passing domain-specific
parameters (cipher key, shift value, etc.).

#### `SolverDescriptor`
The core descriptor dataclass. Not frozen (contains `Callable`) but should
be treated as logically immutable after registration.

| Field | Type | Purpose |
|---|---|---|
| `name` | `str` | Unique registry key |
| `category` | `Literal[...]` | Domain classification |
| `keywords` | `frozenset[str]` | Full-text search tokens |
| `description` | `str` | Human-readable description |
| `entrypoint` | `Callable[[SolverInput], SolverOutput]` | The solver function |
| `tags` | `frozenset[str]` | Capability tags for recipe matching |
| `supports_cipher_id` | `bool` | Can identify cipher types |
| `supports_encoding_chain` | `bool` | Can decode encoding chains |
| `priority` | `int` | Sort weight (lower = higher priority) |

#### `SolverNotFoundError`
Subclass of `KeyError`. Raised by `get()` and `unregister()` when the
named solver is not registered. Callers may catch either `SolverNotFoundError`
or the generic `KeyError`.

### `SolverRegistry` methods

| Method | Signature | Description |
|---|---|---|
| `register` | `(SolverDescriptor) -> None` | Add or overwrite a solver |
| `unregister` | `(str) -> None` | Remove by name; raises `SolverNotFoundError` |
| `get` | `(str) -> SolverDescriptor` | Retrieve by exact name |
| `list_all` | `() -> list[SolverDescriptor]` | All solvers, sorted by name |
| `search` | `(str, *, category=None) -> list[SolverDescriptor]` | Keyword search |
| `find_by_tags` | `(frozenset[str]) -> list[SolverDescriptor]` | Tag intersection |

**`search` algorithm:**
1. Tokenise query on whitespace, lowercase all tokens.
2. Score each descriptor by `len(query_tokens ∩ descriptor.keywords)`.
3. Exclude descriptors with zero overlap.
4. Sort by `(-overlap, priority, name)`.

**`find_by_tags` algorithm:**
1. Include descriptors where `descriptor.tags ∩ tags ≠ ∅`.
2. Sort by `(priority, name)`.

### Global singleton

```python
_GLOBAL_SOLVER_REGISTRY: SolverRegistry = SolverRegistry()

def get_global_solver_registry() -> SolverRegistry: ...
```

The process-level singleton is populated by solver packages at import time
or during application startup. The API layer reads from this singleton.

---

## Recipe Engine

**File:** `thalos_nexus/recipes.py`

### Purpose

Maps `DataSignature` metadata to ranked lists of `SolverDescriptor` instances.
The Recipe Engine is a *planning layer* — it selects appropriate solver tools
for each Babel page candidate without executing any computation.

### `DataSignature`

A frozen dataclass capturing structural and statistical metadata about a text
buffer. Produced by `thalos_runtime.core.prime_pipeline._build_signature()`.

| Field | Type | Description |
|---|---|---|
| `length` | `int` | Character count |
| `char_classes` | `frozenset[str]` | Detected character classes |
| `has_whitespace` | `bool` | Contains whitespace |
| `entropy` | `float` | Normalised Shannon entropy `[0.0, 1.0]` |
| `language_hint` | `str \| None` | ISO language code |
| `likely_cipher` | `str \| None` | Detected cipher name |
| `encoding_layers` | `tuple[str, ...]` | Detected encoding layers |
| `prime_index_score` | `float` | Composite prime-index score `[0.0, 1.0]` |

Character classes drawn from: `{"alpha", "digit", "space", "punct", "other"}`.

### `Recipe` Protocol

A `@runtime_checkable` Protocol defining the contract for solver-selection
heuristics:

```python
class Recipe(Protocol):
    name: str
    def matches(self, sig: DataSignature) -> bool: ...
    def ranked_tools(self, registry: SolverRegistry, sig: DataSignature) -> list[SolverDescriptor]: ...
```

### Built-in recipes

#### `CipherIdentificationRecipe`

Detects probable cipher or classical-cipher text.

**Matching predicate:**
- `sig.likely_cipher is not None`, OR
- `0.35 ≤ sig.entropy ≤ 0.80 AND sig.char_classes ⊆ {"alpha", "space", "punct"}`

**Tool selection:** `registry.find_by_tags({"cipher_id", "classical_cipher"})`

**Boost logic:** When `likely_cipher` is identified, tools whose `tags` contain
that cipher name are moved to the front of the result list.

#### `EncodingChainRecipe`

Detects multi-layer encoded text (Base64, ROT13, hex, etc.).

**Matching predicate:**
- `sig.encoding_layers` is non-empty, OR
- `sig.entropy ≥ 0.85`

**Tool selection:** `registry.find_by_tags({"encoding_chain"})`

#### `PrimeTextRecipe`

Detects prime-index-aligned page text from the Babel library.

**Matching predicate:**
- `sig.prime_index_score ≥ score_threshold` (default `0.5`)

**Tool selection:** `registry.find_by_tags({"prime_sieve", "babel"})`

### `RecipeEngine`

```python
class RecipeEngine:
    def __init__(self, registry: SolverRegistry, recipes: Sequence[Recipe]) -> None: ...
    def plan(self, signature: DataSignature) -> list[SolverDescriptor]: ...
```

**`plan` algorithm:**
1. Iterate `self._recipes` in order.
2. For each recipe where `recipe.matches(signature)` is `True`:
   - Call `recipe.ranked_tools(registry, signature)`.
   - Append each result to the output list, **deduplicating by `name`** (first
     occurrence wins).
3. Return the ordered, deduplicated list.

### `build_default_recipe_engine()`

Factory that constructs a `RecipeEngine` with all three built-in recipes
and the global `SolverRegistry` singleton.

---

## Riemann-Babel Filter

The Riemann-Babel Filter combines prime-number theory with the Library of Babel's
deterministic address space to produce a composite "prime-index alignment score"
for each candidate page. Pages with higher scores are more likely to contain
structured (non-random) text.

### Data Plane: `prime_filter.py`

**File:** `thalos_prime/babel/prime_filter.py`

All functions in this module are **pure** and **deterministic**. No I/O, no
side effects.

#### Algorithms

**Sieve of Eratosthenes — `_sieve_of_eratosthenes(limit)`**

Standard sieve producing all primes up to `limit`. Used internally by
`generate_primorial_indices`, `prime_gap_walk`, and `_primorial_rank`.

**Primorial indices — `generate_primorial_indices(limit)`**

Returns the sequence `[2, 6, 30, 210, 2310, ...]` of primorials ≤ `limit`.
The n-th primorial is `∏(first n primes)`.

**Prime-gap walk — `prime_gap_walk(start, steps)`**

Constructs a monotonically increasing sequence anchored at `start`, where
each step advances by the gap between consecutive primes:

```
gaps = [p_{i+1} - p_i for i in range(len(primes)-1)]
positions[0] = start
positions[k+1] = positions[k] + gaps[k]
```

For `prime_gap_walk(0, 5)`:
```
gaps = [1, 2, 2, 4, 2, ...]
→ [0, 1, 3, 5, 9, 11]
```

**Shannon entropy — `_shannon_entropy(text)`**

Normalised Shannon entropy in `[0.0, 1.0]`:
```
H(text) = -∑(p_i * log₂(p_i)) / log₂(|alphabet|)
```

**Binary derivative score — `_binary_derivative_score(text)`**

First-order character-code difference periodicity:
```
diffs = [ord(text[i+1]) - ord(text[i]) for i in range(len(text)-1)]
score = count(diffs[i] == diffs[i+1]) / (len(diffs) - 1)
```

**Primorial rank — `_primorial_rank(index)`**

Largest `n` such that primorial(n) ≤ `index`. Returns 0 for `index < 2`.

#### `PrimeIndexScore`

Frozen dataclass containing all sub-scores:

| Field | Range | Weight |
|---|---|---|
| `entropy_score` | `[0, 1]` | 0.4 |
| `prime_gap_score` | `[0, 1]` | 0.3 |
| `primorial_rank` (log-scaled) | `[0, 1]` | 0.2 |
| `composite_periodicity_score` | `[0, 1]` | 0.1 |
| `combined` | `[0, 1]` | Weighted sum |

**Combined score formula:**
```python
prank_score = min(1.0, log2(prank + 1) / 10.0)
combined = (entropy * 0.4 + gap_score * 0.3 + prank_score * 0.2 + period * 0.1)
```

**Prime-gap score formula:**
- If `index` is in the prime-gap walk: `1.0 - (pos / len(walk))`
- Otherwise: `max(0.0, 1.0 - min_dist / (max_walk_value + 1))`

### Control Plane: `prime_pipeline.py`

**File:** `thalos_runtime/core/prime_pipeline.py`

#### Module-level singletons

```python
_GENERATOR: BabelGenerator = BabelGenerator()
_ENUMERATOR: BabelEnumerator = BabelEnumerator()
```

Both are stateless; the singletons avoid repeated construction overhead.

#### `CandidatePage`

Frozen dataclass representing a scored Babel page candidate:

| Field | Type | Description |
|---|---|---|
| `index` | `int` | Zero-based position in this pipeline run |
| `address` | `str` | Hexadecimal Babel address |
| `text` | `str` | 3200-character page content |
| `prime_score` | `PrimeIndexScore` | Scoring result |
| `signature` | `DataSignature` | Structural metadata |

#### `find_prime_aligned_candidates(query, *, max_candidates=32)`

**Pipeline:**
1. **Enumerate**: `BabelEnumerator.enumerate_addresses(query, max_results=max_candidates)` → list of hex addresses.
2. **Generate**: `BabelGenerator.address_to_page(address)` → 3200-char page text.
3. **Score**: `score_index(i, text)` → `PrimeIndexScore`.
4. **Signature**: `_build_signature(text, prime_score)` → `DataSignature`.
5. **Sort**: by `prime_score.combined` descending.
6. **Return**: `list[CandidatePage]`.

**Validation:**
- `query` must be non-empty → `ValueError`
- `max_candidates` must be in `[1, 256]` → `ValueError`

---

## Web/API Integration

**File:** `thalos_prime/api/routes/tools.py`

**Router prefix:** `/api/v1/tools` (registered in `server.py`)

### Endpoints

#### `GET /api/v1/tools/search`

Keyword-based solver discovery.

**Query parameters:**
- `query` (required): Whitespace-separated search terms.
- `category` (optional): One of `cryptography`, `math`, `games`, `informatics`.

**Response:**
```json
{
  "results": [
    {
      "name": "caesar-cipher",
      "category": "cryptography",
      "description": "...",
      "keywords": ["caesar", "cipher", "rot"],
      "tags": ["cipher_id", "classical_cipher"],
      "supports_cipher_id": true,
      "supports_encoding_chain": false,
      "priority": 100
    }
  ],
  "total": 1
}
```

**Errors:**
- `400` — Invalid `category` value.
- `422` — Empty `query`.

#### `GET /api/v1/tools`

List all registered solvers with optional category filter.

**Query parameters:**
- `category` (optional): Same as above.

**Response:** Same schema as search.

#### `POST /api/v1/tools/analyze`

Full Riemann-Babel Filter analysis.

**Request body:**
```json
{
  "text": "the quick brown fox",
  "max_candidates": 16
}
```

**Response:**
```json
{
  "candidates": [
    {
      "index": 0,
      "address": "a3f2...",
      "prime_score": {
        "combined": 0.412,
        "entropy_score": 0.823,
        "prime_gap_score": 0.154,
        "primorial_rank": 3,
        "composite_periodicity_score": 0.021
      },
      "signature": {
        "length": 3200,
        "entropy": 0.823,
        "has_whitespace": true,
        "char_classes": ["alpha", "space", "punct"],
        "prime_index_score": 0.412,
        "likely_cipher": null,
        "encoding_layers": []
      },
      "recommended_tools": [...]
    }
  ],
  "total_candidates": 16
}
```

**Errors:**
- `422` — Empty `text`, or `max_candidates` out of `[1, 256]`.
- `500` — Internal pipeline failure.

---

## Relationship to Existing Architecture

### Existing modules this stack coordinates with

| Module | Relationship |
|---|---|
| `thalos_prime.lob_babel_generator.BabelGenerator` | Used by `prime_pipeline.py` (data plane, called at runtime) |
| `thalos_prime.lob_babel_enumerator.BabelEnumerator` | Used by `prime_pipeline.py` (control plane, address enumeration) |
| `thalos_nexus.cytoplasm.ToolRegistry` | **Distinct** — subprocess CLI tools, not cognitive solvers |
| `thalos_prime.lifecycle.BaseLifecycleComponent` | **Not used** — these modules are stateless planners/data-plane functions |
| `thalos_runtime.core.engine.RuntimeEngine` | Separate task-dispatch engine; tools router does not use it |
| `thalos_prime.api.server.register_routes()` | Tools router registered here at startup |

### What this stack does NOT touch

- Database models (`thalos_prime/database/`)
- Provenance/audit ledger (`thalos_prime/audit/`)
- Execution IR graph (`thalos_prime/execution_ir/`)
- Agency/agent loop (`thalos_prime/agency/`)
- Library of Sense knowledge synthesis

---

## Lifecycle Contracts

The `LifecycleProtocol` (initialize / validate / operate / reconcile /
checkpoint / terminate) is enforced only for classes in `thalos_prime/` whose
names contain `manager`, `controller`, `service`, `handler`, or `processor`.

**Lifecycle applicability for new modules:**

| Module/Class | Lifecycle required? | Reason |
|---|---|---|
| `SolverRegistry` | **No** | Pure in-memory dictionary; no external dependencies |
| `RecipeEngine` | **No** | Stateless planning layer; constructed fresh per-call |
| `prime_filter` functions | **No** | Data-plane pure functions |
| `CandidatePage` | **No** | Frozen dataclass value object |
| `find_prime_aligned_candidates` | **No** | Stateless orchestrator function |
| `tools.py` router | **No** | FastAPI endpoint; lifecycle managed by ASGI |

None of the new classes have "manager/controller/service/handler/processor" in
their names, so the lifecycle validator will not flag them.

---

## State Surfaces

### `SolverRegistry._solvers`

```
Type: dict[str, SolverDescriptor]
Mutability: Mutable (register/unregister)
Visibility: Exposed via list_all(), get(), search(), find_by_tags()
Consistency: Single-threaded; no internal locking
```

The only mutable state in the entire stack. All other modules are either
stateless functions or hold read-only references to the registry.

### Module-level singletons in `prime_pipeline.py`

```
_GENERATOR: BabelGenerator  — stateless, no mutable internal state
_ENUMERATOR: BabelEnumerator — stateless, no mutable internal state
```

These are created once at import time and reused across calls for efficiency.
They carry no mutable state between calls.

---

## Checkpoint Formats

None of the new modules require checkpointing:

| Module | Checkpoint | Reason |
|---|---|---|
| `SolverRegistry` | N/A — volatile | Rebuilt from caller config on restart |
| `RecipeEngine` | N/A — stateless | Deterministic from registry + recipe list |
| `prime_filter` | N/A — stateless | Pure functions; inputs = full replay state |
| `prime_pipeline` | N/A — stateless | Inputs (query + max_candidates) = full replay |

For durability of solver registrations across restarts, callers should
persist their registration logic (e.g., in application startup code that
calls `get_global_solver_registry().register(...)`) rather than checkpointing
registry state.

---

## Event Log Schema

None of the new modules emit lifecycle events. All are either:
- Pure data-plane functions with no state transitions to record, or
- Simple in-memory registries with no external dependencies.

For audit purposes, the API layer's HTTP access log (provided by FastAPI
middleware in `server.py`) captures all `/api/v1/tools/*` calls with path,
method, and response status. No additional event log schema is defined for
this stack.

If future requirements call for solver-invocation audit trails, the
recommended approach is to wrap `SolverDescriptor.entrypoint` calls with
the existing `DeterminismSpine.log_event()` mechanism from
`thalos_nexus.spine`.

---

## Data Flow Diagram

```
Client Request
     │
     ▼
POST /api/v1/tools/analyze
     │
     ├─── tools.py: AnalyzeRequest validation
     │
     ▼
find_prime_aligned_candidates(query, max_candidates)
     │
     ├─── BabelEnumerator.enumerate_addresses(query)
     │         → list of hex addresses
     │
     ├─── for each address:
     │    ├─── BabelGenerator.address_to_page(address)
     │    │         → 3200-char page text
     │    │
     │    ├─── score_index(i, text)              [DATA PLANE]
     │    │    ├─── _primorial_rank(i)
     │    │    ├─── _shannon_entropy(text)
     │    │    ├─── _binary_derivative_score(text)
     │    │    ├─── prime_gap_walk(0, steps)
     │    │    └─── → PrimeIndexScore
     │    │
     │    └─── _build_signature(text, prime_score)
     │              └─── → DataSignature
     │
     ├─── sort by prime_score.combined desc
     │
     └─── → list[CandidatePage]
          │
          ▼
build_default_recipe_engine()
          │
          ├─── for each CandidatePage:
          │    └─── RecipeEngine.plan(signature)
          │         ├─── CipherIdentificationRecipe.matches(sig)?
          │         │    └─── ranked_tools(registry, sig) → solvers
          │         ├─── EncodingChainRecipe.matches(sig)?
          │         │    └─── ranked_tools(registry, sig) → solvers
          │         └─── PrimeTextRecipe.matches(sig)?
          │              └─── ranked_tools(registry, sig) → solvers
          │
          └─── deduplicate by name → list[SolverDescriptor]
               │
               ▼
          JSON Response: candidates with prime_score, signature,
                         recommended_tools
```

---

*Document generated for ThalosPrimeLibrary v3.0.0*
