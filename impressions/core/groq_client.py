"""Groq-backed model client implementation.

Groq's API is OpenAI-compatible, so this client reuses the ``openai``
package against the Groq base URL with the Chat Completions interface.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import openai
from openai import OpenAI

from impressions.core.model_client import (
    ModelGenerationError,
    ModelRequest,
    ModelResponse,
)


GROQ_API_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"

_MAX_GENERATION_ATTEMPTS = 6
_INITIAL_BACKOFF_SECONDS = 5.0
_MAX_BACKOFF_SECONDS = 60.0


class GroqModelClient:
    """Generate model responses through Groq's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float | None = None,
        *,
        client: Any | None = None,
        base_url: str = GROQ_API_BASE_URL,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = _MAX_GENERATION_ATTEMPTS,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self._sleep = sleep
        self._max_attempts = max(1, max_attempts)
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

        backoff = _INITIAL_BACKOFF_SECONDS
        for attempt in range(self._max_attempts):
            try:
                response = self._client.chat.completions.create(**completion_kwargs)
            except openai.APIError as exc:
                if attempt == self._max_attempts - 1 or not _is_retryable(exc):
                    raise ModelGenerationError(
                        f"Groq generation failed: {exc}"
                    ) from exc
                self._sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
                continue

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


def _is_retryable(exc: openai.APIError) -> bool:
    """Rate-limit, connection, and transient server errors are worth retrying."""
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code == 429 or code >= 500

    return isinstance(exc, openai.APIConnectionError)
