"""Docker-backed executor for isolated Python programs."""

from __future__ import annotations

import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping, Sequence

from impressions.core.execution import ExecutionError, ExecutionResult


DEFAULT_MAX_OUTPUT_BYTES = 1_000_000


@dataclass(frozen=True)
class DockerPythonExecutor:
    """Execute Python source in a resource-constrained Docker container."""

    image: str = "python:3.12-slim"
    memory_limit: str = "256m"
    pids_limit: int = 64
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES

    def execute(
        self,
        code: str,
        *,
        timeout_seconds: int,
        files: Mapping[str, str] | None = None,
        source_filename: str = "main.py",
        command: Sequence[str] | None = None,
    ) -> ExecutionResult:
        """Run source code in an ephemeral Docker container with no network access."""
        _validate_code(code)
        _validate_timeout(timeout_seconds)
        _validate_output_limit(self.max_output_bytes)
        _validate_relative_path(source_filename, "source filename")
        _validate_files(files)
        command = ("python", f"/source/{source_filename}") if command is None else tuple(command)
        _validate_command(command)

        with tempfile.TemporaryDirectory(prefix="impressions-execution-") as directory:
            workspace = Path(directory)
            workspace.chmod(0o755)
            source_path = workspace / source_filename
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(code, encoding="utf-8")
            source_path.chmod(0o444)
            for relative_path, content in (files or {}).items():
                file_path = workspace / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                file_path.chmod(0o444)
            container_name = f"impressions-execution-{uuid.uuid4().hex}"

            started_at = time.monotonic()
            try:
                process = subprocess.Popen(
                    self._docker_command(workspace, container_name, command),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except FileNotFoundError as exc:
                raise ExecutionError(
                    "Docker executable was not found. Install Docker and ensure it is "
                    "available on PATH."
                ) from exc
            except OSError as exc:
                raise ExecutionError(f"Unable to start Docker execution: {exc}") from exc

            stdout = _BoundedOutput(self.max_output_bytes)
            stderr = _BoundedOutput(self.max_output_bytes)
            readers = _start_readers(process, stdout, stderr)
            timed_out = False
            output_limit_exceeded = False
            deadline = started_at + timeout_seconds
            while process.poll() is None:
                if stdout.exceeded or stderr.exceeded:
                    output_limit_exceeded = True
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
                time.sleep(0.01)

            if timed_out or output_limit_exceeded:
                process.terminate()
                self._cleanup_timed_out_container(container_name)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                self._cleanup_timed_out_container(container_name)
            for reader in readers:
                reader.join()

            return ExecutionResult(
                stdout=stdout.text,
                stderr=stderr.text,
                exit_code=None if timed_out else process.returncode,
                timed_out=timed_out,
                duration_seconds=time.monotonic() - started_at,
                output_limit_exceeded=output_limit_exceeded,
            )

    def _docker_command(
        self, workspace: Path, container_name: str, command: Sequence[str]
    ) -> list[str]:
        source_mount = f"{workspace.resolve()}:/source:ro"
        return [
            "docker",
            "run",
            "--rm",
            "--log-driver",
            "none",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--tmpfs",
            "/work:rw,nosuid,size=64m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            self.memory_limit,
            "--pids-limit",
            str(self.pids_limit),
            "--user",
            "65534:65534",
            "--volume",
            source_mount,
            "--workdir",
            "/work",
            "--env",
            "PYTHONPATH=/source",
            self.image,
            *command,
        ]

    def _cleanup_timed_out_container(self, container_name: str) -> None:
        """Force-remove the executor-owned container after a client timeout."""
        try:
            subprocess.run(
                ["docker", "rm", "--force", container_name],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            # The original timeout is still the meaningful result; Docker's --rm
            # flag performs a best-effort cleanup if the daemon remains available.
            return


def _validate_code(code: str) -> None:
    if not isinstance(code, str):
        raise ExecutionError("Code to execute must be a string.")


def _validate_timeout(timeout_seconds: int) -> None:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
        raise ExecutionError("Execution timeout must be a positive integer number of seconds.")
    if timeout_seconds <= 0:
        raise ExecutionError("Execution timeout must be a positive integer number of seconds.")


def _validate_output_limit(max_output_bytes: int) -> None:
    if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int):
        raise ExecutionError("Maximum captured output must be a positive integer number of bytes.")
    if max_output_bytes <= 0:
        raise ExecutionError("Maximum captured output must be a positive integer number of bytes.")


def _validate_relative_path(value: str, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise ExecutionError(f"{field.capitalize()} must be a non-empty relative path.")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ExecutionError(f"{field.capitalize()} must be a non-empty relative path.")


def _validate_files(files: Mapping[str, str] | None) -> None:
    if files is None:
        return
    if not isinstance(files, Mapping):
        raise ExecutionError("Execution files must be a mapping of relative paths to text.")
    for path, content in files.items():
        _validate_relative_path(path, "execution file path")
        if not isinstance(content, str):
            raise ExecutionError("Execution file contents must be strings.")


def _validate_command(command: Sequence[str]) -> None:
    if not command or any(not isinstance(part, str) or not part for part in command):
        raise ExecutionError("Execution command must contain non-empty string arguments.")


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


class _BoundedOutput:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._chunks: list[str] = []
        self._size = 0
        self.exceeded = False

    def append(self, value: str) -> None:
        remaining = self._limit - self._size
        if remaining <= 0:
            self.exceeded = True
            return
        encoded = value.encode()
        if len(encoded) > remaining:
            self._chunks.append(encoded[:remaining].decode(errors="replace"))
            self._size = self._limit
            self.exceeded = True
            return
        self._chunks.append(value)
        self._size += len(encoded)

    @property
    def text(self) -> str:
        return "".join(self._chunks)


def _start_readers(
    process: subprocess.Popen[str], stdout: _BoundedOutput, stderr: _BoundedOutput
) -> list[threading.Thread]:
    def drain(stream, target: _BoundedOutput) -> None:
        if stream is None:
            return
        for chunk in iter(lambda: stream.read(8192), ""):
            target.append(chunk)

    readers = [
        threading.Thread(target=drain, args=(process.stdout, stdout)),
        threading.Thread(target=drain, args=(process.stderr, stderr)),
    ]
    for reader in readers:
        reader.start()
    return readers
