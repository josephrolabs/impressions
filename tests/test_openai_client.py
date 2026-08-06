import pytest

import impressions.core.openai_client as openai_client
from impressions.core import OpenAIModelClient as PublicOpenAIModelClient
from impressions.core.model_client import ModelClient, ModelGenerationError, ModelRequest
from impressions.core.openai_client import OpenAIModelClient


def test_openai_model_client_implements_model_client_protocol():
    client: ModelClient = OpenAIModelClient(
        api_key="test-key",
        model="gpt-test",
        client=FakeOpenAIClient(response=successful_response()),
    )

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.text == "Hello."


def test_generate_translates_model_request_to_responses_api_request():
    sdk_client = FakeOpenAIClient(response=successful_response())
    client = OpenAIModelClient(api_key="test-key", model="gpt-5", client=sdk_client)

    client.generate(
        ModelRequest(
            prompt="Write a function that reverses a string.",
            system_prompt="You are a careful coding assistant.",
            temperature=0.2,
            max_tokens=512,
            metadata={"task": "reverse-string"},
        )
    )

    assert sdk_client.responses.requests == [
        {
            "model": "gpt-5",
            "input": "Write a function that reverses a string.",
            "temperature": 0.2,
            "metadata": {"task": "reverse-string"},
            "instructions": "You are a careful coding assistant.",
            "max_output_tokens": 512,
        }
    ]


def test_generate_omits_optional_openai_arguments_when_not_configured():
    sdk_client = FakeOpenAIClient(response=successful_response())
    client = OpenAIModelClient(api_key="test-key", model="gpt-5", client=sdk_client)

    client.generate(ModelRequest(prompt="Say hello."))

    assert sdk_client.responses.requests == [
        {
            "model": "gpt-5",
            "input": "Say hello.",
            "temperature": 0.0,
            "metadata": {},
        }
    ]


def test_generate_translates_openai_response_to_model_response():
    sdk_client = FakeOpenAIClient(
        response=successful_response(
            text="Here is the solution.",
            model="gpt-5-2026-08-04",
            input_tokens=31,
            output_tokens=84,
            response_id="resp_123",
            request_id="req_456",
        )
    )
    client = OpenAIModelClient(api_key="test-key", model="gpt-5", client=sdk_client)

    response = client.generate(ModelRequest(prompt="Solve it."))

    assert response.text == "Here is the solution."
    assert response.model == "gpt-5-2026-08-04"
    assert response.input_tokens == 31
    assert response.output_tokens == 84
    assert response.metadata == {
        "provider_response_id": "resp_123",
        "provider_request_id": "req_456",
    }


def test_generate_keeps_usage_optional_when_openai_response_has_no_usage():
    sdk_client = FakeOpenAIClient(
        response=FakeResponse(
            output_text="Hello.",
            model="gpt-5",
            id="resp_123",
            usage=None,
            request_id=None,
        )
    )
    client = OpenAIModelClient(api_key="test-key", model="gpt-5", client=sdk_client)

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.input_tokens is None
    assert response.output_tokens is None
    assert response.metadata == {"provider_response_id": "resp_123"}


def test_generate_maps_openai_api_errors_to_model_generation_error(monkeypatch):
    class FakeAPIError(Exception):
        pass

    monkeypatch.setattr(openai_client.openai, "APIError", FakeAPIError)
    sdk_client = FakeOpenAIClient(error=FakeAPIError("provider failed"))
    client = OpenAIModelClient(api_key="test-key", model="gpt-5", client=sdk_client)

    with pytest.raises(ModelGenerationError, match="OpenAI generation failed"):
        client.generate(ModelRequest(prompt="Say hello."))


def test_constructor_passes_api_key_and_timeout_to_openai_sdk(monkeypatch):
    created_clients = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(openai_client, "OpenAI", FakeOpenAI)

    OpenAIModelClient(api_key="test-key", model="gpt-5", timeout=30.0)

    assert created_clients == [{"api_key": "test-key", "timeout": 30.0}]


def test_constructor_omits_timeout_when_not_provided(monkeypatch):
    created_clients = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(openai_client, "OpenAI", FakeOpenAI)

    OpenAIModelClient(api_key="test-key", model="gpt-5")

    assert created_clients == [{"api_key": "test-key"}]


def test_openai_model_client_api_exports_from_core_package():
    assert PublicOpenAIModelClient is OpenAIModelClient


def successful_response(
    text="Hello.",
    model="gpt-5",
    input_tokens=9,
    output_tokens=3,
    response_id="resp_test",
    request_id="req_test",
):
    return FakeResponse(
        output_text=text,
        model=model,
        id=response_id,
        usage=FakeUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        request_id=request_id,
    )


class FakeOpenAIClient:
    def __init__(self, response=None, error=None):
        self.responses = FakeResponses(response=response, error=error)


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeResponse:
    def __init__(self, output_text, model, id, usage, request_id):
        self.output_text = output_text
        self.model = model
        self.id = id
        self.usage = usage
        self._request_id = request_id


class FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
