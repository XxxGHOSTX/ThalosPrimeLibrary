"""Plugin loader for thalos_runtime.

Auto-discovers and registers plugins using a deterministic two-phase process:

Phase 1 - Built-in plugins:
    LegacyPlugin is always registered.  Ordering is alphabetical by name.

Phase 2 - External entry-point plugins:
    Discovered from the ``thalos_runtime.plugins`` importlib.metadata
    entry-point group.  Each must implement the PluginInterface protocol.
    Discovery is deterministic: plugins are sorted by name before
    registration to guarantee reproducible ordering.

Control Plane boundary: manages plugin lifecycle and engine wiring only.
No computational work is performed by the loader itself.

State surfaces:
- _loaded: list of successfully registered PluginInterface instances.

Event log:
    INFO  PluginLoader: discovered external plugin '{name}'
    INFO  PluginLoader: registered plugin '{name}'
    INFO  PluginLoader: discovery complete; N plugin(s) registered: [...]
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from thalos_runtime.core.engine import RuntimeEngine

logger = logging.getLogger(__name__)

_ENTRY_POINT_GROUP: str = "thalos_runtime.plugins"


@runtime_checkable
class PluginInterface(Protocol):
    """Protocol for all thalos_runtime plugins.

    Implementations must provide a unique ``name`` property and a
    ``register()`` method that wires the plugin's task handlers into
    the RuntimeEngine.
    """

    @property
    def name(self) -> str:
        """Unique, stable plugin identifier (e.g. ``"legacy"``)."""
        ...

    def register(self, engine: RuntimeEngine) -> None:
        """Register all plugin task handlers with the engine.

        Args:
            engine: RuntimeEngine to wire task handlers into.
        """
        ...


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded or fails protocol validation.

    Attributes:
        plugin_ref: String reference to the plugin that failed.
        cause: Underlying exception that triggered this error.
    """

    def __init__(self, plugin_ref: str, cause: Exception) -> None:
        """Initialize with a plugin reference and cause.

        Args:
            plugin_ref: Plugin name or entry-point reference string.
            cause: Underlying exception.
        """
        super().__init__(f"Failed to load plugin '{plugin_ref}': {cause}")
        self.plugin_ref = plugin_ref
        self.cause = cause


class PluginLoader:
    """Discovers and registers thalos_runtime plugins with the RuntimeEngine.

    Control Plane component: manages plugin registration lifecycle.
    Built-in plugins are always registered first; external plugins are
    discovered via importlib.metadata entry points and registered in
    alphabetical order to guarantee deterministic behavior.
    """

    def __init__(self) -> None:
        """Initialize an empty plugin loader."""
        self._loaded: list[PluginInterface] = []
        logger.debug("PluginLoader initialized")

    def _load_builtin_plugins(self) -> list[PluginInterface]:
        """Return instantiated built-in plugin objects.

        Returns:
            List of built-in runtime task plugins.
        """
        from thalos_runtime.plugins.babel_decode_task import BabelDecodeTaskPlugin
        from thalos_runtime.plugins.babel_enumerate_task import BabelEnumerateTaskPlugin
        from thalos_runtime.plugins.babel_generate_task import BabelGenerateTaskPlugin
        from thalos_runtime.plugins.chat_high_coherence_task import ChatHighCoherenceTaskPlugin
        from thalos_runtime.plugins.chat_task import ChatTaskPlugin
        from thalos_runtime.plugins.legacy_adapter import LegacyPlugin
        from thalos_runtime.plugins.search_task import SearchTaskPlugin

        return [
            LegacyPlugin(),
            ChatTaskPlugin(),
            ChatHighCoherenceTaskPlugin(),
            SearchTaskPlugin(),
            BabelGenerateTaskPlugin(),
            BabelEnumerateTaskPlugin(),
            BabelDecodeTaskPlugin(),
        ]

    def _load_entrypoint_plugins(self) -> list[PluginInterface]:
        """Discover and instantiate external plugins from entry points.

        Returns:
            List of PluginInterface instances from the entry-point group,
            sorted by entry-point name for deterministic ordering.

        Raises:
            PluginLoadError: If any discovered plugin fails to load or
                does not implement PluginInterface.
        """
        discovered: list[PluginInterface] = []
        eps = sorted(entry_points(group=_ENTRY_POINT_GROUP), key=lambda e: e.name)
        for ep in eps:
            ref = f"{ep.group}:{ep.name}"
            try:
                plugin_class: type[Any] = ep.load()
                plugin: Any = plugin_class()
                if not isinstance(plugin, PluginInterface):
                    raise TypeError(
                        f"Plugin '{ep.name}' does not implement PluginInterface "
                        f"(missing 'name' property or 'register' method)"
                    )
                discovered.append(plugin)
                logger.info("PluginLoader: discovered external plugin '%s'", ep.name)
            except Exception as exc:
                raise PluginLoadError(ref, exc) from exc
        return discovered

    def discover_and_register(self, engine: RuntimeEngine) -> list[str]:
        """Discover all plugins and register them with the engine.

        Runs the two-phase discovery (built-in + entry-point) and
        registers all plugins in alphabetical order by name.

        Args:
            engine: RuntimeEngine to register plugins into.

        Returns:
            Sorted list of successfully registered plugin names.

        Raises:
            PluginLoadError: If any external plugin fails to load.
        """
        all_plugins = sorted(
            self._load_builtin_plugins() + self._load_entrypoint_plugins(),
            key=lambda p: p.name,
        )
        registered: list[str] = []
        for plugin in all_plugins:
            plugin.register(engine)
            self._loaded.append(plugin)
            registered.append(plugin.name)
            logger.info("PluginLoader: registered plugin '%s'", plugin.name)
        logger.info(
            "PluginLoader: discovery complete; %d plugin(s) registered: %s",
            len(registered),
            registered,
        )
        return registered

    def loaded_plugins(self) -> list[str]:
        """Return names of all successfully loaded plugins.

        Returns:
            Sorted list of loaded plugin names.
        """
        return sorted(p.name for p in self._loaded)

    def get_graph_transformer(self) -> Any:
        """Build a GraphTransformer from plugins that expose a transform() method.

        Iterates over all loaded plugins and wraps any plugin that has a
        ``transform(graph)`` callable as a RewriteRule added to a
        GraphTransformer.

        Returns:
            GraphTransformer containing rules derived from eligible plugins.
        """
        from thalos_prime.rewrite.dsl import RewriteRule
        from thalos_prime.rewrite.engine import GraphTransformer

        transformer = GraphTransformer()
        for plugin in self._loaded:
            transform_fn: Any = getattr(plugin, "transform", None)
            if callable(transform_fn):

                def _make_rule(fn: Any, name: str) -> RewriteRule:
                    return RewriteRule(
                        name=name,
                        match_fn=lambda _g: True,
                        transform_fn=fn,
                        version="1.0",
                    )

                transformer.add_rule(_make_rule(transform_fn, f"{plugin.name}.transform"))
        return transformer


__all__ = ["PluginInterface", "PluginLoadError", "PluginLoader"]
