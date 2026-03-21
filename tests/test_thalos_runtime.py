"""Tests for thalos_runtime: engine, registry, executor, memory, plugins, CLI, API."""

from __future__ import annotations

import json
from typing import Any

import pytest

from thalos_runtime.core.engine import EngineInitializationError, RuntimeEngine
from thalos_runtime.core.executor import ExecutionError, TaskExecutor
from thalos_runtime.core.memory import ExecutionMemory, ExecutionRecord
from thalos_runtime.core.registry import RegistryError, TaskHandler, TaskRegistry
from thalos_runtime.plugins.legacy_adapter import LegacyAdapter, LegacyPlugin
from thalos_runtime.plugins.loader import PluginInterface, PluginLoader, PluginLoadError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class EchoHandler:
    """Task handler that echoes the payload back as the result."""

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the payload unchanged."""
        return payload


class FailingHandler:
    """Task handler that always raises ValueError."""

    def run(self, payload: dict[str, Any]) -> Any:
        """Raise ValueError unconditionally."""
        raise ValueError("intentional failure")


# ---------------------------------------------------------------------------
# TaskRegistry
# ---------------------------------------------------------------------------


class TestTaskRegistry:
    """Tests for thalos_runtime.core.registry.TaskRegistry."""

    def test_register_and_get(self) -> None:
        """Registered handler is retrievable by name."""
        registry = TaskRegistry()
        handler = EchoHandler()
        registry.register("echo", handler)
        assert registry.get("echo") is handler

    def test_register_duplicate_raises(self) -> None:
        """Registering the same name twice raises RegistryError."""
        registry = TaskRegistry()
        registry.register("echo", EchoHandler())
        with pytest.raises(RegistryError) as exc_info:
            registry.register("echo", EchoHandler())
        assert exc_info.value.task == "echo"
        assert "already registered" in exc_info.value.reason

    def test_get_missing_raises(self) -> None:
        """Getting an unregistered name raises RegistryError."""
        registry = TaskRegistry()
        with pytest.raises(RegistryError) as exc_info:
            registry.get("missing")
        assert exc_info.value.task == "missing"
        assert "no handler registered" in exc_info.value.reason

    def test_names_sorted(self) -> None:
        """names() returns alphabetically sorted task names."""
        registry = TaskRegistry()
        registry.register("zebra", EchoHandler())
        registry.register("alpha", EchoHandler())
        assert registry.names() == ["alpha", "zebra"]

    def test_checkpoint(self) -> None:
        """checkpoint() returns dict with registered_tasks list."""
        registry = TaskRegistry()
        registry.register("t1", EchoHandler())
        cp = registry.checkpoint()
        assert cp["registered_tasks"] == ["t1"]

    def test_task_handler_protocol(self) -> None:
        """EchoHandler satisfies the TaskHandler runtime_checkable protocol."""
        assert isinstance(EchoHandler(), TaskHandler)


# ---------------------------------------------------------------------------
# ExecutionMemory
# ---------------------------------------------------------------------------


class TestExecutionMemory:
    """Tests for thalos_runtime.core.memory.ExecutionMemory."""

    def test_store_and_get_all(self) -> None:
        """Stored records are returned by get_all()."""
        mem = ExecutionMemory()
        record = mem.store("echo", {"k": "v"}, {"result": 1})
        assert isinstance(record, ExecutionRecord)
        assert record.task == "echo"
        all_records = mem.get_all()
        assert len(all_records) == 1
        assert all_records[0] is record

    def test_get_by_task_filters(self) -> None:
        """get_by_task() returns only matching records."""
        mem = ExecutionMemory()
        mem.store("echo", {}, "a")
        mem.store("other", {}, "b")
        mem.store("echo", {}, "c")
        echo_records = mem.get_by_task("echo")
        assert len(echo_records) == 2
        other_records = mem.get_by_task("other")
        assert len(other_records) == 1

    def test_get_all_returns_copy(self) -> None:
        """get_all() returns a copy; mutation does not affect internal state."""
        mem = ExecutionMemory()
        mem.store("t", {}, 1)
        copy = mem.get_all()
        copy.clear()
        assert len(mem.get_all()) == 1

    def test_checkpoint_structure(self) -> None:
        """checkpoint() returns versioned dict with records list."""
        mem = ExecutionMemory()
        mem.store("t", {"x": 1}, "res")
        cp = mem.checkpoint()
        assert cp["version"] == "1.0"
        assert len(cp["records"]) == 1
        rec = cp["records"][0]
        assert rec["task"] == "t"
        assert rec["result"] == "res"

    def test_record_immutable(self) -> None:
        """ExecutionRecord is frozen (immutable dataclass)."""
        mem = ExecutionMemory()
        record = mem.store("t", {}, 42)
        with pytest.raises((AttributeError, TypeError)):
            record.task = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TaskExecutor
# ---------------------------------------------------------------------------


class TestTaskExecutor:
    """Tests for thalos_runtime.core.executor.TaskExecutor."""

    def test_execute_returns_handler_result(self) -> None:
        """Executor returns whatever the handler's run() returns."""
        registry = TaskRegistry()
        registry.register("echo", EchoHandler())
        executor = TaskExecutor(registry)
        result = executor.execute("echo", {"x": 1})
        assert result == {"x": 1}

    def test_execute_missing_task_raises_registry_error(self) -> None:
        """Executing an unregistered task raises RegistryError."""
        registry = TaskRegistry()
        executor = TaskExecutor(registry)
        with pytest.raises(RegistryError):
            executor.execute("missing", {})

    def test_execute_handler_failure_raises_execution_error(self) -> None:
        """A handler exception is wrapped as ExecutionError."""
        registry = TaskRegistry()
        registry.register("fail", FailingHandler())
        executor = TaskExecutor(registry)
        with pytest.raises(ExecutionError) as exc_info:
            executor.execute("fail", {})
        assert exc_info.value.task == "fail"
        assert isinstance(exc_info.value.cause, ValueError)


