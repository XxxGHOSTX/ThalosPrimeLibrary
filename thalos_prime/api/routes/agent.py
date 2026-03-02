"""Agent API Routes - Autonomous agent endpoints.

Provides true agent API endpoints for goal submission, plan execution,
constraint checking, knowledge graph queries, and agent state management.
Uses the MCTSPlanner, SymbolicConstraintEngine, and Neo4jKnowledgeGraph
components for autonomous planning and reasoning.
"""

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from thalos_prime.constraints.symbolic_engine import (
    ConstraintSet,
    OptimizationObjective,
    SymbolicConstraintEngine,
    SymbolicSolution,
    SymbolicSolutionDict,
    VariableDeclaration,
    VariableSort,
)
from thalos_prime.knowledge_graph.neo4j_graph import (
    CypherQuery,
    Neo4jKnowledgeGraph,
    NodeRecord,
    NodeRecordDict,
    RelationshipRecord,
    RelationshipRecordDict,
)
from thalos_prime.planning.mcts_planner import MCTSPlanner

router = APIRouter()

# Singleton agent components (initialized on first use)
_graph: Neo4jKnowledgeGraph | None = None
_engine: SymbolicConstraintEngine | None = None
_planner: MCTSPlanner | None = None


def _get_graph() -> Neo4jKnowledgeGraph:
    """Get or create the knowledge graph singleton."""
    global _graph
    if _graph is None:
        _graph = Neo4jKnowledgeGraph(seed=0)
        _graph.initialize()
    return _graph


def _get_engine() -> SymbolicConstraintEngine:
    """Get or create the constraint engine singleton."""
    global _engine
    if _engine is None:
        _engine = SymbolicConstraintEngine(seed=0)
        _engine.initialize()
    return _engine


def _get_planner() -> MCTSPlanner:
    """Get or create the MCTS planner singleton."""
    global _planner
    if _planner is None:
        _planner = MCTSPlanner(component_seed=0)
        _planner.initialize()
    return _planner


# ------------------------------------------------------------------
# Agent State
# ------------------------------------------------------------------


@router.get("/status")
async def agent_status() -> dict[str, Any]:
    """Get current agent subsystem status."""
    graph = _get_graph()
    engine = _get_engine()
    planner = _get_planner()
    return {
        "status": "operational",
        "timestamp": time.time(),
        "subsystems": {
            "knowledge_graph": graph.validate().to_dict(),
            "constraint_engine": engine.validate().to_dict(),
            "mcts_planner": planner.validate().to_dict(),
        },
        "statistics": {
            "graph_nodes": graph.node_count,
            "graph_relationships": graph.relationship_count,
            "graph_queries": graph.query_count,
            "constraint_solves": engine.solve_count,
            "plans_generated": planner.plan_count,
        },
    }


@router.post("/checkpoint")
async def agent_checkpoint() -> dict[str, Any]:
    """Checkpoint all agent subsystem state."""
    graph = _get_graph()
    engine = _get_engine()
    planner = _get_planner()
    return {
        "knowledge_graph": graph.checkpoint(),
        "constraint_engine": engine.checkpoint(),
        "mcts_planner": planner.checkpoint(),
    }


# ------------------------------------------------------------------
# Knowledge Graph Endpoints
# ------------------------------------------------------------------


@router.post("/graph/nodes")
async def create_graph_node(
    node_id: str,
    labels: list[str] | None = None,
    properties: dict[str, Any] | None = None,
) -> NodeRecordDict:
    """Create a labeled node in the knowledge graph."""
    graph = _get_graph()
    record = NodeRecord(
        node_id=node_id,
        labels=set(labels or []),
        properties=dict(properties or {}),
    )
    try:
        created = graph.create_node(record)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return created.to_dict()


@router.get("/graph/nodes/{node_id}")
async def get_graph_node(node_id: str) -> NodeRecordDict:
    """Retrieve a node from the knowledge graph."""
    graph = _get_graph()
    record = graph.get_node(node_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id!r}")
    return record.to_dict()


@router.delete("/graph/nodes/{node_id}")
async def delete_graph_node(node_id: str) -> dict[str, Any]:
    """Delete a node and its relationships from the knowledge graph."""
    graph = _get_graph()
    deleted = graph.delete_node(node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id!r}")
    return {"deleted": True, "node_id": node_id}


@router.post("/graph/relationships")
async def create_graph_relationship(
    source_id: str,
    target_id: str,
    rel_type: str,
    properties: dict[str, Any] | None = None,
) -> RelationshipRecordDict:
    """Create a typed relationship between two nodes."""
    graph = _get_graph()
    record = RelationshipRecord(
        source_id=source_id,
        target_id=target_id,
        rel_type=rel_type,
        properties=dict(properties or {}),
    )
    try:
        created = graph.create_relationship(record)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return created.to_dict()


@router.get("/graph/relationships/{source_id}")
async def get_graph_relationships(
    source_id: str,
    rel_type: str = "",
) -> list[dict[str, Any]]:
    """Get outgoing relationships from a node."""
    graph = _get_graph()
    rels = graph.get_relationships(source_id, rel_type=rel_type)
    return [r.to_dict() for r in rels]


