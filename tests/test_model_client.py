from dataclasses import FrozenInstanceError

import pytest

from impressions.core import ModelClient as PublicModelClient
from impressions.core import ModelGenerationError as PublicModelGenerationError
from impressions.core import ModelRequest as PublicModelRequest
from impressions.core import ModelResponse as PublicModelResponse
from impressions.core.model_client import (
    ModelClient,
    ModelGenerationError,
    ModelRequest,
    ModelResponse,
)


def test_model_request_captures_generation_parameters():
    request = ModelRequest(
        prompt="Implement merge sort.",
        system_prompt="You are precise.",
        temperature=0.2,
        max_tokens=2048,
        metadata={"task": "sorting"},
    )

    assert request.prompt == "Implement merge sort."
    assert request.system_prompt == "You are precise."
    assert request.temperature == 0.2
    assert request.max_tokens == 2048
    assert request.metadata == {"task": "sorting"}


def test_model_request_defaults_are_provider_agnostic():
    request = ModelRequest(prompt="Explain recursion.")

    assert request.system_prompt is None
    assert request.temperature == 0.0
    assert request.max_tokens is None
    assert request.metadata == {}


def test_model_request_is_immutable():
    request = ModelRequest(prompt="Explain recursion.")

    with pytest.raises(FrozenInstanceError):
        request.prompt = "Explain iteration."


def test_model_response_captures_generation_result():
    response = ModelResponse(
        text="Here is a merge sort implementation.",
        model="provider-model",
        input_tokens=12,
        output_tokens=42,
        metadata={"provider": "fake"},
    )

    assert response.text == "Here is a merge sort implementation."
    assert response.model == "provider-model"
    assert response.input_tokens == 12
    assert response.output_tokens == 42
    assert response.metadata == {"provider": "fake"}


def test_model_response_defaults_keep_token_counts_optional():
    response = ModelResponse(text="Hello.", model="local-test-model")

    assert response.input_tokens is None
    assert response.output_tokens is None
    assert response.metadata == {}


def test_model_response_is_immutable():
    response = ModelResponse(text="Hello.", model="local-test-model")

    with pytest.raises(FrozenInstanceError):
        response.text = "Goodbye."


def test_model_client_protocol_accepts_structural_implementations():
    client: ModelClient = EchoModelClient(model="test-model")
    request = ModelRequest(prompt="Say hello.")

    response = client.generate(request)

    assert response == ModelResponse(
        text="Say hello.",
        model="test-model",
        input_tokens=2,
        output_tokens=2,
    )


def test_model_generation_error_wraps_provider_failures():
    client: ModelClient = FailingModelClient()

    with pytest.raises(ModelGenerationError, match="Provider failed"):
        client.generate(ModelRequest(prompt="Say hello."))


def test_model_client_api_exports_from_core_package():
    assert PublicModelClient is ModelClient
    assert PublicModelGenerationError is ModelGenerationError
    assert PublicModelRequest is ModelRequest
    assert PublicModelResponse is ModelResponse


class EchoModelClient:
    def __init__(self, model: str) -> None:
        self.model = model

    def generate(self, request: ModelRequest) -> ModelResponse:
        token_count = len(request.prompt.split())
        return ModelResponse(
            text=request.prompt,
            model=self.model,
            input_tokens=token_count,
            output_tokens=token_count,
        )


class FailingModelClient:
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise ModelGenerationError("Provider failed")
