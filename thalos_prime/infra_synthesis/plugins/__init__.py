"""Plugins sub-package for infra-synthesis."""

from __future__ import annotations

from thalos_prime.infra_synthesis.plugins.interface import InfraSynthesisPlugin
from thalos_prime.infra_synthesis.plugins.loader import PluginLoader

__all__ = ["InfraSynthesisPlugin", "PluginLoader"]
