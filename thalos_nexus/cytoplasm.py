"""Thalos NEXUS — Cytoplasm: tool registry envelopes.

Provides ``ToolEnvelope`` (a descriptor for a local executable) and
``ToolRegistry`` (a lookup/execute registry).

All subprocess calls use list form and ``check=False`` to remain compatible
with Windows 10 Home.

Control Plane boundary: tool registration and dispatch only; no gate logic.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# ToolEnvelope
# ---------------------------------------------------------------------------


@dataclass
class ToolEnvelope:
    """Descriptor for a locally available command-line tool.

    Attributes
    ----------
    name:
        Registry key for this tool (must be unique within a ``ToolRegistry``).
    command:
        Executable name or path (e.g. ``"ruff"``, ``"python"``).
    default_args:
        Default argument list prepended to every invocation.
    description:
        Human-readable description of what the tool does.

    """

    name: str
    command: str
    default_args: list[str] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


class ToolNotFoundError(KeyError):
    """Raised when a requested tool is not registered."""


class ToolRegistry:
    """Registry for local tool envelopes.

    Tools are registered by name and can be looked up and executed.

    Examples
    --------
    >>> reg = ToolRegistry()
    >>> reg.register(ToolEnvelope(name="ruff", command="ruff", default_args=["check"]))
    >>> result = reg.execute("ruff", extra_args=["thalos_nexus/"])

    """

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._tools: dict[str, ToolEnvelope] = {}

    def register(self, tool: ToolEnvelope) -> None:
        """Register a tool envelope under ``tool.name``.

        Overwrites any existing registration for the same name.

        Parameters
        ----------
        tool:
            The tool envelope to register.

        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolEnvelope:
        """Return the registered ``ToolEnvelope`` for *name*.

        Parameters
        ----------
        name:
            Registry key.

        Returns
        -------
        ToolEnvelope
            The registered envelope.

        Raises
        ------
        ToolNotFoundError
            If no tool is registered under *name*.

        """
        try:
            return self._tools[name]
        except KeyError as exc:
            available = sorted(self._tools)
            msg = f"Tool '{name}' is not registered. Available: {available}"
            raise ToolNotFoundError(msg) from exc

    def execute(
        self,
        name: str,
        extra_args: list[str] | None = None,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Execute a registered tool and return the completed process.

        Parameters
        ----------
        name:
            Registry key of the tool to execute.
        extra_args:
            Additional arguments appended after ``default_args``.
        cwd:
            Working directory for the subprocess.
        timeout:
            Subprocess timeout in seconds.  ``None`` means no timeout.

        Returns
        -------
        subprocess.CompletedProcess[str]
            The completed process result.

        Raises
        ------
        ToolNotFoundError
            If no tool is registered under *name*.
        subprocess.TimeoutExpired
            If the subprocess exceeds *timeout* seconds.

        """
        tool = self.get(name)
        cmd = [tool.command, *tool.default_args, *(extra_args or [])]
        return subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=timeout,
        )

    def list_tools(self) -> list[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._tools)
