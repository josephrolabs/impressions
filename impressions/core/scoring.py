"""Multi-attempt evaluation orchestration and reliability metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from impressions.core.evaluation import EvaluationResult, Evaluator
from impressions.core.tasks import Task


@dataclass(frozen=True)
class AttemptResult:
    """One deterministic attempt outcome for a task."""

    attempt: int
    result: EvaluationResult
    succeeded: bool


@dataclass(frozen=True)
class MultiAttemptResult:
    """All attempts for one task, in evaluation order."""

    task: Task
    attempts: tuple[AttemptResult, ...]


@dataclass(frozen=True)
class ReliabilityMetrics:
    """Aggregate metrics calculated from complete multi-attempt task results."""

    task_count: int
    first_attempt_success_rate: float
    observed_pass_at_k: float
    mean_attempts_to_success: float | None
    attempts_per_task: int
    pass_at_k: int


class MultiAttemptEvaluator:
    """Evaluate each task repeatedly through a provider-independent evaluator."""

    def __init__(self, evaluator: Evaluator, *, attempts: int) -> None:
        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
            raise ValueError("attempts must be a positive integer.")
        self._evaluator = evaluator
        self._attempts = attempts

    def evaluate(self, task: Task) -> MultiAttemptResult:
        attempts = tuple(
            AttemptResult(
                attempt=index,
                result=result,
                succeeded=_is_success(result),
            )
            for index in range(1, self._attempts + 1)
            for result in (self._evaluator.evaluate(task),)
        )
        return MultiAttemptResult(task=task, attempts=attempts)

    def evaluate_all(self, tasks: Iterable[Task]) -> list[MultiAttemptResult]:
        return [self.evaluate(task) for task in tasks]


def calculate_reliability_metrics(
    results: Iterable[MultiAttemptResult], *, pass_at_k: int
) -> ReliabilityMetrics:
    results = list(results)
    if isinstance(pass_at_k, bool) or not isinstance(pass_at_k, int) or pass_at_k <= 0:
        raise ValueError("pass_at_k must be a positive integer.")
    if not results:
        return ReliabilityMetrics(0, 0.0, 0.0, None, 0, pass_at_k)
    attempt_count = len(results[0].attempts)
    if pass_at_k > attempt_count:
        raise ValueError("pass_at_k cannot exceed configured attempts.")
    if any(len(result.attempts) != attempt_count for result in results):
        raise ValueError("All tasks must contain the same number of attempts.")
    first = sum(result.attempts[0].succeeded for result in results)
    pass_k = sum(any(a.succeeded for a in result.attempts[:pass_at_k]) for result in results)
    successful_attempts = [
        next(attempt.attempt for attempt in result.attempts if attempt.succeeded)
        for result in results
        if any(attempt.succeeded for attempt in result.attempts)
    ]
    total = len(results)
    return ReliabilityMetrics(
        task_count=total,
        first_attempt_success_rate=first / total,
        observed_pass_at_k=pass_k / total,
        mean_attempts_to_success=(sum(successful_attempts) / len(successful_attempts) if successful_attempts else None),
        attempts_per_task=attempt_count,
        pass_at_k=pass_at_k,
    )


def _is_success(result: EvaluationResult) -> bool:
    return result.metadata.get("passed") is True
