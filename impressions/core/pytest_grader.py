"""Pytest-based grading for generated Python solutions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from impressions.core.evaluation import EvaluationResult
from impressions.core.execution import CodeExecutor, ExecutionError
from impressions.core.failure_classification import classify_failure
from impressions.core.tasks import Task


class GradingError(Exception):
    """Raised when a task cannot be prepared for pytest grading."""


@dataclass(frozen=True)
class PytestCodeGrader:
    """Grade generated Python code against task-relative pytest files."""

    executor: CodeExecutor

    def grade(self, task: Task, code: str) -> EvaluationResult:
        if task.execution is None:
            raise GradingError(f"Task {task.name!r} does not define an [execution] block.")
        test_path = _task_relative_test_path(task)
        try:
            test_source = test_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise GradingError(f"Unable to read task test file {test_path}: {exc}") from exc

        try:
            files = {task.execution.tests: test_source}
            for relative_path in task.execution.files:
                fixture_path = _task_relative_file_path(task, relative_path)
                files[relative_path] = fixture_path.read_text(encoding="utf-8")
            execution = self.executor.execute(
                code,
                timeout_seconds=task.execution.timeout_seconds,
                source_filename=task.execution.entrypoint,
                files=files,
                command=("python", "-m", "pytest", f"/source/{task.execution.tests}"),
            )
        except ExecutionError as exc:
            raise GradingError(f"Unable to execute pytest for task {task.name!r}: {exc}") from exc

        passed, failed, errors, skipped, xfailed = _pytest_counts(
            execution.stdout + "\n" + execution.stderr
        )
        counts = (passed, failed, errors, skipped, xfailed)
        metadata = {
            "grader": "pytest",
            "passed": execution.exit_code == 0 and not execution.timed_out,
            "passed_tests": passed,
            "failed_tests": failed,
            "error_tests": errors,
            "skipped_tests": skipped,
            "xfailed_tests": xfailed,
            "total_tests": sum(counts) if all(count is not None for count in counts) else None,
            "stdout": execution.stdout,
            "stderr": execution.stderr,
            "exit_code": execution.exit_code,
            "timed_out": execution.timed_out,
            "output_limit_exceeded": execution.output_limit_exceeded,
        }
        classification = classify_failure(metadata)
        if classification is not None:
            metadata["failure_classification"] = classification
        return EvaluationResult(
            task=task,
            output=code,
            metadata=metadata,
        )


def _task_relative_test_path(task: Task) -> Path:
    return _task_relative_file_path(task, task.execution.tests)


def _task_relative_file_path(task: Task, relative_name: str) -> Path:
    relative_path = Path(relative_name)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise GradingError("Task test path must be relative to its task file.")
    task_root = task.path.parent.resolve()
    test_path = (task_root / relative_path).resolve()
    if not test_path.is_relative_to(task_root):
        raise GradingError("Task test path must not resolve outside its task directory.")
    return test_path


def _pytest_counts(output: str) -> tuple[int | None, int | None, int | None, int | None, int | None]:
    fields = ("passed", "failed", "errors?", "skipped", "xfailed")
    matches = [re.search(rf"(\d+) {field}", output) for field in fields]
    if not any(matches):
        return (None, None, None, None, None)
    return tuple(int(match.group(1)) if match else 0 for match in matches)
