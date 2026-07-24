"""Provider-agnostic language model generation primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class ModelClient(Protocol):
    """Language model provider interface."""

    def generate(self, request: "ModelRequest") -> "ModelResponse":
        """Generate text for a validated model request."""


class ModelGenerationError(Exception):
    """Raised when model generation fails."""


@dataclass(frozen=True)
class ModelRequest:
    """Immutable request passed to a model provider."""

    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    """Immutable response returned by a model provider."""

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
