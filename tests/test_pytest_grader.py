from pathlib import Path

import pytest

from impressions.core.execution import ExecutionResult
from impressions.core.pytest_grader import GradingError, PytestCodeGrader
from impressions.core.tasks import Task, TaskExecution, TaskExpected, TaskInput


def test_pytest_grader_materializes_task_relative_tests_and_normalizes_pass(tmp_path):
    task = make_task(tmp_path)
    test_file = task.path.parent / "tests/test_solution.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_add(): assert True\n", encoding="utf-8")
    executor = RecordingExecutor(ExecutionResult("1 passed in 0.01s", "", 0, False))

    result = PytestCodeGrader(executor).grade(task, "def add(a, b): return a + b")

    assert executor.kwargs == {
        "timeout_seconds": 30,
        "source_filename": "solution.py",
        "files": {"tests/test_solution.py": "def test_add(): assert True\n"},
        "command": ("python", "-m", "pytest", "/source/tests/test_solution.py"),
    }
    assert result.metadata["passed"] is True
    assert result.metadata["passed_tests"] == 1
    assert result.metadata["failed_tests"] == 0
    assert result.metadata["total_tests"] == 1


def test_pytest_grader_normalizes_failed_tests(tmp_path):
    task = make_task(tmp_path)
    test_file = task.path.parent / "tests/test_solution.py"
    test_file.parent.mkdir()
    test_file.write_text("", encoding="utf-8")
    result = PytestCodeGrader(
        RecordingExecutor(ExecutionResult("1 failed, 2 passed", "", 1, False))
    ).grade(task, "code")

    assert result.metadata["passed"] is False
    assert result.metadata["passed_tests"] == 2
    assert result.metadata["failed_tests"] == 1
    assert result.metadata["total_tests"] == 3


def test_pytest_grader_normalizes_pytest_errors(tmp_path):
    task = make_task(tmp_path)
    test_file = task.path.parent / "tests/test_solution.py"
    test_file.parent.mkdir()
    test_file.write_text("", encoding="utf-8")
    result = PytestCodeGrader(
        RecordingExecutor(ExecutionResult("2 errors in 0.01s", "", 2, False))
    ).grade(task, "code")

    assert result.metadata["error_tests"] == 2
    assert result.metadata["total_tests"] == 2


def test_pytest_grader_preserves_unknown_counts_for_unparseable_output(tmp_path):
    task = make_task(tmp_path)
    test_file = task.path.parent / "tests/test_solution.py"
    test_file.parent.mkdir()
    test_file.write_text("", encoding="utf-8")
    result = PytestCodeGrader(
        RecordingExecutor(ExecutionResult("output truncated", "", 1, False))
    ).grade(task, "code")

    assert result.metadata["passed_tests"] is None
    assert result.metadata["total_tests"] is None


def test_pytest_grader_counts_skipped_and_xfailed_tests(tmp_path):
    task = make_task(tmp_path)
    test_file = task.path.parent / "tests/test_solution.py"
    test_file.parent.mkdir()
    test_file.write_text("", encoding="utf-8")
    result = PytestCodeGrader(
        RecordingExecutor(ExecutionResult("1 passed, 2 skipped, 3 xfailed", "", 0, False))
    ).grade(task, "code")

    assert result.metadata["skipped_tests"] == 2
    assert result.metadata["xfailed_tests"] == 3
    assert result.metadata["total_tests"] == 6


@pytest.mark.parametrize("test_path", ["../outside.py", "/etc/passwd"])
def test_pytest_grader_rejects_test_paths_outside_task_directory(tmp_path, test_path):
    task = make_task(tmp_path, execution=TaskExecution("solution.py", test_path, 30))

    with pytest.raises(GradingError, match="Task test path"):
        PytestCodeGrader(RecordingExecutor(ExecutionResult("", "", 0, False))).grade(task, "code")


def test_pytest_grader_requires_execution_configuration(tmp_path):
    task = make_task(tmp_path, execution=None)

    with pytest.raises(GradingError, match="does not define"):
        PytestCodeGrader(RecordingExecutor(ExecutionResult("", "", 0, False))).grade(task, "code")


class RecordingExecutor:
    def __init__(self, result):
        self.result = result
        self.kwargs = None

    def execute(self, code, **kwargs):
        self.kwargs = kwargs
        return self.result


def make_task(tmp_path, execution=TaskExecution("solution.py", "tests/test_solution.py", 30)):
    return Task(
        path=tmp_path / "add.yaml",
        version=1,
        name="add",
        description="Add.",
        input=TaskInput(prompt="Write add."),
        expected=TaskExpected(type="code"),
        execution=execution,
    )
