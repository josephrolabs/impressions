"""Deterministic prompt rendering for validated tasks."""

from __future__ import annotations

from dataclasses import dataclass

from impressions.core.tasks import Task


PROMPT_VERSION = "v1"
DEFAULT_VARIANT = "baseline"
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful coding assistant. Follow the task instructions exactly "
    "and return only the requested output."
)
ENGINEERED_SYSTEM_PROMPT = (
    "You are a meticulous Python coding assistant. Return only runnable code for the requested "
    "entrypoint. Satisfy every stated requirement, handle edge cases, and reason against the tests."
)
PROMPT_VARIANTS = {
    "baseline": (PROMPT_VERSION, DEFAULT_SYSTEM_PROMPT),
    "engineered": ("engineered-v1", ENGINEERED_SYSTEM_PROMPT),
}


class PromptBuilderError(Exception):
    """Raised when a prompt cannot be rendered from a task."""


@dataclass(frozen=True)
class PromptRenderResult:
    """Immutable prompt payload produced from a task definition."""

    system_prompt: str
    user_prompt: str
    prompt_version: str
    prompt_variant: str = DEFAULT_VARIANT


class PromptBuilder:
    """Render provider-agnostic prompts from validated tasks."""

    def __init__(
        self,
        *,
        variant: str = DEFAULT_VARIANT,
        system_prompt: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        if variant not in PROMPT_VARIANTS:
            raise PromptBuilderError(f"Unknown prompt variant {variant!r}. Supported variants: {', '.join(PROMPT_VARIANTS)}.")
        version, default_system_prompt = PROMPT_VARIANTS[variant]
        self._variant = variant
        self._system_prompt = _required_non_empty_str(default_system_prompt if system_prompt is None else system_prompt, "system_prompt")
        self._prompt_version = _required_non_empty_str(version if prompt_version is None else prompt_version, "prompt_version")

    def build(self, task: Task) -> PromptRenderResult:
        """Render deterministic system and user prompts for a validated task."""
        if not isinstance(task, Task):
            raise PromptBuilderError("PromptBuilder.build() requires a validated Task.")

        user_prompt = "\n".join(
            [
                f"Task: {task.name}",
                "",
                "Description:",
                task.description,
                "",
                "Input:",
                task.input.prompt,
                "",
                "Expected output type:",
                task.expected.type,
            ]
        )

        return PromptRenderResult(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            prompt_version=self._prompt_version,
            prompt_variant=self._variant,
        )


def _required_non_empty_str(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise PromptBuilderError(f"{field} must be a string.")

    if not value.strip():
        raise PromptBuilderError(f"{field} must be a non-empty string.")

    return value
