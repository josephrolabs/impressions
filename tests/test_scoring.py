from pathlib import Path

import pytest

from impressions.core.evaluation import EvaluationResult
from impressions.core.scoring import MultiAttemptEvaluator, calculate_reliability_metrics
from impressions.core.tasks import Task, TaskExpected, TaskInput


def test_metrics_calculate_first_attempt_pass_at_k_and_mean_attempts():
    results = [
        result("a", [False, False, True]),
        result("b", [True, False, False]),
        result("c", [False, False, False]),
    ]
    metrics = calculate_reliability_metrics(results, pass_at_k=3)

    assert metrics.first_attempt_success_rate == pytest.approx(1 / 3)
    assert metrics.observed_pass_at_k == pytest.approx(2 / 3)
    assert metrics.mean_attempts_to_success == 2.0


def test_metrics_reject_k_greater_than_attempts():
    with pytest.raises(ValueError, match="cannot exceed"):
        calculate_reliability_metrics([result("a", [True])], pass_at_k=2)


def test_multi_attempt_evaluator_preserves_attempt_order():
    evaluator = MultiAttemptEvaluator(SequenceEvaluator([False, True]), attempts=2)
    attempts = evaluator.evaluate(task("a")).attempts

    assert [attempt.attempt for attempt in attempts] == [1, 2]
    assert [attempt.succeeded for attempt in attempts] == [False, True]


class SequenceEvaluator:
    def __init__(self, outcomes): self.outcomes = iter(outcomes)
    def evaluate(self, task): return EvaluationResult(task=task, metadata={"passed": next(self.outcomes)})


def result(name, outcomes):
    return MultiAttemptEvaluator(SequenceEvaluator(outcomes), attempts=len(outcomes)).evaluate(task(name))


def task(name):
    return Task(Path(f"{name}.yaml"), 1, name, "Task", TaskInput("prompt"), TaskExpected("code"))
