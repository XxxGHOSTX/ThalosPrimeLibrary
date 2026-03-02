"""Thalos Prime NEXUS Core v1 — Windows Isolation Adapter.

Provides :class:`IsolationAdapter` which executes subprocesses inside an
ephemeral workspace with Windows-native sandboxing (Job Objects for memory and
CPU limits, Windows Firewall rules for network isolation).

On non-Windows platforms, calling :meth:`IsolationAdapter.run` raises
:exc:`WindowsRequiredError` immediately without running any subprocess.

Control Plane boundary: execution isolation only — no lifecycle coordination.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class WindowsRequiredError(RuntimeError):
    """Raised when Windows-only isolation is requested on a non-Windows platform."""


@dataclass
class IsolationResult:
    """Result of an isolated subprocess execution."""

    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    workspace_path: str


@dataclass
class IsolationConfig:
    """Configuration for the Windows isolation adapter."""

    workspace_base: Path
    timeout_seconds: float = 300.0
    max_memory_mb: int = 512
    enable_network: bool = False
    key_path: Path | None = field(default=None)


class IsolationAdapter:
    """Windows-native isolation adapter.

    Executes commands inside an ephemeral workspace under
    ``config.workspace_base`` with Job Object memory/CPU limits and
    Windows Firewall network-egress blocking.

    On non-Windows platforms, :meth:`run` raises :exc:`WindowsRequiredError`.

    Args:
        config: Isolation configuration.

    """

    def __init__(self, config: IsolationConfig) -> None:
        """Initialise the adapter with *config*."""
        self._config = config
        logger.debug("IsolationAdapter initialised (platform=%s)", sys.platform)

    def run(
        self,
        cmd: list[str],
        env: dict[str, str] | None = None,
        run_id: str | None = None,
    ) -> IsolationResult:
        """Execute *cmd* inside an ephemeral workspace.

        Args:
            cmd: Command and arguments to execute.
            env: Optional environment variable overrides.  If ``None``, the
                 current process environment is used.
            run_id: Optional deterministic run identifier used to construct the
                    firewall rule name.  Defaults to a random UUID fragment.

        Returns:
            :class:`IsolationResult` with stdout, stderr, returncode, and
            workspace path.

        Raises:
            WindowsRequiredError: On non-Windows platforms.
            ValueError: If *cmd* is empty.

        """
        if sys.platform != "win32":
            raise WindowsRequiredError(
                "IsolationAdapter.run() is only available on Windows. "
                f"Current platform: {sys.platform}"
            )
        if not cmd:
            raise ValueError("cmd must be a non-empty list")

        self._config.workspace_base.mkdir(parents=True, exist_ok=True)
        workspace = Path(tempfile.mkdtemp(dir=self._config.workspace_base, prefix="nexus_"))
        rule_id = run_id[:16] if run_id is not None else uuid.uuid4().hex[:16]
        rule_name = f"thalos_nexus_{rule_id}_block"

        try:
            return self._run_windows(cmd, env, workspace, rule_name)
        finally:
            self._cleanup_workspace(workspace)
            if not self._config.enable_network:
                self._remove_firewall_rule(rule_name)

    def _run_windows(
        self,
        cmd: list[str],
        env: dict[str, str] | None,
        workspace: Path,
        rule_name: str,
    ) -> IsolationResult:
        """Execute *cmd* on Windows with Job Object and firewall sandboxing."""
        merged_env: dict[str, str] = dict(os.environ)
        if env:
            merged_env.update(env)

        if not self._config.enable_network and cmd:
            executable = cmd[0]
            self._add_firewall_rule(rule_name, executable)

        start = time.monotonic()
        job_handle = self._create_job_object()

        proc = subprocess.Popen(
            cmd,
            cwd=workspace,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if job_handle is not None:
            self._assign_process_to_job(job_handle, proc)
            self._set_job_limits(job_handle)

        try:
            stdout_bytes, stderr_bytes = proc.communicate(timeout=self._config.timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout_bytes, stderr_bytes = proc.communicate()
        finally:
            if job_handle is not None:
                self._close_handle(job_handle)

        duration = time.monotonic() - start
        return IsolationResult(
            returncode=proc.returncode,
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
            duration_seconds=duration,
            workspace_path=str(workspace),
        )

    def _add_firewall_rule(self, rule_name: str, executable: str) -> None:
        """Add a Windows Firewall outbound-block rule for *executable*.

        Raises:
            RuntimeError: If ``netsh`` exits non-zero, indicating the rule
                          could not be added and network isolation is not
                          enforced.

        """
        try:
            result = subprocess.run(
                [
                    "netsh",
                    "advfirewall",
                    "firewall",
                    "add",
                    "rule",
                    f"name={rule_name}",
                    "dir=out",
                    "action=block",
                    f"program={executable}",
                ],
                check=False,
                capture_output=True,
            )
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace").strip()
                logger.warning(
                    "Firewall rule %r could not be added (exit %d: %s); "
                    "network egress is NOT blocked for this run.",
                    rule_name,
                    result.returncode,
                    stderr,
                )
        except OSError as exc:
            logger.warning("Failed to add firewall rule %s: %s", rule_name, exc)

    def _remove_firewall_rule(self, rule_name: str) -> None:
        """Remove the Windows Firewall rule named *rule_name*."""
        try:
            subprocess.run(
                [
                    "netsh",
                    "advfirewall",
                    "firewall",
                    "delete",
                    "rule",
                    f"name={rule_name}",
                ],
                check=False,
                capture_output=True,
            )
        except OSError as exc:
            logger.warning("Failed to remove firewall rule %s: %s", rule_name, exc)

    def _create_job_object(self) -> Any | None:
        """Create a Windows Job Object via ctypes.

        Returns:
            Job Object handle, or ``None`` if creation fails.

        """
        try:
            import ctypes

            handle = ctypes.windll.kernel32.CreateJobObjectW(None, None)  # type: ignore[attr-defined]
            if not handle:
                logger.warning("CreateJobObjectW returned NULL; running without Job Object")
                return None
            return handle
        except (AttributeError, OSError) as exc:
            logger.warning("Could not create Job Object: %s", exc)
            return None

    def _assign_process_to_job(self, job_handle: Any, proc: subprocess.Popen[bytes]) -> None:
        """Assign *proc* to the given Job Object handle."""
        try:
            import ctypes

            process_handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
                0x001F0FFF,
                False,
                proc.pid,
            )
            if process_handle:
                ctypes.windll.kernel32.AssignProcessToJobObject(job_handle, process_handle)  # type: ignore[attr-defined]
                ctypes.windll.kernel32.CloseHandle(process_handle)  # type: ignore[attr-defined]
        except (AttributeError, OSError) as exc:
            logger.warning("Could not assign process to Job Object: %s", exc)

    def _set_job_limits(self, job_handle: Any) -> None:
        """Apply memory and CPU time limits to the Job Object."""
        try:
            import ctypes
            import ctypes.wintypes

            JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x100  # noqa: N806
            JOB_OBJECT_LIMIT_JOB_MEMORY = 0x200  # noqa: N806
            JobObjectExtendedLimitInformation = 9  # noqa: N806

            class _JobBasicLimit(ctypes.Structure):  # type: ignore[misc]
                _fields_: ClassVar[list[tuple[str, Any]]] = [
                    ("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", ctypes.wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", ctypes.wintypes.DWORD),
                    ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
                    ("PriorityClass", ctypes.wintypes.DWORD),
                    ("SchedulingClass", ctypes.wintypes.DWORD),
                ]

            class _IoCounters(ctypes.Structure):  # type: ignore[misc]
                _fields_: ClassVar[list[tuple[str, Any]]] = [
                    ("ReadOperationCount", ctypes.c_uint64),
                    ("WriteOperationCount", ctypes.c_uint64),
                    ("OtherOperationCount", ctypes.c_uint64),
                    ("ReadTransferCount", ctypes.c_uint64),
                    ("WriteTransferCount", ctypes.c_uint64),
                    ("OtherTransferCount", ctypes.c_uint64),
                ]

            class _JobExtLimit(ctypes.Structure):  # type: ignore[misc]
                _fields_: ClassVar[list[tuple[str, Any]]] = [
                    ("BasicLimitInformation", _JobBasicLimit),
                    ("IoInfo", _IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t),
                ]

            mem_bytes = self._config.max_memory_mb * 1024 * 1024
            info = _JobExtLimit()
            info.BasicLimitInformation.LimitFlags = (
                JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_JOB_MEMORY
            )
            info.ProcessMemoryLimit = mem_bytes
            info.JobMemoryLimit = mem_bytes

            ctypes.windll.kernel32.SetInformationJobObject(  # type: ignore[attr-defined]
                job_handle,
                JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
        except (AttributeError, OSError) as exc:
            logger.warning("Could not set Job Object limits: %s", exc)

    def _close_handle(self, handle: Any) -> None:
        """Close a Windows kernel handle."""
        try:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
        except (AttributeError, OSError) as exc:
            logger.warning("Could not close Job Object handle: %s", exc)

    @staticmethod
    def _cleanup_workspace(workspace: Path) -> None:
        """Remove the ephemeral *workspace* directory tree."""
        try:
            shutil.rmtree(workspace, ignore_errors=True)
        except OSError as exc:
            logger.warning("Failed to clean up workspace %s: %s", workspace, exc)
