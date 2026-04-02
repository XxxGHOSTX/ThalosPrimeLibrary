"""Thalos Runtime - Production runtime system for ThalosPrimeLibrary.

Control Plane / Data Plane separation:
- Control Plane:  RuntimeEngine, TaskRegistry, PluginLoader
- Data Plane:     TaskExecutor, ExecutionMemory, task handlers

Lifecycle order (RuntimeEngine):
    register_module() → initialize() → validate() → operate()
    → reconcile() → checkpoint() → terminate()

Plugin system:
    PluginLoader.discover_and_register(engine) wires all built-in
    and entry-point plugins before initialize() is called.

Version:
    1.0
"""

from __future__ import annotations

from thalos_runtime.core.engine import EngineInitializationError, RuntimeEngine
from thalos_runtime.core.executor import ExecutionError, TaskExecutor
from thalos_runtime.core.memory import ExecutionMemory, ExecutionRecord
from thalos_runtime.core.registry import RegistryError, TaskHandler, TaskRegistry
from thalos_runtime.plugins.loader import PluginInterface, PluginLoader, PluginLoadError

__all__ = [
    "EngineInitializationError",
    "ExecutionError",
    "ExecutionMemory",
    "ExecutionRecord",
    "PluginInterface",
    "PluginLoadError",
    "PluginLoader",
    "RegistryError",
    "RuntimeEngine",
    "TaskExecutor",
    "TaskHandler",
    "TaskRegistry",
]

_RUNTIME_VERSION: str = "1.0"
