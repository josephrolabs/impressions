"""OpenAI-backed model client implementation."""

from __future__ import annotations

from typing import Any

import openai
from openai import OpenAI

from impressions.core.model_client import (
    ModelGenerationError,
    ModelRequest,
    ModelResponse,
)


class OpenAIModelClient:
    """Generate model responses through the OpenAI Responses API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        self.model = model
        if client is not None:
            self._client = client
            return

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if timeout is not None:
            client_kwargs["timeout"] = timeout
        self._client = OpenAI(**client_kwargs)

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate text for a model request."""
        response_kwargs: dict[str, Any] = {
            "model": self.model,
            "input": request.prompt,
            "temperature": request.temperature,
            "metadata": dict(request.metadata),
        }
        if request.system_prompt is not None:
            response_kwargs["instructions"] = request.system_prompt
        if request.max_tokens is not None:
            response_kwargs["max_output_tokens"] = request.max_tokens

        try:
            response = self._client.responses.create(**response_kwargs)
        except openai.APIError as exc:
            raise ModelGenerationError(f"OpenAI generation failed: {exc}") from exc

        return ModelResponse(
            text=response.output_text,
            model=response.model,
            input_tokens=_get_usage_value(response, "input_tokens"),
            output_tokens=_get_usage_value(response, "output_tokens"),
            metadata=_response_metadata(response),
        )


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

    request_id = getattr(response, "_request_id", None)
    if request_id is not None:
        metadata["provider_request_id"] = request_id

    return metadata
