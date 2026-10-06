"""Meta Muse Spark-backed model client implementation.

Meta's Model API is OpenAI-compatible, so this client reuses the ``openai``
package against the Meta base URL with the Chat Completions interface.
"""

from __future__ import annotations

from typing import Any

import openai
from openai import OpenAI

from impressions.core.model_client import (
    ModelGenerationError,
    ModelRequest,
    ModelResponse,
)


META_API_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.1"


class MetaModelClient:
    """Generate model responses through Meta's OpenAI-compatible Model API."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float | None = None,
        *,
        client: Any | None = None,
        base_url: str = META_API_BASE_URL,
    ) -> None:
        self.model = model
        self.base_url = base_url
        if client is not None:
            self._client = client
            return

        client_kwargs: dict[str, Any] = {"api_key": api_key, "base_url": base_url}
        if timeout is not None:
            client_kwargs["timeout"] = timeout
        self._client = OpenAI(**client_kwargs)

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate text for a model request."""
        messages: list[dict[str, str]] = []
        if request.system_prompt is not None:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        completion_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            completion_kwargs["max_tokens"] = request.max_tokens

        try:
            response = self._client.chat.completions.create(**completion_kwargs)
        except openai.APIError as exc:
            raise ModelGenerationError(f"Meta generation failed: {exc}") from exc

        choice = response.choices[0]
        content = choice.message.content or ""
        return ModelResponse(
            text=content,
            model=response.model,
            input_tokens=_get_usage_value(response, "prompt_tokens"),
            output_tokens=_get_usage_value(response, "completion_tokens"),
            metadata=_response_metadata(response, base_url=self.base_url),
        )


def _get_usage_value(response: Any, key: str) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    value = getattr(usage, key, None)
    if isinstance(value, int):
        return value
    return None


def _response_metadata(response: Any, *, base_url: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {"base_url": base_url}

    response_id = getattr(response, "id", None)
    if response_id is not None:
        metadata["provider_response_id"] = response_id

    finish_reason = getattr(response.choices[0], "finish_reason", None)
    if finish_reason is not None:
        metadata["finish_reason"] = finish_reason

    return metadata
