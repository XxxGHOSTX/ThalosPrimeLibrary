"""Execution IR package — graph-native execution substrate for Thalos Prime."""

from __future__ import annotations

from thalos_prime.execution_ir.builder import GraphBuilder
from thalos_prime.execution_ir.executor import DeterministicExecutor, NodeOperator
from thalos_prime.execution_ir.graph import ExecutionGraph
from thalos_prime.execution_ir.hash import hash_dict, sha256_hex, stable_json
from thalos_prime.execution_ir.node import (
    ExecutionNode,
    FailureMode,
    NodeKind,
    NodeStatus,
)
from thalos_prime.execution_ir.planner import ExecutionPlanner
from thalos_prime.execution_ir.signature import get_env_signature

__all__ = [
    "DeterministicExecutor",
    "ExecutionGraph",
    "ExecutionNode",
    "ExecutionPlanner",
    "FailureMode",
    "GraphBuilder",
    "NodeKind",
    "NodeOperator",
    "NodeStatus",
    "get_env_signature",
    "hash_dict",
    "sha256_hex",
    "stable_json",
]
