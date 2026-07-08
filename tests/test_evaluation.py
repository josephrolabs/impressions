from pathlib import Path

import pytest

from impressions.core import EvaluationEngine as PublicEvaluationEngine
from impressions.core import EvaluationResult as PublicEvaluationResult
from impressions.core import EchoEvaluator as PublicEchoEvaluator
from impressions.core.evaluation import (
    EchoEvaluator,
    EvaluationEngine,
    EvaluationEngineError,
    EvaluationResult,
)
from impressions.core.tasks import Task, TaskExpected, TaskInput


def test_evaluation_engine_routes_task_to_evaluator():
    task = make_task("summarize")
    evaluator = RecordingEvaluator(EvaluationResult(task=task, output="summary"))
    engine = EvaluationEngine(evaluator)

    result = engine.evaluate(task)

    assert result == EvaluationResult(task=task, output="summary")
    assert evaluator.tasks == [task]


def test_evaluation_engine_preserves_structured_result_metadata():
    task = make_task("classify")
    result = EvaluationResult(
        task=task,
        output={"label": "positive"},
        metadata={"model": "fake-evaluator"},
    )
    engine = EvaluationEngine(RecordingEvaluator(result))

    evaluated = engine.evaluate(task)

    assert evaluated.output == {"label": "positive"}
    assert evaluated.metadata == {"model": "fake-evaluator"}


def test_evaluation_engine_evaluates_tasks_in_order():
    tasks = [make_task("first"), make_task("second")]
    evaluator = NamingEvaluator()
    engine = EvaluationEngine(evaluator)

    results = engine.evaluate_all(tasks)

    assert [result.output for result in results] == ["first", "second"]
    assert evaluator.tasks == tasks


def test_evaluation_engine_rejects_unstructured_evaluator_result():
    task = make_task("broken")
    engine = EvaluationEngine(BrokenEvaluator())

    with pytest.raises(EvaluationEngineError, match="Expected an EvaluationResult"):
        engine.evaluate(task)


def test_echo_evaluator_returns_deterministic_task_prompt_result():
    task = make_task("summarize")
    evaluator = EchoEvaluator()

    result = evaluator.evaluate(task)

    assert result == EvaluationResult(
        task=task,
        output="Say hello.",
        metadata={
            "evaluator": "echo",
            "expected_type": "text",
        },
    )


def test_evaluation_api_exports_from_core_package():
    assert PublicEchoEvaluator is EchoEvaluator
    assert PublicEvaluationEngine is EvaluationEngine
    assert PublicEvaluationResult is EvaluationResult


class RecordingEvaluator:
    def __init__(self, result: EvaluationResult) -> None:
        self.result = result
        self.tasks: list[Task] = []

    def evaluate(self, task: Task) -> EvaluationResult:
        self.tasks.append(task)
        return self.result


class NamingEvaluator:
    def __init__(self) -> None:
        self.tasks: list[Task] = []

    def evaluate(self, task: Task) -> EvaluationResult:
        self.tasks.append(task)
        return EvaluationResult(task=task, output=task.name)


class BrokenEvaluator:
    def evaluate(self, task: Task) -> str:
        return task.name


def make_task(name: str) -> Task:
    return Task(
        path=Path(f"tasks/{name}.yaml"),
        version=1,
        name=name,
        description="Test task.",
        input=TaskInput(prompt="Say hello."),
        expected=TaskExpected(type="text"),
    )
