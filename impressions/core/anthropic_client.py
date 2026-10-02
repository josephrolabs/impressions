"""Anthropic Claude-backed model client implementation."""

from __future__ import annotations

from typing import Any

import anthropic
from anthropic import Anthropic

from impressions.core.model_client import (
    ModelGenerationError,
    ModelRequest,
    ModelResponse,
)


DEFAULT_MAX_TOKENS = 4096


class AnthropicModelClient:
    """Generate model responses through the Anthropic Messages API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float | None = None,
        *,
        client: Any | None = None,
        default_max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = model
        self.default_max_tokens = default_max_tokens
        if client is not None:
            self._client = client
            return

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if timeout is not None:
            client_kwargs["timeout"] = timeout
        self._client = Anthropic(**client_kwargs)

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate text for a model request."""
        message_kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_tokens or self.default_max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "metadata": {"user_id": _metadata_user_id(request)},
        }
        if request.system_prompt is not None:
            message_kwargs["system"] = request.system_prompt

        try:
            response = self._client.messages.create(**message_kwargs)
        except anthropic.APIError as exc:
            raise ModelGenerationError(f"Anthropic generation failed: {exc}") from exc

        return ModelResponse(
            text="".join(
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            ),
            model=response.model,
            input_tokens=_get_usage_value(response, "input_tokens"),
            output_tokens=_get_usage_value(response, "output_tokens"),
            metadata=_response_metadata(response),
        )


def _metadata_user_id(request: ModelRequest) -> str:
    task_name = request.metadata.get("task_name")
    if isinstance(task_name, str) and task_name:
        return f"impressions:{task_name}"
    return "impressions"


def _get_usage_value(response: Any, key: str) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    value = getattr(usage, key, None)
    if isinstance(value, int):
        return value
    return None


def _response_metadata(response: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    response_id = getattr(response, "id", None)
    if response_id is not None:
        metadata["provider_response_id"] = response_id

    stop_reason = getattr(response, "stop_reason", None)
    if stop_reason is not None:
        metadata["stop_reason"] = stop_reason

    return metadata
