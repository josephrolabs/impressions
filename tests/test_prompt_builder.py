from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from impressions.core import PromptBuilder as PublicPromptBuilder
from impressions.core import PromptBuilderError as PublicPromptBuilderError
from impressions.core import PromptRenderResult as PublicPromptRenderResult
from impressions.core.prompt_builder import (
    DEFAULT_SYSTEM_PROMPT,
    PROMPT_VERSION,
    PromptBuilder,
    PromptBuilderError,
    PromptRenderResult,
)
from impressions.core.tasks import Task, TaskExpected, TaskInput


def test_prompt_builder_renders_task_into_system_and_user_prompts():
    task = make_task()
    builder = PromptBuilder()

    result = builder.build(task)

    assert result == PromptRenderResult(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        user_prompt="\n".join(
            [
                "Task: merge-sort",
                "",
                "Description:",
                "Implement merge sort for a list of integers.",
                "",
                "Input:",
                "Write a Python function named merge_sort.",
                "",
                "Expected output type:",
                "code",
            ]
        ),
        prompt_version=PROMPT_VERSION,
    )


def test_prompt_builder_is_deterministic_for_same_task():
    task = make_task()
    builder = PromptBuilder()

    first = builder.build(task)
    second = builder.build(task)

    assert first == second


def test_prompt_render_result_is_immutable():
    result = PromptBuilder().build(make_task())

    with pytest.raises(FrozenInstanceError):
        result.user_prompt = "Changed."


def test_prompt_builder_records_default_prompt_version():
    result = PromptBuilder().build(make_task())

    assert result.prompt_version == "v1"


def test_prompt_builder_accepts_explicit_prompt_version():
    result = PromptBuilder(prompt_version="v2").build(make_task())

    assert result.prompt_version == "v2"


def test_prompt_builder_rejects_non_task_input():
    builder = PromptBuilder()

    with pytest.raises(PromptBuilderError, match="requires a validated Task"):
        builder.build({"input": {"prompt": "Say hello."}})


def test_prompt_builder_rejects_invalid_configuration():
    with pytest.raises(PromptBuilderError, match="system_prompt must be a non-empty"):
        PromptBuilder(system_prompt="")

    with pytest.raises(PromptBuilderError, match="prompt_version must be a string"):
        PromptBuilder(prompt_version=1)


def test_prompt_builder_api_exports_from_core_package():
    assert PublicPromptBuilder is PromptBuilder
    assert PublicPromptBuilderError is PromptBuilderError
    assert PublicPromptRenderResult is PromptRenderResult


def make_task() -> Task:
    return Task(
        path=Path("tasks/merge-sort.yaml"),
        version=1,
        name="merge-sort",
        description="Implement merge sort for a list of integers.",
        input=TaskInput(prompt="Write a Python function named merge_sort."),
        expected=TaskExpected(type="code"),
    )
