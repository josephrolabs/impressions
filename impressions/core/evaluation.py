"""Evaluation engine orchestration primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol

from impressions.core.tasks import Task


class Evaluator(Protocol):
    """Evaluation backend interface."""

    def evaluate(self, task: Task) -> "EvaluationResult":
        """Evaluate a validated task and return a structured result."""


class EvaluationEngineError(Exception):
    """Raised when evaluation orchestration fails."""


@dataclass(frozen=True)
class EvaluationResult:
    """Structured result returned by an evaluator."""

    task: Task
    output: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationEngine:
    """Coordinate evaluation of validated tasks with a backend evaluator."""

    evaluator: Evaluator

    def evaluate(self, task: Task) -> EvaluationResult:
        """Evaluate a validated task through the configured evaluator."""
        result = self.evaluator.evaluate(task)
        if not isinstance(result, EvaluationResult):
            raise EvaluationEngineError(
                "Evaluator returned an invalid result. "
                "Expected an EvaluationResult instance."
            )
        return result

    def evaluate_all(self, tasks: Iterable[Task]) -> list[EvaluationResult]:
        """Evaluate validated tasks in iteration order."""
        return [self.evaluate(task) for task in tasks]
