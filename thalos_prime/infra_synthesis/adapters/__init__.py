"""Infra-synthesis adapter package.

Each adapter translates a validated schema dict into one or more provider
artifact files.  All adapters expose a single ``generate(schema, out_dir)``
method that returns the list of :class:`pathlib.Path` objects written.
"""

from __future__ import annotations

from thalos_prime.infra_synthesis.adapters.cloudflare import CloudflareAdapter
from thalos_prime.infra_synthesis.adapters.docker import DockerAdapter
from thalos_prime.infra_synthesis.adapters.github_actions import GitHubActionsAdapter
from thalos_prime.infra_synthesis.adapters.opentofu import OpenTofuAdapter
from thalos_prime.infra_synthesis.adapters.terraform import TerraformAdapter

__all__ = [
    "CloudflareAdapter",
    "DockerAdapter",
    "GitHubActionsAdapter",
    "OpenTofuAdapter",
    "TerraformAdapter",
]
