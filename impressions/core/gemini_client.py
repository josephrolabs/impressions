"""Google Gemini-backed model client implementation."""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import errors, types

from impressions.core.model_client import (
    ModelGenerationError,
    ModelRequest,
    ModelResponse,
)


class GeminiModelClient:
    """Generate model responses through the Gemini Developer API."""

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
            client_kwargs["http_options"] = types.HttpOptions(
                timeout=int(timeout * 1000)
            )
        self._client = genai.Client(**client_kwargs)

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate text for a model request."""
        config_kwargs: dict[str, Any] = {"temperature": request.temperature}
        if request.system_prompt is not None:
            config_kwargs["system_instruction"] = request.system_prompt
        if request.max_tokens is not None:
            config_kwargs["max_output_tokens"] = request.max_tokens

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=request.prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except errors.APIError as exc:
            raise ModelGenerationError(f"Gemini generation failed: {exc}") from exc

        return ModelResponse(
            text=response.text or "",
            model=self.model,
            input_tokens=_get_usage_value(response, "prompt_token_count"),
            output_tokens=_get_usage_value(response, "candidates_token_count"),
            metadata=_response_metadata(response),
        )


def _get_usage_value(response: Any, key: str) -> int | None:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None

    value = getattr(usage, key, None)
    if isinstance(value, int):
        return value
    return None


def _response_metadata(response: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    response_id = getattr(response, "response_id", None)
    if response_id is not None:
        metadata["provider_response_id"] = response_id

    return metadata