# ---------------------------------------------------------------------------
# RuntimeEngine
# ---------------------------------------------------------------------------


class TestRuntimeEngine:
    """Tests for thalos_runtime.core.engine.RuntimeEngine."""

    def test_register_and_execute(self) -> None:
        """Engine registers a module and executes it successfully."""
        engine = RuntimeEngine()
        engine.register_module("echo", EchoHandler())
        engine.initialize()
        result = engine.execute("echo", {"hello": "world"})
        assert result == {"hello": "world"}

    def test_result_stored_in_memory(self) -> None:
        """Execute stores the result in memory."""
        engine = RuntimeEngine()
        engine.register_module("echo", EchoHandler())
        engine.initialize()
        engine.execute("echo", {"k": "v"})
        # Access memory via engine's checkpoint
        cp = engine.checkpoint()
        memory = cp["memory"]
        assert isinstance(memory, dict)
        records = memory["records"]
        assert len(records) == 1
        assert records[0]["task"] == "echo"

    def test_validate_before_initialize(self) -> None:
        """validate() returns invalid result before initialize() is called."""
        engine = RuntimeEngine()
        result = engine.validate()
        assert not result.valid

    def test_validate_after_initialize(self) -> None:
        """validate() returns valid result after initialize() is called."""
        engine = RuntimeEngine()
        engine.initialize()
        result = engine.validate()
        assert result.valid

    def test_task_names(self) -> None:
        """task_names() returns sorted list of registered task names."""
        engine = RuntimeEngine()
        engine.register_module("z", EchoHandler())
        engine.register_module("a", EchoHandler())
        assert engine.task_names() == ["a", "z"]

    def test_checkpoint_versioned(self) -> None:
        """checkpoint() returns versioned dict with seed and initialized flag."""
        engine = RuntimeEngine()
        engine.initialize()
        cp = engine.checkpoint()
        assert cp["version"] == "1.0"
        assert cp["seed"] == 42
        assert cp["initialized"] is True

    def test_terminate_marks_uninitialized(self) -> None:
        """terminate() marks the engine as not initialized."""
        engine = RuntimeEngine()
        engine.initialize()
        assert engine._initialized is True
        engine.terminate()
        assert engine._initialized is False

    def test_operate_does_not_raise(self) -> None:
        """operate() is a no-op and does not raise."""
        engine = RuntimeEngine()
        engine.initialize()
        engine.operate()  # must not raise

    def test_reconcile_does_not_raise(self) -> None:
        """reconcile() logs state and does not raise."""
        engine = RuntimeEngine()
        engine.initialize()
        engine.reconcile()  # must not raise

    def test_lifecycle_events_recorded(self) -> None:
        """Lifecycle method calls are recorded as events."""
        engine = RuntimeEngine()
        engine.initialize()
        engine.validate()
        events = engine.get_events()
        method_names = [e.method for e in events]
        assert "initialize" in method_names
        assert "validate" in method_names

    def test_engine_initialization_error_message(self) -> None:
        """EngineInitializationError message contains reason."""
        exc = EngineInitializationError("missing dependency")
        assert "missing dependency" in str(exc)
        assert exc.reason == "missing dependency"


# ---------------------------------------------------------------------------
# LegacyAdapter
# ---------------------------------------------------------------------------


