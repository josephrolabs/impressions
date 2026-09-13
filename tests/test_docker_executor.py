from pathlib import Path
from io import StringIO
import subprocess

import pytest

from impressions.core import DockerPythonExecutor as PublicDockerPythonExecutor
from impressions.core.docker_executor import DockerPythonExecutor
from impressions.core.execution import CodeExecutor, ExecutionError


def test_docker_executor_implements_code_executor_protocol():
    executor: CodeExecutor = DockerPythonExecutor()

    assert isinstance(executor, DockerPythonExecutor)


def test_execute_runs_python_in_isolated_docker_container(monkeypatch):
    calls = []
    workspaces = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        mount = command[command.index("--volume") + 1]
        source_path = Path(mount.removesuffix(":/source:ro")) / "main.py"
        workspaces.append(source_path.parent)
        assert source_path.read_text(encoding="utf-8") == 'print("hello")'
        return FakeProcess("hello\n", "", 0)

    monkeypatch.setattr("impressions.core.docker_executor.subprocess.Popen", fake_popen)
    executor = DockerPythonExecutor(image="python:test", memory_limit="128m", pids_limit=32)

    result = executor.execute('print("hello")', timeout_seconds=10)

    command, kwargs = calls[0]
    assert command[:3] == ["docker", "run", "--rm"]
    assert command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert command[command.index("--security-opt") + 1] == "no-new-privileges"
    assert command[command.index("--memory") + 1] == "128m"
    assert command[command.index("--pids-limit") + 1] == "32"
    assert command[command.index("--user") + 1] == "65534:65534"
    assert command[command.index("--name") + 1].startswith("impressions-execution-")
    assert command[command.index("--volume") + 1].endswith(":/source:ro")
    assert command[command.index("--workdir") + 1] == "/work"
    assert "/work:rw,nosuid,size=64m" in command
    assert command[-3:] == ["python:test", "python", "/source/main.py"]
    assert kwargs == {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
    assert result.stdout == "hello\n"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.timed_out is False
    assert not workspaces[0].exists()


def test_execute_returns_nonzero_exit_result(monkeypatch):
    monkeypatch.setattr(
        "impressions.core.docker_executor.subprocess.Popen",
        lambda command, **kwargs: FakeProcess("", "failed\n", 1),
    )

    result = DockerPythonExecutor().execute("raise RuntimeError()", timeout_seconds=5)

    assert result.duration_seconds is not None
    assert result.stdout == ""
    assert result.stderr == "failed\n"
    assert result.exit_code == 1
    assert result.timed_out is False


def test_execute_reports_timeout_with_captured_output(monkeypatch):
    monkeypatch.setattr(
        "impressions.core.docker_executor.subprocess.Popen",
        lambda command, **kwargs: FakeProcess("partial", "still running", None),
    )
    monkeypatch.setattr(
        "impressions.core.docker_executor.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""),
    )

    result = DockerPythonExecutor().execute("while True: pass", timeout_seconds=1)

    assert result.stdout == "partial"
    assert result.stderr == "still running"
    assert result.exit_code is None
    assert result.timed_out is True
    assert result.output_limit_exceeded is False


@pytest.mark.parametrize("timeout", [0, -1, True, 1.5])
def test_execute_rejects_invalid_timeout(timeout):
    with pytest.raises(ExecutionError, match="positive integer"):
        DockerPythonExecutor().execute("print('ok')", timeout_seconds=timeout)


def test_execute_rejects_non_string_code():
    with pytest.raises(ExecutionError, match="must be a string"):
        DockerPythonExecutor().execute(None, timeout_seconds=1)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_execute_rejects_invalid_output_limit(limit):
    with pytest.raises(ExecutionError, match="Maximum captured output"):
        DockerPythonExecutor(max_output_bytes=limit).execute("print('ok')", timeout_seconds=1)


def test_execute_reports_missing_docker_binary(monkeypatch):
    monkeypatch.setattr(
        "impressions.core.docker_executor.subprocess.Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )

    with pytest.raises(ExecutionError, match="Docker executable was not found"):
        DockerPythonExecutor().execute("print('ok')", timeout_seconds=1)


def test_docker_executor_api_exports_from_core_package():
    assert PublicDockerPythonExecutor is DockerPythonExecutor


def test_execute_stops_and_marks_output_overflow(monkeypatch):
    process = FakeProcess("too much output", "", None)
    monkeypatch.setattr(
        "impressions.core.docker_executor.subprocess.Popen", lambda *args, **kwargs: process
    )
    monkeypatch.setattr(
        "impressions.core.docker_executor.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""),
    )

    result = DockerPythonExecutor(max_output_bytes=4).execute("print('x')", timeout_seconds=1)

    assert result.stdout == "too "
    assert result.output_limit_exceeded is True
    assert result.timed_out is False
    assert process.terminated is True


class FakeProcess:
    def __init__(self, stdout: str, stderr: str, returncode: int | None) -> None:
        self.stdout = StringIO(stdout)
        self.stderr = StringIO(stderr)
        self.returncode = returncode
        self.terminated = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = -15
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.returncode = -9
