# Library of Sense - Usage Examples

## Basic Query with Knowledge Graph

```python
from thalos_prime.library_of_sense.api.query_handler import QueryHandler
from thalos_prime.library_of_sense.core.interfaces import QueryContext, QueryDomain
from thalos_prime.library_of_sense.retrieval.knowledge_graph import (
    GraphTriple, KnowledgeGraphRetriever
)
from thalos_prime.library_of_sense.synthesis.knowledge_fusion import KnowledgeFusion

handler = QueryHandler(seed=42)
handler.initialize()
handler.validate()
handler.operate()

kg = KnowledgeGraphRetriever()
kg.add_triple(GraphTriple(subject="Python", predicate="is_a", obj="language"))
handler.register_source(kg)
handler.register_synthesizer(KnowledgeFusion())

ctx = QueryContext(domain=QueryDomain.KNOWLEDGE_GRAPH)
answer = handler.handle_query("Python", ctx)
print(answer.answer)

handler.checkpoint()
handler.terminate()
```

## Mathematical Computation

```python
from thalos_prime.library_of_sense.retrieval.computational import ComputationalRetriever
from thalos_prime.library_of_sense.core.interfaces import QueryContext, QueryDomain

retriever = ComputationalRetriever()
ctx = QueryContext(domain=QueryDomain.COMPUTATIONAL)
result = retriever.query("x**2 + 2*x + 1", ctx)
print(result.content)
```

## Constraint Solving

```python
from thalos_prime.library_of_sense.reasoning.constraint_solver import (
    ConstraintProblem, ConstraintSolver
)

solver = ConstraintSolver()
problem = ConstraintProblem(
    int_vars=["x", "y"],
    constraints=["x > 0", "y > 0", "x + y == 10"],
)
result = solver.solve(problem)
print(result.status, result.model)
```
