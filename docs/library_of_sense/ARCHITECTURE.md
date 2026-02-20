# Library of Sense - Architecture

## Overview

The Library of Sense subsystem provides deterministic, multi-source knowledge retrieval,
synthesis, reasoning, and code generation. It is built on strict control-plane/data-plane
separation with full lifecycle management for all subsystem components.

## Components

### Core (`core/`)
- **interfaces.py**: Protocol definitions (`RetrievalSource`, `KnowledgeSynthesizer`, `ReasoningEngine`) and data classes.
- **lifecycle.py**: `LifecycleState`, `LifecycleEvent`, `SubsystemLifecycle` for deterministic state tracking.
- **state_manager.py**: `StateManager` — observable, serializable subsystem state with 6 lifecycle methods.
- **orchestrator.py**: `QueryOrchestrator` — coordinates retrieval, synthesis, and reasoning.

### Retrieval (`retrieval/`)
- **multi_source.py**: Aggregates and ranks results from multiple sources.
- **web_retrieval.py**: HTTP-based retrieval with session management and lifecycle methods.
- **knowledge_graph.py**: NetworkX-based RDF triple store and graph query.
- **code_search.py**: AST-based Python source indexing and search.
- **computational.py**: SymPy-based mathematical expression evaluation.

### Synthesis (`synthesis/`)
- **knowledge_fusion.py**: Confidence-weighted deduplication and fusion.
- **conflict_resolution.py**: Majority-voting conflict resolution.
- **verification.py**: Source-grounding and confidence verification.
- **answer_generator.py**: Structured answer formatting with provenance.

### Reasoning (`reasoning/`)
- **symbolic_engine.py**: SymPy-based symbolic mathematics reasoning.
- **proof_checker.py**: Algebraic equivalence and identity verification.
- **constraint_solver.py**: Z3-based constraint satisfaction.

### Code Generation (`code_generation/`)
- **validator.py**: AST-based syntax and docstring validation.
- **generator.py**: Function and class template generation.
- **executor.py**: Subprocess-sandboxed code execution with timeout.

### API (`api/`)
- **query_handler.py**: Full-pipeline handler with lifecycle methods.
- **response_builder.py**: Versioned API response construction.

## Data Flow

```
Query → QueryHandler.handle_query()
  → QueryOrchestrator.process_query()
    → retrieve() → [RetrievalSource.query() × N]
    → synthesize() → [KnowledgeSynthesizer.synthesize()]
    → apply_reasoning() (optional, require_proof=True)
  → ResultVerifier.verify_and_mark()
  → AnswerGenerator.generate()
→ StructuredAnswer
```

## Lifecycle

All subsystem classes implement the 6 required lifecycle methods:
1. `initialize()` — resource setup
2. `validate()` — invariant verification, raises on failure
3. `operate()` — transition to active operation
4. `reconcile()` — convergence to consistent state
5. `checkpoint()` — atomic, versioned state serialization
6. `terminate()` — clean resource release

## State Management

`StateManager` tracks: query count, retrieval count, synthesis count, error count, active sources,
seed, and version. All state is serializable via `to_dict()` and includes created/updated timestamps.

## Determinism

- All seeds are explicit and logged in every lifecycle event.
- No randomness without seeding.
- All state transitions are logged with timestamps and seed values.