@router.post("/graph/query")
async def query_graph(
    operation: str,
    node_label: str = "",
    rel_type: str = "",
    source_id: str = "",
    target_id: str = "",
    properties: dict[str, Any] | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Execute a Cypher-style query against the knowledge graph."""
    valid_ops = {"match_nodes", "match_relationships", "shortest_path", "neighbors"}
    if operation not in valid_ops:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid operation: {operation!r}. Must be one of {sorted(valid_ops)}",
        )
    graph = _get_graph()
    query = CypherQuery(
        operation=operation,  # type: ignore[arg-type]
        node_label=node_label,
        rel_type=rel_type,
        source_id=source_id,
        target_id=target_id,
        properties=dict(properties or {}),
        limit=limit,
    )
    try:
        results = graph.execute_query(query)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return results


# ------------------------------------------------------------------
# Constraint Engine Endpoints
# ------------------------------------------------------------------

_SORT_MAP: dict[str, VariableSort] = {
    "int": VariableSort.INT,
    "real": VariableSort.REAL,
    "bool": VariableSort.BOOL,
}


def _parse_variable_declarations(
    variables: list[dict[str, Any]],
) -> list[VariableDeclaration]:
    """Parse variable dicts into VariableDeclaration instances.

    Args:
        variables: List of variable specification dicts.

    Returns:
        List of validated VariableDeclaration instances.

    Raises:
        HTTPException: If a variable sort is invalid.

    """
    var_decls: list[VariableDeclaration] = []
    for v in variables:
        sort_str = str(v.get("sort", "int"))
        sort = _SORT_MAP.get(sort_str)
        if sort is None:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid sort: {sort_str!r}. Must be one of {sorted(_SORT_MAP.keys())}",
            )
        var_decls.append(VariableDeclaration(
            name=str(v["name"]),
            sort=sort,
            lower_bound=v.get("lower_bound"),
            upper_bound=v.get("upper_bound"),
        ))
    return var_decls


@router.post("/constraints/solve")
async def solve_constraints(
    name: str,
    variables: list[dict[str, Any]],
    constraints: list[str],
) -> SymbolicSolutionDict:
    """Solve a constraint satisfaction problem."""
    engine = _get_engine()
    var_decls = _parse_variable_declarations(variables)
    cs = ConstraintSet(name=name, variables=var_decls, constraints=constraints)
    result: SymbolicSolution = engine.solve(cs)
    return result.to_dict()


@router.post("/constraints/optimize")
async def optimize_constraints(
    name: str,
    variables: list[dict[str, Any]],
    constraints: list[str],
    objective_expression: str,
    objective_direction: str = "minimize",
) -> SymbolicSolutionDict:
    """Solve a constraint optimization problem."""
    if objective_direction not in {"minimize", "maximize"}:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid direction: {objective_direction!r}. Must be 'minimize' or 'maximize'",
        )
    engine = _get_engine()
    var_decls = _parse_variable_declarations(variables)
    cs = ConstraintSet(name=name, variables=var_decls, constraints=constraints)
    obj = OptimizationObjective(
        expression=objective_expression,
        direction=objective_direction,  # type: ignore[arg-type]
    )
    result: SymbolicSolution = engine.optimize(cs, obj)
    return result.to_dict()


@router.post("/constraints/check")
async def check_constraints(
    name: str,
    variables: list[dict[str, Any]],
    constraints: list[str],
) -> dict[str, Any]:
    """Check if a constraint set is satisfiable."""
    engine = _get_engine()
    var_decls = _parse_variable_declarations(variables)
    cs = ConstraintSet(name=name, variables=var_decls, constraints=constraints)
    vr = engine.check_satisfiable(cs)
    return vr.to_dict()


# ------------------------------------------------------------------
# Planning Endpoints
# ------------------------------------------------------------------


@router.post("/plan/mcts")
async def mcts_plan(
    root_state: str,
    actions: list[str],
    iterations: int = 50,
    max_depth: int = 5,
    seed: int = 42,
) -> dict[str, Any]:
    """Run MCTS planning from a root state with a fixed action set.

    The action generator cycles through the provided actions list.
    The reward evaluator uses string length heuristic (normalized).
    """
    planner = _get_planner()

    def action_generator(state: str) -> list[str]:
        return [f"{state} -> {a}" for a in actions]

    def reward_evaluator(state: str) -> float:
        return min(len(state) / 200.0, 1.0)

    result = planner.search(
        root_state=root_state,
        action_generator=action_generator,
        reward_evaluator=reward_evaluator,
        iterations=iterations,
        max_depth=max_depth,
        seed=seed,
    )
    return result.to_dict()


@router.get("/plan/stats")
async def plan_stats() -> dict[str, Any]:
    """Get MCTS planner statistics."""
    planner = _get_planner()
    return {
        "plan_count": planner.plan_count,
        "total_iterations": planner.total_iterations,
        "validation": planner.validate().to_dict(),
    }
