import pytest

import impressions.core.gemini_client as gemini_client
from impressions.core import GeminiModelClient as PublicGeminiModelClient
from impressions.core.gemini_client import GeminiModelClient
from impressions.core.model_client import ModelClient, ModelGenerationError, ModelRequest


def test_gemini_model_client_implements_model_client_protocol():
    client: ModelClient = GeminiModelClient(
        api_key="test-key",
        model="gemini-test",
        client=FakeGeminiClient(response=successful_response()),
    )

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.text == "Hello."
    assert response.model == "gemini-test"
    assert response.input_tokens == 9
    assert response.output_tokens == 3
    assert response.metadata == {"provider_response_id": "resp_123"}


def test_generate_translates_model_request_to_generate_content_request():
    sdk_client = FakeGeminiClient(response=successful_response())
    client = GeminiModelClient(
        api_key="test-key", model="gemini-test", client=sdk_client
    )

    client.generate(
        ModelRequest(
            prompt="Write a function that reverses a string.",
            system_prompt="You are a careful coding assistant.",
            temperature=0.2,
            max_tokens=512,
        )
    )

    (request_kwargs,) = sdk_client.models.requests
    assert request_kwargs["model"] == "gemini-test"
    assert request_kwargs["contents"] == "Write a function that reverses a string."
    config = request_kwargs["config"]
    assert config.system_instruction == "You are a careful coding assistant."
    assert config.temperature == 0.2
    assert config.max_output_tokens == 512


def test_generate_omits_optional_generation_config_when_not_configured():
    sdk_client = FakeGeminiClient(response=successful_response())
    client = GeminiModelClient(
        api_key="test-key", model="gemini-test", client=sdk_client
    )

    client.generate(ModelRequest(prompt="Say hello."))

    (request_kwargs,) = sdk_client.models.requests
    config = request_kwargs["config"]
    assert config.system_instruction is None
    assert config.max_output_tokens is None
    assert config.temperature == 0.0


def test_generate_maps_gemini_api_errors_to_model_generation_error(monkeypatch):
    class FakeAPIError(Exception):
        pass

    monkeypatch.setattr(gemini_client.errors, "APIError", FakeAPIError)
    sdk_client = FakeGeminiClient(error=FakeAPIError("provider failed"))
    client = GeminiModelClient(
        api_key="test-key", model="gemini-test", client=sdk_client
    )

    with pytest.raises(ModelGenerationError, match="Gemini generation failed"):
        client.generate(ModelRequest(prompt="Say hello."))


def test_constructor_passes_api_key_and_timeout_to_gemini_sdk(monkeypatch):
    created_clients = []

    class FakeGenAIClient:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(gemini_client.genai, "Client", FakeGenAIClient)

    GeminiModelClient(api_key="test-key", model="gemini-test", timeout=30.0)

    (client_kwargs,) = created_clients
    assert client_kwargs["api_key"] == "test-key"
    assert client_kwargs["http_options"].timeout == 30000


def test_constructor_omits_http_options_when_timeout_not_provided(monkeypatch):
    created_clients = []

    class FakeGenAIClient:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(gemini_client.genai, "Client", FakeGenAIClient)

    GeminiModelClient(api_key="test-key", model="gemini-test")

    assert created_clients == [{"api_key": "test-key"}]


def test_gemini_model_client_api_exports_from_core_package():
    assert PublicGeminiModelClient is GeminiModelClient


def successful_response(text="Hello."):
    return FakeGenerateContentResponse(
        text=text,
        response_id="resp_123",
        usage_metadata=FakeUsageMetadata(
            prompt_token_count=9, candidates_token_count=3
        ),
    )


class FakeGeminiClient:
    def __init__(self, response=None, error=None):
        self.models = FakeModels(response=response, error=error)


class FakeModels:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeGenerateContentResponse:
    def __init__(self, text, response_id, usage_metadata):
        self.text = text
        self.response_id = response_id
        self.usage_metadata = usage_metadata


class FakeUsageMetadata:
    def __init__(self, prompt_token_count, candidates_token_count):
        self.prompt_token_count = prompt_token_count
        self.candidates_token_count = candidates_token_count
