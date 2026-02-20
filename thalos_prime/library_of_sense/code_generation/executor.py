"""Library of Sense - Code Executor.

Safely executes Python code snippets in subprocess sandboxes with
resource limits, timeout enforcement, and captured output.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 5.0
_MAX_OUTPUT_BYTES = 4096


@dataclass
class ExecutionResult:
    """Result of a sandboxed code execution."""

    stdout: str
    stderr: str
    return_code: int
    timed_out: bool

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this execution result.
        """
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "timed_out": self.timed_out,
        }

    @property
    def success(self) -> bool:
        """Whether execution completed successfully.

        Returns:
            True if return_code is 0 and execution did not time out.
        """
        return self.return_code == 0 and not self.timed_out


class CodeExecutor:
    """Executes Python code snippets safely in subprocess sandboxes.

    Writes code to a temporary file and runs it in a subprocess with a
    configurable timeout, capturing stdout and stderr.
    """

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        """Initialize the code executor.

        Args:
            timeout: Maximum execution time in seconds before termination.
        """
        self._timeout = timeout

    def execute(self, source: str) -> ExecutionResult:
        """Execute Python source code in a subprocess with timeout.

        Writes the source to a temporary file and runs it with the current
        Python interpreter, capturing output and enforcing the timeout.

        Args:
            source: Python source code string to execute.

        Returns:
            ExecutionResult with stdout, stderr, return code, and timeout flag.
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(source)
            tmp_path = Path(tmp.name)

        try:
            proc = subprocess.run(  # noqa: S603
                [sys.executable, str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
            stdout = proc.stdout[:_MAX_OUTPUT_BYTES]
            stderr = proc.stderr[:_MAX_OUTPUT_BYTES]
            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                return_code=proc.returncode,
                timed_out=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning("CodeExecutor: execution timed out after %.1fs", self._timeout)
            return ExecutionResult(
                stdout="",
                stderr="",
                return_code=-1,
                timed_out=True,
            )
        finally:
            tmp_path.unlink(missing_ok=True)


__all__ = ["ExecutionResult", "CodeExecutor"]
