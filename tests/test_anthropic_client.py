import pytest

import impressions.core.anthropic_client as anthropic_client
from impressions.core import AnthropicModelClient as PublicAnthropicModelClient
from impressions.core.anthropic_client import AnthropicModelClient
from impressions.core.model_client import ModelClient, ModelGenerationError, ModelRequest


def test_anthropic_model_client_implements_model_client_protocol():
    client: ModelClient = AnthropicModelClient(
        api_key="test-key",
        model="claude-test",
        client=FakeAnthropicClient(response=successful_response()),
    )

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.text == "Hello."
    assert response.model == "claude-test"
    assert response.input_tokens == 9
    assert response.output_tokens == 3
    assert response.metadata == {
        "provider_response_id": "msg_123",
        "stop_reason": "end_turn",
    }


def test_generate_translates_model_request_to_messages_api_request():
    sdk_client = FakeAnthropicClient(response=successful_response())
    client = AnthropicModelClient(
        api_key="test-key", model="claude-test", client=sdk_client
    )

    client.generate(
        ModelRequest(
            prompt="Write a function that reverses a string.",
            system_prompt="You are a careful coding assistant.",
            temperature=0.2,
            max_tokens=512,
            metadata={"task_name": "reverse-words"},
        )
    )

    (request_kwargs,) = sdk_client.messages.requests
    assert request_kwargs["model"] == "claude-test"
    assert request_kwargs["messages"] == [
        {"role": "user", "content": "Write a function that reverses a string."}
    ]
    assert request_kwargs["system"] == "You are a careful coding assistant."
    assert request_kwargs["temperature"] == 0.2
    assert request_kwargs["max_tokens"] == 512
    assert request_kwargs["metadata"] == {"user_id": "impressions:reverse-words"}


def test_generate_uses_default_max_tokens_and_omits_system_when_not_configured():
    sdk_client = FakeAnthropicClient(response=successful_response())
    client = AnthropicModelClient(
        api_key="test-key", model="claude-test", client=sdk_client
    )

    client.generate(ModelRequest(prompt="Say hello."))

    (request_kwargs,) = sdk_client.messages.requests
    assert request_kwargs["max_tokens"] == 4096
    assert "system" not in request_kwargs


def test_generate_concatenates_text_blocks_and_ignores_other_block_types():
    response = successful_response(
        blocks=[FakeTextBlock("Hello, "), FakeToolUseBlock(), FakeTextBlock("world.")]
    )
    client = AnthropicModelClient(
        api_key="test-key",
        model="claude-test",
        client=FakeAnthropicClient(response=response),
    )

    assert client.generate(ModelRequest(prompt="Say hello.")).text == "Hello, world."


def test_generate_maps_anthropic_api_errors_to_model_generation_error(monkeypatch):
    class FakeAPIError(Exception):
        pass

    monkeypatch.setattr(anthropic_client.anthropic, "APIError", FakeAPIError)
    sdk_client = FakeAnthropicClient(error=FakeAPIError("provider failed"))
    client = AnthropicModelClient(
        api_key="test-key", model="claude-test", client=sdk_client
    )

    with pytest.raises(ModelGenerationError, match="Anthropic generation failed"):
        client.generate(ModelRequest(prompt="Say hello."))


def test_constructor_passes_api_key_and_timeout_to_anthropic_sdk(monkeypatch):
    created_clients = []

    class FakeAnthropic:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(anthropic_client, "Anthropic", FakeAnthropic)

    AnthropicModelClient(api_key="test-key", model="claude-test", timeout=30.0)

    assert created_clients == [{"api_key": "test-key", "timeout": 30.0}]


def test_constructor_omits_timeout_when_not_provided(monkeypatch):
    created_clients = []

    class FakeAnthropic:
        def __init__(self, **kwargs):
            created_clients.append(kwargs)

    monkeypatch.setattr(anthropic_client, "Anthropic", FakeAnthropic)

    AnthropicModelClient(api_key="test-key", model="claude-test")

    assert created_clients == [{"api_key": "test-key"}]


def test_anthropic_model_client_api_exports_from_core_package():
    assert PublicAnthropicModelClient is AnthropicModelClient


def successful_response(blocks=None, model="claude-test"):
    return FakeMessageResponse(
        content=blocks if blocks is not None else [FakeTextBlock("Hello.")],
        model=model,
        id="msg_123",
        usage=FakeUsage(input_tokens=9, output_tokens=3),
        stop_reason="end_turn",
    )


class FakeAnthropicClient:
    def __init__(self, response=None, error=None):
        self.messages = FakeMessages(response=response, error=error)


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeMessageResponse:
    def __init__(self, content, model, id, usage, stop_reason):
        self.content = content
        self.model = model
        self.id = id
        self.usage = usage
        self.stop_reason = stop_reason


class FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class FakeToolUseBlock:
    def __init__(self):
        self.type = "tool_use"


class FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
