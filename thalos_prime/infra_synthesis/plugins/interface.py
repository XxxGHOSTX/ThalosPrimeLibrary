"""Plugin interface for infra-synthesis.

External plugins must implement :class:`InfraSynthesisPlugin` and call
``engine.register_plugin(plugin)`` (or use the ``register`` entry point).

Data Plane: plugin interface definition only.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from thalos_prime.infra_synthesis.engine import InfraSynthesisEngine


class InfraSynthesisPlugin(abc.ABC):
    """Abstract base class for infra-synthesis plugins.

    External packages expose plugins by registering subclasses under the
    ``thalos.infra_synthesis.plugins`` entry-point group.

    Each plugin receives the engine instance at load time so it can
    register additional adapters, event handlers, or policy rules.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique name for this plugin.

        Returns:
            String identifier (e.g. ``"my_org.custom_adapter"``).

        """

    @abc.abstractmethod
    def register(self, engine: InfraSynthesisEngine) -> None:
        """Wire this plugin into *engine*.

        Called once by the plugin loader at startup.  Implementations
        should attach adapters, event handlers, or policy rules here.

        Args:
            engine: The active :class:`InfraSynthesisEngine` instance.

        """

    def metadata(self) -> dict[str, Any]:
        """Return optional plugin metadata for observability.

        Returns:
            Arbitrary dict (defaults to ``{"name": self.name}``).

        """
        return {"name": self.name}


__all__ = ["InfraSynthesisPlugin"]
