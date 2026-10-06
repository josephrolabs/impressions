import pytest

import impressions.core.meta_client as meta_client
from impressions.core import MetaModelClient as PublicMetaModelClient
from impressions.core.meta_client import META_API_BASE_URL, MetaModelClient
from impressions.core.model_client import ModelClient, ModelGenerationError, ModelRequest


def test_meta_model_client_implements_model_client_protocol():
    client: ModelClient = MetaModelClient(
        api_key="test-key",
        model="muse-spark-1.1",
        client=FakeMetaClient(response=successful_response()),
    )

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.text == "Hello."
    assert response.model == "muse-spark-1.1"
    assert response.input_tokens == 9
    assert response.output_tokens == 3
    assert response.metadata == {
        "base_url": META_API_BASE_URL,
        "provider_response_id": "chatcmpl_123",
        "finish_reason": "stop",
    }


def test_generate_translates_model_request_to_chat_completions_request():
    sdk_client = FakeMetaClient(response=successful_response())
    client = MetaModelClient(
        api_key="test-key", model="muse-spark-1.1", client=sdk_client
    )

    client.generate(
        ModelRequest(
            prompt="Write a function that reverses a string.",
            system_prompt="You are a careful coding assistant.",
            temperature=0.2,
            max_tokens=512,
        )
    )

    (request_kwargs,) = sdk_client.chat.completions.requests
    assert request_kwargs["model"] == "muse-spark-1.1"
    assert request_kwargs["messages"] == [
        {"role": "system", "content": "You are a careful coding assistant."},
        {"role": "user", "content": "Write a function that reverses a string."},
    ]
    assert request_kwargs["temperature"] == 0.2
    assert request_kwargs["max_tokens"] == 512


def test_generate_omits_system_message_and_max_tokens_when_not_configured():
    sdk_client = FakeMetaClient(response=successful_response())
    client = MetaModelClient(
        api_key="test-key", model="muse-spark-1.1", client=sdk_client
    )

    client.generate(ModelRequest(prompt="Say hello."))

    (request_kwargs,) = sdk_client.chat.completions.requests
    assert request_kwargs["messages"] == [{"role": "user", "content": "Say hello."}]
    assert "max_tokens" not in request_kwargs


def test_generate_maps_meta_api_errors_to_model_generation_error(monkeypatch):
    class FakeAPIError(Exception):
        pass

    monkeypatch.setattr(meta_client.openai, "APIError", FakeAPIError)
    sdk_client = FakeMetaClient(error=FakeAPIError("provider failed"))
    client = MetaModelClient(
        api_key="test-key", model="muse-spark-1.1", client=sdk_client
    )

    with pytest.raises(ModelGenerationError, match="Meta generation failed"):
        client.generate(ModelRequest(prompt="Say hello."))


def test_constructor_targets_meta_api_base_url_with_api_key_and_timeout(monkeypatch):
    created_clients = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(meta_client, "OpenAI", FakeOpenAI)

    MetaModelClient(api_key="test-key", model="muse-spark-1.1", timeout=30.0)

    assert created_clients == [
        {
            "api_key": "test-key",
            "base_url": META_API_BASE_URL,
            "timeout": 30.0,
        }
    ]


def test_constructor_defaults_to_muse_spark_model(monkeypatch):
    created_clients = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(meta_client, "OpenAI", FakeOpenAI)

    client = MetaModelClient(api_key="test-key", client=FakeMetaClient())

    assert client.model == "muse-spark-1.1"
    assert client.base_url == META_API_BASE_URL


def test_generate_records_configured_base_url_in_metadata():
    client = MetaModelClient(
        api_key="test-key",
        model="muse-spark-1.1",
        client=FakeMetaClient(response=successful_response()),
        base_url="https://proxy.example.test/v1",
    )

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.metadata["base_url"] == "https://proxy.example.test/v1"


def test_meta_model_client_api_exports_from_core_package():
    assert PublicMetaModelClient is MetaModelClient


def successful_response(text="Hello.", model="muse-spark-1.1"):
    return FakeChatCompletion(
        id="chatcmpl_123",
        model=model,
        choices=[FakeChoice(message=FakeMessage(content=text), finish_reason="stop")],
        usage=FakeUsage(prompt_tokens=9, completion_tokens=3),
    )


class FakeMetaClient:
    def __init__(self, response=None, error=None):
        self.chat = FakeChat(response=response, error=error)


class FakeChat:
    def __init__(self, response=None, error=None):
        self.completions = FakeCompletions(response=response, error=error)


class FakeCompletions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeChatCompletion:
    def __init__(self, id, model, choices, usage):
        self.id = id
        self.model = model
        self.choices = choices
        self.usage = usage


class FakeChoice:
    def __init__(self, message, finish_reason):
        self.message = message
        self.finish_reason = finish_reason


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeUsage:
    def __init__(self, prompt_tokens, completion_tokens):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
