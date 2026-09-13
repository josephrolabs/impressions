"""Compose model generation and pytest grading for executable tasks."""

from __future__ import annotations

from dataclasses import dataclass

from impressions.core.evaluation import EchoEvaluator, EvaluationResult, Evaluator
from impressions.core.llm_evaluator import LLMEvaluator
from impressions.core.pytest_grader import PytestCodeGrader
from impressions.core.tasks import Task


@dataclass(frozen=True)
class CodeTaskEvaluator:
    """Generate and grade code tasks while retaining echo fallback for text tasks."""

    llm_evaluator: LLMEvaluator
    grader: PytestCodeGrader
    fallback: Evaluator = EchoEvaluator()

    def evaluate(self, task: Task) -> EvaluationResult:
        if task.execution is None:
            return self.fallback.evaluate(task)

        generated = self.llm_evaluator.evaluate(task)
        graded = self.grader.grade(task, generated.output)
        return EvaluationResult(
            task=task,
            output=generated.output,
            metadata={
                **graded.metadata,
                "generation": generated.metadata,
            },
        )
