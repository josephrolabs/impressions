"""Language-model-backed evaluation implementation."""

from __future__ import annotations

from dataclasses import dataclass

from impressions.core.evaluation import EvaluationEngineError, EvaluationResult
from impressions.core.model_client import (
    ModelClient,
    ModelGenerationError,
    ModelRequest,
)
from impressions.core.prompt_builder import PromptBuilder, PromptBuilderError
from impressions.core.tasks import Task


@dataclass(frozen=True)
class LLMEvaluator:
    """Evaluate tasks by rendering a prompt and generating an LLM response."""

    prompt_builder: PromptBuilder
    model_client: ModelClient

    def evaluate(self, task: Task) -> EvaluationResult:
        """Generate a normalized evaluation result for a validated task."""
        try:
            rendered_prompt = self.prompt_builder.build(task)
            response = self.model_client.generate(
                ModelRequest(
                    prompt=rendered_prompt.user_prompt,
                    system_prompt=rendered_prompt.system_prompt,
                    metadata={
                        "task_name": task.name,
                        "prompt_version": rendered_prompt.prompt_version,
                    },
                )
            )
        except (PromptBuilderError, ModelGenerationError) as exc:
            raise EvaluationEngineError(
                f"LLM evaluation failed for task {task.name!r}: {exc}"
            ) from exc

        return EvaluationResult(
            task=task,
            output=response.text,
            metadata={
                "evaluator": "llm",
                "expected_type": task.expected.type,
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "prompt_version": rendered_prompt.prompt_version,
                "system_prompt": rendered_prompt.system_prompt,
                "user_prompt": rendered_prompt.user_prompt,
                "model_response_metadata": dict(response.metadata),
            },
        )
