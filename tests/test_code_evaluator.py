from pathlib import Path

from impressions.core.code_evaluator import CodeTaskEvaluator
from impressions.core.evaluation import EvaluationResult
from impressions.core.tasks import Task, TaskExecution, TaskExpected, TaskInput


def test_code_task_evaluator_generates_then_grades_executable_task():
    task = code_task()
    evaluator = CodeTaskEvaluator(FakeLLM(), FakeGrader())

    result = evaluator.evaluate(task)

    assert result.output == "def add(a, b): return a + b"
    assert result.metadata["passed"] is True
    assert result.metadata["generation"] == {"model": "test-model"}


def test_code_task_evaluator_uses_fallback_for_non_code_task():
    task = Task(Path("text.yaml"), 1, "text", "Text", TaskInput("prompt"), TaskExpected("text"))
    result = CodeTaskEvaluator(FakeLLM(), FakeGrader()).evaluate(task)

    assert result.output == "prompt"
    assert result.metadata["evaluator"] == "echo"


class FakeLLM:
    def evaluate(self, task):
        return EvaluationResult(task, output="def add(a, b): return a + b", metadata={"model": "test-model"})


class FakeGrader:
    def grade(self, task, code):
        assert code.startswith("def add")
        return EvaluationResult(task, output=code, metadata={"passed": True, "grader": "pytest"})


def code_task():
    return Task(
        Path("add.yaml"), 1, "add", "Add", TaskInput("Write add"), TaskExpected("code"),
        TaskExecution("solution.py", "tests/test_solution.py", 30),
    )
