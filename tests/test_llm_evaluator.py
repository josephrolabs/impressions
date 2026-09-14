from pathlib import Path

import pytest

from impressions.core import LLMEvaluator as PublicLLMEvaluator
from impressions.core.evaluation import EvaluationEngine, EvaluationEngineError
from impressions.core.llm_evaluator import LLMEvaluator
from impressions.core.model_client import (
    ModelGenerationError,
    ModelRequest,
    ModelResponse,
)
from impressions.core.prompt_builder import PromptBuilder, PromptBuilderError
from impressions.core.tasks import Task, TaskExpected, TaskInput


def test_llm_evaluator_renders_prompt_and_normalizes_model_response():
    task = make_task()
    client = RecordingModelClient(
        ModelResponse(
            text="def add(a, b): return a + b",
            model="test-model-v1",
            input_tokens=25,
            output_tokens=10,
            metadata={"provider_response_id": "response_123"},
        )
    )
    evaluator = LLMEvaluator(PromptBuilder(prompt_version="test-v2"), client)

    result = evaluator.evaluate(task)

    assert client.requests == [
        ModelRequest(
            prompt=result.metadata["user_prompt"],
            system_prompt=result.metadata["system_prompt"],
                metadata={"task_name": "add", "prompt_version": "test-v2", "prompt_variant": "baseline"},
        )
    ]
    assert result.task is task
    assert result.output == "def add(a, b): return a + b"
    assert result.metadata == {
        "evaluator": "llm",
        "expected_type": "code",
        "model": "test-model-v1",
        "input_tokens": 25,
        "output_tokens": 10,
            "prompt_version": "test-v2",
            "prompt_variant": "baseline",
        "system_prompt": result.metadata["system_prompt"],
        "user_prompt": result.metadata["user_prompt"],
        "model_response_metadata": {"provider_response_id": "response_123"},
    }


def test_llm_evaluator_works_with_evaluation_engine():
    task = make_task()
    evaluator = LLMEvaluator(
        PromptBuilder(), RecordingModelClient(ModelResponse(text="answer", model="test"))
    )

    result = EvaluationEngine(evaluator).evaluate(task)

    assert result.output == "answer"
    assert result.metadata["evaluator"] == "llm"


def test_llm_evaluator_wraps_model_generation_errors():
    evaluator = LLMEvaluator(PromptBuilder(), FailingModelClient())

    with pytest.raises(EvaluationEngineError, match="LLM evaluation failed for task 'add'"):
        evaluator.evaluate(make_task())


def test_llm_evaluator_wraps_prompt_builder_errors():
    evaluator = LLMEvaluator(FailingPromptBuilder(), RecordingModelClient(None))

    with pytest.raises(EvaluationEngineError, match="prompt could not be rendered"):
        evaluator.evaluate(make_task())


def test_llm_evaluator_exports_from_core_package():
    assert PublicLLMEvaluator is LLMEvaluator


class RecordingModelClient:
    def __init__(self, response: ModelResponse | None) -> None:
        self.response = response
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        assert self.response is not None
        return self.response


class FailingModelClient:
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise ModelGenerationError("provider request failed")


class FailingPromptBuilder:
    def build(self, task: Task):
        raise PromptBuilderError("prompt could not be rendered")


def make_task() -> Task:
    return Task(
        path=Path("tasks/add.yaml"),
        version=1,
        name="add",
        description="Add two integers.",
        input=TaskInput(prompt="Write an add function."),
        expected=TaskExpected(type="code"),
    )
