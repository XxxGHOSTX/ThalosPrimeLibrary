"""Runtime engine - Control Plane coordinator for thalos_runtime.

Manages module registration, lifecycle, and task dispatch.
Extends BaseLifecycleComponent to satisfy the LifecycleProtocol
defined in thalos_prime.lifecycle.

Control Plane / Data Plane separation:
- Control Plane (this module): lifecycle coordination, module wiring,
  registry management, result storage orchestration.
- Data Plane (TaskExecutor): pure task invocation with no side effects
  beyond the return value.

State surfaces:
- _registry: TaskRegistry mapping task names to handlers.
- _executor: TaskExecutor (Data Plane) invoked via execute().
- _memory: ExecutionMemory storing all execution records.
- _initialized: bool flag tracked by BaseLifecycleComponent.
- _events: LifecycleEvent log from BaseLifecycleComponent.

Checkpoint format: {"version": str, "seed": int, "initialized": bool,
                    "registry": dict, "memory": dict, "events": list}
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from thalos_prime.lifecycle import BaseLifecycleComponent
from thalos_runtime.core.executor import TaskExecutor
from thalos_runtime.core.memory import ExecutionMemory
from thalos_runtime.core.registry import TaskHandler, TaskRegistry

if TYPE_CHECKING:
    from thalos_prime.library_of_sense.core.interfaces import ValidationResult

logger = logging.getLogger(__name__)

_ENGINE_SEED: int = 42
_ENGINE_VERSION: str = "1.0"


class EngineInitializationError(Exception):
    """Raised when the engine fails to initialize.

    Attributes:
        reason: Human-readable description of the initialization failure.
    """

    def __init__(self, reason: str) -> None:
        """Initialize with a failure reason.

        Args:
            reason: Human-readable description of the failure.
        """
        super().__init__(f"Engine initialization failed: {reason}")
        self.reason = reason


class RuntimeEngine(BaseLifecycleComponent):
    """Control Plane coordinator for the thalos_runtime system.

    Orchestrates module registration, plugin wiring, and task dispatch.
    Delegates all computational work to TaskExecutor (Data Plane).

    Lifecycle contract (must be called in order):
        1. register_module() - wire task handlers (before initialize)
        2. initialize()      - mark engine ready
        3. validate()        - assert invariants
        4. execute()         - dispatch task via Data Plane
        5. checkpoint()      - serialize state
        6. terminate()       - release resources
    """

    def __init__(self) -> None:
        """Initialize the runtime engine with empty registry and memory."""
        super().__init__(component_name="runtime_engine", seed=_ENGINE_SEED)
        self._registry: TaskRegistry = TaskRegistry()
        self._executor: TaskExecutor = TaskExecutor(self._registry)
        self._memory: ExecutionMemory = ExecutionMemory()
        self._substrate_initialized: bool = False
        # Substrate components (lazy-initialized by _init_substrate)
        self._graph_builder: Any = None
        self._graph_transformer: Any = None
        self._det_executor: Any = None
        self._graph_store: Any = None
        self._event_log: Any = None
        self._prov_index: Any = None
        self._audit_ledger: Any = None

    def register_module(self, name: str, handler: TaskHandler) -> None:
        """Register a task module with the engine registry.

        Args:
            name: Unique task identifier.
            handler: Object implementing the TaskHandler protocol.

        Raises:
            RegistryError: If the name is already registered.
        """
        self._registry.register(name, handler)
        self._emit_event("register_module", f"task={name}")

    def execute(self, task: str, payload: dict[str, Any]) -> Any:
        """Execute a registered task, store the result, and return it.

        Args:
            task: Task name to execute.
            payload: Input data for the task handler.

        Returns:
            Result produced by the registered TaskHandler.

        Raises:
            RegistryError: If the task is not registered.
            ExecutionError: If the handler raises an exception.
        """
        self._emit_event("execute", f"task={task}")
        result = self._executor.execute(task, payload)
        self._memory.store(task, payload, result)
        return result

    def task_names(self) -> list[str]:
        """Return all registered task names.

        Returns:
            Sorted list of registered task identifiers.
        """
        return self._registry.names()

    # ------------------------------------------------------------------ #
    # Substrate pipeline                                                   #
    # ------------------------------------------------------------------ #

    def _init_substrate(self) -> None:
        """Lazily initialize all substrate components on first call.

        Creates GraphBuilder, GraphTransformer (with normalization rule),
        DeterministicExecutor, LocalGraphStore, EventLog, ProvenanceIndex,
        and AuditLedger. Safe to call multiple times; no-op after first call.
        """
        if self._substrate_initialized:
            return

        from thalos_prime.audit.ledger import AuditLedger
        from thalos_prime.execution_ir.builder import GraphBuilder
        from thalos_prime.execution_ir.executor import DeterministicExecutor
        from thalos_prime.provenance.index import ProvenanceIndex
        from thalos_prime.rewrite.dsl import make_normalization_rule
        from thalos_prime.rewrite.engine import GraphTransformer
        from thalos_prime.storage.event_log import EventLog
        from thalos_prime.storage.graph_store import LocalGraphStore

        self._graph_builder = GraphBuilder()
        transformer = GraphTransformer()
        transformer.add_rule(make_normalization_rule())
        self._graph_transformer = transformer
        self._det_executor = DeterministicExecutor()
        self._graph_store = LocalGraphStore()
        self._event_log = EventLog()
        self._prov_index = ProvenanceIndex()
        self._audit_ledger = AuditLedger()
        self._substrate_initialized = True
        logger.info("RuntimeEngine: substrate components initialized")

    def execute_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a payload through the graph substrate pipeline.

        Pipeline steps:
        1. Build an ExecutionGraph from the payload using GraphBuilder.
        2. Log a ``graph_created`` event.
        3. Apply GraphTransformer rewrites.
        4. Log a ``graph_transformed`` event.
        5. Plan (topological sort) and execute the graph.
        6. Save the graph via LocalGraphStore.
        7. Record node provenance via ProvenanceIndex.
        8. Return a summary dict with graph_id, version, graph_hash, and outputs.

        The legacy execute() path is preserved and unaffected by this method.

        Args:
            payload: Arbitrary key-value data to feed into the graph substrate.

        Returns:
            Dict containing ``graph_id``, ``version``, ``graph_hash``,
            and ``outputs`` mapping node IDs to their output dicts.
        """
        self._init_substrate()

        from thalos_prime.execution_ir.planner import ExecutionPlanner

        graph = self._graph_builder.build_from_payload(payload)
        self._event_log.log("graph_created", graph.id, graph.version)

        graph = self._graph_transformer.transform(graph)
        self._event_log.log("graph_transformed", graph.id, graph.version)

        planner = ExecutionPlanner()
        plan = planner.plan(graph)
        graph = self._det_executor.execute_graph(graph, plan)

        self._graph_store.save(graph)

        for node in graph.nodes.values():
            self._prov_index.record_node(graph.id, node)

        self._audit_ledger.append(
            "graph_executed",
            graph_id=graph.id,
            version=graph.version,
            graph_hash=graph.graph_hash,
        )

        outputs: dict[str, Any] = {nid: n.outputs for nid, n in graph.nodes.items()}
        return {
            "graph_id": graph.id,
            "version": graph.version,
            "graph_hash": graph.graph_hash,
            "outputs": outputs,
        }

    # ------------------------------------------------------------------ #
    # LifecycleProtocol implementation                                     #
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        """Allocate resources and mark the engine as ready.

        Raises:
            EngineInitializationError: If initialization fails.
        """
        self._emit_event("initialize")
        self._initialized = True
        logger.info(
            "RuntimeEngine initialized (version=%s, seed=%d)",
            _ENGINE_VERSION,
            _ENGINE_SEED,
        )

    def validate(self) -> ValidationResult:
        """Check all engine invariants and preconditions.

        Returns:
            ValidationResult indicating whether the engine is operational.
        """
        from thalos_prime.library_of_sense.core.interfaces import ValidationResult

        self._emit_event("validate")
        if not self._initialized:
            return ValidationResult(
                valid=False,
                message="Engine not initialized; call initialize() first.",
            )
        tasks = self._registry.names()
        return ValidationResult(
            valid=True,
            message=(
                f"Engine ready; {len(tasks)} task(s) registered: {tasks}"
            ),
        )

    def operate(self) -> None:
        """Execute primary engine work (no-op; work is dispatched via execute()).

        Tasks are dispatched on-demand through execute().  This method
        satisfies the LifecycleProtocol contract.
        """
        self._emit_event("operate")
        logger.debug("RuntimeEngine.operate(): tasks=%s", self._registry.names())

    def reconcile(self) -> None:
        """Converge the engine to a consistent state.

        Logs the current registry and memory state for observability.
        Any inconsistencies are surfaced here for external resolution.
        """
        self._emit_event("reconcile")
        tasks = self._registry.names()
        records = len(self._memory.get_all())
        logger.info(
            "RuntimeEngine.reconcile(): tasks=%s, records=%d",
            tasks,
            records,
        )

    def checkpoint(self) -> dict[str, object]:
        """Serialize full engine state for restart.

        Returns:
            Versioned dict with registry, memory, and lifecycle event log.
        """
        self._emit_event("checkpoint")
        return {
            "version": _ENGINE_VERSION,
            "seed": _ENGINE_SEED,
            "initialized": self._initialized,
            "registry": self._registry.checkpoint(),
            "memory": self._memory.checkpoint(),
            "events": [e.to_dict() for e in self.get_events()],
        }

    def terminate(self) -> None:
        """Release all resources and mark the engine as terminated."""
        self._emit_event("terminate")
        self._initialized = False
        logger.info("RuntimeEngine terminated")


__all__ = ["EngineInitializationError", "RuntimeEngine"]
