"""Thalos Prime NEXUS Core v1 — Lysosome Package.

Windows isolation adapter sub-package.
"""

from __future__ import annotations

from thalos_nexus.lysosome.windows_adapter import (
    IsolationAdapter,
    IsolationConfig,
    IsolationResult,
    WindowsRequiredError,
)

__all__: list[str] = [
    "IsolationAdapter",
    "IsolationConfig",
    "IsolationResult",
    "WindowsRequiredError",
]
