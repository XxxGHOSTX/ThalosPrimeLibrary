"""Versioned capability/module registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    version: str
    handler: Callable[..., Any]
    capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.name}:{self.version}"


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, dict[str, ModuleSpec]] = {}
        self._active: dict[str, str] = {}

    def register(self, spec: ModuleSpec, activate: bool = False) -> None:
        versions = self._modules.setdefault(spec.name, {})
        if spec.version in versions:
            raise ValueError(f"module already registered: {spec.key}")
        versions[spec.version] = spec
        if activate or spec.name not in self._active:
            self._active[spec.name] = spec.version

    def get(self, name: str, version: str | None = None) -> ModuleSpec:
        selected = version or self._active[name]
        return self._modules[name][selected]

    def versions(self, name: str) -> list[str]:
        return sorted(self._modules.get(name, {}))

    def activate(self, name: str, version: str) -> None:
        self.get(name, version)
        self._active[name] = version

    def active_version(self, name: str) -> str:
        return self._active[name]

    def snapshot(self) -> dict[str, Any]:
        return {
            "modules": {
                name: self.versions(name) for name in sorted(self._modules)
            },
            "active": dict(sorted(self._active.items())),
        }