class TestLegacyAdapter:
    """Tests for thalos_runtime.plugins.legacy_adapter.LegacyAdapter."""

    def test_run_returns_dict(self) -> None:
        """run() returns a dict from deep_synthesis."""
        adapter = LegacyAdapter()
        result = adapter.run({"query": "test"})
        assert isinstance(result, dict)

    def test_run_default_query(self) -> None:
        """run() with empty payload uses default query and succeeds."""
        adapter = LegacyAdapter()
        result = adapter.run({})
        assert isinstance(result, dict)

    def test_run_has_nexus_result(self) -> None:
        """deep_synthesis result contains 'nexus_result' key."""
        adapter = LegacyAdapter()
        result = adapter.run({"query": "hello"})
        assert "nexus_result" in result

    def test_legacy_plugin_name(self) -> None:
        """LegacyPlugin.name returns 'legacy'."""
        plugin = LegacyPlugin()
        assert plugin.name == "legacy"

    def test_legacy_plugin_registers_handler(self) -> None:
        """LegacyPlugin.register() wires LegacyAdapter into the engine."""
        engine = RuntimeEngine()
        plugin = LegacyPlugin()
        plugin.register(engine)
        assert "legacy" in engine.task_names()

    def test_legacy_plugin_satisfies_protocol(self) -> None:
        """LegacyPlugin satisfies the PluginInterface runtime_checkable protocol."""
        plugin = LegacyPlugin()
        assert isinstance(plugin, PluginInterface)


# ---------------------------------------------------------------------------
# PluginLoader
# ---------------------------------------------------------------------------


class TestPluginLoader:
    """Tests for thalos_runtime.plugins.loader.PluginLoader."""

    def test_discover_and_register_legacy(self) -> None:
        """discover_and_register() always registers the legacy plugin."""
        engine = RuntimeEngine()
        loader = PluginLoader()
        registered = loader.discover_and_register(engine)
        assert "legacy" in registered

    def test_loaded_plugins_after_discovery(self) -> None:
        """loaded_plugins() reflects successfully registered plugins."""
        engine = RuntimeEngine()
        loader = PluginLoader()
        loader.discover_and_register(engine)
        assert "legacy" in loader.loaded_plugins()

    def test_plugins_registered_in_engine(self) -> None:
        """Engine can execute a task after discover_and_register."""
        engine = RuntimeEngine()
        loader = PluginLoader()
        loader.discover_and_register(engine)
        engine.initialize()
        result = engine.execute("legacy", {"query": "loader test"})
        assert isinstance(result, dict)

    def test_plugin_load_error_message(self) -> None:
        """PluginLoadError message contains plugin ref and cause."""
        cause = RuntimeError("bad plugin")
        exc = PluginLoadError("my_group:my_plugin", cause)
        assert "my_group:my_plugin" in str(exc)
        assert exc.plugin_ref == "my_group:my_plugin"
        assert exc.cause is cause


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for thalos_runtime.cli.main."""

    def test_main_executes_legacy_task(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CLI main() with --task legacy exits 0 and prints JSON."""
        from thalos_runtime.cli.main import main

        exit_code = main(["--task", "legacy"])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "nexus_result" in data

    def test_main_invalid_json_data(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CLI main() with invalid --data exits 1 and prints error."""
        from thalos_runtime.cli.main import main

        exit_code = main(["--task", "legacy", "--data", "not-json"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.err

    def test_main_unknown_task(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CLI main() with unknown task exits 1 and prints error."""
        from thalos_runtime.cli.main import main

        exit_code = main(["--task", "nonexistent"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err


# ---------------------------------------------------------------------------
# API Server
# ---------------------------------------------------------------------------


class TestAPIServer:
    """Tests for thalos_runtime.api.server."""

    def test_execute_legacy_task(self) -> None:
        """POST /execute with legacy task returns 200 and result."""
        from fastapi.testclient import TestClient

        from thalos_runtime.api.server import app

        with TestClient(app) as client:
            resp = client.post(
                "/execute",
                json={"task": "legacy", "payload": {"query": "api test"}},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["task"] == "legacy"
        assert "nexus_result" in body["result"]

    def test_execute_missing_task_returns_404(self) -> None:
        """POST /execute with unknown task returns 404."""
        from fastapi.testclient import TestClient

        from thalos_runtime.api.server import app

        with TestClient(app) as client:
            resp = client.post(
                "/execute",
                json={"task": "does_not_exist", "payload": {}},
            )
        assert resp.status_code == 404

    def test_health_endpoint(self) -> None:
        """GET /health returns 200 with status=ok and tasks list."""
        from fastapi.testclient import TestClient

        from thalos_runtime.api.server import app

        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "legacy" in body["tasks"]

    def test_execute_default_payload(self) -> None:
        """POST /execute without explicit payload uses empty dict."""
        from fastapi.testclient import TestClient

        from thalos_runtime.api.server import app

        with TestClient(app) as client:
            resp = client.post("/execute", json={"task": "legacy"})
        assert resp.status_code == 200
