"""Model Context Protocol adapter for Thalos Prime.

The MCP package is an integration boundary. Authoritative epistemic state and
logic remain in :mod:`thalos_prime.epistemic_core`.
"""

from thalos_prime.mcp.server import ThalosMcpRuntime, create_mcp_server

__all__ = ["ThalosMcpRuntime", "create_mcp_server"]
