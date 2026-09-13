"""Provider-agnostic interfaces for isolated code execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class CodeExecutor(Protocol):
    """Execute generated code and return its normalized process result."""

    def execute(self, code: str, *, timeout_seconds: int) -> "ExecutionResult":
        """Execute code within the executor's isolation boundary."""


@dataclass(frozen=True)
class ExecutionResult:
    """Normalized outcome of an isolated code execution."""

    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    duration_seconds: float | None = None
    output_limit_exceeded: bool = False


class ExecutionError(Exception):
    """Raised when an execution environment cannot be started or controlled."""
