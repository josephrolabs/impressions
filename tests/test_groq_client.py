import pytest

import impressions.core.groq_client as groq_client
from impressions.core import GroqModelClient as PublicGroqModelClient
from impressions.core.groq_client import GROQ_API_BASE_URL, GroqModelClient
from impressions.core.model_client import ModelClient, ModelGenerationError, ModelRequest


def test_groq_model_client_implements_model_client_protocol():
    client: ModelClient = GroqModelClient(
        api_key="test-key",
        model="openai/gpt-oss-120b",
        client=FakeGroqClient(response=successful_response()),
    )

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.text == "Hello."
    assert response.model == "openai/gpt-oss-120b"
    assert response.input_tokens == 9
    assert response.output_tokens == 3
    assert response.metadata == {
        "base_url": GROQ_API_BASE_URL,
        "provider_response_id": "chatcmpl_123",
        "finish_reason": "stop",
    }


def test_generate_translates_model_request_to_chat_completions_request():
    sdk_client = FakeGroqClient(response=successful_response())
    client = GroqModelClient(
        api_key="test-key", model="openai/gpt-oss-120b", client=sdk_client
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
    assert request_kwargs["model"] == "openai/gpt-oss-120b"
    assert request_kwargs["messages"] == [
        {"role": "system", "content": "You are a careful coding assistant."},
        {"role": "user", "content": "Write a function that reverses a string."},
    ]
    assert request_kwargs["temperature"] == 0.2
    assert request_kwargs["max_tokens"] == 512


def test_generate_omits_system_message_and_max_tokens_when_not_configured():
    sdk_client = FakeGroqClient(response=successful_response())
    client = GroqModelClient(
        api_key="test-key", model="openai/gpt-oss-120b", client=sdk_client
    )

    client.generate(ModelRequest(prompt="Say hello."))

    (request_kwargs,) = sdk_client.chat.completions.requests
    assert request_kwargs["messages"] == [{"role": "user", "content": "Say hello."}]
    assert "max_tokens" not in request_kwargs


def test_generate_maps_groq_api_errors_to_model_generation_error(monkeypatch):
    monkeypatch.setattr(groq_client.openai, "APIError", FakeAPIError)
    sdk_client = FakeGroqClient(error=FakeAPIError("provider failed", status_code=400))
    client = GroqModelClient(
        api_key="test-key", model="openai/gpt-oss-120b", client=sdk_client
    )

    with pytest.raises(ModelGenerationError, match="Groq generation failed"):
        client.generate(ModelRequest(prompt="Say hello."))

    assert len(sdk_client.chat.completions.requests) == 1


def test_generate_retries_rate_limit_errors_with_backoff(monkeypatch):
    monkeypatch.setattr(groq_client.openai, "APIError", FakeAPIError)
    sleeps = []
    sdk_client = FakeGroqClient(
        outcomes=[
            FakeAPIError("rate limited", status_code=429),
            FakeAPIError("rate limited", status_code=429),
            successful_response(),
        ]
    )
    client = GroqModelClient(
        api_key="test-key",
        model="openai/gpt-oss-120b",
        client=sdk_client,
        sleep=sleeps.append,
    )

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.text == "Hello."
    assert len(sdk_client.chat.completions.requests) == 3
    assert sleeps == [5.0, 10.0]


def test_generate_gives_up_after_max_attempts_on_server_errors(monkeypatch):
    monkeypatch.setattr(groq_client.openai, "APIError", FakeAPIError)
    sdk_client = FakeGroqClient(error=FakeAPIError("unavailable", status_code=503))
    client = GroqModelClient(
        api_key="test-key",
        model="openai/gpt-oss-120b",
        client=sdk_client,
        sleep=lambda _seconds: None,
        max_attempts=3,
    )

    with pytest.raises(ModelGenerationError, match="Groq generation failed"):
        client.generate(ModelRequest(prompt="Say hello."))

    assert len(sdk_client.chat.completions.requests) == 3


def test_constructor_targets_groq_api_base_url_with_api_key_and_timeout(monkeypatch):
    created_clients = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(groq_client, "OpenAI", FakeOpenAI)

    GroqModelClient(api_key="test-key", model="openai/gpt-oss-120b", timeout=30.0)

    assert created_clients == [
        {
            "api_key": "test-key",
            "base_url": GROQ_API_BASE_URL,
            "timeout": 30.0,
        }
    ]


def test_constructor_defaults_to_gpt_oss_120b_model(monkeypatch):
    created_clients = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(groq_client, "OpenAI", FakeOpenAI)

    client = GroqModelClient(api_key="test-key", client=FakeGroqClient())

    assert client.model == "openai/gpt-oss-120b"
    assert client.base_url == GROQ_API_BASE_URL


def test_generate_records_configured_base_url_in_metadata():
    client = GroqModelClient(
        api_key="test-key",
        model="openai/gpt-oss-120b",
        client=FakeGroqClient(response=successful_response()),
        base_url="https://proxy.example.test/v1",
    )

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.metadata["base_url"] == "https://proxy.example.test/v1"


def test_groq_model_client_api_exports_from_core_package():
    assert PublicGroqModelClient is GroqModelClient


def successful_response(text="Hello.", model="openai/gpt-oss-120b"):
    return FakeChatCompletion(
        id="chatcmpl_123",
        model=model,
        choices=[FakeChoice(message=FakeMessage(content=text), finish_reason="stop")],
        usage=FakeUsage(prompt_tokens=9, completion_tokens=3),
    )


class FakeAPIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class FakeGroqClient:
    def __init__(self, response=None, error=None, outcomes=None):
        self.chat = FakeChat(response=response, error=error, outcomes=outcomes)


class FakeChat:
    def __init__(self, response=None, error=None, outcomes=None):
        self.completions = FakeCompletions(
            response=response, error=error, outcomes=outcomes
        )


class FakeCompletions:
    def __init__(self, response=None, error=None, outcomes=None):
        self.response = response
        self.error = error
        self.outcomes = list(outcomes) if outcomes is not None else None
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self.outcomes is not None:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
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
