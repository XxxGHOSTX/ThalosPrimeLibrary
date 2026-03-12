"""Plugin loader for infra-synthesis.

Auto-discovers plugins registered under the ``thalos.infra_synthesis.plugins``
entry-point group and calls their ``register(engine)`` method.

Control Plane: plugin lifecycle discovery and wiring.
"""

from __future__ import annotations

import importlib.metadata
import logging
from typing import TYPE_CHECKING

from thalos_prime.infra_synthesis.plugins.interface import InfraSynthesisPlugin

if TYPE_CHECKING:
    from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine

logger = logging.getLogger(__name__)

_ENTRY_POINT_GROUP = "thalos.infra_synthesis.plugins"


class PluginLoader:
    """Discovers and loads external infra-synthesis plugins.

    Plugins must be installed Python packages that declare an entry point
    in the ``thalos.infra_synthesis.plugins`` group pointing to a class
    that subclasses :class:`InfraSynthesisPlugin`.
    """

    def load_plugins(self, engine: InfraSynthesisEngine) -> list[InfraSynthesisPlugin]:
        """Discover all registered plugins and call ``register(engine)`` on each.

        Args:
            engine: The active ``InfraSynthesisEngine`` instance.

        Returns:
            List of successfully loaded plugin instances.

        """
        loaded: list[InfraSynthesisPlugin] = []
        eps = importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP)
        for ep in eps:
            try:
                plugin_cls = ep.load()
                if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, InfraSynthesisPlugin)):
                    logger.warning(
                        "PluginLoader: entry point '%s' is not an InfraSynthesisPlugin subclass; skipping",
                        ep.name,
                    )
                    continue
                plugin: InfraSynthesisPlugin = plugin_cls()
                plugin.register(engine)
                loaded.append(plugin)
                logger.info("PluginLoader: loaded plugin '%s'", plugin.name)
            except (ImportError, TypeError, AttributeError, RuntimeError) as exc:
                logger.exception(
                    "PluginLoader: failed to load entry point '%s'", ep.name
                )
                msg = f"Plugin '{ep.name}' failed to load"
                raise RuntimeError(msg) from exc

        logger.info("PluginLoader: %d plugin(s) loaded", len(loaded))
        return loaded


__all__ = ["PluginLoader"]
