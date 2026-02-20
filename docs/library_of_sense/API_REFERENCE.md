# Library of Sense - API Reference

## QueryHandler

```python
handler = QueryHandler(seed=42)
handler.initialize()
handler.validate()
handler.operate()
handler.register_source(source)
handler.register_synthesizer(synthesizer)
answer: StructuredAnswer = handler.handle_query("query", context)
handler.checkpoint()
handler.terminate()
```

## QueryContext

```python
context = QueryContext(
    domain=QueryDomain.MATHEMATICS,
    require_proof=True,
    seed=42,
    timeout_seconds=30.0,
)
```

## Retrieval Sources

- `KnowledgeGraphRetriever` — add_triple, query_subject, find_path, query, validate
- `ComputationalRetriever` — query (sympy), validate
- `CodeSearchRetriever` — index_source, search, query, validate
- `WebRetrievalHandler` — initialize, validate, query, terminate

## Synthesizers

- `KnowledgeFusion` — deduplicate, synthesize
- `ConflictResolver` — synthesize

## Reasoning

- `SymbolicReasoningEngine` — simplify_expression, differentiate, reason
- `ProofChecker` — check_equivalence, check_identity
- `ConstraintSolver` — solve, check_satisfiable

## ResponseBuilder

```python
builder = ResponseBuilder()
response = builder.build(answer)
error = builder.build_error("query", "message")
```
